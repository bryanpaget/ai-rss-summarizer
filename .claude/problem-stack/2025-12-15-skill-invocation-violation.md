# KB:KBM
# Problem Stack: Skill Invocation Violation
**Created:** 2025-12-16T00:10:00-08:00
**Status:** ACTIVE

---

## Violation

**What happened:** Called knowledge-query.sh directly via Bash instead of using the knowledge-retriever skill.

**Why this is wrong:** Skills have a defined invocation pattern. Using Bash bypasses the skill system.

**Concrete action:** Use the Skill tool to invoke knowledge-retriever.

---
