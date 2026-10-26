"""Automated test runner verifying compiler output and exit codes against expected files."""

import os
import subprocess
import sys
from typing import Tuple


def run_test_suite() -> int:
    failed = 0
    total = 0

    print("Running positive tests (tests/ok)...")
    ok_dir = "tests/ok"
    if os.path.exists(ok_dir):
        for filename in sorted(os.listdir(ok_dir)):
            if not filename.endswith(".txt"):
                continue
            total += 1
            test_path = os.path.join(ok_dir, filename)
            expected_path = os.path.join(ok_dir, filename[:-4] + ".expected")

            result = subprocess.run(
                [sys.executable, "compiler.py", "--ast", test_path],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                print(f"[FAIL] {filename}: returned non-zero exit code {result.returncode}")
                if result.stderr:
                    print(f"       error: {result.stderr.strip()}")
                failed += 1
                continue

            if os.path.exists(expected_path):
                with open(expected_path, "r", encoding="utf-8") as f:
                    expected_output = f.read().strip()
                actual_output = result.stdout.strip()

                if actual_output != expected_output:
                    print(f"[FAIL] {filename}: stdout does not match {expected_path}")
                    print(f"--- Expected:\n{expected_output}\n--- Actual:\n{actual_output}")
                    failed += 1
                    continue

            print(f"[PASS] {filename}")

    print("\nRunning negative tests (tests/err)...")
    err_dir = "tests/err"
    if os.path.exists(err_dir):
        for filename in sorted(os.listdir(err_dir)):
            if not filename.endswith(".txt"):
                continue
            total += 1
            test_path = os.path.join(err_dir, filename)
            expected_path = os.path.join(err_dir, filename[:-4] + ".expected")

            result = subprocess.run(
                [sys.executable, "compiler.py", "--ast", test_path],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print(f"[FAIL] {filename}: expected compilation error, but exited with code 0")
                failed += 1
                continue

            if os.path.exists(expected_path):
                with open(expected_path, "r", encoding="utf-8") as f:
                    expected_err = f.read().strip()
                actual_err = result.stderr.strip()

                if actual_err != expected_err:
                    print(f"[FAIL] {filename}: stderr does not match {expected_path}")
                    print(f"--- Expected:\n{expected_err}\n--- Actual:\n{actual_err}")
                    failed += 1
                    continue

            print(f"[PASS] {filename}")

    passed = total - failed
    print(f"\nTest Summary: {passed}/{total} passed.")
    if failed == 0:
        print("All tests passed successfully!")
        return 0
    else:
        print(f"{failed} tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(run_test_suite())
