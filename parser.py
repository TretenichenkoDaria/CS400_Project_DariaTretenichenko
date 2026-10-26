"""Recursive-descent syntax parser for the survival language compiler."""

import sys
from typing import List, Optional

from tokens import Token
from ast_nodes import (
    ASTNode,
    ProgramNode,
    Statement,
    Expression,
    DeclarationNode,
    AssignmentNode,
    IfNode,
    BlockNode,
    ExitNode,
    BinaryOpNode,
    UnaryOpNode,
    VariableNode,
    ConstantNode,
    BooleanNode,
)

MAX_32BIT_INT = 2147483647
MAX_64BIT_INT = 9223372036854775807


class Parser:
    """Parses a 2D list of tokens (lines of tokens) into an AST."""

    def __init__(self, token_lines: List[List[Token]]):
        self.lines: List[List[Token]] = [line for line in token_lines if line]
        self.line_index = 0
        self.token_index = 0
        self.last_line = 0
        self.last_column = 0

    def error(self, line: int, column: int, message: str) -> None:
        sys.stderr.write(f"compilation error: line {line}:{column}: {message}\n")
        sys.exit(1)

    def peek(self) -> Optional[Token]:
        """Returns the current token without consuming it."""
        if self.line_index < len(self.lines) and self.token_index < len(self.lines[self.line_index]):
            return self.lines[self.line_index][self.token_index]
        return None

    def eat(self) -> Optional[Token]:
        """Consumes and returns the current token."""
        token = self.peek()
        if token is not None:
            self.last_line = token.line
            self.last_column = token.column
            self.token_index += 1
        return token

    def is_end_of_line(self) -> bool:
        """Checks if all tokens on the current line have been consumed."""
        return (
            self.line_index >= len(self.lines)
            or self.token_index >= len(self.lines[self.line_index])
        )

    def advance_line(self) -> None:
        """Advances to the next line of tokens."""
        if self.token_index > 0 or self.is_end_of_line():
            self.line_index += 1
            self.token_index = 0

    def check_end_of_line(self) -> None:
        """Verifies no trailing junk exists on the current line, then advances."""
        if not self.is_end_of_line():
            token = self.peek()
            assert token is not None
            self.error(token.line, token.column, "junk at end")
        self.advance_line()

    def expect(self, expected_kind: str, description: str) -> Token:
        """Consumes the next token if it matches the expected kind/text, or raises error."""
        token = self.peek()
        if not token or (token.kind != expected_kind and token.text != description):
            line = token.line if token else self.last_line
            column = token.column if token else self.last_column + 1
            self.error(line, column, f"expected {description}")
        consumed = self.eat()
        assert consumed is not None
        return consumed

    def parse_program(self) -> ProgramNode:
        """Parses the entire program: statements followed by an exit statement."""
        statements: List[Statement] = []
        exit_node: Optional[ExitNode] = None

        while self.line_index < len(self.lines):
            token = self.peek()
            if exit_node is not None:
                assert token is not None
                self.error(token.line, token.column, "unreachable code")

            if token and token.kind == "keyword" and token.text == "exit":
                exit_node = self.parse_exit()
            else:
                statements.append(self.parse_statement())

        if exit_node is None:
            line = self.last_line if self.last_line else 0
            column = self.last_column if self.last_column else 0
            self.error(line, column, "no exit")

        return ProgramNode(statements, exit_node)

    def parse_statement(self) -> Statement:
        """Parses a single statement: declaration, assignment, or conditional."""
        token = self.peek()
        if token and token.text in ("infect", "immune"):
            return self.parse_declaration()
        elif token and token.kind == "identifier":
            return self.parse_assignment()
        elif token and token.text == "survive":
            return self.parse_if()
        elif token and token.text == "perish":
            self.error(token.line, token.column, "'perish' without a 'survive'")
        else:
            line = token.line if token else self.last_line
            column = token.column if token else self.last_column + 1
            self.error(line, column, "bad statement")

    def parse_declaration(self) -> DeclarationNode:
        """Parses a variable declaration: (infect|immune) type name 💉 expr ⏳."""
        modifier_token = self.eat()
        assert modifier_token is not None
        is_mutable = modifier_token.text == "infect"

        type_token = self.peek()
        if not type_token or type_token.text not in ("🩸", "🫀", "💊"):
            line = type_token.line if type_token else self.last_line
            column = type_token.column if type_token else self.last_column + 1
            self.error(line, column, "expected type")
        self.eat()

        name_token = self.expect("identifier", "name")

        assign_op = self.expect("operator", "💉")
        if assign_op.text != "💉":
            self.error(assign_op.line, assign_op.column, "expected '💉'")

        initializer = self.parse_expression()

        # Check type overflow if initializing with integer constant
        if type_token.text == "🩸" and isinstance(initializer, ConstantNode):
            if int(initializer.value) > MAX_32BIT_INT:
                self.error(
                    initializer.line,
                    initializer.column,
                    f"type overflow: constant value {initializer.value} exceeds 32-bit integer range",
                )
        elif type_token.text == "🫀" and isinstance(initializer, ConstantNode):
            if int(initializer.value) > MAX_64BIT_INT:
                self.error(
                    initializer.line,
                    initializer.column,
                    f"type overflow: constant value {initializer.value} exceeds 64-bit integer range",
                )

        terminator_op = self.expect("operator", "⏳")
        if terminator_op.text != "⏳":
            self.error(terminator_op.line, terminator_op.column, "expected '⏳'")

        self.check_end_of_line()
        return DeclarationNode(
            name_token.line,
            name_token.column,
            type_token.text,
            name_token.text,
            is_mutable,
            initializer,
        )

    def parse_assignment(self) -> AssignmentNode:
        """Parses a variable assignment: name 💉 expr ⏳."""
        name_token = self.expect("identifier", "name")

        assign_op = self.expect("operator", "💉")
        if assign_op.text != "💉":
            self.error(assign_op.line, assign_op.column, "expected '💉'")

        value = self.parse_expression()

        terminator_op = self.expect("operator", "⏳")
        if terminator_op.text != "⏳":
            self.error(terminator_op.line, terminator_op.column, "expected '⏳'")

        self.check_end_of_line()
        return AssignmentNode(name_token.line, name_token.column, name_token.text, value)

    def parse_if(self) -> IfNode:
        """Parses conditional block: survive expr { stmts } [ perish { stmts } ]."""
        survive_token = self.eat()
        assert survive_token is not None
        condition = self.parse_expression()

        open_brace = self.peek()
        if not open_brace or open_brace.text != "{":
            line = open_brace.line if open_brace else self.last_line
            column = open_brace.column if open_brace else self.last_column + 1
            self.error(line, column, "expected '{'")

        then_block = self.parse_block()
        else_block: Optional[BlockNode] = None

        next_token = self.peek()
        if next_token and next_token.text == "perish":
            self.eat()  # Consume 'perish' keyword
            after_perish = self.peek()
            if not after_perish or after_perish.text != "{":
                line = after_perish.line if after_perish else self.last_line
                column = after_perish.column if after_perish else self.last_column + 1
                self.error(line, column, "expected '{' after perish")
            else_block = self.parse_block()

        return IfNode(survive_token.line, survive_token.column, condition, then_block, else_block)

    def parse_block(self) -> BlockNode:
        """Parses a block enclosed in braces { ... }."""
        left_brace = self.eat()
        assert left_brace is not None

        if not self.is_end_of_line():
            token = self.peek()
            assert token is not None
            self.error(token.line, token.column, f"unexpected '{token.text}' after '{{'")
        self.advance_line()

        statements: List[Statement] = []
        while self.line_index < len(self.lines):
            token = self.peek()
            if token and token.text == "}":
                break
            statements.append(self.parse_statement())

        closing_token = self.peek()
        if not closing_token or closing_token.text != "}":
            self.error(left_brace.line, left_brace.column, "'{' is never closed")
        self.eat()

        if self.is_end_of_line():
            self.advance_line()

        if not statements:
            self.error(left_brace.line, left_brace.column, "empty block")

        return BlockNode(left_brace.line, left_brace.column, statements)

    def parse_exit(self) -> ExitNode:
        """Parses exit statement: exit expr ⏳."""
        exit_token = self.eat()
        assert exit_token is not None
        value = self.parse_expression()

        terminator_op = self.expect("operator", "⏳")
        if terminator_op.text != "⏳":
            self.error(terminator_op.line, terminator_op.column, "expected '⏳'")

        self.check_end_of_line()
        return ExitNode(exit_token.line, exit_token.column, value)

    def parse_expression(self) -> Expression:
        """Parses expressions with comparisons: expr [ (== | !=) expr ]."""
        node = self.parse_arithmetic()
        peek_token = self.peek()
        if peek_token and peek_token.text in ("==", "!="):
            op_token = self.eat()
            assert op_token is not None
            right = self.parse_arithmetic()
            node = BinaryOpNode(op_token.line, op_token.column, op_token.text, node, right)
        return node

    def parse_arithmetic(self) -> Expression:
        """Parses arithmetic addition and subtraction: term { (+ | -) term }."""
        node = self.parse_term()
        while True:
            peek_token = self.peek()
            if peek_token and peek_token.text in ("+", "-"):
                op_token = self.eat()
                assert op_token is not None
                right = self.parse_term()
                node = BinaryOpNode(op_token.line, op_token.column, op_token.text, node, right)
            else:
                break
        return node

    def parse_term(self) -> Expression:
        """Parses multiplication terms: factor { * factor }."""
        node = self.parse_factor()
        while True:
            peek_token = self.peek()
            if peek_token and peek_token.text == "*":
                op_token = self.eat()
                assert op_token is not None
                right = self.parse_factor()
                node = BinaryOpNode(op_token.line, op_token.column, op_token.text, node, right)
            else:
                break
        return node

    def parse_factor(self) -> Expression:
        """Parses factors: [!] (identifier | constant | boolean)."""
        token = self.peek()
        if not token:
            self.error(self.last_line, self.last_column + 1, "need val")
        assert token is not None

        if token.text == "!":
            op_token = self.eat()
            assert op_token is not None
            operand = self.parse_factor()
            return UnaryOpNode(op_token.line, op_token.column, "!", operand)

        if token.kind == "constant":
            consumed = self.eat()
            assert consumed is not None
            return ConstantNode(consumed.line, token.column, token.text)

        if token.kind == "boolean":
            consumed = self.eat()
            assert consumed is not None
            return BooleanNode(consumed.line, token.column, token.text)

        if token.kind == "identifier":
            consumed = self.eat()
            assert consumed is not None
            return VariableNode(consumed.line, token.column, token.text)

        self.error(token.line, token.column, "bad val")
