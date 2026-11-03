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

    print("\nRunning optimizer tests (tests/opt)...")
    opt_dir = "tests/opt"
    if os.path.exists(opt_dir):
        for filename in sorted(os.listdir(opt_dir)):
            if not filename.endswith(".txt"):
                continue
            total += 1
            test_path = os.path.join(opt_dir, filename)
            base_name = filename[:-4]
            opt_ast_path = os.path.join(opt_dir, base_name + ".opt_ast")
            expected_path = os.path.join(opt_dir, base_name + ".expected")
            ll_no_opt = os.path.join(opt_dir, base_name + "_no_opt.ll")
            bin_no_opt = os.path.join(opt_dir, base_name + "_no_opt.bin")
            ll_opt = os.path.join(opt_dir, base_name + "_opt.ll")
            bin_opt = os.path.join(opt_dir, base_name + "_opt.bin")

            with open(expected_path, "r", encoding="utf-8") as f:
                expected_output = f.read().strip()

            with open(opt_ast_path, "r", encoding="utf-8") as f:
                expected_opt_ast = f.read().strip()

            ast_res = subprocess.run(
                [sys.executable, "compiler.py", "--optimize", "--ast", test_path],
                capture_output=True,
                text=True,
            )
            if ast_res.returncode != 0:
                print(f"[FAIL] {filename} (--optimize --ast failed): {ast_res.stderr.strip()}")
                failed += 1
                continue
            actual_opt_ast = ast_res.stdout.strip()
            if actual_opt_ast != expected_opt_ast:
                print(f"[FAIL] {filename}: optimized AST mismatch")
                print(f"--- Expected:\n{expected_opt_ast}\n--- Actual:\n{actual_opt_ast}")
                failed += 1
                continue

            c1 = subprocess.run([sys.executable, "compiler.py", test_path, ll_no_opt], capture_output=True, text=True)
            if c1.returncode != 0:
                print(f"[FAIL] {filename}: compilation without --optimize failed: {c1.stderr.strip()}")
                failed += 1
                continue
            l1 = subprocess.run(["clang", ll_no_opt, "-o", bin_no_opt], capture_output=True, text=True)
            if l1.returncode != 0:
                print(f"[FAIL] {filename}: clang link (unoptimized) failed")
                failed += 1
                continue
            r1 = subprocess.run([bin_no_opt], capture_output=True, text=True)

            c2 = subprocess.run([sys.executable, "compiler.py", "--optimize", test_path, ll_opt], capture_output=True, text=True)
            if c2.returncode != 0:
                print(f"[FAIL] {filename}: compilation with --optimize failed: {c2.stderr.strip()}")
                failed += 1
                continue
            l2 = subprocess.run(["clang", ll_opt, "-o", bin_opt], capture_output=True, text=True)
            if l2.returncode != 0:
                print(f"[FAIL] {filename}: clang link (optimized) failed")
                failed += 1
                continue
            r2 = subprocess.run([bin_opt], capture_output=True, text=True)

            out1 = r1.stdout.strip()
            out2 = r2.stdout.strip()

            for cl in (ll_no_opt, bin_no_opt, ll_opt, bin_opt):
                if os.path.exists(cl):
                    os.remove(cl)

            if out1 != expected_output or out2 != expected_output:
                print(f"[FAIL] {filename}: output mismatch (no_opt={out1}, opt={out2}, expected={expected_output})")
                failed += 1
                continue

            print(f"[PASS] {filename} (Optimized AST & Execution match)")

    print("\nRunning interactive programs (programs/)...")
    prog_dir = "programs"
    if os.path.exists(prog_dir):
        prog_file = os.path.join(prog_dir, "survival_game.txt")
        if os.path.exists(prog_file):
            prog_ll = os.path.join(prog_dir, "survival_game.ll")
            prog_bin = os.path.join(prog_dir, "survival_game.bin")
            comp = subprocess.run([sys.executable, "compiler.py", prog_file, prog_ll], capture_output=True, text=True)
            if comp.returncode == 0:
                lnk = subprocess.run(["clang", prog_ll, "-o", prog_bin], capture_output=True, text=True)
                if lnk.returncode == 0:
                    for s_in, s_exp, label in [
                        (os.path.join(prog_dir, "survival_game.in"), os.path.join(prog_dir, "survival_game.expected"), "Session 1"),
                        (os.path.join(prog_dir, "survival_game_2.in"), os.path.join(prog_dir, "survival_game_2.expected"), "Session 2"),
                    ]:
                        total += 1
                        with open(s_in, "r", encoding="utf-8") as f:
                            sin_data = f.read()
                        with open(s_exp, "r", encoding="utf-8") as f:
                            sexp_data = f.read().strip()
                        prun = subprocess.run([prog_bin], input=sin_data, capture_output=True, text=True)
                        pout = prun.stdout.strip()
                        if pout == sexp_data:
                            print(f"[PASS] survival_game ({label})")
                        else:
                            print(f"[FAIL] survival_game ({label}): output mismatch")
                            print(f"--- Expected:\n{sexp_data}\n--- Actual:\n{pout}")
                            failed += 1
                else:
                    print(f"[FAIL] survival_game linking failed: {lnk.stderr.strip()}")
                    failed += 1
            else:
                print(f"[FAIL] survival_game compilation failed: {comp.stderr.strip()}")
                failed += 1

            for cl in (prog_ll, prog_bin):
                if os.path.exists(cl):
                    os.remove(cl)

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
