# Survival Language Compiler — Stage 3

A domain-specific programming language set in a harsh, post-apocalyptic steppe where data and state must survive to compile. Stage 3 adds custom iteration primitives (`endure` while loops, `scavenge` for-range loops, `flee` break), an AST optimizer with three passes behind `--optimize`, and a full interactive terminal survival simulation compiled to native machine code.

---

## 1. Language Overview & Syntax

### 1.1 Types
* `🩸` — Signed 32-bit integer (`i32`), valid range: `[-2147483648, 2147483647]`.
* `🫀` — Signed 64-bit integer (`i64`), valid range: `[-9223372036854775808, 9223372036854775807]`.
* `💊` — Boolean type (`bool`), taking literals `alive` (true) or `dead` (false).
* Named Structure Types (`identifier`) — Defined via `shelter` / `struct`.

### 1.2 Variables & Assignment
* `infect` — Declares a mutable variable.
* `immune` — Declares an immutable constant.
* `💉` — Assignment / binding operator.
* `⏳` — Statement terminator.

### 1.3 Arithmetic & Logic
* Binary arithmetic: `+`, `-`, `*` (standard precedence).
* Comparisons: `==`, `!=`.
* Unary: `!`.
* Literals: integers, booleans (`alive` / `dead`), and string literals (`"..."`).

### 1.4 Control Flow
* `survive <condition> { ... } perish { ... }` — Conditional branching.
* `endure <condition> { ... }` — Condition-controlled loop (`while`).
* `scavenge <var> amid <start> .. <end> { ... }` — Range-controlled loop (`for`).
* `flee ⏳` — Immediate termination of the innermost enclosing loop (`break`).

### 1.5 Exit Statement
* `exit <expr> ⏳` — Concludes the program with an exit code.

---

## 2. Stage 3 Feature: Loops (`endure`, `scavenge`, `flee`)

### Rules
1. `endure <condition> { ... }` evaluates `<condition>` before every iteration. The condition must evaluate to boolean `💊` (`alive` / `dead`); any other type produces a compilation error.
2. `scavenge <var> amid <start> .. <end> { ... }` evaluates `<start>` and `<end>`, which must both be integers (`🩸` or `🫀`) of the same type. The loop induction variable `<var>` is automatically scoped to the loop body, starting at `<start>` and incrementing by 1 while strictly less than `<end>`.
3. `flee ⏳` immediately transfers control to the basic block following the innermost active loop. Using `flee ⏳` outside any loop construct produces a compile-time error.
4. Loops may be nested arbitrarily deep, and loop bodies may declare their own variables which are re-scoped each iteration.

### Example Programs
```
infect 🩸 count 💉 0 ⏳
endure count != 3 {
  print count ⏳
  count 💉 count + 1 ⏳
}
exit 0 ⏳
```

```
scavenge i amid 0 .. 4 {
  print i ⏳
}
exit 0 ⏳
```

### LLVM IR Excerpt (Loop Lowering)
```llvm
loop_cond:
  %".4" = load i32, i32* %"count"
  %".5" = icmp ne i32 %".4", 3
  br i1 %".5", label %"loop_body", label %"loop_merge"
loop_body:
  %".7" = load i32, i32* %"count"
  %".8" = getelementptr [4 x i8], [4 x i8]* @"fmt_i32", i32 0, i32 0
  %".9" = call i32 (i8*, ...) @"printf"(i8* %".8", i32 %".7")
  %".10" = load i32, i32* %"count"
  %".11" = add i32 %".10", 1
  store i32 %".11", i32* %"count"
  br label %"loop_cond"
loop_merge:
  ret i32 0
```
* **Explanation:**
  * In `loop_cond`, the loop guard evaluates the condition and conditionally branches to either the loop body or loop exit (`loop_merge`).
  * In `loop_body`, the body statements execute, here printing the current count and incrementing the stored variable.
  * The unconditional branch `br label %"loop_cond"` forms the back edge, transferring control back to the condition header for the next iteration.

---

## 3. Stage 3 Task 2: The Optimizer (`--optimize`)

The optimizer runs three AST-level transformations on the checked tree before code generation:
1. **Unused variables:** Scans declarations and assignments; any variable never read across the entire program (taking lexical scopes and shadowing into account) is eliminated along with its assignments. Initializers or expressions containing function calls or `read()` are never dropped.
2. **Unused functions:** Removes any top-level function that is never called directly or indirectly from live code. Removing an unused function body may uncover additional uncalled functions, which are eliminated in subsequent iterations until a fixpoint is reached.
3. **Inlining:** Functions called exactly once across the program that are non-recursive, have a single exit point (`yield` / `return` at the end of their body), and contain no early exits are replaced directly at their call site. Each formal parameter becomes a local declaration bound to the evaluated argument, body statements are inserted before the call site with unique alpha-renamed variables to avoid collisions with the caller, and the return expression substitutes the call node. Recursive functions, functions called more than once, and functions containing `exit` statements inside branches are left intact.

### Before and After Inlining Excerpt (LLVM IR)

**Before Inlining (calls `f_square` via `call` instruction):**
```llvm
define i32 @"f_square"(i32 %".1")
{
entry:
  %"x" = alloca i32
  store i32 %".1", i32* %"x"
  %".4" = load i32, i32* %"x"
  %".5" = load i32, i32* %"x"
  %".6" = mul i32 %".4", %".5"
  ret i32 %".6"
}

define i32 @"main"()
{
entry:
  %"val" = alloca i32
  store i32 7, i32* %"val"
  %".3" = load i32, i32* %"val"
  %".4" = call i32 @"f_square"(i32 %".3")
  store i32 %".4", i32* %"val"
  ...
```

**After Inlining (`f_square` eliminated, body substituted in `main`):**
```llvm
define i32 @"main"()
{
entry:
  %"val" = alloca i32
  store i32 7, i32* %"val"
  %"inline_square_3_x" = alloca i32
  %".3" = load i32, i32* %"val"
  store i32 %".3", i32* %"inline_square_3_x"
  %".5" = load i32, i32* %"inline_square_3_x"
  %".6" = load i32, i32* %"inline_square_3_x"
  %".7" = mul i32 %".5", %".6"
  store i32 %".7", i32* %"val"
  ...
```

---

## 4. Stage 3 Task 3: Interactive Program (`programs/survival_game.txt`)

`programs/survival_game.txt` is an interactive post-apocalyptic steppe survival simulation.
* **What it does:** The user guides a survivor across days on the steppe, balancing health, food, and day count.
* **Language features used:** Uses structure `Survivor` with two mutating member functions (`rest`, `forage`), helper function `calculate_score`, console input/output (`read`, `print`), and custom loops (`endure`, `scavenge`, and `flee`).
* **Where the feature is used:** An outer `endure` loop drives the interactive day-by-day turns; inside action 2, a `scavenge` for-range loop simulates searching across multiple areas; action 3 uses `flee` to break out and escape to camp.

### Compilation to Native Binary with `llc` and `clang`
```bash
python3 compiler.py programs/survival_game.txt programs/survival_game.ll
llc -filetype=obj programs/survival_game.ll -o programs/survival_game.o
clang programs/survival_game.o -o programs/survival_game
./programs/survival_game
```

### Running Recorded Sessions
* **Session 1 (Rest and Flee):**
  ```bash
  ./programs/survival_game < programs/survival_game.in
  ```
* **Session 2 (Forage search and Flee):**
  ```bash
  ./programs/survival_game < programs/survival_game_2.in
  ```

---

## 5. How to Run

### 5.1 Generating LLVM IR
```bash
python3 compiler.py input.txt output.ll
```
With the optimizer enabled:
```bash
python3 compiler.py --optimize input.txt output.ll
```

### 5.2 Compiling with Clang and Running
```bash
clang output.ll -o program
./program
```

### 5.3 Printing the AST
```bash
python3 compiler.py --ast input.txt
```
To print the AST after optimization:
```bash
python3 compiler.py --optimize --ast input.txt
```

### 5.4 Running All Tests
```bash
python3 run_tests.py
```

---

## 6. Test Suite Summary
All 64 test scenarios pass:
* **28 Positive Unit Tests (`tests/ok`):** 15 AST tests and 13 End-to-End tests (including `loop_while`, `loop_for`, `loop_nested`).
* **28 Negative Tests (`tests/err`):** 28 semantic and syntax validation tests (including `err_loop_cond_type`, `err_loop_for_range`, `err_break_outside_loop`).
* **6 Optimizer Tests (`tests/opt`):** 2 unused variable tests, 2 unused function tests, 2 inlining tests, verifying AST after `--optimize --ast` and output consistency.
* **2 Interactive Program Sessions (`programs/`):** Session 1 and Session 2 automated with stdin and stdout matching.
