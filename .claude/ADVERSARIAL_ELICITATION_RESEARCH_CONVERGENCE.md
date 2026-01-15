# Adversarial Specification Elicitation - Research Convergence

**Date:** 2025-12-16
**Research Agents:** Gemini (a0cd70e), Claude (ac13f9d)
**Context:** Second research round after critics rejected Z3/Hypothesis/Doorstop

---

## CONSENSUS: Both Agents Agree

### 1. No Unified Framework Exists

**Gemini:** "No dedicated tool exists specifically for adversarial specification elicitation."

**Claude:** "There is no unified open-source framework specifically designed for adversarial specification elicitation."

**Implication:** We must combine existing components or build custom tooling.

### 2. Components Exist Across Three Categories

| Category | Gemini Found | Claude Found | Overlap |
|----------|-------------|--------------|---------|
| **Multi-Agent Orchestration** | AutoGen, CrewAI, LangGraph | AutoGen, CrewAI, LangGraph, ChatDev, MetaGPT, CAMEL | HIGH |
| **Red-Team Attack Patterns** | PyRIT, Garak, Microsoft AI Red Team | DeepTeam, PyRIT, Garak, Promptfoo | HIGH |
| **Questioning Frameworks** | Laddering, Context-Free, BABOK | SocraticAI, iReDev, Socratic Prompting | MEDIUM |

### 3. Multi-Agent Debate (MAD) Is Promising but Immature

**Gemini:** Found MARE (Multi-Agent Requirements Engineering), Elicitron (user simulation)

**Claude:** Found D3 (Debate, Deliberate, Decide), Multi-Agents-Debate (GitHub), MAD for RE

**Shared concerns:**
- Conformity bias ("sycophancy") where agents adopt peer outputs
- Homogeneous groups risk echo chambers
- Extended debate doesn't always improve outcomes
- Requires human adjudication for validation

### 4. Red-Team Tools Need Adaptation

Both agents agree: security red-team tools (DeepTeam, PyRIT, Garak) target **vulnerabilities**, not **requirements gaps**. But attack patterns can be adapted:

| Security Attack | Specification Question |
|-----------------|----------------------|
| Boundary conditions | What happens at edge cases? |
| Input validation | What inputs are invalid? |
| State manipulation | What state transitions are undefined? |
| Bias detection | What assumptions are implicit? |
| PII leakage | What data handling is required? |

### 5. iReDev Is Closest to Our Needs

**Claude:** iReDev (2025) "A Knowledge-Driven Multi-Agent Framework for Intelligent Requirements Development"
- Follows ISO/IEC/IEEE 29148 and BABOK v3
- Uses 5W1H, Socratic inquiry, iterative paraphrasing
- **Adaptation Potential: VERY HIGH**

**Gemini:** Did not find iReDev specifically but found similar Socratic questioning approaches.

---

## UNIQUE FINDINGS

### Gemini Only

| Tool | What It Does | Relevance |
|------|--------------|-----------|
| **Elicitron** | LLM agents simulate diverse users to surface unstated needs | HIGH - discovery phase |
| **MARE** | Five agents (stakeholder, collector, modeler, checker, documenter) | HIGH - checker agent validates |
| **Creative Adversarial Testing (CAT)** | Finds gap between "what system does" and "what it should achieve" | HIGH - goal-task alignment |
| **Gap Analysis Team (GAT)** | CrowdStrike methodology for detection gaps | MEDIUM - different domain |

### Claude Only

| Tool | What It Does | Relevance |
|------|--------------|-----------|
| **D3 (Debate, Deliberate, Decide)** | Cost-aware adversarial framework with advocates + judge + jury | HIGH - formalized protocol |
| **ED2D** | Evidence-driven debate for misinformation detection | MEDIUM - adaptable |
| **ELK (Eliciting Latent Knowledge)** | Builder-breaker game from alignment research | HIGH - adversarial validation |
| **SocraticAI** | Three-agent Socratic questioning (Princeton NLP) | HIGH - direct application |
| **Specification by Example** | Concrete examples expose gaps | MEDIUM - complementary |

---

## RECOMMENDED TOOL STACK

Based on convergence of both agents:

### Tier 1: Core Framework (Must Have)

| Component | Tool | Why |
|-----------|------|-----|
| **Orchestration** | AutoGen | Both agents recommend; flexible debate structure |
| **Attack Library** | DeepTeam | Open source, 40+ patterns, extensible |
| **Questioning** | SocraticAI patterns + iReDev techniques | Direct RE application |

### Tier 2: Valuable Additions (Should Have)

| Component | Tool | Why |
|-----------|------|-----|
| **Simulation** | Elicitron patterns | User perspective discovery |
| **Formalization** | D3 protocols | Structured debate rounds |
| **Validation** | ELK builder-breaker game | Adversarial completeness check |

### Tier 3: Infrastructure (Nice to Have)

| Component | Tool | Why |
|-----------|------|-----|
| **State Management** | LangGraph | Complex workflow tracking |
| **Alternative Orchestration** | CrewAI | Faster prototyping |
| **Traceability** | Sphinx-Needs | Post-debate gap mapping |

---

## GAPS: What Neither Agent Found

1. **Specification-specific attack library** - 40+ templates targeting requirements (not security)
2. **Automated gap detection from debate logs** - NLP to identify unresolved questions
3. **Completeness metrics** - Standard for "is this spec done?"
4. **Debate protocol standard** - Like BPMN but for spec review
5. **Integration tooling** - Connectors to Jira, GitHub, etc.

---

## RECOMMENDED PATH

### Option A: Minimal Custom (Low Effort)
- Use AutoGen with manually crafted red/blue team prompts
- Adapt DeepTeam attack categories to specification questions
- Manual gap analysis from debate transcripts
- **Effort:** Days
- **Risk:** Low automation, relies on prompt quality

### Option B: Prototype Framework (Medium Effort)
- Build SpecDebate wrapper around AutoGen
- Create YAML-based attack library (40+ templates)
- Implement basic gap detection (keyword extraction)
- **Effort:** Weeks
- **Risk:** Maintenance burden, may need iteration

### Option C: Full Framework (High Effort)
- SpecDebate with all three tiers
- NLP-based gap detection
- Metrics dashboard
- Open source release
- **Effort:** Months
- **Risk:** Scope creep, over-engineering

---

## DECISION NEEDED

User should decide:

1. **Scope:** Minimal, Prototype, or Full framework?
2. **Starting point:** AutoGen vs CrewAI vs LangGraph?
3. **Attack library:** Adapt DeepTeam or write custom templates?
4. **Integration:** Standalone tool or integrate with existing workflow?

---

## NEXT STEPS (After User Decision)

1. Create specification for chosen approach (staying in SPEC mode)
2. Define attack template categories
3. Design debate protocol (rounds, roles, termination)
4. Prototype with one existing spec as test case
5. Validate and iterate

---

## SOURCE DOCUMENTS

- Gemini Research: Task a0cd70e output (inline)
- Claude Research: ADVERSARIAL_SPECIFICATION_ELICITATION_RESEARCH.md (project root)
- Original Critique: .claude/SPEC_SYSTEM_CRITIQUE_AGGREGATION.md
