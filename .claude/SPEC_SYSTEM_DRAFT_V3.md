# Specification System - Draft Proposal v3

**Purpose:** Empower AI coding assistants to write comprehensive, complete specifications before implementation.

**Changes from v2:** Added missing domains (Usability, Maintainability, Resilience), Progressive Specification (Lite vs Full modes), EARS syntax patterns, Agent-resolvable unknowns, Hostile QA critic prompt, Multi-service hierarchy.

---

## Core Design Principles

1. **Progressive Specification** - Simple tasks get simple specs; complex tasks get full structure.
2. **No Process Paralysis** - If the spec is longer than the code, the process is broken.
3. **Blockers vs Warnings** - Critical issues halt progress; minor issues get flagged.
4. **Hostile QA** - Critic finds loopholes, not just validates syntax.
5. **Agent Self-Service** - Technical unknowns resolved by agent; business unknowns escalated to user.

---

## Progressive Specification Levels

### Level 1: Lite Spec (Simple Tasks)

For tasks where Complexity < 3 (single file, clear outcome, no architectural decisions).

**User provides markdown:**
```markdown
## Task: Fix login button alignment

**What:** The login button on /auth/login is misaligned on mobile screens.

**Success:** Button is centered on screens < 768px wide.

**Constraints:** Don't change desktop layout.
```

**Agent internally converts to structured format but doesn't burden user with YAML.**

### Level 2: Standard Spec (Features)

For tasks with 3+ steps, multiple files, or user decisions required.

Uses the full YAML schema (see below).

### Level 3: System Spec (Architecture)

For multi-service changes, defines global constraints that all service specs inherit.

```yaml
system_spec:
  id: SYS-AUTH
  title: Authentication System
  global_constraints:
    - "All APIs shall use JSON-API response format."
    - "All services shall log to centralized ELK stack."
    - "All PII shall be encrypted at rest using AES-256."

  services:
    - service: auth-service
      spec_file: ./specs/auth-service.yaml
    - service: user-service
      spec_file: ./specs/user-service.yaml
```

---

## Completeness Domains (Updated)

| Domain | What It Covers | When Required |
|--------|----------------|---------------|
| **Functional** | What the system does | Always |
| **Security** | AuthZ, AuthN, data protection | When handling user data or auth |
| **Performance** | Latency, throughput, capacity | When SLAs exist or scale matters |
| **Observability** | Logging, metrics, tracing | When debugging/monitoring needed |
| **Resilience** | Failure modes, recovery, retries | When external dependencies exist |
| **Data** | Storage, retention, migration | When persisting data |
| **Integration** | External systems, APIs | When calling external services |
| **Usability** | UI/UX, accessibility, WCAG | When user-facing (frontend/CLI) |
| **Maintainability** | Tech debt, complexity limits | When touching core/shared code |

**Rule:** Mark domains as N/A with rationale if not applicable. Missing domains without N/A = blocker.

---

## EARS Requirement Syntax

All requirement statements MUST follow one of these patterns:

| Pattern | Syntax | Example |
|---------|--------|---------|
| **Ubiquitous** | "The system shall [action]." | "The system shall hash passwords using bcrypt." |
| **Event-Driven** | "When [event], the system shall [action]." | "When login fails, the system shall log the attempt." |
| **State-Driven** | "While [state], the system shall [action]." | "While rate-limited, the system shall return 429." |
| **Unwanted** | "If [condition], the system shall [action]." | "If database unreachable, the system shall retry 3x." |
| **Optional** | "Where [feature enabled], the system shall [action]." | "Where MFA enabled, the system shall require 2FA." |

**Why EARS:** Prevents vague "The system shall be fast" statements. Every requirement has explicit context or trigger.

---

## Full YAML Schema (Level 2)

```yaml
spec:
  id: SPEC-001
  title: User Authentication Service
  version: 1.0
  status: DRAFT  # DRAFT | REVIEW | APPROVED | BLOCKED
  complexity: 5  # 1-10, determines validation strictness

  # WHY - Business context
  objective: >
    Enable users to securely authenticate using email/password,
    supporting session management and secure credential storage.

  # DEFINITIONS - Prevent ambiguity
  terms:
    - term: "Active Session"
      definition: "A JWT token that has not expired (15 min) and has not been revoked."
    - term: "Failed Attempt"
      definition: "An authentication request returning 401 status code."

  # REQUIREMENTS - Using EARS patterns
  requirements:
    - id: REQ-001
      pattern: UBIQUITOUS
      statement: "The system shall accept email and password as login credentials."
      domain: FUNCTIONAL
      priority: P0
      acceptance_criteria:
        - given: "Valid credentials"
          then: "Return 200 with JWT token"
        - given: "Invalid credentials"
          then: "Return 401 Unauthorized"
        - given: "Malformed request body"
          then: "Return 400 Bad Request"
      edge_cases:
        - input: "Empty email"
          expected: "400 with error code 'email_required'"
        - input: "Email > 255 characters"
          expected: "400 with error code 'email_too_long'"
        - input: "SQL injection in email"
          expected: "400 with error code 'invalid_email_format'"
      traces_to: [STORY-001]

    - id: REQ-002
      pattern: UBIQUITOUS
      statement: "The system shall hash passwords using bcrypt with cost factor 12."
      domain: SECURITY
      priority: P0
      rationale: "OWASP recommendation for password storage (2024)."
      acceptance_criteria:
        - given: "Any password storage operation"
          then: "Stored value is bcrypt hash, never plaintext"

    - id: REQ-003
      pattern: EVENT_DRIVEN
      statement: "When login fails, the system shall log the attempt with IP and timestamp."
      domain: OBSERVABILITY
      priority: P1
      acceptance_criteria:
        - given: "Failed login"
          then: "Log entry created with: email, IP, timestamp, failure_reason"
        - given: "Log entry"
          then: "Password never included in log"

    - id: REQ-004
      pattern: STATE_DRIVEN
      statement: "While under rate limit, the system shall return 429 Too Many Requests."
      domain: RESILIENCE
      priority: P1
      acceptance_criteria:
        - given: "> 10 requests per minute from same IP"
          then: "Return 429 with Retry-After header"

    - id: REQ-005
      pattern: UNWANTED
      statement: "If database connection fails, the system shall retry 3 times with exponential backoff."
      domain: RESILIENCE
      priority: P1
      acceptance_criteria:
        - given: "DB connection timeout"
          then: "Retry at 1s, 2s, 4s intervals"
        - given: "3 retries exhausted"
          then: "Return 503 Service Unavailable"

  # DECISIONS - With alternatives considered
  decisions:
    - id: DEC-001
      question: "Session storage mechanism?"
      chosen: "JWT tokens (stateless)"
      alternatives:
        - option: "Server-side sessions with Redis"
          rejected_because: "Requires shared session store, complicates horizontal scaling."
        - option: "OAuth2 with external provider"
          rejected_because: "Adds external dependency for internal-only service."
      rationale: "Stateless tokens enable horizontal scaling without shared state."

  # CONSTRAINTS - Hard boundaries
  constraints:
    - "Must integrate with existing PostgreSQL database (v14+)."
    - "Must not introduce new infrastructure dependencies."
    - "Response latency p99 < 500ms under normal load."

  # UNKNOWNS - Categorized by who can resolve
  unknowns:
    - id: UNK-001
      question: "What is the password reset flow?"
      type: BUSINESS  # BUSINESS (user decides) | TECHNICAL (agent researches)
      impact: "Cannot implement forgot-password endpoint."
      status: OPEN
      assignee: USER

    - id: UNK-002
      question: "What auth library is currently used in the codebase?"
      type: TECHNICAL
      impact: "Need to determine if new library needed or can extend existing."
      status: OPEN
      assignee: AGENT
      resolution_action: "Search codebase for auth imports and configuration."

  # DOMAIN COVERAGE - Explicit tracking
  domain_coverage:
    FUNCTIONAL: [REQ-001]
    SECURITY: [REQ-002]
    OBSERVABILITY: [REQ-003]
    RESILIENCE: [REQ-004, REQ-005]
    PERFORMANCE: []  # Covered by constraints
    DATA: N/A  # Using existing schema
    INTEGRATION: N/A  # No external services
    USABILITY: N/A  # Backend API only
    MAINTAINABILITY: N/A  # New service, no legacy concerns

  # VALIDATION - Generated by Critic Agent
  validation:
    timestamp: null
    status: BLOCKED
    blockers:
      - "UNK-001 (BUSINESS) unresolved - escalate to user"
    warnings:
      - "UNK-002 (TECHNICAL) unresolved - agent should research"
      - "REQ-001 has 3 edge_cases, consider more boundary conditions"
    coverage_check:
      complete: [FUNCTIONAL, SECURITY, OBSERVABILITY, RESILIENCE]
      missing: []
      marked_na: [DATA, INTEGRATION, USABILITY, MAINTAINABILITY]
```

---

## Critic Agent Prompt (Hostile QA)

```
You are a hostile QA Lead reviewing a software specification. Your job is NOT to
validate syntax - your job is to find LOOPHOLES.

A loophole is anything that would allow a lazy developer to deliver broken code
while technically meeting the requirements.

For each requirement, ask:
1. "What input could break this that isn't listed in edge_cases?"
2. "What state could the system be in where this requirement is ambiguous?"
3. "If I implement ONLY what's written here, what user expectations would be violated?"

For the spec as a whole, ask:
1. "What domains are missing or marked N/A that should be covered?"
2. "What decision was made implicitly that should be explicit?"
3. "What would a senior engineer ask in a design review?"

Output:
- BLOCKERS: Issues that MUST be fixed before implementation.
- WARNINGS: Issues that SHOULD be fixed but won't break the build.
- LOOPHOLES: Specific ways the spec could be "gamed" by minimal compliance.

If you find ZERO loopholes, the spec PASSES. Otherwise, list each loophole with
a suggested fix.
```

---

## Workflow Summary

```
User Request
     │
     ▼
┌─────────────────┐
│ Complexity < 3? │
└────────┬────────┘
         │
    YES  │  NO
    │    │
    ▼    ▼
Lite   Full YAML
Spec   Spec
    │    │
    └─┬──┘
      │
      ▼
┌─────────────────────┐
│ Agent resolves      │
│ TECHNICAL unknowns  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Hostile QA Critic   │
│ reviews spec        │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    │             │
BLOCKERS?    NO BLOCKERS
    │             │
    ▼             ▼
Refine      User Review
Loop        (resolves BUSINESS unknowns)
    │             │
    └──────┬──────┘
           │
           ▼
      APPROVED
           │
           ▼
    Implementation
    (code traces to REQ-IDs)
```

---

## What This Achieves

1. **Right-sized process** - Simple tasks aren't over-specified
2. **Complete coverage** - Domain checklist catches blind spots
3. **Quality requirements** - EARS patterns prevent vague statements
4. **Self-service** - Agent resolves what it can, escalates what it can't
5. **Adversarial validation** - Finds loopholes, not just syntax errors
6. **Traceability** - Every requirement traceable, every decision documented

---

## Remaining Questions

1. Is the Lite Spec mode well-defined enough?
2. Are there edge cases in the workflow that aren't handled?
3. Is this implementable with current Claude Code capabilities?
