import os
import subprocess
import sys


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
            base_name = filename[:-4]
            expected_path = os.path.join(ok_dir, base_name + ".expected")
            in_path = os.path.join(ok_dir, base_name + ".in")
            ll_path = os.path.join(ok_dir, base_name + ".ll")
            bin_path = os.path.join(ok_dir, base_name + ".bin")

            with open(expected_path, "r", encoding="utf-8") as f:
                expected_output = f.read().strip()

            if expected_output.startswith("program"):
                # Stage 1 AST test
                result = subprocess.run(
                    [sys.executable, "compiler.py", "--ast", test_path],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    print(f"[FAIL] {filename}: returned non-zero exit code {result.returncode}")
                    failed += 1
                    continue
                actual_output = result.stdout.strip()
                if actual_output != expected_output:
                    print(f"[FAIL] {filename}: AST output mismatch")
                    failed += 1
                    continue
                print(f"[PASS] {filename} (AST)")
            else:
                # Stage 2 End-to-end test
                compile_res = subprocess.run(
                    [sys.executable, "compiler.py", test_path, ll_path],
                    capture_output=True,
                    text=True,
                )
                if compile_res.returncode != 0:
                    print(f"[FAIL] {filename}: compilation failed: {compile_res.stderr.strip()}")
                    failed += 1
                    continue

                clang_res = subprocess.run(
                    ["clang", ll_path, "-o", bin_path],
                    capture_output=True,
                    text=True,
                )
                if clang_res.returncode != 0:
                    print(f"[FAIL] {filename}: clang link failed: {clang_res.stderr.strip()}")
                    failed += 1
                    if os.path.exists(ll_path):
                        os.remove(ll_path)
                    continue

                stdin_data = None
                if os.path.exists(in_path):
                    with open(in_path, "r", encoding="utf-8") as inf:
                        stdin_data = inf.read()

                run_res = subprocess.run(
                    [bin_path],
                    input=stdin_data,
                    capture_output=True,
                    text=True,
                )

                actual_output = run_res.stdout.strip()
                if actual_output != expected_output:
                    print(f"[FAIL] {filename}: output mismatch")
                    print(f"--- Expected:\n{expected_output}\n--- Actual:\n{actual_output}")
                    failed += 1
                else:
                    print(f"[PASS] {filename} (End-to-End)")

                for cleanup_file in (ll_path, bin_path):
                    if os.path.exists(cleanup_file):
                        os.remove(cleanup_file)

    print("\nRunning negative tests (tests/err)...")
    err_dir = "tests/err"
    if os.path.exists(err_dir):
        for filename in sorted(os.listdir(err_dir)):
            if not filename.endswith(".txt"):
                continue
            total += 1
            test_path = os.path.join(err_dir, filename)
            base_name = filename[:-4]
            expected_path = os.path.join(err_dir, base_name + ".expected")
            ll_path = os.path.join(err_dir, base_name + ".ll")

            result = subprocess.run(
                [sys.executable, "compiler.py", test_path, ll_path],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print(f"[FAIL] {filename}: expected compilation error, but exited with code 0")
                if os.path.exists(ll_path):
                    os.remove(ll_path)
                failed += 1
                continue

            if os.path.exists(ll_path):
                print(f"[FAIL] {filename}: output .ll file was produced despite error")
                os.remove(ll_path)
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
