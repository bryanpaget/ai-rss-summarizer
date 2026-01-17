#!/bin/bash
# =============================================================================
# safe-model-load.sh - Safe gateway for LM Studio requests
# =============================================================================
#
# When called:
#   1. Adds request to queue
#   2. Processes queue items one at a time
#   3. Returns response
#   4. Exits
#
# No daemon. No background process. Script runs when called.
#
# =============================================================================

set -euo pipefail

IPC_DIR="${HOME}/.claude/ipc"
QUEUE_FILE="${IPC_DIR}/queue.jsonl"
RESPONSES_DIR="${IPC_DIR}/responses"
PIPES_DIR="${IPC_DIR}/pipes"
LOG_FILE="${IPC_DIR}/gateway.log"
PID_FILE="${IPC_DIR}/processor.pid"
HEARTBEAT_FILE="${IPC_DIR}/processor.heartbeat"
LOCK_FILE="${IPC_DIR}/processor.lock"
STALE_THRESHOLD_SECONDS=10
CONFIG_FILE="${HOME}/.claude/config/safe-auto-load.json"
LM_STUDIO_URL="http://localhost:1234/v1"
VERBOSE="${VERBOSE:-false}"
PIPE_MAX_AGE_SECONDS=3600  # 1 hour

# Adaptive embedding batch size (count-based)
EMBEDDING_BATCH_MIN=1
EMBEDDING_BATCH_MAX=16
EMBEDDING_BATCH_DEFAULT=8  # Start conservative
EMBEDDING_BATCH_FILE="${IPC_DIR}/embedding_batch_size"
EMBEDDING_BATCH_SIZE=$EMBEDDING_BATCH_DEFAULT  # Runtime value
MEMORY_HIGH_THRESHOLD=92  # Don't increase if above this %
MEMORY_LOW_THRESHOLD=85   # Can increase if below this %

# Size-based batching (preferred over count-based)
# Small files batch together, large files go alone
EMBEDDING_MAX_BATCH_BYTES=128000    # Max total bytes per batch (32KB)
EMBEDDING_LARGE_FILE_THRESHOLD=16000 # Files > 8KB go alone or in pairs

# Ensure directories exist
mkdir -p "$IPC_DIR" "$RESPONSES_DIR" "$PIPES_DIR"
touch "$QUEUE_FILE"

# -----------------------------------------------------------------------------
# Logging - errors always go to log file, and to stderr when verbose
# -----------------------------------------------------------------------------

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg" >> "$LOG_FILE"
    if [[ "$VERBOSE" == "true" ]]; then
        echo "$msg" >&2
    fi
}

log_error() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1"
    echo "$msg" >> "$LOG_FILE"
    echo "ERROR: $1" >&2
}

# Capture stderr from a command, log it, and surface if verbose
log_stderr() {
    local err
    err=$(cat)
    if [[ -n "$err" ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] STDERR: $err" >> "$LOG_FILE"
        if [[ "$VERBOSE" == "true" ]]; then
            echo "$err" >&2
        fi
    fi
}

# -----------------------------------------------------------------------------
# Pipe management
# -----------------------------------------------------------------------------

cleanup_old_pipes() {
    # Remove pipes older than PIPE_MAX_AGE_SECONDS (1 hour)
    # Log error for each stale pipe found
    local now
    now=$(date +%s)

    shopt -s nullglob
    for pipe in "$PIPES_DIR"/*.pipe; do
        [[ -e "$pipe" ]] || continue

        local mtime
        # Try Linux stat format first, then macOS format
        if mtime=$(stat -c %Y "$pipe" 2>&1); then
            :
        elif mtime=$(stat -f %m "$pipe" 2>&1); then
            :
        else
            log "Could not get mtime for $pipe: $mtime"
            continue
        fi

        if [[ -n "$mtime" ]]; then
            local age=$((now - mtime))
            if [[ $age -gt $PIPE_MAX_AGE_SECONDS ]]; then
                log_error "Stale pipe found (age: ${age}s): $pipe - removing"
                rm -f "$pipe"
            fi
        fi
    done
    shopt -u nullglob
}

create_request_pipe() {
    local request_id="$1"
    local pipe_path="${PIPES_DIR}/${request_id}.pipe"

    # Create the named pipe
    if ! mkfifo "$pipe_path"; then
        log_error "Failed to create pipe: $pipe_path"
        return 1
    fi

    echo "$pipe_path"
}

# -----------------------------------------------------------------------------
# Processor lifecycle management
# -----------------------------------------------------------------------------

is_processor_alive() {
    # Check if processor is alive using PID file
    # Returns 0 if alive, 1 if dead or no PID file
    if [[ ! -f "$PID_FILE" ]]; then
        return 1
    fi

    local pid
    pid=$(cat "$PID_FILE")

    if [[ -z "$pid" ]]; then
        return 1
    fi

    # Check if process exists
    if kill -0 "$pid" 2>> "$LOG_FILE"; then
        return 0
    else
        return 1
    fi
}

is_heartbeat_stale() {
    # Check if heartbeat file hasn't been updated in STALE_THRESHOLD_SECONDS
    # Returns 0 if stale, 1 if recent
    if [[ ! -f "$HEARTBEAT_FILE" ]]; then
        return 0  # No heartbeat = stale
    fi

    local now mtime age
    now=$(date +%s)

    # Get heartbeat file mtime
    if mtime=$(stat -c %Y "$HEARTBEAT_FILE" 2>&1); then
        :
    elif mtime=$(stat -f %m "$HEARTBEAT_FILE" 2>&1); then
        :
    else
        return 0  # Can't get mtime = assume stale
    fi

    age=$((now - mtime))

    if [[ $age -gt $STALE_THRESHOLD_SECONDS ]]; then
        return 0  # Stale
    else
        return 1  # Recent
    fi
}

should_spawn_processor() {
    # Determine if we need to spawn a new processor
    # Returns 0 if should spawn, 1 if processor already running

    # Queue empty = definitely spawn
    if [[ ! -s "$QUEUE_FILE" ]]; then
        log "Queue empty, will spawn processor"
        return 0
    fi

    # Queue not empty - check if processor is working
    if ! is_heartbeat_stale; then
        # Recent heartbeat, processor is actively completing work
        log "Queue not empty, recent heartbeat, processor alive"
        return 1
    fi

    # Heartbeat is stale - check PID
    log "Queue not empty but heartbeat stale, checking PID"

    if is_processor_alive; then
        log "Processor PID still alive, not spawning"
        return 1
    else
        log "Processor appears dead, will spawn new one"
        # Clean up stale PID file
        rm -f "$PID_FILE"
        return 0
    fi
}

# -----------------------------------------------------------------------------
# Config helpers
# -----------------------------------------------------------------------------

get_config() {
    local key="$1" default="$2"
    if [[ -f "$CONFIG_FILE" ]]; then
        local val err
        val=$(jq -r ".$key // empty" "$CONFIG_FILE" 2> >(log_stderr)) || {
            log "Config read failed for key: $key"
            echo "$default"
            return
        }
        [[ -n "$val" ]] && echo "$val" || echo "$default"
    else
        echo "$default"
    fi
}

# -----------------------------------------------------------------------------
# Adaptive batch sizing for embeddings
# -----------------------------------------------------------------------------

get_embedding_batch_size() {
    # Read current batch size from file, or return default
    if [[ -f "$EMBEDDING_BATCH_FILE" ]]; then
        local size
        size=$(cat "$EMBEDDING_BATCH_FILE" 2>/dev/null)
        if [[ "$size" =~ ^[0-9]+$ ]] && [[ $size -ge $EMBEDDING_BATCH_MIN ]] && [[ $size -le $EMBEDDING_BATCH_MAX ]]; then
            echo "$size"
            return
        fi
    fi
    echo "$EMBEDDING_BATCH_DEFAULT"
}

set_embedding_batch_size() {
    # Write batch size to file (persist across invocations)
    local size="$1"
    # Clamp to valid range
    if [[ $size -lt $EMBEDDING_BATCH_MIN ]]; then
        size=$EMBEDDING_BATCH_MIN
    elif [[ $size -gt $EMBEDDING_BATCH_MAX ]]; then
        size=$EMBEDDING_BATCH_MAX
    fi
    echo "$size" > "$EMBEDDING_BATCH_FILE"
    log "Batch size set to $size"
}

get_memory_usage() {
    # Get memory usage percentage (0-100)
    # Works on Windows (MSYS/Git Bash), Linux, and macOS
    local mem_percent=50  # Default if we can't determine

    if [[ -f /proc/meminfo ]]; then
        # Linux
        local total free available
        total=$(grep '^MemTotal:' /proc/meminfo | awk '{print $2}')
        available=$(grep '^MemAvailable:' /proc/meminfo | awk '{print $2}')
        if [[ -z "$available" ]]; then
            # Older kernels without MemAvailable
            free=$(grep '^MemFree:' /proc/meminfo | awk '{print $2}')
            local buffers cached
            buffers=$(grep '^Buffers:' /proc/meminfo | awk '{print $2}')
            cached=$(grep '^Cached:' /proc/meminfo | awk '{print $2}')
            available=$((free + buffers + cached))
        fi
        if [[ -n "$total" ]] && [[ "$total" -gt 0 ]]; then
            local used=$((total - available))
            mem_percent=$((used * 100 / total))
        fi
    elif command -v wmic >/dev/null 2>&1; then
        # Windows (MSYS/Git Bash with wmic)
        local total free
        total=$(wmic OS get TotalVisibleMemorySize /value 2>/dev/null | grep -o '[0-9]*')
        free=$(wmic OS get FreePhysicalMemory /value 2>/dev/null | grep -o '[0-9]*')
        if [[ -n "$total" ]] && [[ "$total" -gt 0 ]] && [[ -n "$free" ]]; then
            local used=$((total - free))
            mem_percent=$((used * 100 / total))
        fi
    elif command -v vm_stat >/dev/null 2>&1; then
        # macOS
        local page_size free_pages total_pages
        page_size=$(pagesize 2>/dev/null || echo 4096)
        free_pages=$(vm_stat | grep 'Pages free' | awk '{print $3}' | tr -d '.')
        # This is approximate - macOS memory accounting is complex
        if [[ -n "$free_pages" ]]; then
            local total_mem
            total_mem=$(sysctl -n hw.memsize 2>/dev/null)
            if [[ -n "$total_mem" ]] && [[ "$total_mem" -gt 0 ]]; then
                local free_mem=$((free_pages * page_size))
                local used_mem=$((total_mem - free_mem))
                mem_percent=$((used_mem * 100 / total_mem))
            fi
        fi
    fi

    # Clamp to 0-100
    if [[ $mem_percent -lt 0 ]]; then
        mem_percent=0
    elif [[ $mem_percent -gt 100 ]]; then
        mem_percent=100
    fi

    echo "$mem_percent"
}

check_memory_before_batch() {
    # Called BEFORE dispatching a batch - back off if memory is critical
    # Returns the safe batch size to use (may be reduced from current)
    local current_size
    current_size=$(get_embedding_batch_size)
    local mem_usage
    mem_usage=$(get_memory_usage)

    # If memory > 90%, keep decrementing until below threshold or at minimum
    while [[ $mem_usage -gt $MEMORY_HIGH_THRESHOLD ]] && [[ $current_size -gt $EMBEDDING_BATCH_MIN ]]; do
        local new_size=$((current_size - 1))
        log "CRITICAL: Memory ${mem_usage}% > ${MEMORY_HIGH_THRESHOLD}%, reducing batch size: $current_size -> $new_size"
        set_embedding_batch_size "$new_size"
        current_size=$new_size

        # Re-check memory (give system a moment)
        sleep 0.5
        mem_usage=$(get_memory_usage)
    done

    if [[ $mem_usage -gt $MEMORY_HIGH_THRESHOLD ]]; then
        log "WARNING: Memory still at ${mem_usage}% but batch size at minimum ($EMBEDDING_BATCH_MIN)"
    fi

    echo "$current_size"
}

adjust_batch_size_on_success() {
    # After successful batch, conservatively increase batch size for better GPU utilization
    # Small embedding models can handle large batches efficiently
    local current_size
    current_size=$(get_embedding_batch_size)
    local mem_usage
    mem_usage=$(get_memory_usage)

    if [[ $mem_usage -lt $MEMORY_LOW_THRESHOLD ]]; then
        # Memory has headroom - increase batch size aggressively
        if [[ $current_size -lt $EMBEDDING_BATCH_MAX ]]; then
            # Increment batch size conservatively (+2) (capped at max)
            local new_size=$((current_size + 2))
            if [[ $new_size -gt $EMBEDDING_BATCH_MAX ]]; then
                new_size=$EMBEDDING_BATCH_MAX
            fi
            log "Memory ${mem_usage}% < ${MEMORY_LOW_THRESHOLD}%, increasing batch (+2): $current_size -> $new_size"
            set_embedding_batch_size "$new_size"
        else
            log "Memory ${mem_usage}%, batch size at max ($current_size)"
        fi
    elif [[ $mem_usage -gt $MEMORY_HIGH_THRESHOLD ]]; then
        # Memory critically high - decrease batch size
        if [[ $current_size -gt $EMBEDDING_BATCH_MIN ]]; then
            local new_size=$EMBEDDING_BATCH_MIN  # Reset to min, not halve
            if [[ $new_size -lt $EMBEDDING_BATCH_MIN ]]; then
                new_size=$EMBEDDING_BATCH_MIN
            fi
            log "Memory ${mem_usage}% > ${MEMORY_HIGH_THRESHOLD}%, halving batch: $current_size -> $new_size"
            set_embedding_batch_size "$new_size"
        fi
    else
        log "Memory ${mem_usage}%, batch size $current_size stable"
    fi
}

adjust_batch_size_on_failure() {
    # After failed batch, decrease batch size
    local current_size
    current_size=$(get_embedding_batch_size)

    if [[ $current_size -gt $EMBEDDING_BATCH_MIN ]]; then
        # Reset to minimum on failure (crash = need to be very conservative)
        local new_size=$EMBEDDING_BATCH_MIN  # Reset to min, not halve
        if [[ $new_size -lt $EMBEDDING_BATCH_MIN ]]; then
            new_size=$EMBEDDING_BATCH_MIN
        fi
        log "Batch failed, resetting to minimum: $current_size -> $new_size"
        set_embedding_batch_size "$new_size"
    else
        log "Batch failed but already at minimum size $EMBEDDING_BATCH_MIN"
    fi
}

# -----------------------------------------------------------------------------
# LM Studio communication
# -----------------------------------------------------------------------------

check_lm_studio() {
    curl -s --max-time 5 "$LM_STUDIO_URL/models" >/dev/null 2> >(log_stderr)
}

# Cache for lms ps results (reduces redundant API calls)
LMS_PS_CACHE_FILE="${IPC_DIR}/lms_ps_cache.json"
LMS_PS_CACHE_TTL=2  # seconds

get_lms_ps_cached() {
    # Return cached lms ps result if recent, otherwise refresh
    local now
    now=$(date +%s)

    if [[ -f "$LMS_PS_CACHE_FILE" ]]; then
        local cache_time
        cache_time=$(stat -c %Y "$LMS_PS_CACHE_FILE" 2>/dev/null || stat -f %m "$LMS_PS_CACHE_FILE" 2>/dev/null || echo 0)
        local age=$((now - cache_time))
        if [[ $age -lt $LMS_PS_CACHE_TTL ]]; then
            cat "$LMS_PS_CACHE_FILE"
            return
        fi
    fi

    # Refresh cache
    local result
    if command -v lms >/dev/null 2>&1; then
        result=$(lms ps --json 2> >(log_stderr))
    else
        result=$(curl -s "$LM_STUDIO_URL/models" 2> >(log_stderr))
    fi
    echo "$result" > "$LMS_PS_CACHE_FILE"
    echo "$result"
}

invalidate_lms_ps_cache() {
    rm -f "$LMS_PS_CACHE_FILE"
}

get_loaded_model() {
    if command -v lms >/dev/null 2>&1; then
        get_lms_ps_cached | jq -r '.[0].path // empty' | tr -d '\r'
    else
        get_lms_ps_cached | jq -r '.data[0].id // empty'
    fi
}

get_loaded_model_identifier() {
    if command -v lms >/dev/null 2>&1; then
        get_lms_ps_cached | jq -r '.[0].identifier // empty' | tr -d '\r'
    else
        get_lms_ps_cached | jq -r '.data[0].id // empty'
    fi
}

get_current_model_type() {
    # Returns: text, vision, embedding, or empty if no model loaded
    local current
    current=$(get_loaded_model)

    if [[ -z "$current" ]]; then
        echo ""
        return
    fi

    local text_model vision_model embedding_model
    text_model=$(get_config "text_model" "")
    vision_model=$(get_config "vision_model" "")
    embedding_model=$(get_config "embedding_model" "")

    if [[ "$current" == "$text_model" ]]; then
        echo "text"
    elif [[ "$current" == "$vision_model" ]]; then
        echo "vision"
    elif [[ "$current" == "$embedding_model" ]]; then
        echo "embedding"
    else
        # Unknown model, check if vision (can handle text)
        echo "unknown"
    fi
}

wait_for_unload() {
    local max_wait=30
    local waited=0
    log "Waiting for unload to complete..."
    while [[ $waited -lt $max_wait ]]; do
        local loaded
        loaded=$(lms ps --json 2> >(log_stderr) | jq -r '.[0].path // empty' | tr -d '\r')
        if [[ -z "$loaded" ]]; then
            log "Unload confirmed"
            return 0
        fi
        sleep 1
        ((waited++))
    done
    log_error "Timeout waiting for unload after ${max_wait}s"
    return 1
}

load_model() {
    local model="$1"
    local ttl_seconds
    ttl_seconds=$(get_config "ttl_seconds" "300")

    log "Loading model: $model (TTL: ${ttl_seconds}s)"

    # ALL lms output goes to log file only. Never stdout. Never stderr.
    if ! lms load "$model" --ttl "$ttl_seconds" --yes >> "$LOG_FILE" 2>&1; then
        log_error "Failed to load model: $model"
        return 1
    fi

    sleep 2
    invalidate_lms_ps_cache  # Model changed, invalidate cache
    log "Model loaded: $model"
    return 0
}

ensure_model_for_request() {
    local request_type="$1"

    if ! check_lm_studio; then
        log_error "LM Studio is not reachable. Check that the server toggle is ON in LM Studio."
        return 1
    fi

    local current
    current=$(get_loaded_model)

    local text_model vision_model embedding_model
    text_model=$(get_config "text_model" "")
    vision_model=$(get_config "vision_model" "")
    embedding_model=$(get_config "embedding_model" "")

    local target_model
    case "$request_type" in
        embedding)
            target_model="$embedding_model"
            ;;
        vision)
            target_model="$vision_model"
            ;;
        text)
            target_model="$text_model"
            ;;
        *)
            log_error "Unknown request type: $request_type"
            return 1
            ;;
    esac

    if [[ -z "$target_model" ]]; then
        log_error "No model configured for type: $request_type"
        return 1
    fi

    local need_switch=false

    if [[ -z "$current" ]]; then
        need_switch=true
        log "No model loaded, need to load $target_model"
    elif [[ "$current" == "$target_model" ]]; then
        need_switch=false
        log "Current model '$current' is target, no switch needed"
    elif [[ "$current" == "$vision_model" && "$request_type" == "text" ]]; then
        need_switch=false
        log "Vision model '$current' can handle text, no switch needed"
    elif [[ "$request_type" == "text" && -n "$current" && "$current" != "$embedding_model" ]]; then
        need_switch=false
        log "Current model '$current' can handle text, no switch needed"
    else
        need_switch=true
        log "Current '$current' cannot handle '$request_type', switching to '$target_model'"
    fi

    if [[ "$need_switch" == "true" ]]; then
        if [[ -n "$current" ]]; then
            local current_id
            current_id=$(get_loaded_model_identifier)
            log "Unloading current model: $current (id: $current_id)"
            lms unload "$current_id" >> "$LOG_FILE" 2>&1 || log "Unload command returned non-zero"
            invalidate_lms_ps_cache  # Model changed, invalidate cache
            if ! wait_for_unload; then
                log_error "Cannot proceed - previous model still loaded"
                return 1
            fi
        fi

        if ! load_model "$target_model"; then
            return 1
        fi
    fi

    if [[ "$need_switch" == "false" && -n "$current" ]]; then
        echo "$current"
    else
        echo "$target_model"
    fi
    return 0
}

# -----------------------------------------------------------------------------
# Request processing
# -----------------------------------------------------------------------------

dispatch_embedding_batch() {
    # Dispatch a BATCH of embedding requests in a single API call
    # LM Studio supports array input: {"input": ["text1", "text2", ...]}
    # This is MUCH more efficient than individual requests
    #
    # Args: model request_file1 request_file2 ... request_fileN
    local model="$1"
    shift
    local request_files=("$@")
    local count=${#request_files[@]}

    if [[ $count -eq 0 ]]; then
        return 0
    fi

    log "Dispatching embedding batch ($count items)"

    local batch_id="batch_$(date +%s)_$$"
    local payload_file="${IPC_DIR}/payload_${batch_id}.json"
    local response_file="${IPC_DIR}/response_${batch_id}.json"

    # Build array of prompts and track metadata
    local prompts_file="${IPC_DIR}/prompts_${batch_id}.json"
    echo "[]" > "$prompts_file"

    local request_ids=()
    local file_paths=()
    local queued_times=()

    for rf in "${request_files[@]}"; do
        local req_id file_path queued_at prompt
        req_id=$(jq -r '.id' "$rf")
        file_path=$(jq -r '.file_path // ""' "$rf")
        queued_at=$(jq -r '.queued_at // 0' "$rf")
        [[ -z "$file_path" ]] && file_path="${RESPONSES_DIR}/${req_id}.json"

        request_ids+=("$req_id")
        file_paths+=("$file_path")
        queued_times+=("$queued_at")

        # Append prompt to array (using jq to handle escaping properly)
        jq -c --slurpfile existing "$prompts_file" \
            '.prompt as $p | $existing[0] + [$p]' "$rf" > "${prompts_file}.tmp"
        mv "${prompts_file}.tmp" "$prompts_file"
    done

    # Build final payload with array of prompts
    jq -nc --slurpfile prompts "$prompts_file" \
        --arg model "$model" \
        '{model: $model, input: $prompts[0]}' > "$payload_file"

    rm -f "$prompts_file"

    local dispatch_at
    dispatch_at=$(date +%s%3N)

    # Send single request for all embeddings
    local timeout=600
    if curl -sS --fail --max-time "$timeout" \
        -H "Content-Type: application/json" \
        -d @"$payload_file" \
        "$LM_STUDIO_URL/embeddings" > "$response_file" 2>> "$LOG_FILE"; then

        local completed_at
        completed_at=$(date +%s%3N)

        # Parse response and distribute to each request's file
        # Response format: {"data": [{"embedding": [...], "index": 0}, ...]}
        local i=0
        for req_id in "${request_ids[@]}"; do
            local file_path="${file_paths[$i]}"
            local queued_at="${queued_times[$i]}"

            # Calculate timing
            local queue_time_ms=$((dispatch_at - queued_at))
            local process_time_ms=$((completed_at - dispatch_at))
            local total_time_ms=$((completed_at - queued_at))

            # Extract this request's embedding and write to its response file
            jq --argjson idx "$i" \
               --argjson queued_at "$queued_at" \
               --argjson dispatch_at "$dispatch_at" \
               --argjson completed_at "$completed_at" \
               --argjson queue_time_ms "$queue_time_ms" \
               --argjson process_time_ms "$process_time_ms" \
               --argjson total_time_ms "$total_time_ms" \
               '{
                   data: [{embedding: .data[$idx].embedding, index: 0}],
                   model: .model,
                   _timing: {
                       queued_at: $queued_at,
                       dispatch_at: $dispatch_at,
                       completed_at: $completed_at,
                       queue_time_ms: $queue_time_ms,
                       process_time_ms: $process_time_ms,
                       total_time_ms: $total_time_ms
                   }
               }' "$response_file" > "$file_path"

            log "Request $req_id completed (queue: ${queue_time_ms}ms, process: ${process_time_ms}ms)"
            i=$((i + 1))
        done

        log "Embedding batch complete ($count items in $((completed_at - dispatch_at))ms)"

        # Adaptive sizing: consider increasing batch size after success
        adjust_batch_size_on_success
    else
        log_error "Embedding batch failed"

        # Adaptive sizing: decrease batch size after failure
        adjust_batch_size_on_failure

        # Write error to each request's file
        for i in "${!request_ids[@]}"; do
            echo '{"error": "Batch request failed"}' > "${file_paths[$i]}"
        done
    fi

    # Cleanup
    rm -f "$payload_file" "$response_file"
    for rf in "${request_files[@]}"; do
        rm -f "$rf"
    done

    return 0
}

dispatch_request_to_lm_studio() {
    # Dispatches request to LM Studio - curl writes directly to pipe and file
    # Returns immediately - does not wait for LM Studio response
    # Model must already be loaded - this function does not manage models
    # Arg 1: PATH to request JSON file (not the JSON itself - avoids arg limit)
    # Arg 2: model identifier
    local request_file="$1"
    local model="$2"

    # Extract small metadata fields using jq reading from FILE (safe - results are small)
    local request_id request_type system_prompt temperature pipe_path file_path queued_at
    request_id=$(jq -r '.id' "$request_file")
    request_type=$(jq -r '.type' "$request_file")
    system_prompt=$(jq -r '.system // ""' "$request_file")
    temperature=$(jq -r '.temperature // "0.0"' "$request_file")
    pipe_path=$(jq -r '.pipe_path // ""' "$request_file")
    file_path=$(jq -r '.file_path // ""' "$request_file")
    queued_at=$(jq -r '.queued_at // 0' "$request_file")

    # Default file path if not in request
    [[ -z "$file_path" ]] && file_path="${RESPONSES_DIR}/${request_id}.json"

    local timeout=600
    local endpoint
    local payload_file="${IPC_DIR}/payload_${request_id}.json"

    # Build payload file using jq file-to-file transformation (no variables with large content)
    if [[ "$request_type" == "embedding" ]]; then
        endpoint="$LM_STUDIO_URL/embeddings"
        # Transform request file to embedding payload file
        jq --arg model "$model" \
            '{model: $model, input: .prompt}' \
            "$request_file" > "$payload_file"
    else
        endpoint="$LM_STUDIO_URL/chat/completions"
        # Transform request file to chat payload file
        jq --arg model "$model" \
            '{
                model: $model,
                messages: (
                    [if .system != "" then {role: "system", content: .system} else empty end] +
                    [{role: "user", content: .prompt}]
                ),
                temperature: ((.temperature // "0.7") | tonumber)
            }' "$request_file" > "$payload_file"
    fi

    # Dispatch curl - writes to pipe OR file based on mode
    # Curl runs in background, processor doesn't wait
    (
        local output_path
        if [[ -n "$pipe_path" ]]; then
            output_path="$pipe_path"
        else
            output_path="$file_path"
        fi

        # Record dispatch time (when LM Studio processing starts)
        local dispatch_at
        dispatch_at=$(date +%s%3N)

        # Use temp file for FILE mode so we can add timing metadata
        local temp_output="${output_path}.tmp"

        if curl -sS --fail --max-time "$timeout" \
            -H "Content-Type: application/json" \
            -d @"$payload_file" \
            "$endpoint" > "$temp_output" 2>> "$LOG_FILE"; then

            # Record completion time
            local completed_at
            completed_at=$(date +%s%3N)

            # Add timing metadata to response (FILE mode only, not pipes)
            if [[ -z "$pipe_path" ]]; then
                # Calculate timing in milliseconds
                local queue_time_ms=$((dispatch_at - queued_at))
                local process_time_ms=$((completed_at - dispatch_at))
                local total_time_ms=$((completed_at - queued_at))

                # Merge timing into response JSON
                jq --argjson queued_at "$queued_at" \
                   --argjson dispatch_at "$dispatch_at" \
                   --argjson completed_at "$completed_at" \
                   --argjson queue_time_ms "$queue_time_ms" \
                   --argjson process_time_ms "$process_time_ms" \
                   --argjson total_time_ms "$total_time_ms" \
                   '. + {_timing: {queued_at: $queued_at, dispatch_at: $dispatch_at, completed_at: $completed_at, queue_time_ms: $queue_time_ms, process_time_ms: $process_time_ms, total_time_ms: $total_time_ms}}' \
                   "$temp_output" > "$output_path"
                rm -f "$temp_output"
            else
                # Pipe mode - just move temp to output (can't add metadata to stream)
                mv "$temp_output" "$output_path"
            fi

            log "Request $request_id completed (queue: ${queue_time_ms:-?}ms, process: ${process_time_ms:-?}ms)"
        else
            local error_msg="{\"error\": \"Request failed\"}"
            log_error "Request $request_id failed"
            echo "$error_msg" > "$output_path"
            rm -f "$temp_output"
        fi

        # Clean up payload file
        rm -f "$payload_file"
    ) &

    log "Dispatched $request_id to LM Studio (pid: $!)"
    return 0
}
process_single_request() {
    # Legacy function for single request processing (with model management)
    local request_json="$1"
    local request_id request_type

    request_id=$(echo "$request_json" | jq -r '.id')
    request_type=$(echo "$request_json" | jq -r '.type')

    log "Processing request $request_id (type: $request_type)"

    local model
    if ! model=$(ensure_model_for_request "$request_type"); then
        echo '{"error": "LM Studio is not reachable. Check that the server toggle is ON in LM Studio."}' > "${RESPONSES_DIR}/${request_id}.json"
        return 1
    fi

    dispatch_request_to_lm_studio "$request_json" "$model"
    log "Dispatched request $request_id"
    return 0
}

sort_queue_by_type() {
    # Sort queue by priority first, then by type:
    # 1. HIGH priority requests first (interactive: Oracle, agents)
    # 2. Within each priority: group by type to minimize model switches
    # Uses jq streaming to avoid shell variable limits with large prompts

    if [[ ! -s "$QUEUE_FILE" ]]; then
        return
    fi

    local current_type
    current_type=$(get_current_model_type)

    log "Sorting queue by priority and type (current model: ${current_type:-none})"

    # Step 1: Separate by priority
    local temp_high="${QUEUE_FILE}.high"
    local temp_low="${QUEUE_FILE}.low"

    jq -c 'select(.priority == "high")' "$QUEUE_FILE" > "$temp_high" 2>/dev/null || true
    jq -c 'select(.priority != "high")' "$QUEUE_FILE" > "$temp_low" 2>/dev/null || true

    # Step 2: Within each priority, sort by type compatibility
    local temp_high_current="${QUEUE_FILE}.high.current"
    local temp_high_other="${QUEUE_FILE}.high.other"
    local temp_low_current="${QUEUE_FILE}.low.current"
    local temp_low_other="${QUEUE_FILE}.low.other"

    if [[ -z "$current_type" || "$current_type" == "unknown" ]]; then
        # No model loaded - just use priority order, no type sorting
        cat "$temp_high" "$temp_low" > "$QUEUE_FILE"
    else
        # Sort each priority group by type compatibility
        if [[ "$current_type" == "vision" ]]; then
            # Vision can handle text
            jq -c 'select(.type == "vision" or .type == "text")' "$temp_high" > "$temp_high_current" 2>/dev/null || true
            jq -c 'select(.type != "vision" and .type != "text")' "$temp_high" > "$temp_high_other" 2>/dev/null || true
            jq -c 'select(.type == "vision" or .type == "text")' "$temp_low" > "$temp_low_current" 2>/dev/null || true
            jq -c 'select(.type != "vision" and .type != "text")' "$temp_low" > "$temp_low_other" 2>/dev/null || true
        else
            jq -c --arg t "$current_type" 'select(.type == $t)' "$temp_high" > "$temp_high_current" 2>/dev/null || true
            jq -c --arg t "$current_type" 'select(.type != $t)' "$temp_high" > "$temp_high_other" 2>/dev/null || true
            jq -c --arg t "$current_type" 'select(.type == $t)' "$temp_low" > "$temp_low_current" 2>/dev/null || true
            jq -c --arg t "$current_type" 'select(.type != $t)' "$temp_low" > "$temp_low_other" 2>/dev/null || true
        fi

        # Recombine: HIGH priority first (current type, then other types), then LOW
        cat "$temp_high_current" "$temp_high_other" "$temp_low_current" "$temp_low_other" > "$QUEUE_FILE"
        rm -f "$temp_high_current" "$temp_high_other" "$temp_low_current" "$temp_low_other"
    fi

    rm -f "$temp_high" "$temp_low"

    local count high_count
    count=$(wc -l < "$QUEUE_FILE" | tr -d ' ')
    high_count=$(jq -c 'select(.priority == "high")' "$QUEUE_FILE" 2>/dev/null | wc -l | tr -d ' ')
    log "Queue sorted ($count items, $high_count high priority)"
}

is_type_compatible() {
    # Check if request type is compatible with current batch type
    local batch_type="$1"
    local request_type="$2"

    if [[ "$request_type" == "$batch_type" ]]; then
        return 0
    fi
    # Vision model can handle text requests
    if [[ "$batch_type" == "vision" && "$request_type" == "text" ]]; then
        return 0
    fi
    return 1
}

pop_queue_item_to_file() {
    # Atomically pop first item from queue, write to file
    # Arg 1: target file path to write the item
    # Returns 1 if queue empty
    local target_file="$1"


    if [[ ! -s "$QUEUE_FILE" ]]; then
        return 1
    fi

    # Write first line directly to target file (no variable expansion)
    head -n 1 "$QUEUE_FILE" > "$target_file"

    if [[ ! -s "$target_file" ]]; then
        return 1
    fi

    # Remove first line from queue
    local temp="${QUEUE_FILE}.tmp"
    tail -n +2 "$QUEUE_FILE" > "$temp" || log "Queue update warning"
    mv "$temp" "$QUEUE_FILE"

    # Add to history (cat from file, not variable)
    cat "$target_file" >> "${IPC_DIR}/history.jsonl"

    return 0
}

get_prompt_size() {
    # Get character count of prompt from request file
    # FAILS LOUDLY if reading fails - no silent fallbacks
    local request_file="$1"
    jq -r '.prompt | length' "$request_file"
}

has_high_priority_waiting() {
    # Check if there are any high-priority items waiting in the queue
    # Returns 0 if high-priority waiting, 1 if not
    # Used by low-priority batch processing to yield to high-priority
    if [[ ! -s "$QUEUE_FILE" ]]; then
        return 1
    fi

    # Check if any line has priority=high
    if grep -q '"priority"[[:space:]]*:[[:space:]]*"high"' "$QUEUE_FILE" 2>/dev/null; then
        return 0
    fi
    return 1
}

process_batch() {
    # Process a batch of same-type requests
    # For embeddings: batches multiple into single API call (much faster)
    # For text/vision: dispatches individually with in-flight tracking
    # PRIORITY: If processing low-priority items and high-priority arrives, yield immediately
    local batch_type="$1"
    local model="$2"
    local count=0
    local pids=()  # Track curl PIDs to wait for
    local request_files=()  # Track request files for cleanup
    local embedding_batch_files=()  # Collect embedding requests for batching
    local embedding_batch_bytes=0   # Track total bytes in current batch
    local in_flight_bytes=0
    local batch_priority=""  # Track priority of items in this batch
    local context_size
    context_size=$(get_config "context_size" "32768")
    local max_in_flight=$((context_size / 2))

    log "Processing batch (type: $batch_type, model: $model, max_in_flight: $max_in_flight)"

    while true; do
        # Peek at next item type (head | jq is safe - doesn't store full content)
        if [[ ! -s "$QUEUE_FILE" ]]; then
            break
        fi

        local peek_file="${IPC_DIR}/peek_$$.json"
        head -n 1 "$QUEUE_FILE" > "$peek_file"
        local next_type next_priority
        next_type=$(jq -r '.type // empty' "$peek_file")
        next_priority=$(jq -r '.priority // "low"' "$peek_file")
        rm -f "$peek_file"

        if ! is_type_compatible "$batch_type" "$next_type"; then
            # Different type, end this batch
            break
        fi

        # Pop to file
        local request_file="${IPC_DIR}/request_${count}_$$.json"
        if ! pop_queue_item_to_file "$request_file"; then
            break
        fi

        # Track batch priority from first item
        if [[ -z "$batch_priority" ]]; then
            batch_priority="$next_priority"
            log "Batch priority: $batch_priority"
        fi

        # Check if this was the last item IMMEDIATELY after pop
        local is_last=false
        if [[ ! -s "$QUEUE_FILE" ]]; then
            is_last=true
        fi

        # EMBEDDING: Collect for batching (don't dispatch yet)
        # Uses SIZE-BASED batching: small files batch together, large files go alone
        if [[ "$batch_type" == "embedding" ]]; then
            local file_size
            file_size=$(get_prompt_size "$request_file")
            local is_large_file=false
            [[ $file_size -gt $EMBEDDING_LARGE_FILE_THRESHOLD ]] && is_large_file=true

            # If this is a large file and we have pending small files, dispatch small files first
            if [[ "$is_large_file" == "true" && ${#embedding_batch_files[@]} -gt 0 ]]; then
                log "Large file (${file_size}B) - dispatching ${#embedding_batch_files[@]} pending small files first"
                dispatch_embedding_batch "$model" "${embedding_batch_files[@]}"
                embedding_batch_files=()
                embedding_batch_bytes=0
            fi

            # If adding this file would exceed batch size limit, dispatch current batch first
            if [[ $((embedding_batch_bytes + file_size)) -gt $EMBEDDING_MAX_BATCH_BYTES && ${#embedding_batch_files[@]} -gt 0 ]]; then
                log "Batch full (${embedding_batch_bytes}B + ${file_size}B > ${EMBEDDING_MAX_BATCH_BYTES}B) - dispatching"
                dispatch_embedding_batch "$model" "${embedding_batch_files[@]}"
                embedding_batch_files=()
                embedding_batch_bytes=0
            fi

            # Add file to batch
            embedding_batch_files+=("$request_file")
            embedding_batch_bytes=$((embedding_batch_bytes + file_size))
            count=$((count + 1))
            touch "$HEARTBEAT_FILE"

            # Check memory and get safe count limit (may reduce if memory > 90%)
            EMBEDDING_BATCH_SIZE=$(check_memory_before_batch)

            # Dispatch if: large file alone, count limit reached, or last item
            local should_dispatch=false
            [[ "$is_large_file" == "true" ]] && should_dispatch=true
            [[ ${#embedding_batch_files[@]} -ge $EMBEDDING_BATCH_SIZE ]] && should_dispatch=true
            [[ "$is_last" == "true" ]] && should_dispatch=true

            if [[ "$should_dispatch" == "true" ]]; then
                log "Dispatching batch of ${#embedding_batch_files[@]} (${embedding_batch_bytes}B, large=$is_large_file)"
                dispatch_embedding_batch "$model" "${embedding_batch_files[@]}"
                embedding_batch_files=()
                embedding_batch_bytes=0

                # PRIORITY CHECK: If we're low-priority and high-priority is waiting, yield
                if [[ "$batch_priority" == "low" ]] && has_high_priority_waiting; then
                    log "HIGH PRIORITY WAITING - yielding low-priority embedding batch after $count items"
                    break
                fi
            fi

            if [[ "$is_last" == "true" ]]; then
                log "Last embedding item processed, batch complete"
                break
            fi
            continue
        fi

        # TEXT/VISION: Individual dispatch with in-flight tracking
        request_files+=("$request_file")

        # Get size of this request
        local request_size
        request_size=$(get_prompt_size "$request_file")

        # If adding this would exceed max, wait for in-flight to complete first
        if [[ $((in_flight_bytes + request_size)) -gt $max_in_flight && ${#pids[@]} -gt 0 ]]; then
            log "In-flight ($in_flight_bytes) + this ($request_size) > max ($max_in_flight), waiting..."
            for pid in "${pids[@]}"; do
                wait "$pid" || true
            done
            pids=()
            in_flight_bytes=0
            log "In-flight requests completed, continuing"
        fi

        dispatch_request_to_lm_studio "$request_file" "$model"
        pids+=($!)  # Capture background curl PID
        in_flight_bytes=$((in_flight_bytes + request_size))
        count=$((count + 1))
        touch "$HEARTBEAT_FILE"

        # PRIORITY CHECK: If we're low-priority and high-priority is waiting, yield
        # Note: We don't cancel in-flight requests, just stop pulling more low-priority items
        if [[ "$batch_priority" == "low" ]] && has_high_priority_waiting; then
            log "HIGH PRIORITY WAITING - yielding low-priority text/vision batch after $count items"
            break
        fi

        # If this was the last item, commit to exit
        if [[ "$is_last" == "true" ]]; then
            log "Last item dispatched, processor committing to exit"
            break
        fi
    done

    # Dispatch any remaining embeddings (shouldn't happen but just in case)
    if [[ ${#embedding_batch_files[@]} -gt 0 ]]; then
        dispatch_embedding_batch "$model" "${embedding_batch_files[@]}"
    fi

    # Wait for ALL dispatched text/vision requests to complete
    if [[ ${#pids[@]} -gt 0 ]]; then
        log "Waiting for ${#pids[@]} requests to complete..."
        for pid in "${pids[@]}"; do
            wait "$pid" || true
        done
        log "All requests in batch completed"
    fi

    # Clean up request files (text/vision only - embeddings cleaned in dispatch_embedding_batch)
    for rf in "${request_files[@]}"; do
        rm -f "$rf"
    done

    log "Batch complete (type: $batch_type, dispatched: $count)"
}

process_queue() {
    # Main queue processor with prefetch batching
    # Groups same-type requests to minimize model switches
    # Maintains prefetch depth to keep GPU busy

    # Acquire exclusive lock using mkdir (atomic on all platforms)
    # The lock directory itself IS the lock - simpler than mutex+file
    local lock_dir="${LOCK_FILE}.dir"
    local lock_pid_file="${lock_dir}/pid"

    # Try to create lock directory atomically
    if ! mkdir "$lock_dir" 2>/dev/null; then
        # Lock directory exists - check if holder is alive
        local existing_pid=""
        
        # Wait briefly for PID file (atomic rename might be in progress)
        local wait_count=0
        while [[ $wait_count -lt 5 ]]; do
            if [[ -f "$lock_pid_file" ]]; then
                existing_pid=$(cat "$lock_pid_file" 2>/dev/null)
                [[ -n "$existing_pid" ]] && break
            fi
            sleep 0.2
            ((wait_count++))
        done

        if [[ -n "$existing_pid" ]] && kill -0 "$existing_pid" 2>/dev/null; then
            # Lock held by live process
            log "Another processor holds the lock (PID: $existing_pid), exiting"
            return
        fi

        # PID missing or process dead - check lock directory age
        local lock_age=999
        if [[ -d "$lock_dir" ]]; then
            local now dir_mtime
            now=$(date +%s)
            if dir_mtime=$(stat -c %Y "$lock_dir" 2>/dev/null) || dir_mtime=$(stat -f %m "$lock_dir" 2>/dev/null); then
                lock_age=$((now - dir_mtime))
            fi
        fi

        if [[ $lock_age -lt 3 ]]; then
            # Lock dir is very fresh - holder might still be writing PID
            log "Lock dir fresh (${lock_age}s), assuming active holder, exiting"
            return
        fi

        # Lock is stale (old dir or dead process)
        log "Stale lock detected (PID: ${existing_pid:-none}, age: ${lock_age}s), cleaning"
        rm -rf "$lock_dir" 2>/dev/null

        if ! mkdir "$lock_dir" 2>/dev/null; then
            # Another process grabbed it during our cleanup
            log "Lock acquired by another process during cleanup, exiting"
            return
        fi
    fi

    # We have the lock - write PID atomically (temp file + rename)
    local pid_tmp="${lock_pid_file}.tmp.${BASHPID:-$$}"
    echo "${BASHPID:-$$}" > "$pid_tmp"
    mv "$pid_tmp" "$lock_pid_file"
    log "Lock acquired (PID: ${BASHPID:-$$})"

    # Set up cleanup trap - remove entire lock directory on exit
    echo "${BASHPID:-$$}" > "$PID_FILE"
    trap 'rm -rf "${LOCK_FILE}.dir" "$PID_FILE" 2>/dev/null; log "Processor exiting (releasing lock)"' EXIT

    if [[ ! -s "$QUEUE_FILE" ]]; then
        log "Queue empty, nothing to process"
        return
    fi

    log "Starting queue processing (PID: ${BASHPID:-$$})"

    while true; do
        # Check if queue is empty
        if [[ ! -s "$QUEUE_FILE" ]]; then
            # Queue appears empty - wait briefly and re-check
            # This catches requests that arrive during the final batch processing
            log "Queue appears empty, waiting 500ms to confirm..."
            sleep 0.5
            if [[ ! -s "$QUEUE_FILE" ]]; then
                log "Queue confirmed empty after wait, exiting processor"
                break
            fi
            log "Queue had items after wait, continuing"
        fi

        # Sort queue to group same-type requests
        sort_queue_by_type

        # Peek at first request to determine batch type (file-based)
        local peek_file="${IPC_DIR}/peek_queue_$$.json"
        head -n 1 "$QUEUE_FILE" > "$peek_file"
        local first_type
        first_type=$(jq -r '.type // empty' "$peek_file")
        rm -f "$peek_file"

        if [[ -z "$first_type" ]]; then
            log "Empty request type, skipping"
            local skip_file="${IPC_DIR}/skip_$$.json"
            pop_queue_item_to_file "$skip_file"
            rm -f "$skip_file"
            continue
        fi

        log "Starting batch for type: $first_type"

        # Load model for this batch type
        local model
        if ! model=$(ensure_model_for_request "$first_type"); then
            log_error "Failed to load model for $first_type"
            # Write error response instead of silently skipping
            local failed_file="${IPC_DIR}/failed_$$.json"
            if pop_queue_item_to_file "$failed_file"; then
                local failed_id
                failed_id=$(jq -r '.id' "$failed_file")
                echo '{"error": "LM Studio is not reachable. Check that the server toggle is ON in LM Studio."}' > "${RESPONSES_DIR}/${failed_id}.json"
                rm -f "$failed_file"
            fi
            continue
        fi

        # Process all compatible requests with prefetch
        process_batch "$first_type" "$model"
    done

    log "Queue processing complete"
}

# -----------------------------------------------------------------------------
# Commands
# -----------------------------------------------------------------------------

generate_request_id() {
    echo "req_$(date +%s)_$$_$RANDOM"
}

cmd_request() {
    local request_type="$1"
    shift

    local prompt_file=""  # Path to file containing prompt (for large prompts)
    local prompt_inline="" # Small inline prompt
    local system_prompt=""
    local temperature
    temperature=$(get_config "${request_type}_temperature" "0.0")
    local max_tokens=""
    local stream_mode="false"
    local priority="low"  # Default to low priority (background tasks)

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --prompt) prompt_inline="$2"; shift 2;;
            --prompt-file) prompt_file="$2"; shift 2;;  # Store PATH, not content
            --system) system_prompt="$2"; shift 2;;
            --temperature) temperature="$2"; shift 2;;
            --max-tokens) log_error "max-tokens is deprecated and ignored (always uses model max context)"; shift 2;;
            --stream) stream_mode="true"; shift;;
            --priority) priority="$2"; shift 2;;  # high or low
            *) shift;;
        esac
    done

    # Validate priority
    if [[ "$priority" != "high" && "$priority" != "low" ]]; then
        log "Invalid priority '$priority', defaulting to low"
        priority="low"
    fi

    # Determine prompt source - prefer file for large prompts
    local temp_prompt_file=""
    local actual_prompt_file=""

    if [[ -n "$prompt_file" ]]; then
        # User provided a file path - use it directly
        if [[ ! -f "$prompt_file" ]]; then
            log_error "Prompt file not found: $prompt_file"
            return 1
        fi
        actual_prompt_file="$prompt_file"
    elif [[ -n "$prompt_inline" ]]; then
        # User provided inline prompt - write to temp file
        # Note: If prompt_inline is >32KB, the shell already failed to pass it.
        # For large prompts, users MUST use --prompt-file
        temp_prompt_file="${IPC_DIR}/prompt_$$.txt"
        echo -n "$prompt_inline" > "$temp_prompt_file"
        actual_prompt_file="$temp_prompt_file"
    else
        log_error "Prompt is required"
        return 1
    fi

    cleanup_old_pipes

    local request_id
    request_id=$(generate_request_id)

    local pipe_path=""
    local file_path=""

    if [[ "$stream_mode" == "true" ]]; then
        pipe_path="${PIPES_DIR}/${request_id}.pipe"
        if ! mkfifo "$pipe_path"; then
            log_error "Failed to create pipe: $pipe_path"
            [[ -n "$temp_prompt_file" ]] && rm -f "$temp_prompt_file"
            return 1
        fi
    else
        file_path="${RESPONSES_DIR}/${request_id}.json"
    fi


    # Check if queue is empty BEFORE adding (for spawn decision)
    local queue_was_empty=false
    if [[ ! -s "$QUEUE_FILE" ]]; then
        queue_was_empty=true
    fi

    # Build request JSON using jq --rawfile to read prompt from file
    # This avoids all shell variable limits
    # IMPORTANT: -c for compact output (single line JSONL format)
    # Include queued_at timestamp for queue time tracking
    # Include priority for queue ordering (high priority processed first)
    local queued_at
    queued_at=$(date +%s%3N)  # milliseconds since epoch
    jq -nc --rawfile prompt "$actual_prompt_file" \
        --arg id "$request_id" \
        --arg type "$request_type" \
        --arg system "$system_prompt" \
        --arg temp "$temperature" \
        --arg max_tokens "$max_tokens" \
        --arg pipe_path "$pipe_path" \
        --arg file_path "$file_path" \
        --arg stream "$stream_mode" \
        --arg queued_at "$queued_at" \
        --arg priority "$priority" \
        '{id: $id, type: $type, prompt: $prompt, system: $system, temperature: $temp, max_tokens: $max_tokens, pipe_path: $pipe_path, file_path: $file_path, stream: $stream, queued_at: ($queued_at | tonumber), priority: $priority}' \
        >> "$QUEUE_FILE"

    # Fix .pipe.lnk extension issue in queue file
    if grep -q '\.pipe\.lnk' "$QUEUE_FILE"; then
        sed -i 's/\.pipe\.lnk/.pipe/g' "$QUEUE_FILE"
    fi


    # Clean up temp file if we created one
    [[ -n "$temp_prompt_file" ]] && rm -f "$temp_prompt_file"

    log "Queued request $request_id (type: $request_type, stream: $stream_mode)"

    # Check if processor lock is held (flock-based)
    is_processor_locked() {
        # Check if lock directory exists and holder is alive
        local lock_dir="${LOCK_FILE}.dir"
        local lock_pid_file="${lock_dir}/pid"
        
        if [[ -d "$lock_dir" ]]; then
            local lock_pid
            lock_pid=$(cat "$lock_pid_file" 2>/dev/null)
            if [[ -n "$lock_pid" ]] && kill -0 "$lock_pid" 2>/dev/null; then
                return 0  # Locked by live process
            fi
            # Lock dir exists but holder is dead - stale
        fi
        
        return 1  # Not locked
    }

    # Spawn processor based on queue state and lock availability
    # The processor itself handles lock acquisition atomically via mkdir
    if [[ "$queue_was_empty" == "true" ]]; then
        local first_id
        first_id=$(head -n 1 "$QUEUE_FILE" | jq -r '.id')
        if [[ "$first_id" == "$request_id" ]]; then
            # We're first in queue - spawn processor (it will acquire lock atomically)
            if ! is_processor_locked; then
                log "Queue was empty and I'm first, spawning processor"
                process_queue </dev/null >> "$LOG_FILE" 2>&1 &
                disown
            else
                log "Queue was empty and I'm first, but processor already running"
            fi
        else
            log "Queue was empty but $first_id is first (not me: $request_id), not spawning"
        fi
    else
        # Queue was not empty - check if processor died
        if ! is_processor_locked; then
            log "Queue not empty but no processor running, spawning processor"
            process_queue </dev/null >> "$LOG_FILE" 2>&1 &
            disown
        fi
        # If locked, processor is running and will handle our request
    fi

    if [[ "$stream_mode" == "true" ]]; then
        echo "PIPE=$pipe_path"
    else
        echo "FILE=$file_path"
    fi
    return 0
}
cmd_stats() {
    # JSON output for dashboard integration
    local queue_size batch_size mem_usage lm_running loaded_model
    queue_size=$(wc -l < "$QUEUE_FILE" 2>/dev/null | tr -d ' ')
    batch_size=$(get_embedding_batch_size)
    mem_usage=$(get_memory_usage)

    if curl -s --max-time 2 "$LM_STUDIO_URL/models" >/dev/null 2>/dev/null; then
        lm_running="true"
        loaded_model=$(get_loaded_model)
    else
        lm_running="false"
        loaded_model=""
    fi

    # Get recent batch stats from log
    local avg_batch_ms="0"
    local recent_batches
    recent_batches=$(grep "Embedding batch complete" "$LOG_FILE" 2>/dev/null | tail -10 | grep -oP '\d+(?=ms)' | tail -5)
    if [[ -n "$recent_batches" ]]; then
        avg_batch_ms=$(echo "$recent_batches" | awk '{s+=$1} END {if(NR>0) print int(s/NR); else print 0}')
    fi

    jq -nc \
        --argjson queue "${queue_size:-0}" \
        --argjson batch_size "$batch_size" \
        --argjson memory "$mem_usage" \
        --argjson lm_running "$lm_running" \
        --arg loaded_model "${loaded_model:-none}" \
        --argjson avg_batch_ms "${avg_batch_ms:-0}" \
        --argjson batch_min "$EMBEDDING_BATCH_MIN" \
        --argjson batch_max "$EMBEDDING_BATCH_MAX" \
        '{
            queue_depth: $queue,
            batch_size: $batch_size,
            batch_range: {min: $batch_min, max: $batch_max},
            memory_percent: $memory,
            lm_studio_running: $lm_running,
            loaded_model: $loaded_model,
            avg_batch_ms: $avg_batch_ms
        }'
}

cmd_status() {
    echo "=== Gateway Status ==="
    echo ""

    local queue_size
    queue_size=$(wc -l < "$QUEUE_FILE" 2> >(log_stderr) | tr -d ' ')
    echo "Pending requests: ${queue_size:-0}"

    if curl -s --max-time 2 "$LM_STUDIO_URL/models" >/dev/null 2> >(log_stderr); then
        echo "LM Studio: Running"
        local loaded
        loaded=$(get_loaded_model)
        echo "Loaded model: ${loaded:-none}"
    else
        echo "LM Studio: NOT RUNNING"
    fi

    echo ""
    echo "=== Configuration ==="
    echo "Config file: $CONFIG_FILE"

    local text_model
    text_model=$(get_config "text_model" "not set")
    echo "Text model: $text_model"

    local vision_model
    vision_model=$(get_config "vision_model" "not set")
    echo "Vision model: $vision_model"

    local embedding_model
    embedding_model=$(get_config "embedding_model" "not set")
    echo "Embedding model: $embedding_model"

    echo ""
    echo "=== Adaptive Batch Sizing ==="
    local current_batch_size mem_usage
    current_batch_size=$(get_embedding_batch_size)
    mem_usage=$(get_memory_usage)
    echo "Current batch size: $current_batch_size (range: $EMBEDDING_BATCH_MIN-$EMBEDDING_BATCH_MAX)"
    echo "Memory usage: ${mem_usage}%"
    echo "Thresholds: increase below ${MEMORY_LOW_THRESHOLD}%, decrease above ${MEMORY_HIGH_THRESHOLD}%"
}

cmd_reset_batch() {
    # Reset batch size to default or set a specific value
    local new_size="${1:-$EMBEDDING_BATCH_DEFAULT}"
    if [[ "$new_size" =~ ^[0-9]+$ ]]; then
        set_embedding_batch_size "$new_size"
        echo "Batch size set to $(get_embedding_batch_size)"
    else
        echo "Usage: reset-batch [size]"
        echo "  size: integer between $EMBEDDING_BATCH_MIN and $EMBEDDING_BATCH_MAX"
        echo "  If omitted, resets to default ($EMBEDDING_BATCH_DEFAULT)"
    fi
}

cmd_clear_queue() {
    # Clear the queue and kill any stale processor
    # Use this to recover from stuck states

    local pending
    pending=$(wc -l < "$QUEUE_FILE" 2>/dev/null || echo 0)

    echo "=== Clear Queue ==="
    echo ""

    # Check for stale processor
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null || echo "")
        if [[ -n "$pid" ]]; then
            echo "Found processor PID file: $pid"
            if kill -0 "$pid" 2>/dev/null; then
                echo "Killing stale processor (PID $pid)..."
                kill "$pid" 2>/dev/null || true
                sleep 1
            else
                echo "Processor $pid not running (stale PID file)"
            fi
        fi
        rm -f "$PID_FILE"
        echo "Removed PID file"
    fi

    # Clear heartbeat
    if [[ -f "$HEARTBEAT_FILE" ]]; then
        rm -f "$HEARTBEAT_FILE"
        echo "Removed heartbeat file"
    fi

    # Clear queue
    if [[ "$pending" -gt 0 ]]; then
        > "$QUEUE_FILE"
        echo "Cleared $pending pending requests from queue"
        log "Queue cleared by user ($pending requests discarded)"
    else
        echo "Queue was already empty"
    fi

    echo ""
    echo "Gateway reset. Next request will spawn a fresh processor."
}

cmd_unload() {
    # Unload all models to free VRAM
    # Also clears the queue to prevent orphaned requests

    echo "=== Unload All Models ==="
    echo ""

    # First clear the queue to prevent new processing
    local pending
    pending=$(wc -l < "$QUEUE_FILE" 2>/dev/null || echo 0)
    if [[ "$pending" -gt 0 ]]; then
        > "$QUEUE_FILE"
        echo "Cleared $pending pending requests"
        log "Queue cleared before unload ($pending requests discarded)"
    fi

    # Kill any processor
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null || echo "")
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            echo "Stopping processor (PID $pid)..."
            kill "$pid" 2>/dev/null || true
            sleep 1
        fi
        rm -f "$PID_FILE"
    fi
    rm -f "$HEARTBEAT_FILE"

    # Unload all models
    echo "Unloading all models..."
    if command -v lms >/dev/null 2>&1; then
        lms unload --all >> "$LOG_FILE" 2>&1 || true
        echo "Unload command sent"
        log "Unload all models requested by user"

        # Wait for unload
        local waited=0
        while [[ $waited -lt 10 ]]; do
            local loaded
            loaded=$(lms ps --json 2>/dev/null | jq -r '.[0].path // empty' 2>/dev/null | tr -d '\r')
            if [[ -z "$loaded" ]]; then
                echo "All models unloaded - VRAM freed"
                return 0
            fi
            sleep 1
            ((waited++))
        done
        echo "Warning: Unload may still be in progress"
    else
        echo "lms command not found - cannot unload"
        return 1
    fi
}

cmd_help() {
    cat << 'EOF'
safe-model-load.sh - Safe gateway for LM Studio

USAGE:
  safe-model-load.sh [--verbose] <command> [options]

GLOBAL FLAGS:
  --verbose, -v             Surface all errors live to stderr (default: log only)

COMMANDS:
  request <type> [flags]    Submit request and get response
      Types: text, vision, embedding
      Flags:
        --prompt <text>       Prompt text (required)
        --prompt-file <path>  Read prompt from file
        --system <text>       System prompt
        --temperature <float> Override config temperature (text: 0.7, vision: 0.0)
        --priority <level>    Request priority: high or low (default: low)
                              HIGH: Interactive queries (Oracle, agents) - processed first
                              LOW:  Background tasks (embeddings, chunking)
        --timeout <sec>       Response timeout

  status                    Show gateway, LM Studio, and adaptive batch sizing status

  reset-batch [size]        Reset embedding batch size (default: 4, range: 2-16)
                            Useful after system changes or to start fresh

  clear-queue               Clear stuck queue and reset processor state
                            Use when: requests pile up but nothing processes
                            This kills any stale processor and clears pending requests

  unload                    Unload all models to free VRAM
                            Also clears the queue to prevent orphaned requests
                            Use when: done with LLM work and want to free GPU memory

  help                      Show this help

PRIORITY SYSTEM:
  High-priority requests (--priority high) are always processed before low-priority.
  Use high priority for:
  - Oracle queries (user or agent needs immediate response)
  - Agent assistance requests
  - Any interactive use case

  Low priority (default) is for:
  - Background embedding generation
  - Batch chunking operations
  - Any task that can wait

ADAPTIVE BATCH SIZING:
  Embedding requests are batched for efficiency. The gateway automatically:
  - Starts conservative (batch size 2-4)
  - Increases batch size (+1) only when memory usage < 50%
  - Stays stable when memory is 50-90%
  - Decreases batch size (halved) on batch failures
  - Decreases batch size (-1) when memory usage > 90%

EXAMPLES:
  # Submit a text request
  safe-model-load.sh request text --prompt "Hello world"

  # Submit with custom temperature
  safe-model-load.sh request text --prompt "Be creative" --temperature 0.9

  # Submit an embedding request
  safe-model-load.sh request embedding --prompt "Text to embed"

  # Run with verbose output (see all errors live)
  safe-model-load.sh --verbose request text --prompt "Debug mode"

EOF
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

main() {
    # Parse global flags first
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            *)
                break
                ;;
        esac
    done

    local cmd="${1:-help}"

    case "$cmd" in
        request)
            shift
            local request_type="${1:-text}"
            shift || true
            cmd_request "$request_type" "$@"
            ;;
        status)
            cmd_status
            ;;
        stats)
            cmd_stats
            ;;
        logs)
            shift
            local lines="${1:-30}"
            tail -n "$lines" "$LOG_FILE"
            ;;
        lms-logs)
            # Tail LM Studio's server logs directly
            shift
            local lines="${1:-30}"
            local today=$(date +%Y-%m-%d)
            local lms_log="$HOME/.lmstudio/server-logs/$(date +%Y-%m)/${today}.1.log"
            if [[ -f "$lms_log" ]]; then
                tail -n "$lines" "$lms_log"
            else
                echo "LM Studio log not found: $lms_log"
                ls "$HOME/.lmstudio/server-logs/$(date +%Y-%m)/" 2>/dev/null | tail -5
            fi
            ;;
        reset-batch)
            shift
            cmd_reset_batch "$@"
            ;;
        clear-queue)
            cmd_clear_queue
            ;;
        unload)
            cmd_unload
            ;;
        help|--help|-h)
            cmd_help
            ;;
        *)
            cmd_help
            ;;
    esac
}

main "$@"
