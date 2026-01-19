# Session Handoff - 2026-01-18

## Current Task: Local Codebase Explorer - Multi-Language Support

### 1. Refactor tool to support ALL file types

- **Why**: Currently Python-only. User requirement: 100% file coverage, no silent skips.
- **Context**: 3-tier architecture:
  1. **Tree-sitter** - Languages with grammars (Python, JS, TS, Go, Rust, C, Java, etc.) → parse structure, describe each function/class
  2. **LLM fallback** - Text files without grammar support → send whole file to LLM, ask for description
  3. **"Couldn't parse"** - ONLY if LLM returns unusable response (detects "I don't understand" or garbage)
- **Where**: `scripts/document-by-function.py` (rename to `local-codebase-explorer.py`)
- **Done when**: Running on mixed-language project documents ALL files - structured for known languages, LLM descriptions for text, explicit "couldn't parse" only as last resort
- **If stuck**: Start with tree-sitter, test on one non-Python file, then add LLM fallback

### 2. Move tool to global location

- **Why**: Tool should be usable from ANY project
- **Context**: Global scripts go in `~/.claude/scripts/` per KNOWLEDGE_BASE_LOCATIONS.md
- **Where**: Copy finished tool to `~/.claude/scripts/local-codebase-explorer.py`
- **Done when**: Can run `python ~/.claude/scripts/local-codebase-explorer.py <any-folder>` from anywhere
- **If stuck**: Check gateway dependency - may need to make LLM calls configurable

### 3. Create global documentation

- **Why**: All agents need to know this tool exists and how to use it
- **Context**: Need user approval before KB modifications (see CLAUDE_MD_MODIFICATION_GUIDE.md)
- **Where**: `~/.claude/topics/development-tools/LOCAL_CODEBASE_EXPLORER.md`
- **Done when**: Documentation exists and is referenced in global CLAUDE.md
- **If stuck**: Present exact text to user, get explicit approval

## What Exists Now

| Component | Status |
|-----------|--------|
| Python AST parsing | Working |
| LLM descriptions | Working |
| Hash-based caching | Working |
| Retry logic (3x) | Working |
| Concurrent processing | Working (10 workers) |
| Error handling | Working (fatal, never in output) |
| Multi-language support | NOT IMPLEMENTED |

## Dependencies

- `tree-sitter` and `tree-sitter-languages` packages needed
- Gateway dependency may need abstraction for global use

## Return To

Task 1 (multi-language refactor) after installing tree-sitter.
