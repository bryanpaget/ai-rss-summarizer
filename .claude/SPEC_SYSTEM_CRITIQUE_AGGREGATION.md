# Specification Mapping System - Critique Aggregation

## Critics
- **Claude Agent**: General-purpose critique
- **Gemini Agent**: Web-researched critique with sources

---

## CONSENSUS: Both Critics Agree

### 1. The Proposed Tools Are Overkill
Both critics strongly agree that Doorstop, Z3, and Hypothesis are wrong for this problem.

**Claude**: "You're trying to solve a behavioral problem with a verification problem."

**Gemini**: "The tools are designed for verification of already-formalized specs, but your problem is elicitation of informal specs."

### 2. Z3 Has a Fatal Translation Bottleneck
Both identify the natural language → formal logic translation as the critical weakness.

**Claude**: "If agents could do that reliably, they wouldn't need help mapping specs in the first place."

**Gemini**: "An agent will either under-specify, over-specify, or mis-specify."

### 3. Hypothesis Is Wrong Phase
Both note this tool tests implementations, not specifications.

**Claude**: "More useful for testing implementation than specifications. Might be premature at spec phase."

**Gemini**: "This is like buying a car inspector before you've designed the car."

### 4. Graphviz Has Some Value (Only High-Value Tool)
Both agree visualization is the least objectionable tool.

**Claude**: "Graphviz: High value - Visual verification is powerful and cheap."

**Gemini**: "Marginal value... only useful if the dependency graph reveals something."

### 5. The Real Problem Is Discovery, Not Verification
Both identify a fundamental mismatch between problem and solution.

**Claude**: "The real issue is: agents don't map specs exhaustively because there's no forcing function."

**Gemini**: "You're stuck in recursive formalism. You need discovery, not verification."

### 6. Adversarial/Multi-Agent Approach Is Better
Both recommend agent-vs-agent questioning over tooling.

**Claude**: Not explicitly stated but implies workflow enforcement.

**Gemini**: "Adversarial specification elicitation... This is how security engineers find vulnerabilities."

### 7. Start Simple, Validate Before Building
Both recommend empirical validation over speculative infrastructure.

**Claude**: "Don't build Phase 2-4 before validating Phase 1."

**Gemini**: "Start simple. Make two agents argue about whether a spec is complete."

---

## DISAGREEMENTS / NUANCES

### On Checklists
**Claude**: Recommends structured checklists as part of solution.
**Gemini**: "Checklists won't work because they're static and generic."

### On Doorstop Specifically
**Claude**: "YAML files in Git are just structured markdown with extra steps."
**Gemini**: "Completely wrong tool. It's for aerospace/defense requirements traceability."

Gemini is harsher but both reject it.

---

## RECOMMENDED ALTERNATIVE (Synthesized)

Both critics converge on a similar alternative:

### Phase 1: Adversarial Specification Elicitation
- Blue team agent writes initial spec
- Red team agent attacks it with structured questions:
  - Boundary conditions
  - Failure modes
  - Scope boundaries
  - Performance requirements
  - Implicit assumptions
- Blue team updates spec or documents assumption
- Repeat until red team exhausts questions

### Phase 2: Forcing Function (Workflow Enforcement)
- Specification mode protocol that agents must follow
- Readiness gates that block implementation
- Human review checkpoint before proceeding
- Feedback loop from implementation failures back to spec process

### Phase 3: Lightweight Visualization (Optional)
- Simple dependency graph generation
- Human reviews for obvious gaps
- Could use Mermaid instead of Graphviz

### Phase 4: Formal Verification (Only for Critical Systems)
- Reserve Z3/Alloy for safety-critical, security-sensitive work
- Requires human expert to translate and review
- Not for everyday use

---

## ISSUES TO TRACK

| ID | Issue | Source | Severity |
|----|-------|--------|----------|
| 1 | Z3 translation bottleneck makes it unreliable | Both | CRITICAL |
| 2 | Hypothesis wrong phase (tests implementation) | Both | CRITICAL |
| 3 | Doorstop is aerospace tooling, wrong domain | Both | HIGH |
| 4 | Missing: what specific spec failures are we targeting? | Gemini | HIGH |
| 5 | Missing: forcing function / workflow enforcement | Claude | HIGH |
| 6 | Missing: adversarial discovery protocol | Both | HIGH |
| 7 | Bootstrapping concern remains unaddressed | Both | MEDIUM |
| 8 | Checklists may be too static (disagreement) | Gemini | MEDIUM |
| 9 | Cost-benefit analysis not done | Gemini | MEDIUM |

---

## NEXT STEPS

Based on critique consensus:

1. **Abandon** Doorstop, Z3, Hypothesis from MVP
2. **Keep** Graphviz/Mermaid for optional visualization
3. **Build** adversarial elicitation protocol (two agents, question templates)
4. **Build** specification readiness gate (workflow enforcement)
5. **Validate** with real projects before building tooling
6. **Defer** formal methods to "critical systems only" tier
