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
    ChainAssignNode,
    IfNode,
    BlockNode,
    ExitNode,
    ReturnNode,
    PrintNode,
    ParamNode,
    FunctionNode,
    FieldDeclNode,
    StructNode,
    BinaryOpNode,
    UnaryOpNode,
    VariableNode,
    ConstantNode,
    BooleanNode,
    StringLiteralNode,
    CallNode,
    FieldAccessNode,
    MemberCallNode,
    StructInitNode,
    ReadNode,
)

MAX_32BIT_INT = 2147483647
MAX_64BIT_INT = 9223372036854775807


class Parser:
    def __init__(self, token_lines: List[List[Token]]):
        self.lines: List[List[Token]] = [line for line in token_lines if line]
        self.line_index = 0
        self.token_index = 0
        self.last_line = 0
        self.last_column = 0
        self.declared_structs = set()

    def error(self, line: int, column: int, message: str) -> None:
        sys.stderr.write(f"compilation error: line {line}:{column}: {message}\n")
        sys.exit(1)

    def peek(self) -> Optional[Token]:
        if self.line_index < len(self.lines) and self.token_index < len(self.lines[self.line_index]):
            return self.lines[self.line_index][self.token_index]
        return None

    def eat(self) -> Optional[Token]:
        token = self.peek()
        if token is not None:
            self.last_line = token.line
            self.last_column = token.column
            self.token_index += 1
        return token

    def is_end_of_line(self) -> bool:
        return (
            self.line_index >= len(self.lines)
            or self.token_index >= len(self.lines[self.line_index])
        )

    def advance_line(self) -> None:
        if self.token_index > 0 or self.is_end_of_line():
            self.line_index += 1
            self.token_index = 0

    def check_end_of_line(self) -> None:
        if not self.is_end_of_line():
            token = self.peek()
            assert token is not None
            self.error(token.line, token.column, "junk at end")
        self.advance_line()

    def expect(self, expected_kind: str, description: str) -> Token:
        token = self.peek()
        if not token or (token.kind != expected_kind and token.text != description):
            line = token.line if token else self.last_line
            column = token.column if token else self.last_column + 1
            self.error(line, column, f"expected {description}")
        consumed = self.eat()
        assert consumed is not None
        return consumed

    def parse_program(self) -> ProgramNode:
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
        token = self.peek()
        if not token:
            self.error(self.last_line, self.last_column + 1, "bad statement")
        assert token is not None

        if token.text in ("infect", "immune"):
            return self.parse_declaration()
        elif token.text in ("ritual", "fn"):
            return self.parse_function()
        elif token.text in ("shelter", "struct"):
            return self.parse_struct()
        elif token.text in ("yield", "return"):
            return self.parse_return()
        elif token.text == "print":
            return self.parse_print()
        elif token.text == "survive":
            return self.parse_if()
        elif token.text == "perish":
            self.error(token.line, token.column, "'perish' without a 'survive'")
        elif token.kind == "identifier":
            return self.parse_assign_or_call_statement()
        else:
            line = token.line if token else self.last_line
            column = token.column if token else self.last_column + 1
            self.error(line, column, "bad statement")

    def parse_declaration(self) -> DeclarationNode:
        modifier_token = self.eat()
        assert modifier_token is not None
        is_mutable = modifier_token.text == "infect"

        type_token = self.peek()
        if not type_token or (
            type_token.text not in ("🩸", "🫀", "💊")
            and type_token.text not in self.declared_structs
        ):
            line = type_token.line if type_token else self.last_line
            column = type_token.column if type_token else self.last_column + 1
            self.error(line, column, "expected type")
        self.eat()

        name_token = self.expect("identifier", "name")

        assign_op = self.expect("operator", "💉")
        if assign_op.text != "💉":
            self.error(assign_op.line, assign_op.column, "expected '💉'")

        initializer = self.parse_expression()

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

    def parse_assign_or_call_statement(self) -> Statement:
        start_token = self.peek()
        assert start_token is not None
        target = self.parse_factor()

        next_tok = self.peek()
        if next_tok and next_tok.text == "💉":
            self.eat()
            value = self.parse_expression()
            terminator = self.expect("operator", "⏳")
            self.check_end_of_line()
            if isinstance(target, VariableNode):
                return AssignmentNode(start_token.line, start_token.column, target.name, value)
            elif isinstance(target, FieldAccessNode):
                return ChainAssignNode(start_token.line, start_token.column, target, value)
            else:
                self.error(start_token.line, start_token.column, "invalid assignment target")
        elif next_tok and next_tok.text == "⏳":
            self.eat()
            self.check_end_of_line()
            if isinstance(target, (CallNode, MemberCallNode)):
                # Expression statement
                return ChainAssignNode(start_token.line, start_token.column, target, target)
            self.error(start_token.line, start_token.column, "bad statement")
        else:
            line = next_tok.line if next_tok else self.last_line
            column = next_tok.column if next_tok else self.last_column + 1
            self.error(line, column, "bad statement")

    def parse_return(self) -> ReturnNode:
        kw = self.eat()
        assert kw is not None
        val = self.parse_expression()
        self.expect("operator", "⏳")
        self.check_end_of_line()
        return ReturnNode(kw.line, kw.column, val)

    def parse_print(self) -> PrintNode:
        kw = self.eat()
        assert kw is not None
        has_paren = False
        if self.peek() and self.peek().text == "(":
            self.eat()
            has_paren = True

        expr = self.parse_expression()
        if has_paren:
            self.expect("paren", ")")

        self.expect("operator", "⏳")
        self.check_end_of_line()
        return PrintNode(kw.line, kw.column, expr)

    def parse_function(self) -> FunctionNode:
        fn_token = self.eat()
        assert fn_token is not None

        name_tok = self.expect("identifier", "function name")
        self.expect("paren", "(")

        params: List[ParamNode] = []
        if self.peek() and self.peek().text != ")":
            while True:
                mod = self.peek()
                if not mod or mod.text not in ("infect", "immune"):
                    line = mod.line if mod else self.last_line
                    col = mod.column if mod else self.last_column + 1
                    self.error(line, col, "expected parameter mutability (infect/immune)")
                self.eat()
                is_mut = mod.text == "infect"

                ptype = self.peek()
                if not ptype or (
                    ptype.text not in ("🩸", "🫀", "💊")
                    and ptype.text not in self.declared_structs
                ):
                    line = ptype.line if ptype else self.last_line
                    col = ptype.column if ptype else self.last_column + 1
                    self.error(line, col, "expected parameter type")
                self.eat()

                pname = self.expect("identifier", "parameter name")
                params.append(ParamNode(pname.line, pname.column, is_mut, ptype.text, pname.text))

                if self.peek() and self.peek().text == ",":
                    self.eat()
                else:
                    break

        self.expect("paren", ")")
        self.expect("operator", "->")

        rtype = self.peek()
        if not rtype or (
            rtype.text not in ("🩸", "🫀", "💊")
            and rtype.text not in self.declared_structs
        ):
            line = rtype.line if rtype else self.last_line
            col = rtype.column if rtype else self.last_column + 1
            self.error(line, col, "expected return type")
        self.eat()

        brace = self.peek()
        if not brace or brace.text != "{":
            line = brace.line if brace else self.last_line
            col = brace.column if brace else self.last_column + 1
            self.error(line, col, "expected '{'")

        body = self.parse_block()
        return FunctionNode(fn_token.line, fn_token.column, name_tok.text, params, rtype.text, body)

    def parse_struct(self) -> StructNode:
        s_tok = self.eat()
        assert s_tok is not None
        name_tok = self.expect("identifier", "struct name")
        self.declared_structs.add(name_tok.text)

        brace = self.peek()
        if not brace or brace.text != "{":
            line = brace.line if brace else self.last_line
            col = brace.column if brace else self.last_column + 1
            self.error(line, col, "expected '{'")
        self.eat()

        if not self.is_end_of_line():
            token = self.peek()
            assert token is not None
            self.error(token.line, token.column, f"unexpected '{token.text}' after '{{'")
        self.advance_line()

        fields: List[FieldDeclNode] = []
        methods: List[FunctionNode] = []

        while self.line_index < len(self.lines):
            tok = self.peek()
            if tok and tok.text == "}":
                break

            if tok and tok.text in ("infect", "immune"):
                mod = self.eat()
                is_mut = mod.text == "infect"
                ftype = self.peek()
                if not ftype or (
                    ftype.text not in ("🩸", "🫀", "💊")
                    and ftype.text not in self.declared_structs
                ):
                    line = ftype.line if ftype else self.last_line
                    col = ftype.column if ftype else self.last_column + 1
                    self.error(line, col, "expected field type")
                self.eat()
                fname = self.expect("identifier", "field name")
                self.expect("operator", "⏳")
                self.check_end_of_line()
                fields.append(FieldDeclNode(fname.line, fname.column, is_mut, ftype.text, fname.text))
            elif tok and tok.text in ("ritual", "fn"):
                methods.append(self.parse_function())
            else:
                line = tok.line if tok else self.last_line
                col = tok.column if tok else self.last_column + 1
                self.error(line, col, "bad struct member")

        closing = self.peek()
        if not closing or closing.text != "}":
            self.error(brace.line, brace.column, "'{' is never closed")
        self.eat()

        if self.is_end_of_line():
            self.advance_line()

        return StructNode(s_tok.line, s_tok.column, name_tok.text, fields, methods)

    def parse_if(self) -> IfNode:
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
            self.eat()
            after_perish = self.peek()
            if not after_perish or after_perish.text != "{":
                line = after_perish.line if after_perish else self.last_line
                column = after_perish.column if after_perish else self.last_column + 1
                self.error(line, column, "expected '{' after perish")
            else_block = self.parse_block()

        return IfNode(survive_token.line, survive_token.column, condition, then_block, else_block)

    def parse_block(self) -> BlockNode:
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
        exit_token = self.eat()
        assert exit_token is not None
        value = self.parse_expression()

        terminator_op = self.expect("operator", "⏳")
        if terminator_op.text != "⏳":
            self.error(terminator_op.line, terminator_op.column, "expected '⏳'")

        self.check_end_of_line()
        return ExitNode(exit_token.line, exit_token.column, value)

    def parse_expression(self) -> Expression:
        node = self.parse_arithmetic()
        peek_token = self.peek()
        if peek_token and peek_token.text in ("==", "!="):
            op_token = self.eat()
            assert op_token is not None
            right = self.parse_arithmetic()
            node = BinaryOpNode(op_token.line, op_token.column, op_token.text, node, right)
        return node

    def parse_arithmetic(self) -> Expression:
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
        node = self.parse_primary()
        while self.peek() and self.peek().text == ".":
            self.eat()  # '.'
            member_tok = self.expect("identifier", "member name")
            if self.peek() and self.peek().text == "(":
                self.eat()
                args = self.parse_arguments()
                self.expect("paren", ")")
                node = MemberCallNode(member_tok.line, member_tok.column, node, member_tok.text, args)
            else:
                node = FieldAccessNode(member_tok.line, member_tok.column, node, member_tok.text)
        return node

    def parse_arguments(self) -> List[Expression]:
        args: List[Expression] = []
        if self.peek() and self.peek().text != ")":
            while True:
                args.append(self.parse_expression())
                if self.peek() and self.peek().text == ",":
                    self.eat()
                else:
                    break
        return args

    def parse_primary(self) -> Expression:
        token = self.peek()
        if not token:
            self.error(self.last_line, self.last_column + 1, "need val")
        assert token is not None

        if token.text == "!":
            op_token = self.eat()
            assert op_token is not None
            operand = self.parse_factor()
            return UnaryOpNode(op_token.line, op_token.column, "!", operand)

        if token.text == "read":
            self.eat()
            self.expect("paren", "(")
            self.expect("paren", ")")
            return ReadNode(token.line, token.column)

        if token.kind == "constant":
            consumed = self.eat()
            assert consumed is not None
            return ConstantNode(consumed.line, token.column, token.text)

        if token.kind == "boolean":
            consumed = self.eat()
            assert consumed is not None
            return BooleanNode(consumed.line, token.column, token.text)

        if token.kind == "string":
            consumed = self.eat()
            assert consumed is not None
            return StringLiteralNode(consumed.line, token.column, token.text)

        if token.kind == "identifier":
            ident = self.eat()
            assert ident is not None
            # Check if function call
            if self.peek() and self.peek().text == "(":
                self.eat()
                args = self.parse_arguments()
                self.expect("paren", ")")
                return CallNode(ident.line, ident.column, ident.text, args)
            # Check if struct instantiation: Name { arg1, arg2 }
            if self.peek() and self.peek().text == "{":
                self.eat()
                args = []
                if self.peek() and self.peek().text != "}":
                    while True:
                        args.append(self.parse_expression())
                        if self.peek() and self.peek().text == ",":
                            self.eat()
                        else:
                            break
                self.expect("brace", "}")
                return StructInitNode(ident.line, ident.column, ident.text, args)

            return VariableNode(ident.line, ident.column, ident.text)

        self.error(token.line, token.column, "bad val")
