"""Gateway tests - verify project portability requirements.

These tests ensure the project works on ANY computer without relying on
user-specific paths like ~/.claude/. NO FALLBACKS ALLOWED.
"""
import os
from pathlib import Path

import pytest


def get_project_root() -> Path:
    """Get the project root directory."""
    # tests/ is one level below project root
    return Path(__file__).parent.parent


class TestGatewayPortability:
    """Tests that gateway script exists in project (not ~/.claude)."""

    def test_gateway_script_exists_in_project(self):
        """Gateway script MUST exist in project/scripts directory.

        This test exists because the script has been missing DOZENS of times.
        Each time someone claims to copy it, then the fallback to ~/.claude
        hides the problem. NO MORE FALLBACKS - if this test fails, the
        project is broken and cannot be used on other machines.
        """
        project_root = get_project_root()
        gateway_script = project_root / "scripts" / "safe-model-load.sh"

        assert gateway_script.exists(), (
            f"CRITICAL: Gateway script missing!\n"
            f"Expected: {gateway_script}\n\n"
            f"This project MUST contain scripts/safe-model-load.sh.\n"
            f"Without it, the project cannot work on other computers.\n"
            f"Copy from ~/.claude/scripts/safe-model-load.sh if needed."
        )

    def test_gateway_script_is_not_empty(self):
        """Gateway script must have actual content."""
        project_root = get_project_root()
        gateway_script = project_root / "scripts" / "safe-model-load.sh"

        if not gateway_script.exists():
            pytest.skip("Gateway script missing - see test_gateway_script_exists_in_project")

        size = gateway_script.stat().st_size
        assert size > 1000, (
            f"Gateway script appears to be empty or truncated.\n"
            f"Size: {size} bytes (expected >1000)\n"
            f"The script should contain model loading, queue management, etc."
        )

    def test_gateway_script_has_required_commands(self):
        """Gateway script must have essential commands."""
        project_root = get_project_root()
        gateway_script = project_root / "scripts" / "safe-model-load.sh"

        if not gateway_script.exists():
            pytest.skip("Gateway script missing - see test_gateway_script_exists_in_project")

        content = gateway_script.read_text(encoding="utf-8")

        required_commands = [
            "cmd_request",      # Core request handling
            "cmd_status",       # Status checking
            "cmd_unload",       # VRAM cleanup
            "cmd_clear_queue",  # Queue cleanup (for cancelled operations)
        ]

        missing = [cmd for cmd in required_commands if cmd not in content]

        assert not missing, (
            f"Gateway script missing required commands: {missing}\n"
            f"The script may be outdated. Copy fresh from ~/.claude/scripts/"
        )

    def test_no_fallback_in_gateway_module(self):
        """gateway.py must NOT have fallback to ~/.claude."""
        project_root = get_project_root()
        gateway_module = project_root / "src" / "gateway.py"

        assert gateway_module.exists(), "src/gateway.py not found"

        content = gateway_module.read_text(encoding="utf-8")

        # These patterns indicate a fallback was added
        forbidden_patterns = [
            "expanduser",           # Used to get ~/ path
            ".claude/scripts",      # Direct reference to user home
            "home_script",          # Variable name from old fallback code
            "Fallback to user",     # Comment from old code
        ]

        violations = [p for p in forbidden_patterns if p in content]

        assert not violations, (
            f"gateway.py contains fallback patterns: {violations}\n"
            f"FALLBACKS ARE ILLEGAL - they hide incompetence.\n"
            f"The code must fail loudly if project script is missing."
        )
