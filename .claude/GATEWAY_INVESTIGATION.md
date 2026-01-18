# Gateway Investigation - Race Condition Found

**Date:** 2026-01-18
**Status:** CONFIRMED BUG - needs fix

## The Problem

Multiple clients using the gateway can cause requests to be lost. A 5-minute gap occurred where 2 requests sat orphaned in the queue.

## Evidence from Gateway Log

```
09:40:46 - Queued request req_1768758046 (type: text)
09:40:46 - "Queue was empty and I'm first, but processor already running"
09:40:48 - "Sorting queue by priority and type (current model: text)"  <-- SORT STARTED
09:40:48 - Queued request req_1768758048 (type: text)                  <-- NEW REQUEST DURING SORT
09:40:49 - "Processor exiting (releasing lock)"                        <-- NO "Queue sorted" LOG!
... 5 MINUTE GAP ...
09:45:47 - Queued request req_1768758347 (type: text)                  <-- New client triggered recovery
09:45:47 - "Queue not empty but no processor running, spawning processor"
09:45:48 - "Queue sorted (1 items, 0 high priority)"                   <-- ONLY 1 ITEM! req_1768758046 LOST!
09:45:53 - Dispatched req_1768758048 to LM Studio                      <-- This was the second request
```

## Root Cause: TOCTOU Race in sort_queue_by_type

The `sort_queue_by_type` function at line ~870 in `safe-model-load.sh`:

1. **READ:** Uses jq to read queue file into temp files (lines 889-891)
2. **PROCESS:** Reorganizes into temp files by priority/type (lines 893-919)
3. **OVERWRITE:** `cat temp... > $QUEUE_FILE` overwrites queue (line 917)

**The Race Window:**
- If a client appends a new request between step 1 (read) and step 3 (overwrite), the new request is LOST
- The overwrite destroys any concurrent appends

**Evidence:**
- "Sorting queue" logged at 09:40:48 (step 1 started)
- "Queued request req_1768758048" logged at 09:40:48 (concurrent append!)
- NO "Queue sorted (N items)" log (step 3 never completed normally)
- Processor exited at 09:40:49
- When recovered at 09:45:48, only 1 item found - req_1768758046 was LOST

## Why req_1768758046 Was Lost

Looking more carefully:
- req_1768758046 was added at 09:40:46
- Sort started at 09:40:48 and read the queue (saw req_1768758046)
- req_1768758048 appended at 09:40:48
- Sort overwrote queue with sorted content
- BUT something went wrong - "Queue sorted" log never appeared
- Processor exited thinking queue was empty
- Both requests orphaned until 09:45:47

## Proposed Fixes

### Option 1: Lock the queue file during sort
```bash
(
  flock -x 200
  # do the sort operations
) 200>"$QUEUE_FILE.lock"
```

### Option 2: Atomic swap instead of overwrite
```bash
# Sort to temp file
sort_to_temp > "$QUEUE_FILE.sorted"
# Atomic rename
mv "$QUEUE_FILE.sorted" "$QUEUE_FILE"
# But this still doesn't handle concurrent appends
```

### Option 3: Append-only queue with separate index
- Never overwrite queue file
- Keep separate index of processed items
- Compact periodically when no processor running

### Option 4: Re-check queue after sort
- After overwriting, check if queue size changed
- If new items appeared, re-sort

## Next Steps

1. Decide on fix approach (user input needed)
2. Implement fix
3. Test with small batches: 1 file, then 2, then 4, etc.
4. Validate multiple concurrent clients work

## Related: Documentation Tool

The documentation tool (`scripts/document-codebase.ps1`) was created to map the codebase. It processed 2/39 files before being stopped due to this gateway issue:
- cli.py: 31 items found
- cli_constitution.py: 31 items found (after 2 timeouts)

Cannot resume documentation until gateway race condition is fixed.
