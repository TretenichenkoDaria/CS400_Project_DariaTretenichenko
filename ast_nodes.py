"""Abstract Syntax Tree (AST) node hierarchy for the survival language compiler."""

from __future__ import annotations
from typing import List, Optional


class ASTNode:
    """Base class for all Abstract Syntax Tree nodes."""

    def __init__(self, line: int = 0, column: int = 0):
        self.line = line
        self.column = column

    def dump(self, indent: str = "") -> None:
        """Dump formatted AST tree to standard output."""
        raise NotImplementedError(f"{self.__class__.__name__} must implement dump()")


class Statement(ASTNode):
    """Base class for statement AST nodes."""
    pass


class Expression(ASTNode):
    """Base class for expression AST nodes."""
    pass


class ProgramNode(ASTNode):
    """Root program node containing statements followed by a mandatory exit statement."""

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
    """Variable declaration node (infect/immune type name 💉 expr ⏳)."""

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
    """Variable reassignment node (name 💉 expr ⏳)."""

    def __init__(self, line: int, column: int, name: str, value: Expression):
        super().__init__(line, column)
        self.name = name
        self.value = value

    def dump(self, indent: str = "") -> None:
        print(f"{indent}assign {self.name}")
        self.value.dump(indent + "  ")


class BlockNode(ASTNode):
    """Block of statements enclosed in braces { ... }."""

    def __init__(self, line: int, column: int, statements: List[Statement]):
        super().__init__(line, column)
        self.statements = statements

    def dump(self, indent: str = "") -> None:
        print(f"{indent}block")
        for statement in self.statements:
            statement.dump(indent + "  ")


class IfNode(Statement):
    """Conditional statement node (survive expr { ... } [ perish { ... } ])."""

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
    """Program exit node (exit expr ⏳)."""

    def __init__(self, line: int, column: int, value: Expression):
        super().__init__(line, column)
        self.value = value

    def dump(self, indent: str = "") -> None:
        print(f"{indent}exit")
        self.value.dump(indent + "  ")


class BinaryOpNode(Expression):
    """Binary operation expression node (left op right)."""

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
    """Unary operation expression node (op operand)."""

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
    """Variable reference expression node."""

    def __init__(self, line: int, column: int, name: str):
        super().__init__(line, column)
        self.name = name

    def dump(self, indent: str = "") -> None:
        print(f"{indent}var {self.name}")


class ConstantNode(Expression):
    """Integer constant literal expression node."""

    def __init__(self, line: int, column: int, value: str):
        super().__init__(line, column)
        self.value = value

    def dump(self, indent: str = "") -> None:
        print(f"{indent}const {self.value}")


class BooleanNode(Expression):
    """Boolean literal expression node (alive / dead)."""

    def __init__(self, line: int, column: int, value: str):
        super().__init__(line, column)
        self.value = value

    def dump(self, indent: str = "") -> None:
        print(f"{indent}bool {self.value}")
