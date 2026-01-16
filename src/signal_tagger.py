"""Signal tagging for articles - assign descriptive quality tags."""

import json
import re
from dataclasses import dataclass, asdict
from typing import Optional

from .storage import Article
from .constitution import get_constitution_context


# Known satire domains
SATIRE_DOMAINS = [
    "theonion.com",
    "babylonbee.com",
    "clickhole.com",
    "thebeaverton.com",
    "newsthump.com",
]


@dataclass
class SignalTags:
    """Signal tags for an article across five dimensions."""

    source_type: list[str]
    evidence: list[str]
    reasoning: list[str]
    tone: list[str]
    actionability: list[str]
    is_ad: bool = False

    def to_json(self) -> str:
        """Serialize to JSON string for storage."""
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, json_str: str) -> "SignalTags":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        # Handle legacy data without is_ad field
        if "is_ad" not in data:
            data["is_ad"] = False
        return cls(**data)

    def to_display_string(self) -> str:
        """Format tags for display: [primary] [well-sourced] [balanced]"""
        all_tags = (
            self.source_type
            + self.evidence
            + self.reasoning
            + self.tone
            + self.actionability
        )
        return " ".join(f"[{tag}]" for tag in all_tags)

    def to_compact_string(self) -> str:
        """Format tags as compact comma-separated string."""
        all_tags = (
            self.source_type
            + self.evidence
            + self.reasoning
            + self.tone
            + self.actionability
        )
        # Remove duplicates while preserving order
        unique_tags = list(dict.fromkeys(all_tags))
        return ", ".join(unique_tags)

    def has_any_tag(self, *tags: str) -> bool:
        """Check if any of the given tags are present."""
        all_tags = (
            self.source_type
            + self.evidence
            + self.reasoning
            + self.tone
            + self.actionability
        )
        return any(tag in all_tags for tag in tags)

    def has_all_tags(self, *tags: str) -> bool:
        """Check if all of the given tags are present."""
        all_tags = (
            self.source_type
            + self.evidence
            + self.reasoning
            + self.tone
            + self.actionability
        )
        return all(tag in all_tags for tag in tags)


class SignalTagger:
    """Assigns signal tags to articles using rule-based or LLM methods."""

    def __init__(self, use_llm: bool = False, provider=None):
        """
        Initialize signal tagger.

        Args:
            use_llm: If True, use LLM for tagging (more accurate)
            provider: LLM provider instance (required if use_llm=True)
        """
        self.use_llm = use_llm
        self.provider = provider

        if use_llm and provider is None:
            # Try to get provider automatically
            try:
                from .llm_providers import get_best_provider

                self.provider, is_llm = get_best_provider()
                if not is_llm:
                    raise ValueError("No LLM provider available")
            except Exception:
                raise ValueError(
                    "use_llm=True requires a valid LLM provider. "
                    "Either pass provider argument or run 'rss setup'"
                )

    def tag_article(self, article: Article) -> SignalTags:
        """
        Assign signal tags to an article.

        Args:
            article: Article to tag

        Returns:
            SignalTags object with assigned tags
        """
        if self.use_llm:
            return self._tag_with_llm(article)
        else:
            return self._tag_with_rules(article)

    def _tag_with_rules(self, article: Article) -> SignalTags:
        """
        Use rule-based pattern matching for tagging.
        Fast but less nuanced than LLM approach.
        """
        combined_text = f"{article.title} {article.content}".lower()

        # Detect source type
        source_type = self._detect_source_type(article, combined_text)

        # Detect evidence handling
        evidence = self._detect_evidence(combined_text)

        # Detect reasoning quality
        reasoning = self._detect_reasoning(combined_text)

        # Detect tone/style
        tone = self._detect_tone(combined_text)

        # Detect actionability
        actionability = self._detect_actionability(combined_text)

        # Detect if this is an ad/promotional content
        is_ad = self._detect_is_ad(article.title.lower(), combined_text)

        return SignalTags(
            source_type=source_type,
            evidence=evidence,
            reasoning=reasoning,
            tone=tone,
            actionability=actionability,
            is_ad=is_ad,
        )

    def _detect_source_type(self, article: Article, text: str) -> list[str]:
        """Detect source type based on patterns and domain."""
        tags = []

        # Check for satire domains
        if any(domain in article.link.lower() for domain in SATIRE_DOMAINS):
            return ["satirical"]

        # Check for press release indicators
        if re.search(
            r"\b(press release|for immediate release|pr newswire)\b", text
        ):
            tags.append("press-release")
            return tags

        # Check for primary source indicators
        primary_patterns = [
            r"\b(witnessed|saw|spoke with|interviewed)\b",
            r"\b(at the scene|on location|first[- ]?hand)\b",
            r"\bour (reporter|correspondent|investigation)\b",
        ]
        if any(re.search(pattern, text) for pattern in primary_patterns):
            tags.append("primary")

        # Check for secondary source indicators
        secondary_patterns = [
            r"\baccording to .+? reported\b",
            r"\breported by\b",
            r"\b(reuters|ap|bloomberg|afp) reports?\b",
        ]
        if any(re.search(pattern, text) for pattern in secondary_patterns):
            tags.append("secondary")

        # Check for aggregator indicators
        if re.search(r"\b(sources include|compiled from|roundup)\b", text):
            tags.append("aggregator")

        # Check for speculation
        speculation_patterns = [
            r"\b(rumored|possibly|might|could|allegedly|reportedly)\b",
            r"\bsources? say\b",
            r"\bunconfirmed\b",
        ]
        if any(re.search(pattern, text) for pattern in speculation_patterns):
            tags.append("speculative")

        # Default to secondary if nothing matched
        if not tags:
            tags.append("secondary")

        return tags

    def _detect_evidence(self, text: str) -> list[str]:
        """Detect evidence handling quality."""
        tags = []

        # Count named sources (rough heuristic)
        source_count = len(re.findall(r'\b(said|told|according to) [A-Z]', text))

        if source_count >= 3:
            tags.append("well-sourced")
        elif source_count == 1:
            tags.append("single-source")

        # Check for documentation
        if re.search(
            r"\b(study|report|document|paper|data) (shows?|reveals?|indicates?)\b",
            text,
        ):
            tags.append("documented")

        # Check for links to primary sources
        if re.search(r"https?://\S+\.(pdf|gov|edu)", text):
            if "documented" not in tags:
                tags.append("documented")

        # Check for anonymous sources
        if re.search(
            r"\b(anonymous source|unnamed official|sources? familiar|people familiar)\b",
            text,
        ):
            tags.append("anonymous-sources")

        # Check for unverified claims
        if re.search(r"\b(unverified|unconfirmed|alleged|claims?)\b", text):
            if not tags:  # Only if no other evidence tags
                tags.append("unverified")

        # Default to single-source if nothing found
        if not tags:
            tags.append("single-source")

        return tags

    def _detect_reasoning(self, text: str) -> list[str]:
        """Detect reasoning quality."""
        tags = []

        # Check for balanced perspective
        balance_patterns = [
            r"\b(however|on the other hand|alternatively|critics say)\b",
            r"\b(supporters|opponents|proponents)\b",
            r"\b(both .+? and)\b",
        ]
        if any(re.search(pattern, text) for pattern in balance_patterns):
            tags.append("balanced")

        # Check for logical reasoning
        logic_patterns = [
            r"\b(because|therefore|thus|as a result|consequently)\b",
            r"\b(evidence suggests|data shows|this indicates)\b",
        ]
        if any(re.search(pattern, text) for pattern in logic_patterns):
            tags.append("logical")

        # Check for cherry-picking indicators
        if re.search(r"\b(ignores|fails to mention|doesn't address)\b", text):
            tags.append("cherry-picked")

        # Default to logical if nothing specific found
        if not tags:
            tags.append("logical")

        return tags

    def _detect_tone(self, text: str) -> list[str]:
        """Detect tone and style."""
        tags = []

        # Count exclamation marks (sensational indicator)
        exclamation_count = text.count("!")

        # Check for sensational language
        sensational_patterns = [
            r"\b(shocking|breaking|explosive|stunning|incredible)\b",
            r"\b(you won't believe|what happened next)\b",
            r"\b(everyone is talking about)\b",
        ]
        if (
            exclamation_count >= 3
            or any(re.search(pattern, text) for pattern in sensational_patterns)
        ):
            tags.append("sensational")

        # Check for opinion markers
        opinion_patterns = [
            r"\b(i think|i believe|in my opinion|my take)\b",
            r"\b(should|must|need to)\b",
        ]
        if any(re.search(pattern, text) for pattern in opinion_patterns):
            tags.append("opinion")

        # Check for analytical depth
        analytical_patterns = [
            r"\b(analysis|examine|consider|implications|factors)\b",
            r"\b(suggests that|indicates that|demonstrates)\b",
            r"\b(understanding|context|framework)\b",
        ]
        analytical_count = sum(
            1 for pattern in analytical_patterns if re.search(pattern, text)
        )
        if analytical_count >= 2:
            tags.append("analytical")

        # Check for spicy/provocative language
        spicy_patterns = [
            r"\b(disaster|catastrophe|crisis|meltdown|chaos)\b",
            r"\b(destroys|demolishes|obliterates)\b",
            r"\b(hot take)\b",
        ]
        if any(re.search(pattern, text) for pattern in spicy_patterns):
            tags.append("spicy")

        # Check for unhinged content
        unhinged_patterns = [
            r"\b(conspiracy|coverup|they don't want you to know)\b",
            r"\b(wake up|sheeple)\b",
            r"\b(the truth about)\b",
        ]
        if any(re.search(pattern, text) for pattern in unhinged_patterns):
            tags.append("unhinged")

        # Default to factual if nothing matched
        if not tags:
            tags.append("factual")

        return tags

    def _detect_actionability(self, text: str) -> list[str]:
        """Detect actionability level."""
        # Check for actionable content
        actionable_patterns = [
            r"\b(how to|guide to|steps to|what you should)\b",
            r"\b(deadline|due date|must .+? by)\b",
            r"\b(recommendation|advice|tip)\b",
            r"\b(you can|you should|here's how)\b",
        ]
        if any(re.search(pattern, text) for pattern in actionable_patterns):
            return ["actionable"]

        # Check for noise indicators
        noise_patterns = [
            r"\b(celebrity|gossip|drama|feud)\b",
            r"\b(viral|trending|twitter|social media)\b",
        ]
        if any(re.search(pattern, text) for pattern in noise_patterns):
            return ["noise"]

        # Default to awareness
        return ["awareness"]

    def _detect_is_ad(self, title: str, text: str) -> bool:
        """Detect if content is advertising/promotional."""
        # Product roundup patterns (common ad formats)
        ad_patterns = [
            r'\bbest\s+\d*\s*(?:of\s+\d+\s*)?(?:baby|kid|pet|home|kitchen|outdoor|tech|gadget)',
            r'\btop\s+\d+\s+(?:best\s+)?(?:products?|picks?|choices?|options?)',
            r'\bbest\s+(?:gear|products?|items?|picks?|buys?)\s+(?:for|of|in)',
            r'\b(?:buyer|buying|gift)\s*(?:\'s)?\s*guide',
            r'\b(?:stroller|crib|bassinet|car\s*seat|baby\s*monitor|high\s*chair)s?\s*(?:review|guide|best)',
            r'\b(?:mattress|furniture|appliance)s?\s*(?:review|guide|best)',
            r'\bwe\s*(?:tested|reviewed|tried)\s*\d+\s+(?:products?|items?)',
            # Discount/promo patterns
            r'\b\d{1,2}%\s*off\b',
            r'\bpromo\s*code',
            r'\bcoupon',
            r'\bdiscount\s*code',
            r'\bflash\s*sale',
            r'\bdeal\s*of\s*the\s*day',
            r'\blimited\s*time\s*offer',
            r'\bsponsored\s*(?:post|content|article)',
            r'\baffiliate',
        ]

        # Check title first (stronger signal)
        for pattern in ad_patterns:
            if re.search(pattern, title, re.IGNORECASE):
                return True

        # Check for multiple ad signals in content
        ad_signals = 0
        for pattern in ad_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                ad_signals += 1

        # Need multiple signals in content to flag as ad
        return ad_signals >= 2

    def _tag_with_llm(self, article: Article) -> SignalTags:
        """
        Use LLM for more accurate, context-aware tagging.
        Falls back to rule-based if LLM fails.
        """
        try:
            prompt = self._build_llm_prompt(article)
            response = self._call_llm(prompt)
            tags = self._parse_llm_response(response)
            return tags
        except Exception as e:
            # Fall back to rule-based tagging
            print(f"LLM tagging failed ({e}), falling back to rules")
            return self._tag_with_rules(article)

    def _build_llm_prompt(self, article: Article) -> str:
        """Build prompt for LLM tagging."""
        # Get user's analysis principles if configured
        constitution_context = get_constitution_context()

        return f"""{constitution_context}Analyze this article and assign appropriate tags from each category.

Article Title: {article.title}
Article Content: {article.content}

Tag Categories:
- Source Type: primary, secondary, aggregator, press-release, speculative, satirical
- Evidence: well-sourced, single-source, anonymous-sources, documented, unverified
- Reasoning: logical, non-sequitur, cherry-picked, balanced
- Tone: factual, analytical, opinion, sensational, spicy, unhinged
- Actionability: actionable, awareness, noise

Also determine if this is advertising/promotional content:
- is_ad: true if this is a product roundup, buying guide, sponsored content, affiliate content, or promotional material (e.g. "Best Baby Gear 2024", "Top 10 Products", buyer's guides). false if it's genuine news/analysis.

Guidelines:
- Assign 1-2 tags per category that best describe the article
- Be concise and accurate
- Consider the overall impression, not just individual words

Return ONLY a JSON object in this exact format (no markdown, no explanation):
{{
  "source_type": ["tag1"],
  "evidence": ["tag1"],
  "reasoning": ["tag1"],
  "tone": ["tag1"],
  "actionability": ["tag1"],
  "is_ad": false
}}"""

    def _call_llm(self, prompt: str) -> str:
        """Call LLM provider with prompt."""
        if not self.provider:
            raise ValueError("No LLM provider configured")

        # Try different provider types
        if hasattr(self.provider, "_get_client"):
            # Claude/Anthropic provider
            client = self.provider._get_client()
            message = client.messages.create(
                model=self.provider.model_name,
                max_tokens=512,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text

        elif hasattr(self.provider, "base_url"):
            # OpenAI-compatible provider (LM Studio, Ollama, etc.)

            # For LM Studio, use the gateway (handles model switching automatically)
            if "localhost:1234" in self.provider.base_url:
                try:
                    from .gateway import get_gateway, GatewayUnavailableError

                    gateway = get_gateway()
                    if gateway.is_available():
                        return gateway.request_text(prompt, temperature=0.3)
                except (ImportError, GatewayUnavailableError):
                    pass  # Fall back to direct API
                except Exception as e:
                    import sys
                    print(f"Warning: Gateway failed, falling back to direct API: {e}", file=sys.stderr)

            # Fallback: Direct API call
            import httpx

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.provider.api_key}",
            }
            payload = {
                "model": self.provider._get_model(),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 512,
            }
            resp = httpx.post(
                f"{self.provider.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            if "choices" not in data:
                raise ValueError(f"Unexpected LLM response format: {list(data.keys())}")
            return data["choices"][0]["message"]["content"]

        else:
            raise ValueError(f"Unsupported provider type: {type(self.provider)}")

    def _parse_llm_response(self, response: str) -> SignalTags:
        """Parse LLM JSON response into SignalTags."""
        # Clean up response (remove markdown formatting if present)
        response = response.strip()
        if response.startswith("```"):
            # Remove markdown code blocks
            lines = response.split("\n")
            response = "\n".join(
                line for line in lines if not line.startswith("```")
            )

        # Parse JSON
        data = json.loads(response)

        # Validate and extract tags
        return SignalTags(
            source_type=data.get("source_type", ["secondary"]),
            evidence=data.get("evidence", ["single-source"]),
            reasoning=data.get("reasoning", ["logical"]),
            tone=data.get("tone", ["factual"]),
            actionability=data.get("actionability", ["awareness"]),
            is_ad=data.get("is_ad", False),
        )


def tag_articles_batch(
    articles: list[Article],
    tagger: SignalTagger,
    show_progress: bool = False,
) -> dict[str, SignalTags]:
    """
    Tag multiple articles in batch.

    Args:
        articles: List of articles to tag
        tagger: SignalTagger instance to use
        show_progress: If True, show progress indication

    Returns:
        Dictionary mapping article ID to SignalTags
    """
    results = {}

    for i, article in enumerate(articles):
        if show_progress:
            print(f"Tagging {i+1}/{len(articles)}: {article.title[:50]}...")

        try:
            tags = tagger.tag_article(article)
            results[article.id] = tags
        except Exception as e:
            import sys
            print(f"Error tagging article '{article.title[:40]}': {e}", file=sys.stderr)
            # Store empty tags on error
            results[article.id] = SignalTags(
                source_type=["secondary"],
                evidence=["single-source"],
                reasoning=["logical"],
                tone=["factual"],
                actionability=["awareness"],
                is_ad=False,
            )

    return results
