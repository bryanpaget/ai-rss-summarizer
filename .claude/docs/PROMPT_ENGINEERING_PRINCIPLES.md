# Prompt Engineering Principles for Code Documentation

Lessons learned from A/B testing prompt structures for LLM-based documentation generation.

## Core Architecture: Sandwich Prompt

```
[1. ROLE]        - Who the LLM is
[2. TASK]        - What to do (clear verb)
[3. FORMAT]      - Exact output template
[4. RULES]       - Numbered constraints
[5. DELINEATED CONTENT] - Clear start/end markers
[6. EXAMPLE]     - Format demonstration AFTER content
[7. FINAL INSTRUCTION] - Restate what to output
```

## Key Principles

### 1. Role Definition First
Tell the LLM who it is before anything else.

**Good:** "You are a code documentation specialist creating concise function summaries."
**Bad:** Starting directly with "Describe this function..."

### 2. Clear Content Delineation
The LLM must know EXACTLY where file content starts and ends.

```
=== BEGIN CODE ===
[actual code here]
=== END CODE ===
```

Without markers, the LLM may confuse instructions with content.

### 3. Examples AFTER Content (Critical)
**A/B test result:** Examples before content causes contamination.

- Test A (examples before): LLM copied "def add(a, b)" from example
- Test B (examples after): LLM analyzed actual content

**Why:** LLM attention biases toward examples. When examples come first, it sees them as "the answer" and copies structure/names.

### 4. Anti-Contamination Warnings
Even with examples after content, add explicit warnings:

```
=== FORMAT EXAMPLE (do NOT copy - reference only) ===
Lines 1-5: function `example` - Example description

CRITICAL: Examples are FORMAT DEMONSTRATIONS ONLY.
Analyze ONLY the actual code between BEGIN/END markers.
Do NOT output items from examples.
```

### 5. Type Enumeration
List ALL valid types the LLM can use. This prevents hallucinated types.

```
VALID TYPES:
- function: Top-level function
- class: Class definition
- method: Method within class
- constant: Module-level variable
```

### 6. One Output Per Line
Request atomic output format. Multi-line descriptions become inconsistent.

**Good:** "Output ONE LINE per item in format: [type] `name` - description"
**Bad:** Free-form paragraph descriptions

### 7. Verification Instructions
Tell the LLM to verify its output against source:

```
VERIFY: Every line number you output MUST exist in the actual code.
If line 1 is not an import, do NOT output import-block for line 1.
```

## What NOT To Do

### Don't: Let LLM Count Lines
LLMs are bad at counting. Use AST/parser for line numbers.

### Don't: Use Vague Instructions
**Bad:** "Describe the important parts"
**Good:** "Describe EVERY function, class, and method"

### Don't: Skip the Role
Without role framing, LLM defaults to generic assistant behavior.

### Don't: Put Examples First
Contamination is nearly guaranteed when examples precede content.

## Template for Function Description

```
You are a code documentation specialist.

TASK: Write ONE sentence describing what this {type} does.

RULES:
1. Be specific about behavior, not just signature
2. Mention key parameters only if they affect meaning
3. Start with a verb (Parses, Returns, Validates, Creates)
4. No filler words ("This function", "basically", "essentially")

=== BEGIN CODE ===
{code}
=== END CODE ===

ONE SENTENCE (start with verb):
```

## Recursive Splitting Threshold

For functions > 5000 tokens:
1. Extract nested functions/methods via AST
2. Document each nested item separately
3. Parent gets summary mentioning it contains N nested items

This prevents context window issues and improves description quality.
