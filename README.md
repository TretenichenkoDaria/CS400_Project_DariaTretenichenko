# Survival Language Compiler — Stage 1

A domain-specific programming language set in a harsh, post-apocalyptic steppe where data and state must survive to compile.

---

## 1. Language Overview & Syntax

### 1.1 Types
The language supports three primary data types:
* `🩸` — Signed 32-bit integer (`i32`), valid range: `[-2147483648, 2147483647]`.
* `🫀` — Signed 64-bit integer (`i64`), valid range: `[-9223372036854775808, 9223372036854775807]`.
* `💊` — Boolean type (`bool`), taking literals `alive` (true) or `dead` (false).

**Type Overflow Checks:** Integer constants are strictly checked during compilation. Any constant exceeding 64-bit integer limits produces a compilation error. Furthermore, constants initializing `🩸` (`i32`) variables are checked to ensure they do not exceed the 32-bit integer bounds.

---

### 1.2 Variables & Assignment
* `infect` — Declares a mutable variable.
* `immune` — Declares an immutable constant.
* `💉` — Assignment / binding operator.
* `⏳` — Statement terminator (line delimiter).

**Example:**
```
infect 🩸 hp 💉 100 ⏳
immune 🩸 damage 💉 25 ⏳
hp 💉 hp - damage ⏳
```

---

### 1.3 Arithmetic Operations
The language supports binary arithmetic operators with standard mathematical precedence:
* `+` — Addition (left-associative)
* `-` — Subtraction (left-associative)
* `*` — Multiplication (binds tighter than `+` and `-`)

**Example:**
```
immune 🫀 total 💉 2 * 3 + 4 ⏳
```
Evaluates as `(2 * 3) + 4`.

---

### 1.4 Comparisons & Boolean Logic
* `==` — Equality comparison
* `!=` — Inequality comparison
* `!` — Unary logical negation (NOT)
* `alive` — Boolean literal representing true
* `dead` — Boolean literal representing false

**Examples:**
```
immune 💊 is_safe 💉 5 == 5 ⏳
immune 💊 is_danger 💉 5 != 10 ⏳
immune 💊 inverted 💉 !alive ⏳
```

---

### 1.5 Control Flow (`survive` / `perish`)
Branching is implemented using `survive` (if) and `perish` (else):
```
survive alive {
    infect 🩸 supply 💉 1 ⏳
} perish {
    infect 🩸 supply 💉 2 ⏳
}
```
* Braced blocks `{ ... }` may be nested.
* An else-block (`perish { ... }`) is optional.
* Blocks cannot be empty and statements inside blocks must adhere to line termination rules.

---

### 1.6 Exit Statement
Every valid program must conclude with a mandatory `exit` statement:
```
exit <expr> ⏳
```
Any code appearing after `exit` is rejected at compile time as unreachable code.

---

### 1.7 Lexical Structure & Token Delimiters
* Identifiers follow `[a-zA-Z_][a-zA-Z0-9_]*`.
* Emojis (`🩸`, `🫀`, `💊`, `💉`, `⏳`) are dedicated multi-byte UTF-8 tokens.
* Emojis are tokenized independently without requiring surrounding spaces (e.g., `x💉5⏳` cleanly tokenizes as `x`, `💉`, `5`, `⏳`).
* Line discipline: each statement resides on its own line ending with `⏳`.

---

## 2. Compiler Architecture & AST Hierarchy

The compiler is organized into a modular object-oriented architecture:

```
cs400-compiler/
├── tokens.py        # Token class and TokenKind enumerations
├── ast_nodes.py     # Object-oriented AST node hierarchy
├── lexer.py         # UTF-8 byte-aware lexer with overflow checks
├── parser.py        # Recursive-descent parser
├── compiler.py      # Main CLI compiler driver
├── run_tests.py     # Automated test suite runner with .expected comparison
├── test_maker.py    # Backwards-compatible test runner wrapper
├── grammar.ebnf     # Formal ISO EBNF grammar specification
├── ai_usage.txt     # AI transparency and modification log
└── tests/
    ├── ok/          # 15 valid test cases (.txt and .expected)
    └── err/         # 15 invalid error test cases (.txt and .expected)
```

### AST Base-Class Hierarchy
All AST nodes inherit from the common abstract base class `ASTNode`:

```
                 ASTNode
                /       \
        Statement       Expression
        /   |   \           |    \
       /    |    \      BinaryOp  UnaryOp
  Declaration  Assignment         /      \
      |            |         Variable   Literal
  IfStatement   ExitNode               /       \
                               ConstantNode   BooleanNode
```

---

## 3. How to Run

### 3.1 Compiling a Program and Printing the AST
To parse a source file and print its Abstract Syntax Tree:
```bash
python3 compiler.py --ast <input_file.txt>
```

**Example:**
```bash
python3 compiler.py --ast tests/ok/cmp_eq.txt
```

**Output:**
```
program
  decl b 💊 const
    binop ==
      const 5
      const 5
  exit
    const 1
```

---

### 3.2 Running the Test Suite
To run all 30 tests (15 valid tests and 15 error tests) with automatic comparison against their `.expected` outputs:
```bash
python3 run_tests.py
```

*(Alternatively, `python3 test_maker.py` also runs the suite).*

**Expected Test Output:**
```
Running positive tests (tests/ok)...
[PASS] assign_var.txt
[PASS] cmp_eq.txt
[PASS] cmp_neq.txt
[PASS] decl_bool_alive.txt
[PASS] decl_imm_i32.txt
[PASS] decl_inf_i64.txt
[PASS] exit_complex.txt
[PASS] math_add.txt
[PASS] math_complex.txt
[PASS] math_sub.txt
[PASS] multiple_stmts.txt
[PASS] not_op.txt
[PASS] survive_nested.txt
[PASS] survive_only.txt
[PASS] survive_perish.txt

Running negative tests (tests/err)...
[PASS] err_bad_assign.txt
[PASS] err_bad_byte.txt
[PASS] err_bad_eq.txt
[PASS] err_bad_type.txt
[PASS] err_double_decl.txt
[PASS] err_else_without_if.txt
[PASS] err_exit_in_block.txt
[PASS] err_if_empty.txt
[PASS] err_if_no_brace.txt
[PASS] err_junk_end.txt
[PASS] err_letter_in_num.txt
[PASS] err_missing_semi.txt
[PASS] err_no_exit.txt
[PASS] err_no_init.txt
[PASS] err_unclosed_block.txt

Test Summary: 30/30 passed.
All tests passed successfully!
```