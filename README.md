# Survival Language Compiler — Stage 2

A domain-specific programming language set in a harsh, post-apocalyptic steppe where data and state must survive to compile. Stage 2 adds functions, structures with fields and member functions, input/output built-ins (`read`, `print`), and full LLVM IR code generation via `llvmlite.ir`.

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
* `survive <condition> { ... } perish { ... }`

### 1.5 Exit Statement
* `exit <expr> ⏳` — Concludes the program with an exit code.

---

## 2. Stage 2 Features & Semantic Rules

### Rule 1: Function Argument Types and Count
* **Rule:** A function call must provide exactly the number of arguments declared in the function parameter list, and each argument expression must evaluate to the declared parameter type.
* **Syntax:**
  ```
  ritual add ( immune 🩸 a , immune 🩸 b ) -> 🩸 {
    yield a + b ⏳
  }
  ```
* **Follows rule:** `tests/ok/fn_call.txt`
* **Breaks rule (count):** `tests/err/err_too_many_args.txt`, `tests/err/err_too_few_args.txt`
* **Breaks rule (type):** `tests/err/err_arg_wrong_type.txt`

### Rule 2: Function Return Type Consistency
* **Rule:** A function leaves with a value via `yield` / `return`. The evaluated expression type must match the function's declared return type.
* **Syntax:**
  ```
  yield <expr> ⏳
  ```
* **Follows rule:** `tests/ok/fn_recursion.txt`
* **Breaks rule:** `tests/err/err_return_wrong_type.txt`

### Rule 3: Function Visibility and Mutual Recursion
* **Rule:** A function may call itself (recursion) and may call any function declared below it (forward references). All functions in a module are declared before bodies are emitted.
* **Follows rule:** `tests/ok/fn_forward_call.txt`
* **Breaks rule (duplicate):** `tests/err/err_duplicate_function.txt`

### Rule 4: Structure Declaration and Field Existence
* **Rule:** Accessing a field via dot notation (`obj.field`) requires that `obj` is of a declared structure type and `field` exists within that structure definition. Structure names must be unique in global scope.
* **Syntax:**
  ```
  shelter Point {
    infect 🩸 x ⏳
    infect 🩸 y ⏳
  }
  infect Point p 💉 Point { 7, 14 } ⏳
  print p.x ⏳
  ```
* **Follows rule:** `tests/ok/struct_basic.txt`
* **Breaks rule (unknown field):** `tests/err/err_unknown_field.txt`
* **Breaks rule (duplicate struct):** `tests/err/err_duplicate_struct.txt`

### Rule 5: Assignment Through Mutable Chains
* **Rule:** Assignment to a field through a chain (`a.b.c 💉 val ⏳`) is permitted only if every link in the chain is declared mutable (`infect`).
* **Syntax:**
  ```
  p.pos.x 💉 42 ⏳
  ```
* **Follows rule:** `tests/ok/struct_chain_assign.txt`
* **Breaks rule:** `tests/err/err_const_chain_assign.txt`

### Rule 6: Name Lookup Inside Member Functions & Method Resolution
* **Rule:** Inside a member function, a name is looked up among parameters and locals, then the structure fields, then the global symbols. Calling an undefined method on a structure is rejected.
* **Syntax:**
  ```
  shelter Box {
    infect 🩸 w ⏳
    infect 🩸 h ⏳
    ritual area ( ) -> 🩸 {
      yield w * h ⏳
    }
  }
  ```
* **Follows rule:** `tests/ok/struct_method.txt`
* **Breaks rule:** `tests/err/err_unknown_method.txt`

### Rule 7: Mutating Member Functions on Constant Objects
* **Rule:** A member function that assigns to any field of its structure may only be invoked on a mutable object (`infect`). Calling it on an immutable object (`immune`) is rejected at compile time.
* **Syntax:**
  ```
  shelter Counter {
    infect 🩸 val ⏳
    ritual inc ( ) -> 🩸 {
      val 💉 val + 1 ⏳
      yield val ⏳
    }
  }
  ```
* **Follows rule:** `tests/ok/struct_mut_method.txt`
* **Breaks rule:** `tests/err/err_mut_method_on_const.txt`

### Rule 8: Built-in Input (`read`)
* **Rule:** `read()` reads one integer from standard input using `scanf("%d")` and evaluates to type `🩸` (`i32`).
* **Follows rule:** `tests/ok/point_read.txt` (reads input from `point_read.in`)

### Rule 9: Built-in Output (`print`) and Object Printing
* **Rule:** `print(expr) ⏳` prints an integer (`%d` for `🩸`, `%lld` for `🫀`), a boolean as `true` or `false`, a string literal as `%s`, or an object by walking its field table in order and printing each field value. Every `print` statement emits a trailing newline `\n`.
* **Follows rule:** `tests/ok/print_types.txt`

---

## 3. How to Run

### 3.1 Generating LLVM IR
Compile source code directly into LLVM IR:
```bash
python3 compiler.py input.txt output.ll
```

### 3.2 Compiling with Clang and Running
```bash
clang output.ll -o program
./program
```

### 3.3 Printing the AST
```bash
python3 compiler.py --ast input.txt
```

### 3.4 Running All Tests
Execute the full test suite (Stage 1 + Stage 2):
```bash
python3 run_tests.py
```
*(Alternatively: `python3 test_maker.py`)*

---

## 4. Test Suite Summary
All 50 tests pass:
* **25 Positive Tests (`tests/ok`):** 15 Stage 1 AST tests and 10 Stage 2 End-to-End compiled/executed tests.
* **25 Negative Tests (`tests/err`):** 15 Stage 1 tests and 10 Stage 2 semantic validation tests.