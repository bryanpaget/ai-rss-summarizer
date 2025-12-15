# Trend Analysis Features - Implementation Plan

This document describes the advanced trend analysis features planned for the RSS summarizer.

## Design Principles (from KB Philosophy)

| Principle | Application |
|-----------|-------------|
| **Uncertainty Reduction** | Reduce noise aggressively. Provide calibrated signals for action. |
| **Back-propagation** | Learning compounds. Build knowledge base from insights. |
| **Specifics Matter** | Personal context uses YOUR actual work, not generic categories. |
| **Full Understanding** | Show what's certain, contested, and unknown separately. |

---

## Feature 1: Two-Level Story Clustering & Evolution Tracking

### Problem
When a story develops, outlets churn through information at different rates. An article might contain:
- **New information** (actual news)
- **Recap/context** (background for readers)
- **Analysis/opinion** (commentary on the news)

Current systems cluster "same story" but don't distinguish what's actually NEW.

### Solution: Two-Level Clustering

**Level 1: Story Identification**
- Is this article about the same ongoing story?
- Cluster articles into story groups

**Level 2: News Item Identification**
- Within a story, what specific news item does this article address?
- Extract: What does this article claim is NEW information?
- Track when new information emerges (multiple providers reference it)

### Output Example
```
STORY: "EU AI Act Implementation"

NEWS ITEM 1 (Dec 10): Parliament vote passes
  - Reuters: First to report (primary source)
  - TechCrunch: Analysis of implications (secondary)
  - BBC: General coverage with recap (secondary)

NEWS ITEM 2 (Dec 12): Industry response
  - Bloomberg: Industry quotes (primary)
  - Wired: Analysis piece (commentary)

NEWS ITEM 3 (Dec 14): Compliance timeline
  - Politico: Official timeline leaked (primary)
  - Others: Picking up the story...
```

### Value
- Track information flow across providers
- See which outlet broke specific news
- Distinguish actual developments from recap/analysis
- Cross-provider comparison on same news item

---

## Feature 2: Signal Tagging System

### Problem
Single scores (85/100) don't communicate meaning intuitively. What does "Evidence: 85" mean? High quality? High quantity? Numbers lose semantic content.

### Solution: Descriptive Tags Instead of Numbers

Replace numeric scores with meaningful tags that communicate actual qualities.

### Tag Categories

**Source Type**
- `primary` - Original reporting, first-hand sources
- `secondary` - Reporting on other reports
- `aggregator` - Compiled from multiple sources
- `press-release` - Corporate/official announcement
- `speculative` - Based on rumors/unnamed sources
- `satirical` - Intentionally humorous/exaggerated

**Evidence Handling**
- `well-sourced` - Multiple named sources
- `single-source` - One source only
- `anonymous-sources` - Unnamed insiders
- `documented` - Links to primary documents
- `unverified` - Claims without backing

**Reasoning Quality**
- `logical` - Sound deductions from evidence
- `non-sequitur` - Conclusions don't follow from premises
- `cherry-picked` - Selective evidence use
- `balanced` - Multiple perspectives considered

**Tone/Style**
- `factual` - Neutral reporting
- `analytical` - Deep analysis
- `opinion` - Clearly editorial
- `sensational` - Clickbait/hype
- `spicy` - Hot takes, provocative
- `unhinged` - Wild speculation (fun filter!)

**Actionability**
- `actionable` - Contains info you can act on
- `awareness` - Good to know, no action needed
- `noise` - No signal value

### Output Example
```
"OpenAI Board Drama: Inside Sources Reveal..."

Tags: [secondary] [anonymous-sources] [spicy] [speculative]
Summary: Entertaining read but treat claims skeptically

vs.

"EU AI Act: Full Text Released"

Tags: [primary] [documented] [factual] [actionable]
Summary: Official document, read if you need compliance info
```

### User-Defined Tag Filters
Users can filter by tags:
- "Show me only `primary` + `documented`" (serious research)
- "Show me `spicy` + `speculative`" (entertainment)
- "Hide all `press-release`" (skip PR)

---

## Feature 3: Perspective Synthesis with User Categories

### Problem
Fixed perspective categories don't match what users actually want to see.

### Solution: User-Defined Perspective Categories

Offer 12+ perspective categories. User chooses which to display.

### Available Categories

**Factual**
- `consensus` - What all sources agree on
- `contested` - Where sources disagree
- `gaps` - What no one is covering
- `timeline` - Chronological fact sequence

**Source Framing**
- `tech-industry` - How tech press frames it
- `mainstream` - General news framing
- `financial` - Business/market angle
- `political` - Policy/government angle
- `academic` - Research perspective

**Fun/Entertainment**
- `spiciest-takes` - Most provocative opinions
- `unhinged-speculation` - Wildest predictions
- `contrarian` - Against-the-grain views
- `doom` - Pessimistic takes
- `hype` - Most optimistic takes

**Analysis**
- `expert-quotes` - What actual experts say
- `prediction-track-record` - How past predictions held up

### Output Example
```
Story: "GPT-5 Rumors"

[consensus]
- OpenAI is working on next model (confirmed)
- No official release date

[spiciest-takes]
- "Will make all other AI obsolete" - TechBro Weekly
- "Skynet but with better UX" - @doomer_ai

[contrarian]
- "Incremental improvement at best" - AI researcher blog
```

---

## Feature 4: Adaptive Personal Context Engine

### Problem
Static user profiles become stale. User priorities change.

### Solution: Adaptive Context with Feedback Loops

### Initial Setup
```yaml
role: ML engineer at fintech startup
current_projects:
  - Fraud detection deployment
  - Claude vs GPT-4 evaluation
watching: [AI regulation, embedding models]
ignore: [crypto, celebrity tech]
```

### Feedback Mechanisms

**Explicit Feedback**
- Periodic prompt: "How are these summaries? Still relevant?"
- Quick reactions: thumbs up/down on recommendations
- Edit profile: "I'm done with the Claude evaluation"

**Implicit Learning**
- Track: Articles expanded/read vs. skipped
- Track: Time spent on articles
- Track: Articles saved/shared
- Adjust relevance scoring based on behavior

### Feedback Prompt Example
```
Weekly Check-in:

This week I marked these as HIGH relevance:
- AI regulation (3 articles read)
- Embedding models (2 articles read)

These were marked relevant but you skipped them:
- Rust performance (0 of 2 read)

Should I:
[ ] Keep current settings
[ ] Reduce "Rust" priority
[ ] Something changed - let me update
```

### Relevance Decay
- Projects completed → reduce relevance
- Topics not engaged with → gradually deprioritize
- User can "pin" topics to prevent decay

---

## Feature 5: Emergence Detection

Tracks weak signals before they become trends.

### What It Tracks
- **Terminology emergence**: New phrases in technical articles
- **Cross-domain connections**: Unusual topic combinations
- **Acceleration**: Mention velocity changes
- **Expert pivots**: Researchers moving to new areas

### Output Example
```
EMERGING (8 mentions, up from 1 two months ago)
"Constitutional AI"
  Trajectory: Research → Blogs → Mainstream
  Time to peak: ~2-4 months
  Action: Learn now before it's everywhere

ACCELERATING (15/week, was 3/week)
"Mixture of Experts"
  Status: Entering mainstream adoption
  Action: If unfamiliar, prioritize learning
```

---

## Feature 6: Knowledge Extraction & Accumulation

Builds a queryable personal knowledge base from articles you read.

### What It Extracts
- **Technical learnings** with confidence levels
- **Tools/resources** mentioned
- **Connections** to your existing knowledge
- **Contradictions** with previous extractions

### Output Example
```
From: "Production LLM Learnings"

EXTRACTED:
"Streaming reduces perceived latency 40%"
  Confidence: High (cited study)
  Related to: Your customer service project

CONNECTION:
This contradicts your Oct 15 note about streaming complexity
```

### Queryable
```
> What have I learned about LLM latency?

From 12 articles:
- Streaming (4 sources): 30-40% perceived improvement
- Prompt caching (3 sources): Cost + some latency benefit
- Smaller models for simple tasks (2 sources)
```

---

## Feature 7: Intelligence Brief Generation

Periodic synthesis into actionable intelligence.

### Contents
- **Macro themes**: Big picture this week
- **Counter-narratives**: Hype vs reality
- **Your reading list**: Exactly what to read, time-estimated
- **Safely ignored**: Noise confidently filtered

### Output Example
```
WEEKLY BRIEF - Dec 16, 2024

MACRO THEME: "AI Safety → Regulatory Reality"
  What changed: Policy moved from theoretical to actionable
  Why it matters: Affects your deployment timeline

COUNTER-NARRATIVE:
  "AI replacing all jobs" - volume up 20%
  Reality check: Studies show mixed results

YOUR READING LIST (18 min):
1. [Claude updates] - affects active decision (5 min)
2. [EU compliance] - affects Q2 launch (8 min)

SAFELY IGNORED:
- Twitter AI drama (no signal)
- GPT-5 rumors (unsubstantiated)
```

---

## Implementation Order

Suggested sequence based on dependencies:

1. **Story Clustering** - Foundation for everything else
2. **Signal Tagging** - Core quality layer
3. **Personal Context** - Relevance filtering
4. **Perspective Synthesis** - Multi-source analysis
5. **Intelligence Brief** - Synthesis of above
6. **Knowledge Extraction** - Long-term value
7. **Emergence Detection** - Advanced pattern recognition

---

## GitHub Issues

Each feature should have a GitHub issue for tracking. See issues #14-20.
