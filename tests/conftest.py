"""
Global Test Harness - Core pytest configuration
================================================

This conftest.py provides automatic test infrastructure for all projects.

USAGE:
------
Option 1 (Recommended): Copy this file to your project's tests/ directory
Option 2: Import in your project's conftest.py:
    from pathlib import Path
    exec(Path.home().joinpath(".claude/testing/conftest.py").read_text())

WHAT THIS PROVIDES:
-------------------
1. Automatic 5-second timeout per test (configurable via marker)
2. Individual test timing in output
3. JSON report generation with timestamps
4. Guaranteed termination enforcement
5. Clear failure on timeout (not silent)

DOCUMENTATION:
--------------
See ~/.claude/topics/testing/GLOBAL_TEST_HARNESS.md
"""

import time
import json
import os
from datetime import datetime
from pathlib import Path

import pytest


# =============================================================================
# CONFIGURATION
# =============================================================================

DEFAULT_TIMEOUT_SECONDS = 5
REPORT_OUTPUT_DIR = Path.home() / ".claude" / "testing" / "reports"


# =============================================================================
# TIMING INFRASTRUCTURE
# =============================================================================

class TestTimingPlugin:
    """Records individual test timing with timestamps."""

    def __init__(self):
        self.results = []
        self.current_test_start = None
        self.session_start = None

    def pytest_sessionstart(self, session):
        self.session_start = datetime.now()
        self.results = []

    def pytest_runtest_setup(self, item):
        self.current_test_start = time.perf_counter()

    def pytest_runtest_makereport(self, item, call):
        if call.when == "call":
            duration = time.perf_counter() - self.current_test_start
            self.results.append({
                "name": item.name,
                "nodeid": item.nodeid,
                "duration_seconds": round(duration, 4),
                "timestamp": datetime.now().isoformat(),
                "outcome": "passed" if call.excinfo is None else "failed",
                "timeout_seconds": self._get_timeout(item),
            })

    def _get_timeout(self, item):
        """Get timeout for this test (from marker or default)."""
        marker = item.get_closest_marker("timeout")
        if marker:
            return marker.args[0] if marker.args else DEFAULT_TIMEOUT_SECONDS
        return DEFAULT_TIMEOUT_SECONDS

    def pytest_sessionfinish(self, session, exitstatus):
        """Generate timing report at end of session."""
        if not self.results:
            return

        # Check for early stopping (e.g., -x flag)
        collected_count = len(session.items) if hasattr(session, 'items') else 0
        ran_count = len(self.results)
        stopped_early = collected_count > 0 and ran_count < collected_count

        # Ensure report directory exists
        REPORT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Generate report filename
        timestamp = self.session_start.strftime("%Y%m%d_%H%M%S")
        project_name = Path.cwd().name
        report_file = REPORT_OUTPUT_DIR / f"{project_name}_{timestamp}.json"

        # Sort by duration (slowest first)
        sorted_results = sorted(self.results, key=lambda x: x["duration_seconds"], reverse=True)

        # Calculate summary
        total_duration = sum(r["duration_seconds"] for r in self.results)
        passed_count = sum(1 for r in self.results if r["outcome"] == "passed")
        failed_count = sum(1 for r in self.results if r["outcome"] == "failed")

        report = {
            "session": {
                "start": self.session_start.isoformat(),
                "end": datetime.now().isoformat(),
                "total_duration_seconds": round(total_duration, 2),
                "test_count": len(self.results),
                "passed": passed_count,
                "failed": failed_count,
                "project": project_name,
            },
            "tests_by_duration": sorted_results,
            "slowest_10": sorted_results[:10],
        }

        # Write report
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        # Print summary to console
        print(f"\n{'='*60}")
        print("TEST HARNESS TIMING REPORT")
        print(f"{'='*60}")
        if stopped_early:
            remaining = collected_count - ran_count
            print(f"STOPPED EARLY: Ran {ran_count} of {collected_count} tests ({remaining} not run)")
            print(f"Reason: Test failure with -x flag (stop on first failure)")
        else:
            print(f"Total: {len(self.results)} tests in {total_duration:.2f}s")
        print(f"Passed: {passed_count}, Failed: {failed_count}")
        print(f"\nTop 5 slowest tests:")
        for i, test in enumerate(sorted_results[:5], 1):
            status = "PASS" if test["outcome"] == "passed" else "FAIL"
            print(f"  {i}. [{status}] {test['duration_seconds']:.3f}s - {test['name']}")
        print(f"\nFull report: {report_file}")
        print(f"{'='*60}\n")


# =============================================================================
# PYTEST HOOKS
# =============================================================================

def pytest_configure(config):
    """Register the timing plugin and enforce warnings as errors."""
    import warnings

    # ==========================================================================
    # WARNINGS AS ERRORS - CANNOT BE BYPASSED
    # ==========================================================================
    # This runs AFTER command line parsing, overriding any -W flags.
    # Warnings are errors. Period. No exceptions except documented ones below.
    # ==========================================================================

    warnings.filterwarnings("error")

    # Approved suppressions (each must be documented with date and reason):
    # - FAISS SWIG internal types lack __module__ (upstream SWIG issue, 2026-01-15)
    warnings.filterwarnings("ignore", message=r"builtin type Swig.*has no __module__")

    config.pluginmanager.register(TestTimingPlugin(), "test_timing_plugin")

    # Register custom markers
    config.addinivalue_line(
        "markers", "timeout(seconds): Set custom timeout for this test"
    )
    config.addinivalue_line(
        "markers", "slow: Mark test as slow (gets extended timeout)"
    )


def pytest_collection_modifyitems(config, items):
    """Apply default timeout to all tests."""
    for item in items:
        # Skip if test already has timeout marker
        if item.get_closest_marker("timeout"):
            continue

        # Apply extended timeout for tests marked as slow
        if item.get_closest_marker("slow"):
            item.add_marker(pytest.mark.timeout(30))
        else:
            # Apply default timeout
            item.add_marker(pytest.mark.timeout(DEFAULT_TIMEOUT_SECONDS))


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(autouse=True)
def _test_timing_context(request):
    """Provides timing context for each test (autouse)."""
    start = time.perf_counter()
    yield
    duration = time.perf_counter() - start

    # Warn if test is approaching timeout
    timeout = DEFAULT_TIMEOUT_SECONDS
    marker = request.node.get_closest_marker("timeout")
    if marker and marker.args:
        timeout = marker.args[0]

    if duration > timeout * 0.8:
        print(f"\n  WARNING: Test '{request.node.name}' took {duration:.2f}s "
              f"(80%+ of {timeout}s timeout)")




# =============================================================================
# UNBYPASSABLE WARNINGS AS ERRORS
# =============================================================================

@pytest.fixture(autouse=True)
def _enforce_warnings_as_errors():
    """
    Enforce warnings as errors for EVERY test.
    
    This cannot be bypassed by -W flags because it runs inside each test.
    """
    import warnings
    
    # Save current filters
    old_filters = warnings.filters[:]
    
    # Force warnings as errors
    warnings.resetwarnings()
    warnings.filterwarnings("error")
    
    # Approved suppressions only:
    # - FAISS SWIG internal types (upstream issue, 2026-01-15)
    warnings.filterwarnings("ignore", message=r"builtin type Swig.*has no __module__")
    
    yield
    
    # Restore (though test should have failed if warning occurred)
    warnings.filters[:] = old_filters


@pytest.fixture
def timing_report(request):
    """
    Fixture to get timing information for the current test.

    Usage:
        def test_something(timing_report):
            # ... test code ...
            timing_report["custom_metric"] = some_value
    """
    report = {
        "test_name": request.node.name,
        "start_time": datetime.now().isoformat(),
    }
    yield report
    report["end_time"] = datetime.now().isoformat()
