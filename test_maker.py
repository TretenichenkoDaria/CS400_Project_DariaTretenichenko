"""Test runner entrypoint (delegates to run_tests.py)."""

import sys
from run_tests import run_test_suite

if __name__ == "__main__":
    sys.exit(run_test_suite())