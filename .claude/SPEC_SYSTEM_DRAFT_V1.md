# Specification System - Draft Proposal v1

**Purpose:** Design a system that empowers AI coding assistants to write comprehensive, complete specifications before implementation.

---

## Research Synthesis

### What We Learned From Tools

| Tool | Key Insight |
|------|-------------|
| **StrictDoc** | Custom grammar (SDoc DSL) lets you define [DECISION], [RATIONALE], [EDGE_CASE] as first-class elements. Text-based, git-friendly, generates traceability matrices. |
| **Sphinx-Needs** | RST-based requirements in documentation. Agent just reads/writes text files. Queries "needs" database during build. |
| **Doorstop** | Each requirement = one YAML file. Simplest possible structure. CLI-driven validation. |
| **Jama Connect** | "Suspect Links" - when upstream requirement changes, downstream links turn red for review. Don't block, visualize impact. Review Center gives stakeholders simplified UI. |
| **IBM DOORS** | Document view + database backend. RQA uses NLP to score requirement quality (detects "fast", "user-friendly", "approximately"). |
| **Polarion** | Dashboards with custom queries for completeness metrics. Work item workflows enforce gates. |

### What We Learned From Methodologies

| Method | Key Insight |
|--------|-------------|
| **MECE** | Categories must be Mutually Exclusive (no overlap) and Collectively Exhaustive (no gaps). Every input maps to exactly one output path. |
| **CRUD-L Matrix** | For every data entity, define Create, Read, Update, Delete, List operations. Missing operations = incomplete spec. |
| **Gap Analysis** | Map business requirements to functional specs. Any unmapped item = gap. |
| **Use Case Analysis** | Define sunny day (success) AND rainy day (failure) scenarios for every feature. |
| **ISO 29148** | A complete requirement contains: units of measurement, valid ranges, conditions, constraints. |
| **Decision Tables** | For N conditions, must have 2^N rules covering all combinations. |

### What We Learned About Quality Detection

**Weak Words to Flag (Unverifiable):**
- Ambiguity: approximately, almost, about, close to
- Performance: fast, quickly, instantly, efficient
- Usability: user-friendly, easy, simple, intuitive, robust
- Optionality: may, could, should, if possible
- Completeness: etc., and so on, including but not limited to
- Quantity: few, many, several, some, various
- Action: handle, manage, process, support (too vague)

**INCOSE Guidelines:**
1. Use "shall" for mandatory requirements
2. One requirement = one sentence = one test (no compound requirements)
3. Active voice: Actor shall Action Object
4. No negatives: "shall reject" not "shall not accept"
5. No pronouns without clear antecedents

**Quality Scoring (0-100):**
- Base: 100
- -30: Contains weak words
- -20: Passive voice
- -20: Compound requirement (and/or linking actions)
- -15: Missing units for numbers
- -15: Uses "will/would" instead of "shall"
- -10: Sentence too complex (readability)
- Threshold: Score < 70 requires rewrite

### What We Learned About AI Integration

**Prompting Techniques:**
1. **Consultant Persona** - "Act as Business Analyst. Do not generate code. Output 5 clarifying questions."
2. **Refusal Strategy** - "Draft requirements first. Mark vague parts as [TO BE DECIDED] with options."
3. **Chain-of-Thought for Edge Cases** - "Simulate user interaction step-by-step. Where could failure occur?"
4. **Recipe Pattern** - "List every ingredient (data) and utensil (API). Flag missing items."

**Multi-Agent Architecture (from MARE/iReDev):**
- Agent A (Product Owner): Generates user stories from business needs
- Agent B (Architect): Converts stories to technical constraints
- Agent C (QA Engineer): Writes test cases before code
- Mediator: Resolves conflicts between agents

---

## Proposed System Design

### Core Components

**1. Specification Format**
```yaml
spec:
  id: FEAT-001
  title: User Authentication
  type: functional

  requirements:
    - id: REQ-001
      shall: "The system shall accept email and password as login credentials"
      rationale: "Standard authentication pattern"
      acceptance:
        - "Valid email format required"
        - "Password minimum 8 characters"
      edge_cases:
        - "Empty email → Error 400"
        - "Empty password → Error 400"
        - "Invalid format → Error 400"
      dependencies: [DB-001]

  decisions:
    - id: DEC-001
      question: "Session storage mechanism?"
      chosen: "JWT tokens"
      alternatives: ["Server-side sessions", "OAuth only"]
      rationale: "Stateless, scales horizontally"

  constraints:
    - "Response time < 200ms"
    - "Token expiry: 15 minutes"

  unknowns:
    - "Password reset flow - TO BE DECIDED"
```

**2. Completeness Checklist (Automated)**
```
[ ] All requirements use "shall"
[ ] No weak words detected
[ ] Every requirement has acceptance criteria
[ ] Edge cases defined for each requirement
[ ] CRUD-L coverage for all entities
[ ] All decisions documented with rationale
[ ] No unknowns remaining
[ ] Dependencies mapped
[ ] Quality score >= 70 for all requirements
```

**3. Quality Validator**
- Parse spec file
- Run weak word detection
- Check INCOSE compliance
- Calculate quality scores
- Generate completeness report
- Flag items needing attention

**4. Workflow Integration**
```
1. [SPEC] Agent receives task
2. [SPEC] Agent asks clarifying questions (Consultant persona)
3. [SPEC] Agent drafts spec in YAML format
4. [SPEC] Validator runs completeness check
5. [SPEC] Agent iterates until checklist passes
6. [SPEC] User reviews and approves
7. [IMPL] Agent implements against spec
8. [IMPL] Each code unit traces back to requirement ID
```

---

## What This System Achieves

1. **Ensures Completeness** - Checklist and validator catch gaps
2. **Catches Contradictions** - Structured format makes conflicts visible
3. **Visualizes Dependencies** - Dependencies field creates traceability
4. **Signals Readiness** - Checklist passes = ready for implementation
5. **Scales with Complexity** - Simple tasks need few requirements; complex tasks get full structure
6. **Quality Measurable** - Scoring system quantifies requirement quality

---

## Open Questions for Critique

1. Is YAML the right format? Should we use StrictDoc's SDoc instead?
2. Is the quality scoring system too rigid or too lenient?
3. Should we integrate actual NLP libraries or is keyword matching sufficient?
4. How do we handle the "TO BE DECIDED" items - block implementation or proceed with assumptions?
5. Is the checklist comprehensive enough?
6. Should there be a separate "reviewer" view for stakeholders?

---

## Next Steps

1. Critique this proposal
2. Refine based on feedback
3. Build minimal validator
4. Test on real specifications
5. Iterate until robust
