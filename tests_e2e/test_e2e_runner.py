"""Standalone E2E Test Suite Runner for NFA to DFA Simulator.

Discovers and executes all 5 tiers of opaque-box E2E and adversarial tests:
- Tier 1: Feature Coverage (Static Assets, Samples, Convert, Simulate, Regex, Strings)
- Tier 2: Boundary & Corner Cases (Empty strings, Epsilon, Single-state, Traps, Schemas)
- Tier 3: Cross-Feature Integration Workflows (Pipelines, Fault Injection, Equivalence)
- Tier 4: Real-World Applications (Modulo 3, Substring 001, Alternating, Tokenizer, TCP)
- Tier 5: Adversarial Stress & Security (Deep regex nesting, Traversal, Concurrency bursts, Payloads)

Usage:
    python tests_e2e/test_e2e_runner.py
"""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Explicit import of Tier 5 module for verification and direct suite inclusion
from tests_e2e import test_tier5_adversarial


# ANSI terminal styling
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RED = "\033[91m"
COLOR_CYAN = "\033[96m"
COLOR_MAGENTA = "\033[95m"


def main() -> int:
    """Discovers and runs all E2E test tiers, printing a structured report."""
    start_time = time.perf_counter()

    loader = unittest.TestLoader()
    start_dir = str(ROOT_DIR / "tests_e2e")
    suite = loader.discover(start_dir=start_dir, pattern="test_tier*.py")

    print("\n" + "=" * 78)
    print(f"{COLOR_BOLD}{COLOR_CYAN}    NFA TO DFA SIMULATOR — E2E TEST SUITE RUNNER (TIERS 1–5){COLOR_RESET}")
    print("=" * 78)
    print(f"Directory: {start_dir}")
    print(f"Python:    {sys.version.split()[0]} on {sys.platform}\n")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    elapsed = time.perf_counter() - start_time
    total_run = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)
    passed = total_run - failures - errors - skipped

    print("\n" + "=" * 78)
    print(f"{COLOR_BOLD}E2E TEST EXECUTION SUMMARY{COLOR_RESET}")
    print("=" * 78)
    print(f"  • Total Tests Discovered & Run : {COLOR_BOLD}{total_run}{COLOR_RESET}")
    print(f"  • Passed                       : {COLOR_GREEN}{passed}{COLOR_RESET}")
    print(f"  • Skipped (Pending M1 Endpoints): {COLOR_YELLOW}{skipped}{COLOR_RESET}")
    print(f"  • Failures                     : {COLOR_RED if failures else COLOR_GREEN}{failures}{COLOR_RESET}")
    print(f"  • Errors                       : {COLOR_RED if errors else COLOR_GREEN}{errors}{COLOR_RESET}")
    print(f"  • Execution Time               : {elapsed:.2f} seconds")
    print("=" * 78)

    if result.wasSuccessful():
        print(f"{COLOR_BOLD}{COLOR_GREEN}✓ ALL EXECUTED E2E TESTS PASSED SUCCESSFULLY!{COLOR_RESET}\n")
        return 0
    else:
        print(f"{COLOR_BOLD}{COLOR_RED}✗ E2E TEST SUITE ENCOUNTERED FAILURES OR ERRORS.{COLOR_RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
