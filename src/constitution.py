"""User constitution/analysis policy framework.

Allows users to define principles and values that guide ALL analysis.
The constitution is injected into LLM prompts to personalize analysis.
"""

import os
from pathlib import Path
from typing import Optional


DEFAULT_CONSTITUTION_PATH = "config/constitution.md"

EXAMPLE_CONSTITUTION = """# My Analysis Principles

## Core Values
- Prioritize scientific consensus over individual opinions
- Value evidence-based reasoning over speculation
- Consider multiple perspectives before drawing conclusions

## Source Evaluation
- Be skeptical of claims from sources with financial conflicts of interest
- Weight peer-reviewed research higher than opinion pieces
- Flag when sources have known biases

## Focus Areas
- Highlight local community impacts
- Track technological developments in AI and software
- Monitor environmental and sustainability topics

## Red Flags to Watch For
- Sensationalist headlines that don't match article content
- Claims without cited sources
- Potential conflicts of interest
- Misleading statistics or cherry-picked data
"""


def get_constitution_path() -> Path:
    """Get the path to the constitution file."""
    return Path(DEFAULT_CONSTITUTION_PATH)


def constitution_exists() -> bool:
    """Check if a constitution file exists."""
    return get_constitution_path().exists()


def get_constitution_content() -> Optional[str]:
    """Load the raw constitution content.

    Returns:
        Constitution content as string, or None if not configured.
    """
    path = get_constitution_path()
    if not path.exists():
        return None

    with open(path, encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        return None

    return content


def get_constitution_context() -> str:
    """Load user's constitution for prompt injection.

    Returns formatted context string to prepend to LLM prompts.
    Returns empty string if no constitution is configured.
    """
    content = get_constitution_content()
    if not content:
        return ""

    return f"""## User Analysis Framework

The user has defined the following principles to guide analysis:

{content}

Apply these principles when analyzing the content below:

"""


def create_constitution(content: Optional[str] = None) -> Path:
    """Create a constitution file.

    Args:
        content: Constitution content. Uses example template if None.

    Returns:
        Path to the created file.
    """
    path = get_constitution_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content or EXAMPLE_CONSTITUTION)

    return path


def get_example_constitution() -> str:
    """Get the example constitution template."""
    return EXAMPLE_CONSTITUTION
