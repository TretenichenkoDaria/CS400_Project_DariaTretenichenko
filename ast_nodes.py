from __future__ import annotations
from typing import List, Optional


class ASTNode:
    def __init__(self, line: int = 0, column: int = 0):
        self.line = line
        self.column = column

    def dump(self, indent: str = "") -> None:
        raise NotImplementedError(f"{self.__class__.__name__} must implement dump()")


class Statement(ASTNode):
    pass


class Expression(ASTNode):
    pass


class ProgramNode(ASTNode):
    def __init__(self, statements: List[Statement], exit_node: ExitNode, line: int = 1, column: int = 1):
        super().__init__(line, column)
        self.statements = statements
        self.exit_node = exit_node

    def dump(self, indent: str = "") -> None:
        print(f"{indent}program")
        for statement in self.statements:
            statement.dump(indent + "  ")
        self.exit_node.dump(indent + "  ")


class DeclarationNode(Statement):
    def __init__(
        self,
        line: int,
        column: int,
        type_name: str,
        name: str,
        is_mutable: bool,
        initializer: Expression,
    ):
        super().__init__(line, column)
        self.type_name = type_name
        self.name = name
        self.is_mutable = is_mutable
        self.initializer = initializer

    def dump(self, indent: str = "") -> None:
        mut_str = "mut" if self.is_mutable else "const"
        print(f"{indent}decl {self.name} {self.type_name} {mut_str}")
        self.initializer.dump(indent + "  ")


class AssignmentNode(Statement):
    def __init__(self, line: int, column: int, name: str, value: Expression):
        super().__init__(line, column)
        self.name = name
        self.value = value

    def dump(self, indent: str = "") -> None:
        print(f"{indent}assign {self.name}")
        self.value.dump(indent + "  ")


class ChainAssignNode(Statement):
    def __init__(self, line: int, column: int, target: Expression, value: Expression):
        super().__init__(line, column)
        self.target = target
        self.value = value

    def dump(self, indent: str = "") -> None:
        print(f"{indent}chain_assign")
        self.target.dump(indent + "  ")
        self.value.dump(indent + "  ")


class BlockNode(ASTNode):
    def __init__(self, line: int, column: int, statements: List[Statement]):
        super().__init__(line, column)
        self.statements = statements

    def dump(self, indent: str = "") -> None:
        print(f"{indent}block")
        for statement in self.statements:
            statement.dump(indent + "  ")


class IfNode(Statement):
    def __init__(
        self,
        line: int,
        column: int,
        condition: Expression,
        then_block: BlockNode,
        else_block: Optional[BlockNode] = None,
    ):
        super().__init__(line, column)
        self.condition = condition
        self.then_block = then_block
        self.else_block = else_block

    def dump(self, indent: str = "") -> None:
        print(f"{indent}if")
        self.condition.dump(indent + "  ")
        self.then_block.dump(indent + "  ")
        if self.else_block is not None:
            self.else_block.dump(indent + "  ")


class ExitNode(Statement):
    def __init__(self, line: int, column: int, value: Expression):
        super().__init__(line, column)
        self.value = value

    def dump(self, indent: str = "") -> None:
        print(f"{indent}exit")
        self.value.dump(indent + "  ")


class ReturnNode(Statement):
    def __init__(self, line: int, column: int, value: Expression):
        super().__init__(line, column)
        self.value = value

    def dump(self, indent: str = "") -> None:
        print(f"{indent}return")
        self.value.dump(indent + "  ")


class PrintNode(Statement):
    def __init__(self, line: int, column: int, expr: Expression):
        super().__init__(line, column)
        self.expr = expr

    def dump(self, indent: str = "") -> None:
        print(f"{indent}print")
        self.expr.dump(indent + "  ")


class ParamNode(ASTNode):
    def __init__(self, line: int, column: int, is_mutable: bool, type_name: str, name: str):
        super().__init__(line, column)
        self.is_mutable = is_mutable
        self.type_name = type_name
        self.name = name

    def dump(self, indent: str = "") -> None:
        mut_str = "mut" if self.is_mutable else "const"
        print(f"{indent}param {self.name} {self.type_name} {mut_str}")


class FunctionNode(Statement):
    def __init__(
        self,
        line: int,
        column: int,
        name: str,
        params: List[ParamNode],
        return_type: str,
        body: BlockNode,
    ):
        super().__init__(line, column)
        self.name = name
        self.params = params
        self.return_type = return_type
        self.body = body

    def dump(self, indent: str = "") -> None:
        print(f"{indent}fn {self.name} -> {self.return_type}")
        for param in self.params:
            param.dump(indent + "  ")
        self.body.dump(indent + "  ")


class FieldDeclNode(ASTNode):
    def __init__(self, line: int, column: int, is_mutable: bool, type_name: str, name: str):
        super().__init__(line, column)
        self.is_mutable = is_mutable
        self.type_name = type_name
        self.name = name

    def dump(self, indent: str = "") -> None:
        mut_str = "mut" if self.is_mutable else "const"
        print(f"{indent}field {self.name} {self.type_name} {mut_str}")


class StructNode(Statement):
    def __init__(
        self,
        line: int,
        column: int,
        name: str,
        fields: List[FieldDeclNode],
        methods: List[FunctionNode],
    ):
        super().__init__(line, column)
        self.name = name
        self.fields = fields
        self.methods = methods

    def dump(self, indent: str = "") -> None:
        print(f"{indent}struct {self.name}")
        for field in self.fields:
            field.dump(indent + "  ")
        for method in self.methods:
            method.dump(indent + "  ")


class BinaryOpNode(Expression):
    def __init__(self, line: int, column: int, operator: str, left: Expression, right: Expression):
        super().__init__(line, column)
        self.operator = operator
        self.left = left
        self.right = right

    def dump(self, indent: str = "") -> None:
        print(f"{indent}binop {self.operator}")
        self.left.dump(indent + "  ")
        self.right.dump(indent + "  ")


class UnaryOpNode(Expression):
    def __init__(self, line: int, column: int, operator: str, operand: Expression):
        super().__init__(line, column)
        self.operator = operator
        self.operand = operand

    def dump(self, indent: str = "") -> None:
        if self.operator == "!":
            print(f"{indent}not")
        else:
            print(f"{indent}unary {self.operator}")
        self.operand.dump(indent + "  ")


class VariableNode(Expression):
    def __init__(self, line: int, column: int, name: str):
        super().__init__(line, column)
        self.name = name

    def dump(self, indent: str = "") -> None:
        print(f"{indent}var {self.name}")


class ConstantNode(Expression):
    def __init__(self, line: int, column: int, value: str):
        super().__init__(line, column)
        self.value = value

    def dump(self, indent: str = "") -> None:
        print(f"{indent}const {self.value}")


class BooleanNode(Expression):
    def __init__(self, line: int, column: int, value: str):
        super().__init__(line, column)
        self.value = value

    def dump(self, indent: str = "") -> None:
        print(f"{indent}bool {self.value}")


class StringLiteralNode(Expression):
    def __init__(self, line: int, column: int, value: str):
        super().__init__(line, column)
        self.value = value

    def dump(self, indent: str = "") -> None:
        print(f"{indent}str \"{self.value}\"")


class CallNode(Expression):
    def __init__(self, line: int, column: int, callee: str, args: List[Expression]):
        super().__init__(line, column)
        self.callee = callee
        self.args = args

    def dump(self, indent: str = "") -> None:
        print(f"{indent}call {self.callee}")
        for arg in self.args:
            arg.dump(indent + "  ")


class FieldAccessNode(Expression):
    def __init__(self, line: int, column: int, target: Expression, field_name: str):
        super().__init__(line, column)
        self.target = target
        self.field_name = field_name

    def dump(self, indent: str = "") -> None:
        print(f"{indent}field_access {self.field_name}")
        self.target.dump(indent + "  ")


class MemberCallNode(Expression):
    def __init__(
        self,
        line: int,
        column: int,
        target: Expression,
        method_name: str,
        args: List[Expression],
    ):
        super().__init__(line, column)
        self.target = target
        self.method_name = method_name
        self.args = args

    def dump(self, indent: str = "") -> None:
        print(f"{indent}member_call {self.method_name}")
        self.target.dump(indent + "  ")
        for arg in self.args:
            arg.dump(indent + "  ")


class StructInitNode(Expression):
    def __init__(self, line: int, column: int, struct_name: str, args: List[Expression]):
        super().__init__(line, column)
        self.struct_name = struct_name
        self.args = args

    def dump(self, indent: str = "") -> None:
        print(f"{indent}struct_init {self.struct_name}")
        for arg in self.args:
            arg.dump(indent + "  ")


class ReadNode(Expression):
    def __init__(self, line: int, column: int):
        super().__init__(line, column)

    def dump(self, indent: str = "") -> None:
        print(f"{indent}read")
