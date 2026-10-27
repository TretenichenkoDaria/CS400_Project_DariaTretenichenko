import sys
from typing import Dict, List, Optional, Tuple, Set

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


class Symbol:
    def __init__(self, name: str, type_name: str, is_mutable: bool, line: int, column: int):
        self.name = name
        self.type_name = type_name
        self.is_mutable = is_mutable
        self.line = line
        self.column = column


class FieldInfo:
    def __init__(self, name: str, type_name: str, is_mutable: bool, index: int, line: int, column: int):
        self.name = name
        self.type_name = type_name
        self.is_mutable = is_mutable
        self.index = index
        self.line = line
        self.column = column


class MethodInfo:
    def __init__(
        self,
        name: str,
        params: List[Tuple[str, str, bool]],
        return_type: str,
        is_mutating: bool,
        node: FunctionNode,
    ):
        self.name = name
        self.params = params  # (name, type, is_mut)
        self.return_type = return_type
        self.is_mutating = is_mutating
        self.node = node


class StructInfo:
    def __init__(self, name: str, line: int, column: int):
        self.name = name
        self.line = line
        self.column = column
        self.fields: Dict[str, FieldInfo] = {}
        self.field_order: List[str] = []
        self.methods: Dict[str, MethodInfo] = {}


class FunctionInfo:
    def __init__(
        self,
        name: str,
        params: List[Tuple[str, str, bool]],
        return_type: str,
        node: FunctionNode,
    ):
        self.name = name
        self.params = params  # (name, type, is_mut)
        self.return_type = return_type
        self.node = node


class SemanticAnalyzer:
    def __init__(self):
        self.structs: Dict[str, StructInfo] = {}
        self.functions: Dict[str, FunctionInfo] = {}
        self.scopes: List[Dict[str, Symbol]] = [{}]
        self.current_function: Optional[FunctionInfo] = None
        self.current_struct: Optional[StructInfo] = None

    def error(self, line: int, column: int, message: str) -> None:
        sys.stderr.write(f"compilation error: line {line}:{column}: {message}\n")
        sys.exit(1)

    def enter_scope(self) -> None:
        self.scopes.append({})

    def exit_scope(self) -> None:
        self.scopes.pop()

    def declare_symbol(self, symbol: Symbol) -> None:
        current_scope = self.scopes[-1]
        if symbol.name in current_scope:
            self.error(symbol.line, symbol.column, f"variable '{symbol.name}' already declared in this scope")
        current_scope[symbol.name] = symbol

    def lookup_symbol(self, name: str) -> Optional[Symbol]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def analyze(self, program: ProgramNode) -> None:
        for stmt in program.statements:
            if isinstance(stmt, StructNode):
                if stmt.name in self.structs:
                    self.error(stmt.line, stmt.column, f"structure '{stmt.name}' already declared")
                s_info = StructInfo(stmt.name, stmt.line, stmt.column)
                for idx, field in enumerate(stmt.fields):
                    if field.name in s_info.fields:
                        self.error(field.line, field.column, f"duplicate field '{field.name}' in struct '{stmt.name}'")
                    s_info.fields[field.name] = FieldInfo(
                        field.name, field.type_name, field.is_mutable, idx, field.line, field.column
                    )
                    s_info.field_order.append(field.name)
                self.structs[stmt.name] = s_info

        for stmt in program.statements:
            if isinstance(stmt, StructNode):
                s_info = self.structs[stmt.name]
                for method in stmt.methods:
                    if method.name in s_info.methods:
                        self.error(method.line, method.column, f"duplicate method '{method.name}' in struct '{stmt.name}'")
                    params = [(p.name, p.type_name, p.is_mutable) for p in method.params]
                    is_mutating = self.check_if_mutating(method.body, s_info)
                    s_info.methods[method.name] = MethodInfo(
                        method.name, params, method.return_type, is_mutating, method
                    )

        for stmt in program.statements:
            if isinstance(stmt, FunctionNode):
                if stmt.name in self.functions:
                    self.error(stmt.line, stmt.column, f"function '{stmt.name}' already declared")
                params = [(p.name, p.type_name, p.is_mutable) for p in stmt.params]
                self.functions[stmt.name] = FunctionInfo(stmt.name, params, stmt.return_type, stmt)

        for stmt in program.statements:
            self.analyze_statement(stmt)

        self.analyze_statement(program.exit_node)

    def check_if_mutating(self, block: BlockNode, s_info: StructInfo) -> bool:
        for stmt in block.statements:
            if isinstance(stmt, AssignmentNode):
                if stmt.name in s_info.fields:
                    return True
            elif isinstance(stmt, ChainAssignNode):
                target = stmt.target
                while isinstance(target, FieldAccessNode):
                    target = target.target
                if isinstance(target, VariableNode) and target.name in s_info.fields:
                    return True
            elif isinstance(stmt, IfNode):
                if self.check_if_mutating(stmt.then_block, s_info):
                    return True
                if stmt.else_block and self.check_if_mutating(stmt.else_block, s_info):
                    return True
        return False

    def analyze_statement(self, stmt: Statement) -> None:
        if isinstance(stmt, DeclarationNode):
            self.analyze_declaration(stmt)
        elif isinstance(stmt, AssignmentNode):
            self.analyze_assignment(stmt)
        elif isinstance(stmt, ChainAssignNode):
            self.analyze_chain_assign(stmt)
        elif isinstance(stmt, IfNode):
            self.analyze_if(stmt)
        elif isinstance(stmt, ExitNode):
            self.analyze_exit(stmt)
        elif isinstance(stmt, ReturnNode):
            self.analyze_return(stmt)
        elif isinstance(stmt, PrintNode):
            self.analyze_print(stmt)
        elif isinstance(stmt, FunctionNode):
            self.analyze_function_body(stmt)
        elif isinstance(stmt, StructNode):
            self.analyze_struct_body(stmt)
        elif isinstance(stmt, BlockNode):
            self.enter_scope()
            for s in stmt.statements:
                self.analyze_statement(s)
            self.exit_scope()

    def analyze_declaration(self, decl: DeclarationNode) -> None:
        init_type = self.analyze_expression(decl.initializer)
        if decl.type_name != init_type:
            self.error(
                decl.line,
                decl.column,
                f"type mismatch in declaration of '{decl.name}': expected {decl.type_name}, got {init_type}",
            )
        self.declare_symbol(Symbol(decl.name, decl.type_name, decl.is_mutable, decl.line, decl.column))

    def analyze_assignment(self, assign: AssignmentNode) -> None:
        sym = self.lookup_symbol(assign.name)
        if sym is None:
            if self.current_struct and assign.name in self.current_struct.fields:
                field = self.current_struct.fields[assign.name]
                if not field.is_mutable:
                    self.error(assign.line, assign.column, f"cannot assign to constant field '{assign.name}'")
                val_type = self.analyze_expression(assign.value)
                if field.type_name != val_type:
                    self.error(assign.line, assign.column, f"type mismatch in field assignment '{assign.name}'")
                return
            self.error(assign.line, assign.column, f"use of undeclared variable '{assign.name}'")

        if not sym.is_mutable:
            self.error(assign.line, assign.column, f"cannot assign to constant variable '{assign.name}'")

        val_type = self.analyze_expression(assign.value)
        if sym.type_name != val_type:
            self.error(
                assign.line,
                assign.column,
                f"type mismatch in assignment to '{assign.name}': expected {sym.type_name}, got {val_type}",
            )

    def analyze_chain_assign(self, assign: ChainAssignNode) -> None:
        # Check chain mutability
        if isinstance(assign.target, (CallNode, MemberCallNode)):
            self.analyze_expression(assign.target)
            return

        target_type, is_mut = self.analyze_chain_lvalue(assign.target)
        if not is_mut:
            self.error(assign.line, assign.column, "cannot assign through a constant chain")

        val_type = self.analyze_expression(assign.value)
        if target_type != val_type:
            self.error(
                assign.line,
                assign.column,
                f"type mismatch in chain assignment: expected {target_type}, got {val_type}",
            )

    def analyze_chain_lvalue(self, target: Expression) -> Tuple[str, bool]:
        if isinstance(target, VariableNode):
            sym = self.lookup_symbol(target.name)
            if sym is None:
                if self.current_struct and target.name in self.current_struct.fields:
                    f = self.current_struct.fields[target.name]
                    return f.type_name, f.is_mutable
                self.error(target.line, target.column, f"use of undeclared variable '{target.name}'")
            return sym.type_name, sym.is_mutable

        if isinstance(target, FieldAccessNode):
            base_type, base_mut = self.analyze_chain_lvalue(target.target)
            if not base_mut:
                return "unknown", False
            if base_type not in self.structs:
                self.error(target.line, target.column, f"type '{base_type}' is not a structure")
            s_info = self.structs[base_type]
            if target.field_name not in s_info.fields:
                self.error(target.line, target.column, f"structure '{base_type}' has no field '{target.field_name}'")
            field = s_info.fields[target.field_name]
            return field.type_name, (base_mut and field.is_mutable)

        self.error(target.line, target.column, "invalid lvalue in assignment")
        return "unknown", False

    def analyze_if(self, stmt: IfNode) -> None:
        cond_type = self.analyze_expression(stmt.condition)
        if cond_type != "💊":
            self.error(stmt.line, stmt.column, f"if condition must be bool (💊), got {cond_type}")
        self.enter_scope()
        for s in stmt.then_block.statements:
            self.analyze_statement(s)
        self.exit_scope()
        if stmt.else_block:
            self.enter_scope()
            for s in stmt.else_block.statements:
                self.analyze_statement(s)
            self.exit_scope()

    def analyze_exit(self, stmt: ExitNode) -> None:
        val_type = self.analyze_expression(stmt.value)
        if val_type not in ("🩸", "🫀"):
            self.error(stmt.line, stmt.column, f"exit code must be an integer, got {val_type}")

    def analyze_return(self, stmt: ReturnNode) -> None:
        if self.current_function is None:
            self.error(stmt.line, stmt.column, "'return' / 'yield' used outside of a function")
        val_type = self.analyze_expression(stmt.value)
        if val_type != self.current_function.return_type:
            self.error(
                stmt.line,
                stmt.column,
                f"function '{self.current_function.name}' returns {self.current_function.return_type}, but returned {val_type}",
            )

    def analyze_print(self, stmt: PrintNode) -> None:
        self.analyze_expression(stmt.expr)

    def analyze_function_body(self, fn: FunctionNode) -> None:
        f_info = self.functions[fn.name]
        prev_fn = self.current_function
        self.current_function = f_info
        self.enter_scope()

        for pname, ptype, pmut in f_info.params:
            self.declare_symbol(Symbol(pname, ptype, pmut, fn.line, fn.column))

        for s in fn.body.statements:
            self.analyze_statement(s)

        self.exit_scope()
        self.current_function = prev_fn

    def analyze_struct_body(self, s_node: StructNode) -> None:
        s_info = self.structs[s_node.name]
        prev_struct = self.current_struct
        self.current_struct = s_info

        for m_node in s_node.methods:
            m_info = s_info.methods[m_node.name]
            prev_fn = self.current_function
            self.current_function = FunctionInfo(m_node.name, m_info.params, m_info.return_type, m_node)
            self.enter_scope()

            for pname, ptype, pmut in m_info.params:
                self.declare_symbol(Symbol(pname, ptype, pmut, m_node.line, m_node.column))

            for s in m_node.body.statements:
                self.analyze_statement(s)

            self.exit_scope()
            self.current_function = prev_fn

        self.current_struct = prev_struct

    def analyze_expression(self, expr: Expression) -> str:
        if isinstance(expr, ConstantNode):
            val = int(expr.value)
            if val > MAX_64BIT_INT:
                self.error(expr.line, expr.column, "integer literal exceeds 64-bit integer limit")
            if val <= MAX_32BIT_INT:
                return "🩸"
            return "🫀"

        if isinstance(expr, BooleanNode):
            return "💊"

        if isinstance(expr, StringLiteralNode):
            return "string"

        if isinstance(expr, ReadNode):
            return "🩸"

        if isinstance(expr, VariableNode):
            sym = self.lookup_symbol(expr.name)
            if sym is not None:
                return sym.type_name
            if self.current_struct and expr.name in self.current_struct.fields:
                return self.current_struct.fields[expr.name].type_name
            self.error(expr.line, expr.column, f"use of undeclared variable '{expr.name}'")

        if isinstance(expr, UnaryOpNode):
            operand_type = self.analyze_expression(expr.operand)
            if expr.operator == "!":
                if operand_type != "💊":
                    self.error(expr.line, expr.column, f"operator '!' requires boolean operand (💊), got {operand_type}")
                return "💊"
            self.error(expr.line, expr.column, f"unknown unary operator '{expr.operator}'")

        if isinstance(expr, BinaryOpNode):
            left_type = self.analyze_expression(expr.left)
            right_type = self.analyze_expression(expr.right)

            if expr.operator in ("+", "-", "*"):
                if left_type not in ("🩸", "🫀") or right_type not in ("🩸", "🫀"):
                    self.error(
                        expr.line,
                        expr.column,
                        f"arithmetic operator '{expr.operator}' requires integer operands, got {left_type} and {right_type}",
                    )
                if left_type != right_type:
                    self.error(
                        expr.line,
                        expr.column,
                        f"type mismatch in arithmetic '{expr.operator}': {left_type} vs {right_type}",
                    )
                return left_type

            if expr.operator in ("==", "!="):
                if left_type != right_type:
                    self.error(
                        expr.line,
                        expr.column,
                        f"type mismatch in comparison '{expr.operator}': {left_type} vs {right_type}",
                    )
                return "💊"

        if isinstance(expr, CallNode):
            if expr.callee not in self.functions:
                self.error(expr.line, expr.column, f"call to undeclared function '{expr.callee}'")
            f_info = self.functions[expr.callee]
            if len(expr.args) != len(f_info.params):
                self.error(
                    expr.line,
                    expr.column,
                    f"function '{expr.callee}' expects {len(f_info.params)} arguments, got {len(expr.args)}",
                )
            for idx, ((_, expected_type, _), arg_expr) in enumerate(zip(f_info.params, expr.args)):
                arg_type = self.analyze_expression(arg_expr)
                if arg_type != expected_type:
                    self.error(
                        arg_expr.line,
                        arg_expr.column,
                        f"argument {idx + 1} to '{expr.callee}' has wrong type: expected {expected_type}, got {arg_type}",
                    )
            return f_info.return_type

        if isinstance(expr, StructInitNode):
            if expr.struct_name not in self.structs:
                self.error(expr.line, expr.column, f"instantiation of undeclared struct '{expr.struct_name}'")
            s_info = self.structs[expr.struct_name]
            if len(expr.args) != len(s_info.field_order):
                self.error(
                    expr.line,
                    expr.column,
                    f"struct '{expr.struct_name}' expects {len(s_info.field_order)} fields, got {len(expr.args)}",
                )
            for idx, (field_name, arg_expr) in enumerate(zip(s_info.field_order, expr.args)):
                expected_type = s_info.fields[field_name].type_name
                arg_type = self.analyze_expression(arg_expr)
                if arg_type != expected_type:
                    self.error(
                        arg_expr.line,
                        arg_expr.column,
                        f"field '{field_name}' in '{expr.struct_name}' has wrong type: expected {expected_type}, got {arg_type}",
                    )
            return expr.struct_name

        if isinstance(expr, FieldAccessNode):
            base_type = self.analyze_expression(expr.target)
            if base_type not in self.structs:
                self.error(expr.line, expr.column, f"cannot access field '{expr.field_name}' on non-struct type '{base_type}'")
            s_info = self.structs[base_type]
            if expr.field_name not in s_info.fields:
                self.error(expr.line, expr.column, f"structure '{base_type}' has no field '{expr.field_name}'")
            return s_info.fields[expr.field_name].type_name

        if isinstance(expr, MemberCallNode):
            base_type, is_mut = self.get_expr_mutability_and_type(expr.target)
            if base_type not in self.structs:
                self.error(expr.line, expr.column, f"cannot call method '{expr.method_name}' on non-struct type '{base_type}'")
            s_info = self.structs[base_type]
            if expr.method_name not in s_info.methods:
                self.error(expr.line, expr.column, f"structure '{base_type}' has no method '{expr.method_name}'")
            m_info = s_info.methods[expr.method_name]

            if m_info.is_mutating and not is_mut:
                self.error(
                    expr.line,
                    expr.column,
                    f"cannot call mutating method '{expr.method_name}' on constant object",
                )

            if len(expr.args) != len(m_info.params):
                self.error(
                    expr.line,
                    expr.column,
                    f"method '{expr.method_name}' expects {len(m_info.params)} arguments, got {len(expr.args)}",
                )
            for idx, ((_, expected_type, _), arg_expr) in enumerate(zip(m_info.params, expr.args)):
                arg_type = self.analyze_expression(arg_expr)
                if arg_type != expected_type:
                    self.error(
                        arg_expr.line,
                        arg_expr.column,
                        f"argument {idx + 1} to method '{expr.method_name}' has wrong type: expected {expected_type}, got {arg_type}",
                    )
            return m_info.return_type

        return "unknown"

    def get_expr_mutability_and_type(self, expr: Expression) -> Tuple[str, bool]:
        if isinstance(expr, VariableNode):
            sym = self.lookup_symbol(expr.name)
            if sym is not None:
                return sym.type_name, sym.is_mutable
            if self.current_struct and expr.name in self.current_struct.fields:
                f = self.current_struct.fields[expr.name]
                return f.type_name, f.is_mutable
            self.error(expr.line, expr.column, f"use of undeclared variable '{expr.name}'")
        if isinstance(expr, FieldAccessNode):
            base_type, base_mut = self.get_expr_mutability_and_type(expr.target)
            if base_type not in self.structs:
                self.error(expr.line, expr.column, f"type '{base_type}' is not a structure")
            s_info = self.structs[base_type]
            if expr.field_name not in s_info.fields:
                self.error(expr.line, expr.column, f"structure '{base_type}' has no field '{expr.field_name}'")
            field = s_info.fields[expr.field_name]
            return field.type_name, (base_mut and field.is_mutable)

        t = self.analyze_expression(expr)
        return t, True
