my language is inspired by a game i have played recently and operates in a harsh, post-apocalyptic steppe setting where data must survive to compile

types:
* `🩸` - equivalent to `i32`
* `🫀` - equivalent to `i64`
* `💊` - equivalent to `bool` (values: `alive` / `dead`)

vars & assignment:
* `infect` - declares a mutable variable (mut)
* `immune` - declares a constant (immutable) variable
* `💉` - assignment operator
* `⏳` - statement terminator (instead of a semicolon)

example:

```bash
immune 🩸 damage 💉 50 ⏳
infect 🫀 health 💉 100 ⏳
health 💉 health - damage ⏳
```

control clow (if/else):
branching is handled using `survive` (if) and `perish` (else)

example:

```bash
survive alive {
infect 🩸 a 💉 1 ⏳
} perish {
infect 🩸 a 💉 2 ⏳
}
```

from our practice compiler i reused:
* core state-machine lexer logic (adapted to support UTF-8 bytes)
* recursive-descent parser mechanism (`peek`, `eat`, `exp`)
* basic ast node hierarchy (`programnode`, `binopnode`, etc.)


how to run a program:

```bash
python3 compiler_.py --ast <input_file.txt>


➜  CS400_Project_DariaTretenichenko python3 compiler.py --ast tests/ok/cmp_eq.txt
program
  decl b 💊 const
    binop ==
      const 5
      const 5
  exit
    const 1

```

how to run all tests:

```bash
python3 run_tests.py

```

expected result:

```bash
➜  CS400_Project_DariaTretenichenko python3 test_maker.py                        
passed: assign_var.txt
program
  decl a 🩸 mut
    const 10
  assign a
    const 20
  exit
    var a
passed: cmp_eq.txt
program
  decl b 💊 const
    binop ==
      const 5
      const 5
  exit
    const 1
passed: cmp_neq.txt
program
  decl b 💊 const
    binop !=
      const 5
      const 10
  exit
    const 1
passed: decl_bool_alive.txt
program
  decl z 💊 const
    bool alive
  exit
    const 1
passed: decl_imm_i32.txt
program
  decl x 🩸 const
    const 5
  exit
    var x
passed: decl_inf_i64.txt
program
  decl y 🫀 mut
    const 100
  exit
    var y
passed: exit_complex.txt
program
  decl a 🩸 const
    const 1
  exit
    binop +
      var a
      const 5
passed: math_add.txt
program
  decl a 🩸 const
    binop +
      const 5
      const 5
  exit
    var a
passed: math_complex.txt
program
  decl a 🫀 const
    binop +
      binop *
        const 2
        const 3
      const 4
  exit
    var a
passed: math_sub.txt
program
  decl a 🩸 const
    binop -
      const 10
      const 5
  exit
    var a
passed: multiple_stmts.txt
program
  decl a 🩸 mut
    const 1
  assign a
    const 2
  decl b 🩸 const
    const 3
  exit
    var a
passed: not_op.txt
program
  decl b 💊 const
    not
      bool alive
  exit
    const 0
passed: survive_nested.txt
program
  if
    bool alive
    block
      if
        bool dead
        block
          decl a 🩸 mut
            const 1
  exit
    const 0
passed: survive_only.txt
program
  if
    bool alive
    block
      decl a 🩸 mut
        const 1
  exit
    const 0
failed ok test: survive_perish.txt
error: compilation error: line 3:3: expected '{' after perish
passed: err_bad_assign.txt
caught error: compilation error: line 1:3: expected '=='
passed: err_bad_byte.txt
caught error: compilation error: line 1:22: bad byte '@'
passed: err_bad_eq.txt
caught error: compilation error: line 1:22: expected '=='
passed: err_bad_type.txt
caught error: compilation error: line 1:8: expected type
passed: err_double_decl.txt
caught error: compilation error: line 1:13: expected name
passed: err_else_without_if.txt
caught error: compilation error: line 1:1: 'perish' without a 'survive'
passed: err_exit_in_block.txt
caught error: compilation error: line 2:1: bad statement
passed: err_if_empty.txt
caught error: compilation error: line 1:15: empty block
passed: err_if_no_brace.txt
caught error: compilation error: line 1:10: expected '{'
passed: err_junk_end.txt
caught error: compilation error: line 2:1: unreachable code
passed: err_letter_in_num.txt
caught error: compilation error: line 1:21: letter in number
passed: err_missing_semi.txt
caught error: compilation error: line 1:21: expected ⏳
passed: err_no_exit.txt
caught error: compilation error: line 1:22: no exit
passed: err_no_init.txt
caught error: compilation error: line 1:15: expected '💉'
passed: err_unclosed_block.txt
caught error: compilation error: line 3:1: bad statement
1 tests failed
```