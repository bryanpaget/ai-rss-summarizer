# Project Documentation

Generated: 2026-01-18 22:24:07

**Stats:** 89 files, 89 functions, 6 classes, ~42233 lines

**Cache:** 91 cached, 120 new, 5 changed

**Timing:** 365.0s LLM time

---

## System Overview

## Architecture Overview: Claude Project

**1. Purpose:** This project appears to be a collection of documentation, specifications, and notes related to the development and maintenance of a system named "Claude." The focus seems to be on addressing issues, planning improvements, and defining the system's architecture and functionality.

**2. Key Modules:**

* **`.claude\CLAUDE.md` (390 lines):** This file likely contains core design specifications and potentially high-level architectural decisions for the Claude system itself. It seems to be a central document outlining the system's purpose, components, and interactions.
* **`.claude\PIPELINE_ISSUES_TRACKING.md` (247 lines):** This file suggests a module dedicated to tracking issues and challenges within the Claude system's pipeline. It likely details problems encountered during development or deployment.
* **`.claude\SPEC_SYSTEM_DRAFT_V3.md` (346 lines):**  This document appears to be the most recent iteration of the system specification, outlining detailed requirements and design decisions for the Claude system. 
* **`.claude\docs\PROMPT_ENGINEERING_PRINCIPLES.md` (124 lines):** This file indicates a module focused on guidelines and best practices for prompt engineering within the Claude system, suggesting it interacts with a language model or similar component.
* **`.claude\PIPELINE_REDESIGN_PROPOSAL.md` (361 lines):**  This document outlines proposals for redesigning aspects of the Claude pipeline, indicating ongoing efforts to improve its efficiency and robustness.

**3. Entry Points:** The codebase doesn't explicitly define a single entry point. However, given the prevalence of documentation files, it's likely that the project is intended to be consumed through reading and updating these documents rather than executing a compiled application.  The `PROMPT_ENGINEERING_PRINCIPLES` file might suggest an interaction with a system that takes prompts as input.

**4. Languages/Stack:** The codebase primarily consists of Markdown files (`.md`). There is no indication of specific programming languages or frameworks used within the code itself, suggesting this project is largely documentation-driven.  The presence of `signal-completion-log.md` suggests potential interaction with a system that generates and logs signals, possibly related to a machine learning model.





---

## File Documentation

### .auto-claude-security.json

**Lines:** 185

- Lines 1-185: json_file `.auto-claude-security.json` - Identifies and categorizes commands into base, stack, and custom categories based on their typical usage.

---

### .auto-claude-status

**Lines:** 26

- Lines 1-26: file `.auto-claude-status` - Tracks the progress of comprehensive testing for a module, detailing completed subtasks, current phase, and session information.

---

### .claude\ADVERSARIAL_ELICITATION_RESEARCH_CONVERGENCE.md

**Lines:** 177

- Lines 1-177: markdown_file `ADVERSARIAL_ELICITATION_RESEARCH_CONVERGENCE.md` - Analyzes existing multi-agent orchestration, red-teaming, and questioning frameworks to identify components for building a custom adversarial specification elicitation tool.

---

### .claude\BACKLOG.md

**Lines:** 68

- Lines 1-68: markdown_file `BACKLOG.md` - Handles user-defined principles and values from a markdown file to guide analysis across various modules like insight extraction, prompt building, signal tagging, and report generation.

---

### .claude\BLOCKING_PRIORITY.md

**Lines:** 76

- Lines 1-76: markdown_file `BLOCKING_PRIORITY.md` - Documents the project's architecture, dependencies, and change impact rules to ensure a clear understanding of the system and prevent regressions.

---

### .claude\CLAUDE.md

**Lines:** 390

- Lines 1-390: markdown_file `CLAUDE.md` - Formats the intelligence briefing output according to the REPORT_DESIGN_SPEC.md specification, including sections for top priorities, user interests, discovered connections, knowledge graph updates, a quick scan, and session statistics.

---

### .claude\COMPACTION_HANDOFF_20251216.md

**Lines:** 10

- Lines 1-10: markdown_file `COMPACTION_HANDOFF_20251216.md` - Documents a session handoff from December 2025 that addressed knowledge system issues, now superseded by later work.

---

### .claude\COMPACTION_HANDOFF_20251216_V2.md

**Lines:** 10

- Lines 1-10: markdown_file `COMPACTION_HANDOFF_20251216_V2.md` - Documents the status and provides a link to a related pipeline issue tracking report for a superseded session handoff from December 2025.

---

### .claude\GATEWAY_INVESTIGATION.md

**Lines:** 153

- Lines 1-153: markdown_file `GATEWAY_INVESTIGATION.md` - Analyzes gateway logs to identify a race condition in the queue sorting process that caused request loss and script crashes due to concurrent file modification.

---

### .claude\HANDOFF_20260112_KNOWLEDGE_EXTRACTION.md

**Lines:** 12

- Lines 1-12: markdown_file `HANDOFF_20260112_KNOWLEDGE_EXTRACTION.md` - Documents project and process principles in markdown files for knowledge management and enforcement.

---

### .claude\HANDOFF_20260113_CODEBASE_AUDIT.md

**Lines:** 10

- Lines 1-10: markdown_file `HANDOFF_20260113_CODEBASE_AUDIT.md` - Addresses code audit findings by implementing features like session tagging, connection detection, and schema versioning.

---

### .claude\HANDOFF_20260113_EMBEDDING_FIXES.md

**Lines:** 15

- Lines 1-15: markdown_file `HANDOFF_20260113_EMBEDDING_FIXES.md` - Implements embedding-based similarity for topic matching, item similarity, and triple finding, providing fallbacks when the EmbeddingService is unavailable.

---

### .claude\HANDOFF_20260113_GATEWAY_ARCHITECTURE.md

**Lines:** 26

- Lines 1-26: markdown_file `HANDOFF_20260113_GATEWAY_ARCHITECTURE.md` - Investigates potential JSON errors in the gateway architecture to address file race conditions during response handling.

---

### .claude\HANDOFF_20260114_ITERATIVE_ABSTRACTION.md

**Lines:** 16

- Lines 1-16: markdown_file `HANDOFF_20260114_ITERATIVE_ABSTRACTION.md` - Documents the completion of tasks related to a session handoff, including documentation fixes, abstraction enforcement, and protocol hole filling.

---

### .claude\HANDOFF_20260118_codebase_explorer.md

**Lines:** 52

- Lines 1-52: markdown_file `HANDOFF_20260118_codebase_explorer.md` - Parses code in multiple languages using Tree-sitter and LLM fallback, creating a searchable index of functions and classes within any project.

---

### .claude\HANDOFF_REPORT_AND_SCHEDULE_FEATURES.md

**Lines:** 33

- Lines 1-33: markdown_file `HANDOFF_REPORT_AND_SCHEDULE_FEATURES.md` - Improves the report generation pipeline and implements a schedule command using OS task schedulers to address gaps in RSS feed updates.

---

### .claude\PIPELINE_ISSUES_TRACKING.md

**Lines:** 247

- Lines 1-247: markdown_file `PIPELINE_ISSUES_TRACKING.md` - Documents identified issues with the report pipeline and proposes solutions focused on optimizing LLM calls for efficiency and scalability.

---

### .claude\PIPELINE_REDESIGN_PROPOSAL.md

**Lines:** 361

- Lines 1-361: markdown_file `PIPELINE_REDESIGN_PROPOSAL.md` - Defines a pipeline redesign to improve efficiency by consolidating LLM and embedding calls into distinct phases, minimizing model switches and redundant data processing.

---

### .claude\REPORT_DESIGN_SPEC.md

**Lines:** 142

- Lines 1-142: markdown_file `REPORT_DESIGN_SPEC.md` - Generates a personalized intelligence briefing report with sections on top priorities, user interests, and discovered connections, prioritizing insights beyond individual articles.

---

### .claude\SPECIFICATION_SYSTEM_FINAL_REPORT.md

**Lines:** 263

- Lines 1-263: markdown_file `SPECIFICATION_SYSTEM_FINAL_REPORT.md` - Creates a specification system that guides AI coding assistants to generate comprehensive requirements before code implementation, employing progressive complexity and adversarial questioning for improved quality.

---

### .claude\SPEC_SYSTEM_CRITIQUE_AGGREGATION.md

**Lines:** 135

- Lines 1-135: markdown_file `SPEC_SYSTEM_CRITIQUE_AGGREGATION.md` - Analyzes the suitability of various tools (Claude Agent, Gemini Agent, Doorstop, Z3, Hypothesis, and Graphviz) for eliciting informal specifications, concluding that verification tools are inappropriate and an adversarial multi-agent approach is more effective.

---

### .claude\SPEC_SYSTEM_DRAFT_V1.md

**Lines:** 178

- Lines 1-178: markdown_file `SPEC_SYSTEM_DRAFT_V1.md` - Analyzes existing specification systems and methodologies to inform the design of a system that enables AI coding assistants to generate comprehensive software specifications.

---

### .claude\SPEC_SYSTEM_DRAFT_V2.md

**Lines:** 273

- Lines 1-273: markdown_file `SPEC_SYSTEM_DRAFT_V2.md` - Validates YAML specifications for AI coding assistants against core design principles, focusing on actionability, critical blockers, and an iterative refinement loop.

---

### .claude\SPEC_SYSTEM_DRAFT_V3.md

**Lines:** 346

- Lines 1-346: markdown_file `SPEC_SYSTEM_DRAFT_V3.md` - Handles the creation of structured specifications using progressive levels (Lite, Standard, System) based on task complexity and architectural scope, incorporating constraints and agent-resolvable unknowns.

---

### .claude\docs\PROMPT_ENGINEERING_PRINCIPLES.md

**Lines:** 124

- Lines 1-124: markdown_file `PROMPT_ENGINEERING_PRINCIPLES.md` - Analyzes prompt engineering principles for generating concise code documentation using LLMs, emphasizing role definition, content delineation, and example placement.

---

### .claude\logs\signal-completion-log.md

**Lines:** 118

- Lines 1-118: markdown_file `signal-completion-log.md` - Tracks completed user signals from the RSS summarizer project, detailing actions taken and completion dates for each signal.

---

### .claude\problem-stack.md

**Lines:** 73

- Lines 1-73: markdown_file `problem-stack.md` - Analyzes a user interaction to identify systemic failures in handling repeated requests and prioritizing tasks, highlighting issues with knowledge retrieval and system awareness.

---

### .claude\problem-stack\2025-12-15-compounding-violations.md

**Lines:** 86

- Lines 1-86: markdown_file `2025-12-15-compounding-violations.md` - Documents identified violations in the system's processes and proposes preventative measures to ensure adherence to established protocols.

---

### .claude\problem-stack\2025-12-15-skill-invocation-violation.md

**Lines:** 17

- Lines 1-17: markdown_file `2025-12-15-skill-invocation-violation.md` - Identifies and explains a violation where the knowledge-query.sh script was called directly via Bash instead of using the intended knowledge-retriever skill, emphasizing the correct usage of the skill tool.

---

### .claude\resolved-problem-history.md

**Lines:** 66

- Lines 1-66: markdown_file `resolved-problem-history.md` - Handles a violation of the USER_INPUT.md principle by adding a mandatory agent instruction to address tool failures and ensure adherence to deviation protocols.

---

### .claude\state\project-graph.json

**Lines:** 21149

- Lines 1-21149: json_file `project-graph.json` - Handles a dictionary of adjacency information, specifying input and output values for different keys like "old timeout", "flock", and "production requirements".

---

### .claude_settings.json

**Lines:** 24

- Lines 1-24: json_file `.claude_settings.json` - Defines the configuration for a sandbox environment, specifying whether it's enabled and the default permissions granted within it.

---

### .gemini\staging\ABSTRACTION_ENFORCEMENT_DESIGN_DRAFT.md

**Lines:** 494

- Lines 1-494: markdown_file `ABSTRACTION_ENFORCEMENT_DESIGN_DRAFT.md` - Parses agent-generated thinking blocks, displaying tags and sequences to provide users with visibility into the reasoning process.

---

### .gemini\staging\PIPELINE_ISSUES_TRACKING.md

**Lines:** 159

- Lines 1-159: markdown_file `PIPELINE_ISSUES_TRACKING.md` - Documents identified issues and proposes solutions for improving the efficiency and scalability of the report pipeline, focusing on optimizing LLM calls, ordering operations, and implementing vector search.

---

### .gemini\staging\PIPELINE_REDESIGN_PROPOSAL.md

**Lines:** 361

- Lines 1-361: markdown_file `PIPELINE_REDESIGN_PROPOSAL.md` - Designs a new report pipeline that consolidates operations to reduce LLM and embedding calls and minimize model switches per article.

---

### .gitignore

**Lines:** 45

- Lines 1-45: file `.gitignore` - Identifies common files and directories generated by Python development environments, virtual environments, databases, IDEs, and testing frameworks.

---

### ADVERSARIAL_SPECIFICATION_ELICITATION_RESEARCH.md

**Lines:** 692

- Lines 1-692: markdown_file `ADVERSARIAL_SPECIFICATION_ELICITATION_RESEARCH.md` - Identifies and analyzes existing tools, frameworks, and research approaches for discovering specification gaps through adversarial debate, questioning, and multi-agent critique systems.

---

### AI_CLI_RESEARCH.md

**Lines:** 105

- Lines 1-105: markdown_file `AI_CLI_RESEARCH.md` - Outlines methodologies, tools, and formats for defining exhaustive specifications for AI agents, focusing on conversational interfaces and leveraging techniques like INVEST, MoSCoW, BDD, and lightweight formal methods.

---

### AI_IMPLEMENTATION_FRAMEWORKS_RESEARCH.md

**Lines:** 1430

- Lines 1-1430: markdown_file `AI_IMPLEMENTATION_FRAMEWORKS_RESEARCH.md` - Analyzes implementation frameworks like TDD, BDD, and ATDD to guide the transition from AI agent task specification to deterministic code execution.

---

### AI_SPECIFICATION_TOOLS_RESEARCH.md

**Lines:** 113

- Lines 1-113: markdown_file `AI_SPECIFICATION_TOOLS_RESEARCH.md` - Highlights Python, JavaScript/TypeScript, and other tools for property-based testing, contract specification, and ontology modeling in software development.

---

### FEED_SEARCH_DEMO.md

**Lines:** 147

- Lines 1-147: markdown_file `FEED_SEARCH_DEMO.md` - Handles adding RSS feeds to a user's account by either importing from curated categories or searching for feeds online.

---

### README.md

**Lines:** 334

- Lines 1-334: markdown_file `README.md` - Handles RSS feed ingestion, AI-powered summarization, trend prediction, and knowledge extraction through a command-line interface.

---

### TRANSCRIPT_SPEC_CRITIQUE.md

**Lines:** 30

- Lines 1-30: markdown_file `TRANSCRIPT_SPEC_CRITIQUE.md` - Analyzes the Transcript Retrieval System specification, highlighting critical gaps in process flow, data model definitions, and logic algorithms that impede implementation.

---

### ai_rss_summarizer.egg-info\PKG-INFO

**Lines:** 43

- Lines 1-11: config `Metadata` - Please provide the code you want me to document. I need the code to be able to write a one-sentence summary following your rules.
- Lines 2-12: config `Name` - Please provide the code you want me to document. I need the code to be able to write a concise summary following your rules.
- Lines 3-13: config `Version` - Please provide the code you want me to document. I need the code to be able to write a one-sentence summary following your rules.
- Lines 4-14: config `Summary` - Please provide the code you want me to document. I need the code to be able to write a concise summary sentence following your rules.
- Lines 6-16: config `Author-email` - Please provide the code you want me to document. I need the code to be able to write a one-sentence summary following your rules.
- Lines 7-17: config `License` - Please provide the code you want me to document. I need the code to be able to write a concise summary following your rules.
- Lines 9-19: config `Classifier-Development Status` - Please provide the code you want me to document. I need the code to be able to write a one-sentence summary following your rules.
- Lines 10-20: config `Classifier-Intended Audience` - Please provide the code you want me to document. I need the code to be able to write a concise summary following your rules.
- Lines 11-21: config `Classifier-License` - Please provide the code you want me to document. I need the code to be able to write a concise summary sentence following your rules.
- Lines 12-22: config `Classifier-Programming Language` - Please provide the code you want me to document. I need the code to be able to write a concise summary sentence following your rules.
- Lines 14-24: config `Requires-Python` - Please provide the code you want me to document. I need the code to write the one-sentence summary.
- Lines 15-25: config `Description-Content-Type` - Please provide the code you want me to document. I need the code to be able to write the one-sentence summary according to your rules.
- Lines 16-26: config `Requires-Dist` - Please provide the code you want me to document. I need the code to write the one-sentence summary.
- Lines 20-30: config `Provides-Extra` - Please provide the code you want me to document. I need the code to be able to write a one-sentence summary following your rules.
- Lines 23-33: target `Description` - Please provide the code you want me to document. I need the code to be able to write a one-sentence summary following your rules.
- Lines 27-37: target `Features` - Please provide the code you want me to document. I need the code to be able to write a one-sentence summary following your rules.
- Lines 31-41: target `Quick Start` - Please provide the code you want me to document. I need the code to be able to write a one-sentence summary following your rules.
- Lines 33-43: target `Installation` - Please provide the code you want me to document. I need the code to be able to write a one-sentence summary following your rules.

---

### ai_rss_summarizer.egg-info\SOURCES.txt

**Lines:** 71

- Lines 1-11: documentation `README.md` - Please provide the code you want me to document. I need the code within the `=== BEGIN CODE ===` and `=== END CODE ===` markers to write the summary.
- Lines 6-16: config `pyproject.toml` - Please provide the code you want me to document. I need the code to be able to write a one-sentence summary following your rules.
- Lines 20-30: package_info `ai_rss_summarizer.egg-info/PKG-INFO` - Please provide the code for `package_info` so I can write the summary. I need the code to understand what it does before I can create a concise description.
- Lines 21-31: package_info `ai_rss_summarizer.egg-info/SOURCES.txt` - Please provide the code for `package_info` so I can write the summary. I need the code to understand what it does before I can create a concise description.
- Lines 22-32: package_info `ai_rss_summarizer.egg-info/dependency_links.txt` - Please provide the code for `package_info` so I can write the summary. I need the code to understand what it does.
- Lines 23-33: package_info `ai_rss_summarizer.egg-info/entry_points.txt` - Please provide the code for `package_info` so I can write the summary. I need the code to understand what it does before I can create a concise description.
- Lines 24-34: package_info `ai_rss_summarizer.egg-info/requires.txt` - Please provide the code for `package_info`. I need the code to write the one-sentence summary.
- Lines 25-35: package_info `ai_rss_summarizer.egg-info/top_level.txt` - Please provide the code for `package_info` so I can write the summary. I need the code to understand what it does before I can create a concise description.
- Lines 28-38: module `src/__init__.py` - Please provide the code you want me to document. I need the code within the `=== BEGIN CODE ===` and `=== END CODE ===` markers to write the summary.
- Lines 31-41: module `src/cli.py` - Please provide the code you want me to document. I need the code to be able to write a concise summary sentence following your rules.
- Lines 34-44: module `src/cli_constitution.py` - Please provide the code you want me to document. I need the code to write a one-sentence summary following your rules.
- Lines 37-47: module `src/cli_context.py` - Please provide the code you want me to document. I need the code within the `=== BEGIN CODE ===` and `=== END CODE ===` markers to write the summary.
- Lines 40-50: module `src/cli_perspectives.py` - Please provide the code you want me to document. I need the code within the `=== BEGIN CODE ===` and `=== END CODE ===` markers to write the summary.
- Lines 43-53: module `src/cli_schedule.py` - Please provide the code you want me to document. I need the code within the `=== BEGIN CODE ===` and `=== END CODE ===` markers to write the summary.
- Lines 46-56: module `src/cli_signal_tags.py` - Please provide the code you want me to document. I need the code to be able to write a one-sentence summary following your rules.
- Lines 49-59: module `src/cli_stories.py` - Please provide the code you want me to document. I need the code to be able to write a one-sentence summary following your rules.
- Lines 52-62: module `src/clustering.py` - Please provide the code you want me to document. I need the code within the `=== BEGIN CODE ===` and `=== END CODE ===` markers to write the summary.
- Lines 55-65: module `src/commands.py` - Please provide the code you want me to document. I need the code within the `=== BEGIN CODE ===` and `=== END CODE ===` markers to write the summary.
- Lines 58-68: module `src/constitution.py` - Please provide the code you want me to document. I need the code to write a one-sentence summary according to your rules.
- Lines 61-71: module `src/content_filter.py` - Please provide the code you want me to document. I need the code to write the one-sentence summary.

---

### ai_rss_summarizer.egg-info\entry_points.txt

**Lines:** 3

- Lines 1-3: file `entry_points.txt` - Handles command-line arguments to execute the application defined in `src.cli:app`.

---

### ai_rss_summarizer.egg-info\requires.txt

**Lines:** 28

- Lines 1-28: file `requires.txt` - Specifies the required versions of various Python libraries and dependencies for different application environments, including core libraries, AI providers, testing tools, and specific API integrations.

---

### ai_rss_summarizer.egg-info\top_level.txt

**Lines:** 2

- Lines 1-2: file `top_level.txt` - Handles user input to determine the duration of a task in minutes or hours and converts it to seconds.

---

### config\constitution.md

**Lines:** 23

- Lines 1-23: markdown_file `constitution.md` - Analyzes principles for evaluating information by outlining core values, source evaluation methods, focus areas, and red flags to watch for.

---

### config\feeds.txt

**Lines:** 44

- Lines 1-44: file `feeds.txt` - Collects RSS feed URLs for various news categories, including tech, world, and science.

---

### config\llm.json

**Lines:** 12

- Lines 1-12: json_file `llm.json` - Configures settings for loading the Gemma-3n-e4b model from LM Studio, enabling automatic loading with a 5-minute time-to-live.

---

### config\model_config.json

**Lines:** 10

- Lines 1-10: json_file `model_config.json` - Configures model paths for language, vision, and embedding models in LM Studio, along with parameters like temperature and a time-to-live duration.

---

### config\schedule.json

**Lines:** 4

- Lines 1-4: json_file `schedule.json` - Handles configuration for a background task by specifying whether the task is enabled and the interval between executions in minutes.

---

### config\user_context.json

**Lines:** 25

- Lines 1-25: json_file `user_context.json` - Returns a dictionary containing the user's current projects, watched topics, and personalization settings.

---

### docs\ERROR_HANDLING_STRATEGY.md

**Lines:** 492

- Lines 1-492: markdown_file `ERROR_HANDLING_STRATEGY.md` - Documents the RSS Summarizer's error handling strategy, emphasizing explicit error surfacing and quality observability across LLM-dependent features.

---

### docs\FALLBACK_WORK_MAP.md

**Lines:** 178

- Lines 1-178: markdown_file `FALLBACK_WORK_MAP.md` - Documents critical failure modes in the codebase where fallback mechanisms hide potential failures, outlining proper handling strategies for each.

---

### docs\FEED_ONBOARDING_OVERHAUL.md

**Lines:** 186

- Lines 1-186: markdown_file `FEED_ONBOARDING_OVERHAUL.md` - Creates a curated database of verified RSS feeds organized by category for users to easily add to their feed subscriptions.

---

### docs\LM_STUDIO_VERIFICATION.md

**Lines:** 107

- Lines 1-107: markdown_file `LM_STUDIO_VERIFICATION.md` - Handles automatic model loading using LM Studio, checking available memory and headroom to prevent system instability.

---

### docs\OPENAI_AGENTS_SDK_MIGRATION.md

**Lines:** 176

- Lines 1-176: markdown_file `OPENAI_AGENTS_SDK_MIGRATION.md` - Creates a new OpenAI provider using the OpenAI Agents SDK to support advanced features like story clustering and signal tagging while maintaining compatibility with existing configurations.

---

### docs\PROJECT_DOCS.md

**Lines:** 805

- Lines 1-805: markdown_file `PROJECT_DOCS.md` - Analyzes news articles using LLMs, vector embeddings, and structured data management to perform tasks like clustering, summarization, and knowledge extraction.

---

### docs\TREND_ANALYSIS_FEATURES.md

**Lines:** 349

- Lines 1-349: markdown_file `TREND_ANALYSIS_FEATURES.md` - Handles complex news articles by clustering them into stories and identifying specific new information items within those stories, tracking their emergence across different sources.

---

### docs\specs\EMERGENCE_DETECTION_RESULTS.md

**Lines:** 333

- Lines 1-333: markdown_file `EMERGENCE_DETECTION_RESULTS.md` - Implements an emergence detection feature that extracts terms, analyzes their velocity and trajectory, scores confidence, and provides action recommendations based on historical data and configurable thresholds.

---

### docs\specs\EMERGENCE_DETECTION_SPEC.md

**Lines:** 437

- Lines 1-437: markdown_file `EMERGENCE_DETECTION_SPEC.md` - Detects emerging trends by analyzing term frequency, velocity, cross-domain appearance, and trajectory patterns across different time windows.

---

### docs\specs\KNOWLEDGE_EXTRACTION_RESULTS.md

**Lines:** 382

- Lines 1-382: markdown_file `KNOWLEDGE_EXTRACTION_RESULTS.md` - Implements a knowledge base system to extract insights from articles, track entities and relationships, and enable natural language querying using an LLM and a relational database.

---

### docs\specs\KNOWLEDGE_EXTRACTION_SPEC.md

**Lines:** 515

- Lines 1-515: markdown_file `KNOWLEDGE_EXTRACTION_SPEC.md` - Extracts structured insights from articles read through an RSS summarizer, assigning confidence levels and storing them in a knowledge graph to build a queryable personal knowledge base.

---

### docs\specs\PERSONAL_CONTEXT_RESULTS.md

**Lines:** 424

- Lines 1-424: markdown_file `PERSONAL_CONTEXT_RESULTS.md` - Implements a personal context engine with storage, relevance scoring, and CLI commands to personalize article relevance based on user roles, projects, and interaction history.

---

### docs\specs\PERSONAL_CONTEXT_SPEC.md

**Lines:** 520

- Lines 1-520: markdown_file `PERSONAL_CONTEXT_SPEC.md` - Handles user context profiles and article interactions to learn and apply personalized content relevance scoring and filtering.

---

### docs\specs\PERSPECTIVE_SYNTHESIS_RESULTS.md

**Lines:** 379

- Lines 1-379: markdown_file `PERSPECTIVE_SYNTHESIS_RESULTS.md` - Implements perspective synthesis for articles by clustering them into categories based on user selection and synthesizing content using LLM prompts, while incorporating caching and fallback mechanisms.

---

### docs\specs\PERSPECTIVE_SYNTHESIS_SPEC.md

**Lines:** 608

- Lines 1-608: markdown_file `PERSPECTIVE_SYNTHESIS_SPEC.md` - Handles perspective synthesis across articles by grouping them into story clusters and allowing users to select from 12+ categories to customize their view.

---

### docs\specs\SIGNAL_TAGGING_RESULTS.md

**Lines:** 374

- Lines 1-374: markdown_file `SIGNAL_TAGGING_RESULTS.md` - Implements a Signal Tagging System to categorize signals across five dimensions using rule-based and LLM-based detection, storing tags in the database and integrating with the summarization module.

---

### docs\specs\SIGNAL_TAGGING_SPEC.md

**Lines:** 581

- Lines 1-581: markdown_file `SIGNAL_TAGGING_SPEC.md` - Defines a system for replacing numeric signal scores with descriptive tags across source type, evidence handling, reasoning quality, tone/style, and actionability to improve article understanding and filtering.

---

### docs\specs\STORY_CLUSTERING_RESULTS.md

**Lines:** 266

- Lines 1-266: markdown_file `STORY_CLUSTERING_RESULTS.md` - Implements two-level story clustering and evolution tracking by using LLMs for similarity comparison and information extraction, and tracking story lifecycle states.

---

### docs\specs\STORY_CLUSTERING_SPEC.md

**Lines:** 527

- Lines 1-527: markdown_file `STORY_CLUSTERING_SPEC.md` - Handles clustering articles into stories and news items, tracking their evolution and provenance using a two-level system with data models for Stories and NewsItems.

---

### docs\specs\TRANSCRIPT_RETRIEVAL_SPEC.md

**Lines:** 95

- Lines 1-95: markdown_file `TRANSCRIPT_RETRIEVAL_SPEC.md` - Handles JSONL session logs and compaction markers to reconstruct complete conversational narratives and analyze discontinuities across long-term interactions.

---

### docs\specs\TRUSTGRAPH_INTEGRATION_SPEC.md

**Lines:** 103

- Lines 1-103: markdown_file `TRUSTGRAPH_INTEGRATION_SPEC.md` - Handles optional integration with the TrustGraph knowledge graph backend for advanced semantic search and knowledge representation.

---

### install.sh

**Lines:** 71

- Lines 1-71: file `install.sh` - Handles the installation of RSS Summarizer, including pipx if necessary, from either a local pyproject.toml or PyPI source, and provides post-installation instructions.

---

### pyproject.toml

**Lines:** 79

- Lines 1-79: toml_file `pyproject.toml` - Configures the build system, project metadata including dependencies and optional dependencies, scripts, and tooling options for an AI-powered RSS feed summarizer.

---

### requirements-llm.txt

**Lines:** 10

- Lines 1-10: file `requirements-llm.txt` - Specifies required Python dependencies for LLM/ML tasks, including optional large downloads for local summarization and API-based alternatives for lighter-weight LLM access.

---

### requirements.txt

**Lines:** 17

- Lines 1-17: file `requirements.txt` - Specifies the required Python libraries and dependencies for a project involving feed parsing, command-line interaction, and optional large language model integration.

---

### rssTestProfile2\config\llm.json

**Lines:** 6

- Lines 1-6: json_file `llm.json` - Handles configuration settings for an LM Studio model, specifying the provider, base URL, model name, and default parameters.

---

### rssTestProfile3\config\feeds.txt

**Lines:** 4

- Lines 1-4: file `feeds.txt` - Creates a list of five RSS feed suggestions for technology philosophy, neuroscience, and aikido, formatted with their names and URLs.

---

### rssTestProfile3\config\llm.json

**Lines:** 6

- Lines 1-6: json_file `llm.json` - Handles configuration settings for an LM Studio model, specifying the provider, base URL, model name, and default parameters.

---

### scripts\document-by-function.py

**Lines:** 770

- Lines 27-32: function `load_cache` - Loads cached function descriptions from a JSON file if it exists, otherwise returns an empty dictionary.
- Lines 35-39: function `save_cache` - Saves the provided cache data to a JSON file in a designated directory.
- Lines 42-44: function `hash_code` - Generates a short MD5 hash of the input code string for change detection by returning the first 8 characters of the hexadecimal representation.
- Lines 47-119: function `extract_functions` - Extracts function and class definitions, imports, and top-level assignments from a Python file, providing their line numbers and code.
- Lines 122-124: class `LLMError` - Handles errors that occur when an LLM call fails after multiple retry attempts.
- Lines 127-156: function `call_llm` - Handles calling an LLM via a gateway with retry logic and exponential backoff, returning the response and LLM processing time upon success.
- Lines 159-161: function `estimate_tokens` - Estimates the number of tokens in a given text by dividing the text length by approximately 4 characters per token.
- Lines 164-193: function `extract_nested_functions` - Extracts nested functions from a given code string, excluding the parent function itself, and returns a list of dictionaries containing information about each nested function's name, type, location, and code.
- Lines 196-259: function `describe_function` - Parses a Python function's code using a sandwich prompt to generate a concise, one-sentence description of its functionality.
- Lines 262-333: function `process_file` - Processes a file by extracting function information, comparing it against a cache, and updating the cache with the results and their status.
- Lines 336-349: function `find_python_files` - Finds all Python files within a specified directory, recursively excluding specified directories and returning a sorted list of their full paths.
- Lines 352-422: function `generate_overview` - Generates a system architecture overview prompt for a large language model, including project statistics and file summaries to guide the creation of a concise architectural document.
- Lines 425-723: function `process_directory` - Processes Python files in a directory by extracting functions, building a work queue for LLM processing, and executing the LLM calls concurrently to generate descriptions.
- Lines 497-504: function `process_item` - Returns a filepath, function, description, and timing information including the total execution time of the function.
- Lines 726-770: function `main` - Processes Python files or directories to generate documentation, including function names, descriptions, and code statistics.

---

### scripts\local-codebase-explorer.py

**Lines:** 1170

- Lines 64-76: function `_log_llm_exchange` - Logs the timestamp, timing, prompt (truncated if necessary), and response to a file for debugging purposes.
- Lines 211-216: function `load_cache` - Loads cached function descriptions from a JSON file, returning an empty dictionary if the file doesn't exist.
- Lines 219-223: function `save_cache` - Saves the provided cache data to a JSON file in a designated directory.
- Lines 226-228: function `hash_code` - Generates a short MD5 hash of the input code string for change detection by returning the first 8 characters of the hexadecimal digest.
- Lines 235-238: function `get_language_for_file` - Returns the tree-sitter language name associated with a file's extension, or None if the extension is not supported.
- Lines 241-342: function `extract_with_treesitter` - Parses a code file using tree-sitter, extracting code units with their name, type, start and end lines, and the code itself.
- Lines 349-423: function `extract_with_python_ast` - Extracts information about functions, classes, imports, and assignments from a Python file, including their line numbers and code, and returns the results sorted by starting line number.
- Lines 430-432: class `LLMError` - Handles errors that occur when an LLM call fails after multiple retry attempts.
- Lines 440-450: function `configure_llm` - Configures the LLM backend by setting the backend type and any associated configuration parameters.
- Lines 453-491: function `_detect_llm_backend` - Detects the available LLM backend (gateway, LM Studio, or OpenAI) by attempting to import necessary libraries or connect to specific endpoints, and raises an error if none are found.
- Lines 494-498: function `_call_gateway` - Calls a project gateway to send a text prompt and returns the gateway's response.
- Lines 501-514: function `_call_lmstudio` - Calls the LM Studio API with a given prompt to generate text, returning the model's response.
- Lines 517-531: function `_call_openai` - Calls the OpenAI API with a given prompt to generate text, using the specified model and temperature, and returns the generated text.
- Lines 534-577: function `call_llm` - Handles calling an LLM with retry logic and exponential backoff, selecting the appropriate call function based on the configured backend.
- Lines 580-582: function `estimate_tokens` - Estimates the number of tokens in a given text by dividing the text length by approximately 4 characters per token.
- Lines 585-636: function `describe_code_unit` - Generates a concise description of a code unit by prompting an LLM to summarize its functionality, considering the code's language and type.
- Lines 639-710: function `analyze_text_file_with_llm` - Analyzes a text file using an LLM to identify sections and their approximate line numbers, returning a list of dictionaries describing the findings.
- Lines 717-761: function `extract_from_file` - Extracts code units from a file by attempting tree-sitter parsing, falling back to AST parsing for Python files and LLM analysis for other text-based files.
- Lines 764-779: function `is_text_file` - Validates whether a file is likely a text file by checking for null bytes and attempting UTF-8 decoding.
- Lines 786-810: function `find_files` - Finds all processable files within a given directory, recursively excluding specified directories and prioritizing files with known extensions or text-like content.
- Lines 817-1033: function `process_directory` - Handles processing of files within a directory by extracting code units, building a work queue for LLM descriptions, and concurrently generating descriptions while managing caching and error handling.
- Lines 905-913: function `process_item` - Processes a code unit by measuring its execution time and returning the filepath, unit, description, and timing information.
- Lines 1036-1101: function `generate_overview` - Generates a system architecture overview prompt for a codebase, including project statistics and file summaries, to guide a language model in creating a concise architectural description.
- Lines 1104-1135: function `write_output` - Writes project documentation to a specified output file, including statistics, overview, and detailed file-level information with line-by-line analysis.
- Lines 1138-1170: function `main` - Processes a directory to extract functions and classes from files, optionally writing the results to an output file and controlling processing behavior with command-line arguments.

---

### scripts\quality_test_harness.py

**Lines:** 377

- Lines 34-42: class `ExtractionResult` - Creates a data structure to hold the results of a single extraction run, including metrics like the number of insights, triples, and tags, as well as execution time and raw output.
- Lines 46-52: class `QualityMetrics` - Defines quality metrics for evaluating insights based on specificity, accuracy, relevance, and summary completeness, culminating in an overall score.
- Lines 56-61: class `TestRun` - Handles the storage of article test results, including title, timestamp, extraction results, and quality metrics.
- Lines 64-95: function `get_sample_article` - Creates a sample Article object with predefined details for testing purposes.
- Lines 98-152: function `extract_single_task` - Handles a specified extraction task (insights, triples, tags, or summary) from an article using a language model and returns the parsed JSON response.
- Lines 155-185: function `extract_combined` - Handles multiple extraction tasks (insights, triples, tags, summary) on an article using a language model and returns a JSON object containing the extracted information.
- Lines 188-256: function `run_extraction_test` - Collects insights, triples, tags, and summary from an article using specified extraction modes and an LLM provider, then returns the results with metadata.
- Lines 259-350: function `GatewayWrapper` - Runs a quality test suite on an article multiple times with different modes, logging insights, triples, tags, and time, then optionally saves the results to a file.
- Lines 277-279: class `GatewayWrapper` - Handles text generation by sending a prompt to a gateway and returning the generated text.
- Lines 278-279: function `generate` - Returns text generated from a prompt using the gateway's request_text function, with an optional limit on the number of tokens.
- Lines 353-377: function `main` - Handles quality testing of articles by reading article content from a file, then running the test specified number of times and saving results to a JSON file.

---

### scripts\safe-model-load.sh

**Lines:** 1860

- Lines 55-61: function `log` - Handles logging messages with a timestamp to a file and optionally to standard error, based on the VERBOSE variable.
- Lines 63-67: function `log_error` - Handles errors by logging a timestamped message to a file and displaying it to standard error.
- Lines 70-79: function `log_stderr` - Handles standard error by logging it with a timestamp to a file and optionally displaying it to the console if verbose mode is enabled.
- Lines 85-115: function `cleanup_old_pipes` - Handles stale pipe files in the specified directory by removing those older than a defined age, logging errors for any failures.
- Lines 117-128: function `create_request_pipe` - Creates a named pipe with a path based on the provided request ID and returns the pipe's path.
- Lines 134-154: function `is_processor_alive` - Verifies if a process is running by checking for the existence of a PID file and confirming the process ID is valid.
- Lines 156-182: function `is_heartbeat_stale` - Validates if the heartbeat file has been updated within the specified threshold, returning 0 if stale and 1 if recent.
- Lines 184-213: function `should_spawn_processor` - Determines whether to spawn a new processor by checking the queue status, heartbeat, and processor PID, returning 0 if a new processor should be spawned and 1 if the existing one is active.
- Lines 219-232: function `get_config` - Retrieves a configuration value from a file, using a provided default if the key is not found or the read fails.
- Lines 238-249: function `get_embedding_batch_size` - Retrieves the embedding batch size from a file, validating it against minimum and maximum values, and returns the specified size if valid, otherwise uses the default value.
- Lines 251-262: function `set_embedding_batch_size` - Handles the setting of the embedding batch size by validating user-provided input against minimum and maximum values and persisting the selected size to a file.
- Lines 264-320: function `get_memory_usage` - Calculates the system's memory usage percentage (0-100) by querying system information on Linux, Windows, or macOS.
- Lines 322-347: function `check_memory_before_batch` - Handles memory usage by reducing the embedding batch size if memory exceeds a critical threshold, ensuring system stability.
- Lines 349-383: function `adjust_batch_size_on_success` - Handles memory usage to conservatively increase batch size if memory is available or decrease it if memory is critically high.
- Lines 385-401: function `adjust_batch_size_on_failure` - Handles failed embedding batches by decreasing the batch size to a minimum value, logging the change.
- Lines 407-409: function `check_lm_studio` - Handles checking the availability of models from the LM Studio API by querying the specified URL and logging any errors.
- Lines 415-439: function `get_lms_ps_cached` - Handles retrieving the latest LMS PS result from a cache file, or refreshes the cache by calling the `lms` command or querying the LM Studio API if the cache is stale.
- Lines 441-443: function `invalidate_lms_ps_cache` - Handles the removal of the LMS PS cache file specified by the LMS_PS_CACHE_FILE variable.
- Lines 445-451: function `get_loaded_model` - Retrieves the path to the loaded language model from `lms` if available, otherwise retrieves the model ID from the cached data.
- Lines 453-459: function `get_loaded_model_identifier` - Retrieves the model identifier from either the `lms` command or the `data.id` field in the `get_lms_ps_cached` output, prioritizing the `lms` command if available.
- Lines 461-486: function `get_current_model_type` - Identifies the current model type (text, vision, or embedding) by querying configuration settings and returning "unknown" if the model is not recognized.
- Lines 488-504: function `wait_for_unload` - Waits for a process to complete unloading by repeatedly checking for the absence of a loaded process path for a maximum of 30 seconds, logging success or failure.
- Lines 506-523: function `load_model` - Loads a specified model, handling time-to-live settings and logging success or failure.
- Lines 525-606: function `ensure_model_for_request` - Handles model switching for requests by unloading the current model and loading a new one if necessary, based on the request type and configured models.
- Lines 612-738: function `dispatch_embedding_batch` - Handles a batch of embedding requests by constructing a single API call with an array of prompts and distributing the results to individual response files.
- Lines 740-849: function `dispatch_request_to_lm_studio` - Dispatches a request to LM Studio by constructing a JSON payload and executing a curl command, optionally writing the output to a file or pipe.
- Lines 850-869: function `process_single_request` - Handles a single request by extracting request ID and type from a JSON string, ensuring a model is available, dispatching the request to LM Studio, and logging the process.
- Lines 871-934: function `sort_queue_by_type` - Sorts the queue by priority (high first) and then by type compatibility within each priority, using `jq` to minimize shell variable limits and prevent race conditions.
- Lines 936-949: function `is_type_compatible` - Validates if a request type is compatible with a given batch type, allowing text requests for vision batches.
- Lines 951-978: function `pop_queue_item_to_file` - Handles the removal of the first item from a queue file and writes it to a specified target file, then appends the content of the target file to a history file.
- Lines 980-985: function `get_prompt_size` - Parses the prompt length from a JSON request file using `jq`, exiting with an error if the file is not readable or the prompt length cannot be determined.
- Lines 987-1000: function `has_high_priority_waiting` - Determines if the queue file contains any high-priority items by checking for the existence of the queue file and the presence of "priority=high" in any queue entries.
- Lines 1002-1197: function `process_batch` - Handles a batch of requests, either by batching embedding requests for faster API calls or dispatching text/vision requests individually with in-flight tracking and priority considerations.
- Lines 1199-1329: function `process_queue` - Handles the processing of requests from a queue by acquiring an exclusive lock, sorting requests by type, loading the appropriate model, and processing them in batches with prefetch.
- Lines 1335-1337: function `generate_request_id` - Generates a unique request ID consisting of a timestamp and a random number.
- Lines 1339-1516: function `cmd_request` - Parses command-line arguments to configure a prompt request, including prompt source, system prompt, temperature, and stream mode, then queues the request for processing.
- Lines 1466-1481: function `is_processor_locked` - Checks if a lock file is currently held by a live process.
- Lines 1517-1558: function `cmd_stats` - Generates a JSON string containing the status of the language model studio, including queue size, memory usage, and recent batch performance.
- Lines 1560-1601: function `cmd_status` - Handles and displays the status of the gateway, including queue size, LM Studio running status, configuration settings, adaptive batch sizing parameters, and memory usage.
- Lines 1603-1614: function `cmd_reset_batch` - Handles resetting the embedding batch size to a specified integer value or the default, validating the input against defined minimum and maximum values.
- Lines 1616-1661: function `cmd_clear_queue` - Clears the request queue, checks for and terminates a stale processor, and removes the heartbeat file, logging the number of discarded requests.
- Lines 1663-1716: function `cmd_unload` - Handles unloading all models and clearing the queue to free VRAM by stopping the processor, removing files, and using the `lms unload --all` command, waiting for completion.
- Lines 1718-1790: function `cmd_help` - Displays usage instructions and available commands for the safe-model-load.sh script, including options and flags for model requests, status checks, and resource management.
- Lines 1796-1860: function `main` - Handles various commands related to LM Studio, including requesting text, displaying status, viewing logs, and managing queues.

---

### scripts\test-gateway-continuous.sh

**Lines:** 162

- Lines 1-162: file `test-gateway-continuous.sh` - Handles a specified number of requests by submitting them to a gateway, then waits for responses from those requests, monitoring for timeouts and assessing continuous throughput.

---

### src\TEST_10FILES.md

**Lines:** 516

- Lines 1-516: markdown_file `TEST_10FILES.md` - Documents the architecture of an RSS summarizer system, detailing modules like CLI, perspectives, constitution, signal tags, and context management, along with their purposes, dependencies, and key functionalities.

---

### src\TEST_5FILES.md

**Lines:** 312

- Lines 1-312: markdown_file `TEST_5FILES.md` - Documents the architecture of the RSS Summarizer application, detailing modules, dependencies, and their respective functionalities.

---

