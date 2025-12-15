# Fallback Work Map: Discovered Failure Modes

Per SHORTCUTS_ARE_DISCOVERIES.md: "Adding a fallback = A failure mode that needs proper handling"

Each fallback in this codebase signals something that CAN fail and was hidden instead of properly handled. This document catalogs them as a work map of what needs to be fixed.

## Priority: CRITICAL

These affect core functionality and hide significant failures.

### 1. LLM Provider Auto-Load External Reference
**File**: `src/llm_providers.py:356`
**Current Code**: "Try to load universal config, fall back to bundled defaults"
**Hidden Failure**: Config system has external dependency on `~/.claude/`
**Proper Handling**:
- Remove ALL external references
- Use only project-local config
- If config missing, ERROR with clear setup instructions
**Status**: [ ] Not Fixed

### 2. Story Clustering LLM Failure
**File**: `src/clustering.py:71-73`
**Current Code**: `except Exception: return self._keyword_similarity(article, story)`
**Hidden Failure**: LLM comparison silently degrades to keyword matching
**Proper Handling**:
- If LLM unavailable at start, ERROR before processing
- If LLM fails mid-operation, surface the specific error
- User should know clustering quality is degraded
**Status**: [ ] Not Fixed

### 3. Perspective Generation LLM Failure
**File**: `src/perspectives.py:417-449, 525-528, 586-587`
**Current Code**: `generate_fallback_perspective()` silently returns low-quality output
**Hidden Failure**: User gets garbage perspectives without knowing LLM failed
**Proper Handling**:
- If LLM unavailable, ERROR with setup instructions
- If LLM fails, show error message in output, not silent degradation
- Consider: perspectives require LLM, should fail if LLM unavailable
**Status**: [ ] Not Fixed

### 4. Knowledge Extraction LLM Failure
**File**: `src/knowledge.py:603-615`
**Current Code**: "Fall back to simple extraction if LLM fails"
**Hidden Failure**: Knowledge extraction silently returns minimal data
**Proper Handling**:
- Surface the extraction failure to user
- Don't pretend extraction succeeded with garbage data
**Status**: [ ] Not Fixed

---

## Priority: HIGH

These affect important features.

### 5. Signal Tagging LLM Failure
**File**: `src/signal_tagger.py:381`
**Current Code**: "Fall back to rule-based tagging"
**Hidden Failure**: AI signal detection silently becomes rule-based
**Proper Handling**:
- If LLM required for signal detection, fail clearly
- Or: Make rule-based the explicit default, LLM an enhancement
- User should know which mode is active
**Status**: [ ] Not Fixed

### 6. Emergence Detection Failure
**File**: `src/trends.py:188-190`
**Current Code**: `except Exception as e: print(f"Emergence detection failed: {e}")`
**Hidden Failure**: Enhanced trends silently become empty, basic trends used
**Proper Handling**:
- Surface the failure in the returned data
- User should see "emergence detection unavailable" not just empty results
**Status**: [ ] Not Fixed

### 7. Similarity Response Parsing
**File**: `src/clustering.py:110-117`
**Current Code**: Fallback keyword search in response if JSON parsing fails
**Hidden Failure**: Malformed LLM response silently becomes guess
**Proper Handling**:
- If LLM returns unparseable response, that's an error
- Retry with clearer prompt or surface the parsing failure
**Status**: [ ] Not Fixed

---

## Priority: MEDIUM

These affect auxiliary features.

### 8. Story Title Generation
**File**: `src/clustering.py:206-209`
**Current Code**: `except Exception: return article.title[:100]`
**Hidden Failure**: Title generation failure hidden, article title used
**Proper Handling**:
- Log the failure
- Mark story as "title auto-generated from article"
**Status**: [ ] Not Fixed

### 9. Story Description Generation
**File**: `src/clustering.py:222-225`
**Current Code**: `except Exception: return article.summary or article.content[:200]`
**Hidden Failure**: Description generation failure hidden
**Proper Handling**:
- Log the failure
- Mark story as "description auto-extracted"
**Status**: [ ] Not Fixed

### 10. Keyword Extraction
**File**: `src/clustering.py:241-244`
**Current Code**: `except Exception: return [word for word in article.title.split()...]`
**Hidden Failure**: Keyword extraction failure hidden, title words used
**Proper Handling**:
- Log the failure
- Mark keywords as "auto-extracted from title"
**Status**: [ ] Not Fixed

### 11. Feed Discovery URL Parsing
**File**: `src/feed_discovery.py:323`
**Current Code**: "This is a fallback - feedsearch works best with URLs"
**Hidden Failure**: Discovery mode silently changed
**Proper Handling**:
- Surface which discovery mode was used
- If fallback mode, tell user "best results with full URL"
**Status**: [ ] Not Fixed

### 12. RSS Content Extraction
**File**: `src/rss.py:57`
**Current Code**: "Fall back to summary"
**Hidden Failure**: Content extraction failure hidden
**Proper Handling**:
- If content unavailable, mark article as "summary only"
- User should know full content wasn't available
**Status**: [ ] Not Fixed

---

## Work Tracking

| # | File | Line | Priority | Status |
|---|------|------|----------|--------|
| 1 | llm_providers.py | 356 | CRITICAL | [ ] |
| 2 | clustering.py | 71-73 | CRITICAL | [ ] |
| 3 | perspectives.py | 417+ | CRITICAL | [ ] |
| 4 | knowledge.py | 603-615 | CRITICAL | [ ] |
| 5 | signal_tagger.py | 381 | HIGH | [ ] |
| 6 | trends.py | 188-190 | HIGH | [ ] |
| 7 | clustering.py | 110-117 | HIGH | [ ] |
| 8 | clustering.py | 206-209 | MEDIUM | [ ] |
| 9 | clustering.py | 222-225 | MEDIUM | [ ] |
| 10 | clustering.py | 241-244 | MEDIUM | [ ] |
| 11 | feed_discovery.py | 323 | MEDIUM | [ ] |
| 12 | rss.py | 57 | MEDIUM | [ ] |

**Total**: 12 fallback patterns to address
**Critical**: 4
**High**: 3
**Medium**: 5

---

## Design Decision: LLM is Mandatory

Many of these fallbacks hide "LLM not available" failures.

**Decision**: LLM is REQUIRED for this program to function. User chooses which provider, but one must be configured.

Without an LLM, this program is just a manual RSS reader with no AI capabilities. The core value proposition requires LLM functionality.

**Implications for fallback fixes**:
- All LLM-failure fallbacks should become ERRORS with clear setup instructions
- If LLM unavailable at startup, error immediately with provider setup guidance
- No silent degradation - if LLM fails mid-operation, surface the error clearly

**Future Option** (after core features work):
- Degraded mode without LLM (basic fetch/list only)
- Embedded lightweight LLM option (auto-download small model if user consents)
- These are enhancements for later, not current priorities
