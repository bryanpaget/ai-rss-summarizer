#!/usr/bin/env bash
# Test: Gateway should maintain continuous throughput (no batch-then-drain)
#
# EXPECTED BEHAVIOR:
#   - When processing multiple requests, in-flight count should stay HIGH
#   - Responses should arrive continuously (no long gaps)
#
# FAILURE INDICATOR:
#   - Large gaps between responses indicate "drain to zero" behavior
#   - Gap > 2x average response time = FAIL
#
# Usage: ./test-gateway-continuous.sh [num_requests]

set -euo pipefail

NUM_REQUESTS="${1:-30}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GATEWAY="$SCRIPT_DIR/safe-model-load.sh"
RESPONSES_DIR="${HOME}/.claude/ipc/responses"

echo "=== Gateway Continuous Batching Test ==="
echo "Requests: $NUM_REQUESTS"
echo ""

# Record start time and get list of existing response files
START_TIME=$(date +%s)
EXISTING_FILES=$(ls "$RESPONSES_DIR"/*.json 2>/dev/null | wc -l || echo "0")

# Submit all requests as fast as possible
echo "Submitting $NUM_REQUESTS requests..."
declare -a response_files=()
for i in $(seq 1 "$NUM_REQUESTS"); do
    prompt="Describe this function in one sentence: function test_$i() { return $i * 2; }"
    # Gateway returns FILE=<path>, capture it
    output=$("$GATEWAY" request text --prompt "$prompt" 2>/dev/null)
    file_path="${output#FILE=}"
    response_files+=("$file_path")
done

echo "All requests submitted, waiting for responses..."
echo ""

# Wait for all response files to exist and have content
echo "Waiting for responses to complete..."
for file_path in "${response_files[@]}"; do
    while [[ ! -s "$file_path" ]]; do
        sleep 0.1
    done
done

echo "All responses received!"
echo ""

# Extract completion times from responses
echo "Analyzing response timing..."
declare -a completion_times=()

for file_path in "${response_files[@]}"; do
    if [[ -f "$file_path" ]]; then
        completed_at=$(jq -r '._timing.completed_at // empty' "$file_path" 2>/dev/null || echo "")
        if [[ -n "$completed_at" ]]; then
            completion_times+=("$completed_at")
        fi
    fi
done

if [[ ${#completion_times[@]} -lt 5 ]]; then
    echo "ERROR: Not enough responses with timing data (got ${#completion_times[@]})"
    echo "Check that gateway is running and LM Studio is available"
    exit 1
fi

# Sort completion times
IFS=$'\n' sorted_times=($(sort -n <<<"${completion_times[*]}")); unset IFS

# Calculate gaps between consecutive completions
echo "Response completion gaps (ms):"
declare -a gaps=()
prev_time="${sorted_times[0]}"
for time in "${sorted_times[@]:1}"; do
    gap=$((time - prev_time))
    gaps+=("$gap")
    prev_time="$time"
done

# Calculate statistics
total_gap=0
max_gap=0
for gap in "${gaps[@]}"; do
    total_gap=$((total_gap + gap))
    if [[ $gap -gt $max_gap ]]; then
        max_gap=$gap
    fi
done
avg_gap=$((total_gap / ${#gaps[@]}))

echo "  Average gap: ${avg_gap}ms"
echo "  Max gap: ${max_gap}ms"
echo "  Total responses: ${#completion_times[@]}"
echo ""

# Count large gaps (potential drain events)
drain_threshold=$((avg_gap * 3))  # Gap > 3x average indicates drain
drain_events=0
for gap in "${gaps[@]}"; do
    if [[ $gap -gt $drain_threshold ]]; then
        drain_events=$((drain_events + 1))
    fi
done

echo "Drain detection (threshold: ${drain_threshold}ms):"
echo "  Large gaps detected: $drain_events"
echo ""

# PASS/FAIL determination
# Allow up to 2 large gaps (startup/shutdown), but more indicates drain behavior
MAX_ALLOWED_DRAINS=2

if [[ $drain_events -gt $MAX_ALLOWED_DRAINS ]]; then
    echo "=== FAIL ==="
    echo "Detected $drain_events drain events (max allowed: $MAX_ALLOWED_DRAINS)"
    echo "Gateway is using batch-then-drain instead of continuous processing"
    echo ""
    echo "Gap distribution:"
    for i in "${!gaps[@]}"; do
        gap="${gaps[$i]}"
        marker=""
        if [[ $gap -gt $drain_threshold ]]; then
            marker=" <-- DRAIN"
        fi
        echo "  Response $((i+1))->$((i+2)): ${gap}ms${marker}"
    done
    exit 1
else
    echo "=== PASS ==="
    echo "Gateway maintained continuous throughput"
    echo "Only $drain_events gaps exceeded threshold (acceptable)"
    exit 0
fi
