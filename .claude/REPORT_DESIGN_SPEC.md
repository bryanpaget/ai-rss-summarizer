# Report Design Specification

**Status:** IMPLEMENTED (2026-01-15), Updated with cluster-based connection detection

Implementation: `src/report.py:_show_final_report()` (lines 1225-1470)

---

## The Briefing - Report Structure

### Design Philosophy

You're not reading RSS. You're getting an **intelligence briefing**.

Raw articles are commodity - anyone can subscribe to feeds. Our value is the **intelligence layer**: what matters, why it matters to you, what connects to what, what you'd miss if you read articles in isolation.

Every section below is personalized. There is no "generic" report.

---

### Section 1: Top Priority

**What it is:** The 1-3 items you cannot skip today.

**How we select:**
- High signal strength (important tags, not ads/fluff)
- Strong match to user interests
- High novelty (not redundant with what you already know)
- Cross-referenced: multiple sources covering it = more important

**For each item:**
- Headline (our framing, not clickbait)
- Why this matters to you (connects to user's tracked interests/context)
- Key insight (the one thing to take away)
- What we know (relevant facts from knowledge base that provide context)
- Developing story? (Yes/No - if yes, link to previous coverage)
- Source link

---

### Section 2: Your Interest Areas

**What it is:** Dynamic sections generated from user's tracked topics. If you track "AI Policy" and "Climate Tech", you get those sections. Someone else gets different sections.

**For each interest area:**
- What's new (brief on new articles matching this interest)
- Connections to your knowledge base
- Story threads (if multiple articles form a narrative)
- Worth reading (ranked list with one-line descriptions + links)

---

### Section 3: Discovered Connections

**What it is:** Insights you couldn't get from reading articles individually. This is where our system earns its keep.

**Types of connections:**
- Cross-source synthesis: articles from different sources about same underlying trend
- Historical echoes: similarity to past events
- Contradictions: conflicting claims across sources
- Pattern confirmation: repeated signals

---

### Section 4: Knowledge Graph Updates

**What it is:** What we learned that's worth remembering.

**Subsections:**
- New entities (people, organizations, concepts)
- Relationship updates
- Confidence changes
- Contradictions to resolve

---

### Section 5: Quick Scan

**What it is:** Everything else, minimal real estate. For completeness, not deep engagement.

Sorted by relevance score descending. Genuinely skippable items marked as such.

---

### Section 6: Session Stats (Optional Footer)

- Articles processed
- From feeds
- Time range
- New insights extracted
- New triples added (from articles)
- Graph triples (from cluster analysis)
- Connections discovered
- Stories updated

---

## Modularity

Each section is a module. The system:
- Generates each section independently
- User can configure which sections they want
- Sections can be reordered
- New section types can be added without rewriting the pipeline

---

## Implementation

Phase 4 synthesis prompt receives:
- All extracted data from Phase 1
- All embeddings from Phase 2
- All discovered connections from Phase 3
- User's interest profile and context
- Template indicating which sections to generate
