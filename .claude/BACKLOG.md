# RSS Summarizer Backlog

Project-specific future features and improvements.

## High Priority

### User Constitution / Analysis Policy Framework
**Status:** Proposed
**Complexity:** Medium

Allow users to define their own principles and values that guide ALL analysis. A personal "constitution" document that gets injected into LLM prompts.

**User Story:**
> "I want the user to be able to specify how they want things analyzed and processed so that their own principles and viewpoints can be the metrics of the analysis. If they have a certain perspective they want analyzed through, they can set that up and configure it so that this is a personalized news feed based on their values."

**Proposed Implementation:**
- `config/constitution.md` - User-editable markdown file containing their analysis framework
- Example content:
  ```markdown
  ## My Analysis Principles

  - Prioritize scientific consensus over individual opinions
  - Be skeptical of claims from pharmaceutical industry sources
  - Highlight local community impacts
  - Value evidence-based reasoning over speculation
  - Flag potential conflicts of interest
  ```

**Integration Points:**
1. `src/knowledge.py` - `extract_insights_from_article()` - prepend constitution to extraction prompts
2. `src/perspectives.py` - `build_perspective_prompt()` - include constitution context
3. `src/signal_tagger.py` - tagging prompts - apply user values to signal detection
4. `src/report.py` - any summary generation

**New CLI Commands:**
- `rss constitution` - View current constitution
- `rss constitution edit` - Open constitution file for editing
- `rss constitution example` - Show example constitution templates

**Prompt Injection Pattern:**
```python
def get_constitution_context():
    """Load user's constitution for prompt injection."""
    constitution_path = "config/constitution.md"
    if os.path.exists(constitution_path):
        with open(constitution_path) as f:
            return f"## User Analysis Framework\n{f.read()}\n\nApply these principles when analyzing:\n"
    return ""
```

---

## Medium Priority

(Add items here)

---

## Low Priority / Nice to Have

(Add items here)

---

## Completed

(Move completed items here with dates)
