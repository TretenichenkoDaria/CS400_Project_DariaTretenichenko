import os
import sys
import subprocess

def run_tests():
    failed = 0
    for f in sorted(os.listdir("tests/ok")):
        if not f.endswith(".txt"):
            continue
        p = f"tests/ok/" + f
        res = subprocess.run(["python3", "compiler.py", "--ast", p], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"failed ok test: {f}")
            print(f"error: {res.stderr.strip()}")
            failed += 1
        else:
            print(f"passed: {f}")
            print(res.stdout.strip())

    for f in sorted(os.listdir("tests/err")):
        if not f.endswith(".txt"):
            continue
        p = f"tests/err/" + f
        res = subprocess.run(["python3", "compiler.py", "--ast", p], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"failed error test: {f}")
            failed += 1
        else:
            print(f"passed: {f}")
            print(f"caught error: {res.stderr.strip()}")

    if failed == 0:
        print("all tests passed")
        sys.exit(0)
    else:
        print(f"{failed} tests failed")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()