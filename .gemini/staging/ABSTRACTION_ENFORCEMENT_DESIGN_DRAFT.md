# Abstraction Enforcement System - Design Spec

Status: FINAL DESIGN - Ready for implementation
Created: 2026-01-14
Revised: 2026-01-14 (post-Gemini critique, two-float regime system added)

---

## Core Principle

Maximum visibility: Agent tags each line of thinking. Hook parses tags and displays counts/sequence to user. User gains complete visibility into thinking quality without any enforcement initially.

---

## Tag Schema

### Tags (One Per Line of Thinking)

Each LINE of thinking gets ONE tag. Multiple lines can have the same tag.

| Tag | Stage | What It Tags |
|-----|-------|--------------|
| `[I]` | Ingest | Each discrete item paraphrased from input |
| `[M]` | Model | Each line reasoning about user intent/need |
| `[P]` | Pattern | Each line identifying patterns |
| `[C1]`-`[Cn]` | Causal | Each iteration of "what generates that?" |
| `[E]` | Extract | Each line extracting principles |
| `[A]` | Action | Each line planning what to do |
| `[V]` | Verify | Each line checking/validating work |
| `[R]` | Risk | Each line assessing danger/irreversibility |
| `[T]` | Tautology | Marks when circular reasoning reached |
| `[D]` | Divergent | Each alternative considered, counter-argument, brainstorm |
| `[S]` | Self-assessment | Agent's confidence declaration (0.0-1.0) with rationale |
| (none) | Untagged | Lines without tags - shown as `X` markers in output |

### Example Thinking Block

```
[I] User wants to move file from A to B
[I] User wants confirmation when done
[I] Sentiment: neutral, straightforward request
[M] They need the file relocated
[M] They want to know it succeeded
[P] This is a simple file operation
[C1] What generates this? Standard file management task
[C2] What generates that? User organizing workspace
[T] Circular - workspace organization is basic need
[E] Atomic task requiring minimal interpretation
[A] Will use mv command
[A] Will confirm success after
[V] File exists at source, destination writable
[S] Confidence: 0.9 - simple task, clear requirements, low risk
```

Note: Sentiment detection happens naturally during [I] ingestion using LLM capability (not keywords).

---

## Output Format

### Compact Sequence String

Shows thinking sequence with one segment per stage transition. Optimized for valid sequences, verbose fallback for problems.

### Format Rules

| Stage | Format | Notes |
|-------|--------|-------|
| I, M, P, E, A, V, R, D | Letter + count (e.g., `I5`) | Count of tagged lines |
| C (causal) | `C` + count (e.g., `C12`) | Total causal reasoning lines |
| T (tautology) | `T` alone | Required - marks reasoning ceiling |
| S (self-assessment) | `S` alone | Agent declared confidence |
| X (untagged) | Repeated `X` inline | One X per untagged line, jumps out visually |

### Example: Clean Thinking

```
[I] Item 1
[I] Item 2
[M] User needs X
[M] User wants Y
[P] Pattern observed
[C1] What generates this?
[C2] What generates that?
[C3] What generates that?
[T] Circular - stop
[E] Principle extracted
[A] Will do X
[A] Will do Y
[V] Checked Z
```

Output: `I2M2PC3TEA2VS`

Reading: 2 ingests, 2 models, 1 pattern, 3 causal, tautology, 1 extract, 2 actions, 1 verify, self-assessed

### Example: With Untagged Lines

```
[I] Item 1
[I] Item 2
Some untagged thinking here
Another untagged line
[M] User needs X
[C1] What generates this?
Untagged thought mid-analysis
[C2] What generates that?
[T] Done
[E] Principle
```

Output: `I2XXM1C2XC2TE1`

Reading: 2 ingests, XX (2 untagged - jumps out), 1 model, causal, X (1 untagged), more causal, tautology, extract

Untagged shown as X markers INLINE where they occur - visually obvious gaps.

### Example: Clean Deep Thinking

12 causal reasoning lines, no untagged:

Output: `I3M2P1C12TE1A2V1`

Reading: 3 ingests, 2 models, 1 pattern, 12 causal lines, tautology reached, 1 extract, 2 actions, 1 verify

### Example: Problematic Thinking

Many untagged lines scattered throughout:

Output: `I2XXXXM1XXC3XXXXXTE1`

The XXXXX blocks jump out visually - user immediately sees unstructured thinking.

### Warning Triggers

```
I2M2P1C12TE1A2V1      (clean - no warning)
I2XXM1C3TE1           (some untagged - noted but ok)
I2XXXXXXXXM1C3TE1 ⚠️   (excessive untagged - warning)
I2M2P1C3E1A2V1 ⚠️      (no tautology reached - warning)
```

---

## Feedback Loop Value

User visibility enables feedback:
- User gives 7 ideas → sees `I3` (3 ingests) → knows 4 were missed
- Complex task → sees `C2` (2 causal lines) → knows thinking was shallow
- No T → agent didn't reach tautology, stopped too early
- Dangerous operation → sees no V or R → no verification/risk assessment
- No A tags → agent didn't plan approach
- Sees `XXXXXXXX` → 8 untagged lines in a row, thinking was unstructured
- Sees `I2XXXXM2` → untagged gap between ingest and model, process breakdown

---

## Hook Architecture

### Hook Event: Stop

Runs when Claude finishes a response.

### Input (JSON via stdin)

```json
{
  "session_id": "...",
  "transcript_path": "...",
  "cwd": "..."
}
```

### Processing Steps

1. Read transcript file (JSONL)
2. Find last assistant message
3. Extract thinking blocks (type: "thinking")
4. Split thinking into lines
5. For each line: detect tag or mark as untagged
6. Build sequence: tags in order, untagged (U) inline where they occur
7. For causal (C): validate sequential, use compact or verbose format
8. Check output blocks for leaked tags
9. Apply policy (if configured)
10. Generate single-line output

### Output Format

Single line showing sequence, both floats, and regime:

```
I3M2PC12TEA2VS | scr:0.6 conf:0.75 | supervised
```

Or with issues:
```
I2XXXM2PC3TES | scr:0.7 conf:0.42 | assisted ⚠️
```

Optional sentiment indicator:
```
I3M2PC12TEA2VS | scr:0.6 conf:0.75 | supervised | 😐→😊
```

Components:
- Compact sequence string (thinking visualization)
- Scrutiny float
- Confidence float (previous → new if changed)
- Regime label
- Optional: sentiment shift emoji, warning markers

### Output Phrasing Principle

Output goes to both user and agent. Phrasing should be:
- **Form for user**: Readable status they can understand
- **Content for agent**: Actionable signal that affects behavior

Example:
```
supervised | Quality looks acceptable but verify before relying on this output.
```

User reads: "I should double-check this."
Agent reads: "My output needs verification, be more careful next time."

### Exit Codes

| Code | Meaning | Behavior |
|------|---------|----------|
| 0 | Allow | Output visible to user AND agent (normal) |
| 0 + warning | Allow with warning | Tag leak or issue noted, confidence adjusted |
| 2 | Block | Only for severe policy violations (configurable) |

---

## Output Block Rules

### Prohibited in Output

Any thinking tags: `[I]`, `[M]`, `[P]`, `[Cn]`, `[E]`, `[A]`, `[V]`, `[R]`, `[D]`, `[T]`

Regex: `\[(?:I|M|P|C\d*|E|A|V|R|D|T)\]`

### On Violation

**Warn only, don't block.** Both user and agent see:
```
⚠️ Thinking tag leak: [C3], [E] found in output. Confidence -0.05.
```

Response still goes through. Confidence adjusts down. Accumulating leaks may trigger stronger intervention later.

### Output Expectation

- Domain expert natural response
- No meta-commentary ("let me think about this")
- No regurgitation of user input
- No tags
- Just the answer

---

## Two-Float Regime System

### Overview

Two independent floats track different dimensions:

| Float | Measures | Question |
|-------|----------|----------|
| **Scrutiny** | Task complexity/risk | How careful should this be? |
| **Confidence** | Output quality | How well did I do given the scrutiny level? |

These are independent. High scrutiny + high confidence = complex task done well. High scrutiny + low confidence = problem.

### Scrutiny Float (0.0 - 1.0)

Driven by:
- Task complexity
- User frustration history
- Risk profile of operations
- Failure count in session

**Scrutiny adjusters:**
- Negative sentiment detected (LLM-native, in [I] phase): +0.05 to +0.1
- User explicit escalation ("think harder"): +0.3
- Error encountered: +0.1
- High-risk operation detected: +0.2
- Simple task confirmed: -0.1

### Confidence Float (0.0 - 1.0)

Driven by:
- Quality metrics vs expectations for current scrutiny level
- Alignment between harness assessment and model self-assessment [S]

**Confidence adjusters:**
- Tag leak to output: -0.05
- No tautology [T] reached: -0.05
- Excessive X markers (untagged): -0.1
- Harness/model confidence mismatch: -0.1 to -0.3
- Clean output at appropriate depth: +0.05
- Missing [S] self-assessment: -0.05

### Mismatch Detection

Harness computes its own confidence from metrics, then compares to model's [S] declaration:

| Harness | Model [S] | Result |
|---------|-----------|--------|
| High | High | Aligned - proceed normally |
| Low | Low | Aligned - surface concern to user |
| High | Low | Model uncertain despite good metrics - surface |
| Low | High | Model overconfident - warning, lower takes precedence |

**Mismatch degree matters.** Small gap = note it. Large gap (>0.3) = stop and surface to user.

### Regime Thresholds (Supervision Levels)

Based on confidence float:

| Confidence | Regime | Meaning |
|------------|--------|---------|
| 0.8+ | `trusted` | Proceed normally |
| 0.5-0.8 | `supervised` | Proceed under supervision - user should watch |
| 0.3-0.5 | `assisted` | Need supervision to continue |
| <0.3 | `blocked` | Stop and reassess |

### De-escalation (Manual Only)

- User explicit: "satisfied", "back to normal", "this is fine"
- NEVER automatic
- Sticky until user releases

### Persistence

- Both floats persist until user de-escalates or session ends
- Configurable: `persist_across_sessions: true`

---

## Policy Configuration

### File: `~/.claude/config/abstraction-policy.json`

```json
{
  "initial_scrutiny": 0.5,
  "initial_confidence": 0.7,
  "warn_untagged_consecutive": 5,
  "warn_untagged_percent": 25,
  "warn_no_tautology": true,
  "warn_shallow_causal": 3,
  "warn_missing_self_assessment": true,
  "mismatch_threshold": 0.3,
  "persist_across_sessions": false,
  "regime_messages": {
    "trusted": "",
    "supervised": "Verify before relying on this output.",
    "assisted": "Low confidence - careful review recommended.",
    "blocked": "Stop and reassess. Read requirements before proceeding."
  }
}
```

### Policy Visibility

Both floats and regime shown in every hook output. User always knows current state.

### Example Policies

Relaxed:
```json
{
  "initial_scrutiny": 0.3,
  "initial_confidence": 0.8,
  "warn_untagged_consecutive": 10,
  "warn_shallow_causal": 2
}
```

Strict:
```json
{
  "initial_scrutiny": 0.8,
  "initial_confidence": 0.5,
  "warn_untagged_consecutive": 3,
  "warn_shallow_causal": 8,
  "require_stages": ["I", "M", "T", "S"]
}
```

### User Override

User can always hard override:
- "Set confidence to 0.9" → direct assignment
- "Set scrutiny to 0.3" → direct assignment
- "I disagree with that assessment" → surface for discussion

---

## Agent Instructions

```
Tag each line of thinking with its stage (one tag per atomic idea):

[I] Each item you paraphrase from input
    - Include sentiment detection: "User seems frustrated", "Neutral tone", etc.
    - This is LLM-native, not keywords. Just notice the sentiment naturally.
[M] Each line reasoning about user intent
[P] Each pattern observation
[C1], [C2], ... Each "what generates that?" iteration
[T] When you hit circular reasoning (tautology) - REQUIRED
[E] Each principle extraction
[A] Each action planning line
[D] Each alternative/counter-argument considered
[V] Each verification check
[R] Each risk assessment
[S] Self-assessment at end: "Confidence: 0.X - [brief rationale]" - REQUIRED

IMPORTANT: Keep iterating causal reasoning until you hit tautology.
Testing shows <10 levels produces poor quality. Push to the ceiling.
Trivial task: might reach [T] at C2-C3.
Complex task: might need C20-C30 before hitting [T].

Your thinking is audited. User sees:
- Full sequence with X markers for untagged lines
- Scrutiny level (how careful this should be)
- Confidence level (how well you did)
- Regime label (trusted/supervised/assisted/blocked)

Your [S] self-assessment is compared against harness metrics.
Mismatch between your confidence and measured quality is flagged.

Output block contains ONLY final response. NO tags in output.
```

---

## Complexity Tiers (Reference)

| Tier | Causal Levels | Interpretation |
|------|---------------|----------------|
| Trivial | 0-1 | Atomic task, no interpretation |
| Light | 2-3 | Simple task, minimal ambiguity |
| Medium | 4-7 | Standard task |
| Thorough | 8-14 | Complex task, good depth |
| Deep | 15-24 | Very complex, extensive analysis |
| Exhaustive | 25+ | Maximum depth |

---

## Files to Create

| File | Purpose |
|------|---------|
| `~/.claude/config/abstraction-policy.json` | Policy configuration |
| `~/.claude/hooks/stop/abstraction-audit.ps1` | Main enforcement hook |
| `~/.claude/topics/ai-principles/ITERATIVE_ABSTRACTION_PROTOCOL.md` | Update with agent instructions |

---

## Implementation Order

1. Update protocol document with agent instructions
2. Create policy config file with defaults
3. Write audit hook (parse, count, output)
4. Add hook to settings.json under Stop event
5. Test with various response types
6. Iterate based on observed behavior
7. Future: A/B test different tag structures

---

## Resolved Design Decisions

1. **Tag set**: I, M, P, C, E, A, D, V, R, T, S (added D for divergent, S for self-assessment)
2. **Output format**: Compact with X markers for untagged (visually obvious)
3. **Tautology [T]**: Required. Keep iterating until reached.
4. **Self-assessment [S]**: Required. Agent declares confidence with rationale.
5. **Tag leaks**: Warn only, adjust confidence down. No blocking.
6. **Two floats**: Scrutiny (task complexity) and Confidence (output quality)
7. **Sentiment detection**: LLM-native during [I] ingestion, not keywords
8. **Mismatch detection**: Harness vs model confidence, lower takes precedence
9. **Regime thresholds**: trusted/supervised/assisted/blocked based on confidence
10. **Output phrasing**: Form for user, content for agent

## Remaining Questions

1. How to handle responses with NO tags at all? (Legacy/non-compliant)
2. Exact sentiment adjustment values - need calibration through use
3. A/B testing infrastructure for tag structures - future scope
4. Should harness compute scrutiny automatically from task analysis?
