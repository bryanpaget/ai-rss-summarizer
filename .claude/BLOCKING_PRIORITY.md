# BLOCKING PRIORITY: Project Organization

**Status: NOTHING MOVES FORWARD UNTIL THIS IS RESOLVED**

## The Problem

This project has grown to a size where it MUST be well organized or nothing can achieve progress. Currently:

- Every change causes regressions because consequences are unknown
- Multiple code paths exist for the same operations (undocumented)
- Special cases are scattered throughout with no central documentation
- No one can touch anything without breaking something else
- Every step forward causes 5 steps backward

## The Requirement

Until the following conditions are met, NO CODE CHANGES should be made:

1. **Complete System Map**: Every module, every function, every code path must be documented
2. **Dependency Documentation**: Every function must list what it affects and what affects it
3. **Change Impact Rules**: Before touching ANY code, you must be able to identify ALL consequences
4. **No Hidden Special Cases**: Every conditional branch, every edge case must be visible and documented
5. **Single Source of Truth**: One place that describes how the entire system works

## Why This Matters

The embedding system is a perfect example of the failure:
- Multiple code paths (short text vs long text) exist with different behaviors
- Chunking logic is scattered and inconsistent
- "Fixes" applied to one path don't affect other paths
- No documentation explains which path data takes or why
- Every "optimization" fails because it only addresses part of the system

This pattern repeats across the ENTIRE codebase:
- Gateway vs direct API calls
- Different embedding methods in different places
- Extraction logic duplicated with variations
- Storage operations with hidden side effects

## What Must Happen

### Phase 1: Map Everything
- Document every module and its purpose
- Document every public function and its behavior
- Document every code path and when it's taken
- Document every special case and why it exists

### Phase 2: Identify Inconsistencies
- Find all places where the same operation is done differently
- Find all undocumented special cases
- Find all hidden dependencies

### Phase 3: Create Change Protocol
- Define rules for how changes must be evaluated
- Create checklist of impacts that must be checked
- Make it IMPOSSIBLE to change code without following protocol

### Phase 4: Only Then, Fix Things
- With full understanding, consolidate duplicate logic
- Remove unnecessary special cases
- Apply optimizations that work across the ENTIRE system

## Until This Is Done

- DO NOT apply "fixes" to individual components
- DO NOT add new features
- DO NOT optimize anything
- DO NOT touch code without documenting what you're touching first

Every line of code touched without this foundation makes the problem worse.

---

**This document must be referenced at the start of every session.**
**Any agent working on this project must read this FIRST.**
