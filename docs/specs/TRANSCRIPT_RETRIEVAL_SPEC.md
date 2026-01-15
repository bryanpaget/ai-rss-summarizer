# Logical Specification: Transcript Retrieval & Compaction Analysis System

## 1. Purpose and Goals

The primary purpose of the Transcript Retrieval System is to provide a robust mechanism for accessing, analyzing, and synthesizing long-term interaction histories that have been subjected to context "compaction." As conversational sessions grow to millions of tokens, systems often reduce context by summarizing or truncating older exchanges. This system aims to:

1.  **Recover Lost Context:** Reconstruct the complete narrative arc of a session by bridging the gaps created by compaction events.
2.  **Analyze Discontinuities:** Intelligent detection of logical breaks or information loss that occurs at compaction boundaries.
3.  **Synthesize Long-Horizon Summaries:** Generate coherent summaries across arbitrarily long sessions by processing history in segments defined by these boundaries.
4.  **Local Execution:** Perform high-volume processing using local, open-weights Large Language Models to ensure privacy and cost-efficiency.

## 2. Inputs and Data Sources

The system operates on specific structured text artifacts located within the user's filesystem.

*   **Session Logs:** The primary input consists of newline-delimited JSON (JSONL) files. Each file represents a distinct session, identified by a UUID. The path structure encodes the project context.
*   **Compaction Markers:** Special system events within the event stream (specifically logical types denoting a boundary) indicate where the conversational context was formally reduced.
*   **User Queries:** Natural language requests specifying what information or themes need to be retrieved from the history.
*   **Configuration:** Parameters defining the sensitivity of discontinuity detection, the specific local LLM to employ, and search depth limits.

## 3. Process Flows

### 3.1. Session Discovery and Segmentation

The process begins by locating the relevant session files based on the user's current project context. Once a target session is identified:

1.  **Stream Parsing:** The system reads the JSONL stream sequentially. It does not load the entire file into memory but processes it event by event.
2.  **Boundary Identification:** The system scans for specific system events that act as "compaction boundaries." These events serve as delimiters, breaking the continuous stream into distinct "Epochs."
3.  **Epoch Indexing:** Each Epoch is cataloged with metadata, including its start and end timestamps, the number of turns it contains, and whether it terminates in a compaction event or the end of the session.

### 3.2. Iterative Relevance Search

Mimicking the behavior of an iterative knowledge retrieval system, this component locates specific information within the massive transcript.

1.  **Query Decomposition:** The local LLM analyzes the user's high-level request and breaks it down into specific search criteria or thematic keywords.
2.  **Epoch Scanning:** The system scans the indexed Epochs. Instead of a simple keyword match, it samples content from each Epoch and uses the local LLM to score the probability that the Epoch contains relevant information.
3.  **Deep Dive:** When a high-relevance Epoch is identified, the system retrieves the full text of that segment.
4.  **Evidence Extraction:** The LLM processes the segment to extract specific quotes, decisions, or context related to the query.
5.  **Refinement:** If the extracted evidence is partial or references unknown prior context, the system generates a new, refined query to search preceding Epochs, effectively "walking back" through time.

### 3.3. Compaction Analysis and Discontinuity Detection

This flow addresses the critical loss of information at boundary points.

1.  **Boundary Context Comparison:** The system retrieves the text immediately preceding a compaction event (the "Pre-Compaction Tail") and the text immediately following it (the "Post-Compaction Head").
2.  **Semantic Coherence Check:** The local LLM compares the Tail and Head. It evaluates whether the logical thread continues smoothly or if there is a jarring shift in topic, tone, or context.
3.  **Summary Validation:** If the system inserted a summary message effectively replacing the compacted history, the retrieval system compares this summary against the actual raw text of the preceding Epoch. It verifies if the summary accurately reflects the key decisions made in that now-compressed timeframe.
4.  **Discontinuity Flagging:** If the Head refers to concepts defined in the Tail that are no longer present in the active context (and not adequately summarized), the system flags a "Critical Discontinuity."

### 3.4. Long-Horizon Summarization

For requests requiring a summary of the entire session:

1.  **Rolling Summarization:** The system processes the session Epoch by Epoch, chronologically.
2.  **State Carry-Over:** It generates a summary of Epoch 1. This summary is then provided as context to the LLM when processing Epoch 2.
3.  **Aggregation:** The LLM produces a summary for Epoch 2 that incorporates the context from Epoch 1. This process repeats, creating a rolling "current state of the world" representation.
4.  **Final Synthesis:** The final output is a meta-summary derived from the chain of Epoch summaries, ensuring that early decisions are represented even if they occurred millions of tokens ago.

## 4. Decision Logic

The system must make autonomous decisions during execution:

*   **Relevance Thresholding:** When scoring an Epoch for relevance, the system compares the LLM's confidence score against a configured threshold. Below the threshold, the Epoch is skipped to save compute; above, it triggers a Deep Dive.
*   **Search Termination:** The iterative search stops when either:
    *   The information saturation point is reached (new searches yield no new unique information).
    *   The earliest Epoch is reached.
    *   A maximum iteration limit is hit.
*   **Model Fallback:** If the primary local LLM fails to generate a structured response (e.g., malformed JSON output), the system triggers a retry logic, potentially simplifying the prompt or falling back to a more robust (though slower) quantization or model if available.

## 5. Outputs and Success Criteria

### Outputs
*   **Reconstructed Narrative:** A chronological account of the requested topic, stitched together from various Epochs.
*   **Discontinuity Report:** A list of detected compaction boundaries where significant context loss or logical breaks occurred, including the severity of the break.
*   **Source References:** Specific pointers (Epoch ID, Message Index) to the raw log entries where the information was found.

### Success Criteria
*   **Accuracy:** The retrieved information is factually present in the logs.
*   **Completeness:** The system identifies references to information that existed in a Pre-Compaction Tail even if it is absent in the Post-Compaction Head.
*   **Coherence:** The generated summaries read as a continuous narrative rather than a disjointed list of log entries.
*   **Performance:** The system operates within acceptable time limits on consumer hardware using quantized local models.

## 6. Error Handling

*   **Corrupt Logs:** If a JSONL line is malformed, the parser logs a warning, skips the specific line, and attempts to resynchronize at the next valid newline. It does not abort the entire session scan.
*   **Hallucination Check:** When the LLM extracts "facts," the system performs a verification pass (if configured) by strictly searching for the extracted phrase in the raw text to ensure it hasn't been fabricated.
*   **Context Window Overflow:** If a single Epoch is too large for the local LLM's context window, the system automatically subdivides the Epoch into smaller chunks, summarizes those chunks, and then processes the summaries.

## 7. Dependencies and Prerequisites

*   **Infrastructure:** Access to the shared Python libraries used by the existing knowledge-query system (for LLM interfacing and prompting).
*   **Local LLM Service:** A running instance or library access to a capable local Large Language Model (e.g., Llama 3, Mistral) served via an API-compatible layer.
*   **File Access:** Read permissions for the `~/.claude` directory structure.
*   **Index Storage:** A location to store temporary indices of parsed sessions to speed up subsequent queries on the same session.
