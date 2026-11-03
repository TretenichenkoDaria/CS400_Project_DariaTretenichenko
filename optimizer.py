import copy
from typing import Dict, List, Set, Tuple, Optional
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
    WhileNode,
    ForNode,
    BreakNode,
)


class Optimizer:
    def __init__(self):
        self.inline_counter = 0

    def optimize(self, program: ProgramNode) -> ProgramNode:
        changed = True
        while changed:
            changed = False
            if self.inline_pass(program):
                changed = True
            if self.unused_functions_pass(program):
                changed = True
            if self.unused_variables_pass(program):
                changed = True
        return program

    def has_side_effects(self, expr: Expression) -> bool:
        if isinstance(expr, (ReadNode, CallNode, MemberCallNode)):
            return True
        if isinstance(expr, UnaryOpNode):
            return self.has_side_effects(expr.operand)
        if isinstance(expr, BinaryOpNode):
            return self.has_side_effects(expr.left) or self.has_side_effects(expr.right)
        if isinstance(expr, FieldAccessNode):
            return self.has_side_effects(expr.target)
        if isinstance(expr, StructInitNode):
            return any(self.has_side_effects(a) for a in expr.args)
        return False

    def get_function_calls(self, node: ASTNode) -> Set[str]:
        calls = set()
        if isinstance(node, CallNode):
            calls.add(node.callee)
            for arg in node.args:
                calls.update(self.get_function_calls(arg))
        elif isinstance(node, MemberCallNode):
            calls.update(self.get_function_calls(node.target))
            for arg in node.args:
                calls.update(self.get_function_calls(arg))
        elif isinstance(node, BinaryOpNode):
            calls.update(self.get_function_calls(node.left))
            calls.update(self.get_function_calls(node.right))
        elif isinstance(node, UnaryOpNode):
            calls.update(self.get_function_calls(node.operand))
        elif isinstance(node, FieldAccessNode):
            calls.update(self.get_function_calls(node.target))
        elif isinstance(node, StructInitNode):
            for arg in node.args:
                calls.update(self.get_function_calls(arg))
        elif isinstance(node, DeclarationNode):
            calls.update(self.get_function_calls(node.initializer))
        elif isinstance(node, AssignmentNode):
            calls.update(self.get_function_calls(node.value))
        elif isinstance(node, ChainAssignNode):
            calls.update(self.get_function_calls(node.target))
            calls.update(self.get_function_calls(node.value))
        elif isinstance(node, PrintNode):
            calls.update(self.get_function_calls(node.expr))
        elif isinstance(node, ExitNode):
            calls.update(self.get_function_calls(node.value))
        elif isinstance(node, ReturnNode):
            calls.update(self.get_function_calls(node.value))
        elif isinstance(node, IfNode):
            calls.update(self.get_function_calls(node.condition))
            calls.update(self.get_function_calls(node.then_block))
            if node.else_block:
                calls.update(self.get_function_calls(node.else_block))
        elif isinstance(node, WhileNode):
            calls.update(self.get_function_calls(node.condition))
            calls.update(self.get_function_calls(node.body))
        elif isinstance(node, ForNode):
            calls.update(self.get_function_calls(node.start))
            calls.update(self.get_function_calls(node.end))
            calls.update(self.get_function_calls(node.body))
        elif isinstance(node, BlockNode):
            for stmt in node.statements:
                calls.update(self.get_function_calls(stmt))
        elif isinstance(node, FunctionNode):
            calls.update(self.get_function_calls(node.body))
        elif isinstance(node, StructNode):
            for m in node.methods:
                calls.update(self.get_function_calls(m))
        return calls

    def count_calls_to(self, target_name: str, node: ASTNode) -> int:
        count = 0
        if isinstance(node, CallNode):
            if node.callee == target_name:
                count += 1
            for arg in node.args:
                count += self.count_calls_to(target_name, arg)
        elif isinstance(node, MemberCallNode):
            count += self.count_calls_to(target_name, node.target)
            for arg in node.args:
                count += self.count_calls_to(target_name, arg)
        elif isinstance(node, BinaryOpNode):
            count += self.count_calls_to(target_name, node.left)
            count += self.count_calls_to(target_name, node.right)
        elif isinstance(node, UnaryOpNode):
            count += self.count_calls_to(target_name, node.operand)
        elif isinstance(node, FieldAccessNode):
            count += self.count_calls_to(target_name, node.target)
        elif isinstance(node, StructInitNode):
            for arg in node.args:
                count += self.count_calls_to(target_name, arg)
        elif isinstance(node, DeclarationNode):
            count += self.count_calls_to(target_name, node.initializer)
        elif isinstance(node, AssignmentNode):
            count += self.count_calls_to(target_name, node.value)
        elif isinstance(node, ChainAssignNode):
            count += self.count_calls_to(target_name, node.target)
            count += self.count_calls_to(target_name, node.value)
        elif isinstance(node, PrintNode):
            count += self.count_calls_to(target_name, node.expr)
        elif isinstance(node, ExitNode):
            count += self.count_calls_to(target_name, node.value)
        elif isinstance(node, ReturnNode):
            count += self.count_calls_to(target_name, node.value)
        elif isinstance(node, IfNode):
            count += self.count_calls_to(target_name, node.condition)
            count += self.count_calls_to(target_name, node.then_block)
            if node.else_block:
                count += self.count_calls_to(target_name, node.else_block)
        elif isinstance(node, WhileNode):
            count += self.count_calls_to(target_name, node.condition)
            count += self.count_calls_to(target_name, node.body)
        elif isinstance(node, ForNode):
            count += self.count_calls_to(target_name, node.start)
            count += self.count_calls_to(target_name, node.end)
            count += self.count_calls_to(target_name, node.body)
        elif isinstance(node, BlockNode):
            for stmt in node.statements:
                count += self.count_calls_to(target_name, stmt)
        elif isinstance(node, FunctionNode):
            count += self.count_calls_to(target_name, node.body)
        elif isinstance(node, StructNode):
            for m in node.methods:
                count += self.count_calls_to(target_name, m)
        return count

    def unused_functions_pass(self, program: ProgramNode) -> bool:
        any_removed = False
        loop = True
        while loop:
            loop = False
            top_level_fns: Dict[str, FunctionNode] = {}
            for s in program.statements:
                if isinstance(s, FunctionNode):
                    top_level_fns[s.name] = s

            called_functions = set()
            for s in program.statements:
                if not isinstance(s, FunctionNode):
                    called_functions.update(self.get_function_calls(s))
            called_functions.update(self.get_function_calls(program.exit_node))

            for fn_name, fn_node in top_level_fns.items():
                for s in program.statements:
                    if isinstance(s, FunctionNode) and s.name != fn_name:
                        called_functions.update(self.get_function_calls(s))

            for fn_name, fn_node in list(top_level_fns.items()):
                if fn_name not in called_functions:
                    program.statements.remove(fn_node)
                    any_removed = True
                    loop = True
                    break
        return any_removed

    def is_recursive(self, fn_name: str, functions: Dict[str, FunctionNode]) -> bool:
        visited = set()
        stack = [fn_name]
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            if cur in functions:
                calls = self.get_function_calls(functions[cur].body)
                if fn_name in calls:
                    return True
                for c in calls:
                    if c not in visited and c in functions:
                        stack.append(c)
        return False

    def can_inline_function(self, fn: FunctionNode, functions: Dict[str, FunctionNode]) -> bool:
        if self.is_recursive(fn.name, functions):
            return False
        if not fn.body.statements:
            return False
        last_stmt = fn.body.statements[-1]
        if not isinstance(last_stmt, ReturnNode):
            return False
        for stmt in fn.body.statements[:-1]:
            if self.contains_exit_or_return(stmt):
                return False
        return True

    def contains_exit_or_return(self, node: ASTNode) -> bool:
        if isinstance(node, (ExitNode, ReturnNode)):
            return True
        if isinstance(node, IfNode):
            if self.contains_exit_or_return(node.then_block):
                return True
            if node.else_block and self.contains_exit_or_return(node.else_block):
                return True
        elif isinstance(node, WhileNode):
            return self.contains_exit_or_return(node.body)
        elif isinstance(node, ForNode):
            return self.contains_exit_or_return(node.body)
        elif isinstance(node, BlockNode):
            for s in node.statements:
                if self.contains_exit_or_return(s):
                    return True
        return False

    def rename_in_ast(self, node: ASTNode, mapping: Dict[str, str]) -> None:
        if isinstance(node, VariableNode):
            if node.name in mapping:
                node.name = mapping[node.name]
        elif isinstance(node, DeclarationNode):
            if node.name in mapping:
                node.name = mapping[node.name]
            self.rename_in_ast(node.initializer, mapping)
        elif isinstance(node, AssignmentNode):
            if node.name in mapping:
                node.name = mapping[node.name]
            self.rename_in_ast(node.value, mapping)
        elif isinstance(node, ChainAssignNode):
            self.rename_in_ast(node.target, mapping)
            self.rename_in_ast(node.value, mapping)
        elif isinstance(node, BinaryOpNode):
            self.rename_in_ast(node.left, mapping)
            self.rename_in_ast(node.right, mapping)
        elif isinstance(node, UnaryOpNode):
            self.rename_in_ast(node.operand, mapping)
        elif isinstance(node, FieldAccessNode):
            self.rename_in_ast(node.target, mapping)
        elif isinstance(node, MemberCallNode):
            self.rename_in_ast(node.target, mapping)
            for a in node.args:
                self.rename_in_ast(a, mapping)
        elif isinstance(node, CallNode):
            for a in node.args:
                self.rename_in_ast(a, mapping)
        elif isinstance(node, StructInitNode):
            for a in node.args:
                self.rename_in_ast(a, mapping)
        elif isinstance(node, PrintNode):
            self.rename_in_ast(node.expr, mapping)
        elif isinstance(node, ExitNode):
            self.rename_in_ast(node.value, mapping)
        elif isinstance(node, ReturnNode):
            self.rename_in_ast(node.value, mapping)
        elif isinstance(node, IfNode):
            self.rename_in_ast(node.condition, mapping)
            self.rename_in_ast(node.then_block, mapping)
            if node.else_block:
                self.rename_in_ast(node.else_block, mapping)
        elif isinstance(node, WhileNode):
            self.rename_in_ast(node.condition, mapping)
            self.rename_in_ast(node.body, mapping)
        elif isinstance(node, ForNode):
            if node.var_name in mapping:
                node.var_name = mapping[node.var_name]
            self.rename_in_ast(node.start, mapping)
            self.rename_in_ast(node.end, mapping)
            self.rename_in_ast(node.body, mapping)
        elif isinstance(node, BlockNode):
            for s in node.statements:
                self.rename_in_ast(s, mapping)

    def replace_call_in_expr(
        self, expr: Expression, target_fn: str, ret_expr: Expression
    ) -> Tuple[Expression, Optional[CallNode]]:
        if isinstance(expr, CallNode) and expr.callee == target_fn:
            return ret_expr, expr

        if isinstance(expr, UnaryOpNode):
            new_op, call = self.replace_call_in_expr(expr.operand, target_fn, ret_expr)
            expr.operand = new_op
            return expr, call

        if isinstance(expr, BinaryOpNode):
            new_l, call = self.replace_call_in_expr(expr.left, target_fn, ret_expr)
            if call is not None:
                expr.left = new_l
                return expr, call
            new_r, call2 = self.replace_call_in_expr(expr.right, target_fn, ret_expr)
            expr.right = new_r
            return expr, call2

        if isinstance(expr, FieldAccessNode):
            new_t, call = self.replace_call_in_expr(expr.target, target_fn, ret_expr)
            expr.target = new_t
            return expr, call

        if isinstance(expr, StructInitNode):
            new_args = []
            found_call = None
            for a in expr.args:
                if found_call is None:
                    new_a, call = self.replace_call_in_expr(a, target_fn, ret_expr)
                    if call is not None:
                        found_call = call
                    new_args.append(new_a)
                else:
                    new_args.append(a)
            expr.args = new_args
            return expr, found_call

        if isinstance(expr, MemberCallNode):
            new_t, call = self.replace_call_in_expr(expr.target, target_fn, ret_expr)
            if call is not None:
                expr.target = new_t
                return expr, call
            new_args = []
            found_call = None
            for a in expr.args:
                if found_call is None:
                    new_a, call = self.replace_call_in_expr(a, target_fn, ret_expr)
                    if call is not None:
                        found_call = call
                    new_args.append(new_a)
                else:
                    new_args.append(a)
            expr.args = new_args
            return expr, found_call

        if isinstance(expr, CallNode):
            new_args = []
            found_call = None
            for a in expr.args:
                if found_call is None:
                    new_a, call = self.replace_call_in_expr(a, target_fn, ret_expr)
                    if call is not None:
                        found_call = call
                    new_args.append(new_a)
                else:
                    new_args.append(a)
            expr.args = new_args
            return expr, found_call

        return expr, None

    def inline_pass(self, program: ProgramNode) -> bool:
        top_level_fns: Dict[str, FunctionNode] = {}
        for s in program.statements:
            if isinstance(s, FunctionNode):
                top_level_fns[s.name] = s

        for fn_name, fn_node in top_level_fns.items():
            total_calls = 0
            for s in program.statements:
                total_calls += self.count_calls_to(fn_name, s)
            total_calls += self.count_calls_to(fn_name, program.exit_node)

            if total_calls == 1 and self.can_inline_function(fn_node, top_level_fns):
                if self.try_inline_in_stmt_list(program.statements, fn_node):
                    if fn_node in program.statements:
                        program.statements.remove(fn_node)
                    return True
        return False

    def try_inline_in_stmt_list(self, stmts: List[Statement], fn_node: FunctionNode) -> bool:
        fn_name = fn_node.name
        for idx, stmt in enumerate(stmts):
            if isinstance(stmt, FunctionNode):
                if self.try_inline_in_stmt_list(stmt.body.statements, fn_node):
                    return True
                continue
            if isinstance(stmt, StructNode):
                for m in stmt.methods:
                    if self.try_inline_in_stmt_list(m.body.statements, fn_node):
                        return True
                continue
            if isinstance(stmt, IfNode):
                if self.try_inline_in_stmt_list(stmt.then_block.statements, fn_node):
                    return True
                if stmt.else_block and self.try_inline_in_stmt_list(stmt.else_block.statements, fn_node):
                    return True
            if isinstance(stmt, WhileNode):
                if self.try_inline_in_stmt_list(stmt.body.statements, fn_node):
                    return True
            if isinstance(stmt, ForNode):
                if self.try_inline_in_stmt_list(stmt.body.statements, fn_node):
                    return True

            self.inline_counter += 1
            prefix = f"inline_{fn_name}_{self.inline_counter}"

            renames = {}
            for p in fn_node.params:
                renames[p.name] = f"{prefix}_{p.name}"
            for s in fn_node.body.statements:
                if isinstance(s, DeclarationNode):
                    renames[s.name] = f"{prefix}_{s.name}"

            fn_body_copy = copy.deepcopy(fn_node.body.statements)
            for s in fn_body_copy:
                self.rename_in_ast(s, renames)

            ret_stmt = fn_body_copy[-1]
            assert isinstance(ret_stmt, ReturnNode)
            ret_expr = ret_stmt.value
            body_stmts = fn_body_copy[:-1]

            call_node = None
            if isinstance(stmt, DeclarationNode):
                new_init, call_node = self.replace_call_in_expr(stmt.initializer, fn_name, ret_expr)
                stmt.initializer = new_init
            elif isinstance(stmt, AssignmentNode):
                new_val, call_node = self.replace_call_in_expr(stmt.value, fn_name, ret_expr)
                stmt.value = new_val
            elif isinstance(stmt, ChainAssignNode):
                if stmt.target is stmt.value and isinstance(stmt.target, CallNode) and stmt.target.callee == fn_name:
                    call_node = stmt.target
                    param_decls = []
                    for p, a in zip(fn_node.params, call_node.args):
                        param_decls.append(
                            DeclarationNode(p.line, p.column, p.type_name, renames[p.name], p.is_mutable, a)
                        )
                    stmts[idx : idx + 1] = param_decls + body_stmts
                    return True
                new_val, call_node = self.replace_call_in_expr(stmt.value, fn_name, ret_expr)
                stmt.value = new_val
            elif isinstance(stmt, PrintNode):
                new_e, call_node = self.replace_call_in_expr(stmt.expr, fn_name, ret_expr)
                stmt.expr = new_e
            elif isinstance(stmt, ExitNode):
                new_v, call_node = self.replace_call_in_expr(stmt.value, fn_name, ret_expr)
                stmt.value = new_v
            elif isinstance(stmt, ReturnNode):
                new_v, call_node = self.replace_call_in_expr(stmt.value, fn_name, ret_expr)
                stmt.value = new_v

            if call_node is not None:
                param_decls = []
                for p, a in zip(fn_node.params, call_node.args):
                    param_decls.append(
                        DeclarationNode(p.line, p.column, p.type_name, renames[p.name], p.is_mutable, a)
                    )
                hoisted = param_decls + body_stmts
                stmts[idx:idx] = hoisted
                return True

        return False

    def unused_variables_pass(self, program: ProgramNode) -> bool:
        any_removed = False
        loop = True
        while loop:
            loop = False
            all_decls: Dict[int, DeclarationNode] = {}
            external_reads: Dict[int, int] = {}
            assignments: Dict[int, List[AssignmentNode]] = {}

            scope_stack: List[Dict[str, int]] = [{}]

            def process_block(stmts: List[Statement]) -> None:
                scope_stack.append({})
                for s in stmts:
                    process_stmt(s)
                scope_stack.pop()

            def process_expr(expr: Expression, current_target_sym: Optional[int] = None) -> None:
                if isinstance(expr, VariableNode):
                    for scope in reversed(scope_stack):
                        if expr.name in scope:
                            sym_id = scope[expr.name]
                            if current_target_sym is not None and sym_id == current_target_sym:
                                pass
                            else:
                                external_reads[sym_id] = external_reads.get(sym_id, 0) + 1
                            break
                elif isinstance(expr, UnaryOpNode):
                    process_expr(expr.operand, current_target_sym)
                elif isinstance(expr, BinaryOpNode):
                    process_expr(expr.left, current_target_sym)
                    process_expr(expr.right, current_target_sym)
                elif isinstance(expr, FieldAccessNode):
                    process_expr(expr.target, current_target_sym)
                elif isinstance(expr, MemberCallNode):
                    process_expr(expr.target, current_target_sym)
                    for a in expr.args:
                        process_expr(a, current_target_sym)
                elif isinstance(expr, CallNode):
                    for a in expr.args:
                        process_expr(a, current_target_sym)
                elif isinstance(expr, StructInitNode):
                    for a in expr.args:
                        process_expr(a, current_target_sym)

            def process_stmt(stmt: Statement) -> None:
                if isinstance(stmt, DeclarationNode):
                    process_expr(stmt.initializer)
                    sym_id = id(stmt)
                    all_decls[sym_id] = stmt
                    external_reads[sym_id] = 0
                    assignments[sym_id] = []
                    scope_stack[-1][stmt.name] = sym_id
                elif isinstance(stmt, AssignmentNode):
                    target_sym = None
                    for scope in reversed(scope_stack):
                        if stmt.name in scope:
                            target_sym = scope[stmt.name]
                            assignments[target_sym].append(stmt)
                            break
                    process_expr(stmt.value, target_sym)
                elif isinstance(stmt, ChainAssignNode):
                    process_expr(stmt.target)
                    process_expr(stmt.value)
                elif isinstance(stmt, PrintNode):
                    process_expr(stmt.expr)
                elif isinstance(stmt, ExitNode):
                    process_expr(stmt.value)
                elif isinstance(stmt, ReturnNode):
                    process_expr(stmt.value)
                elif isinstance(stmt, IfNode):
                    process_expr(stmt.condition)
                    process_block(stmt.then_block.statements)
                    if stmt.else_block:
                        process_block(stmt.else_block.statements)
                elif isinstance(stmt, WhileNode):
                    process_expr(stmt.condition)
                    process_block(stmt.body.statements)
                elif isinstance(stmt, ForNode):
                    process_expr(stmt.start)
                    process_expr(stmt.end)
                    scope_stack.append({})
                    scope_stack[-1][stmt.var_name] = id(stmt)
                    for s in stmt.body.statements:
                        process_stmt(s)
                    scope_stack.pop()
                elif isinstance(stmt, BlockNode):
                    process_block(stmt.statements)
                elif isinstance(stmt, FunctionNode):
                    scope_stack.append({})
                    for p in stmt.params:
                        scope_stack[-1][p.name] = id(p)
                    for s in stmt.body.statements:
                        process_stmt(s)
                    scope_stack.pop()
                elif isinstance(stmt, StructNode):
                    for m in stmt.methods:
                        process_stmt(m)

            for s in program.statements:
                process_stmt(s)
            process_stmt(program.exit_node)

            stmts_to_remove = set()
            for sym_id, decl in all_decls.items():
                if external_reads.get(sym_id, 0) == 0:
                    if not self.has_side_effects(decl.initializer):
                        stmts_to_remove.add(id(decl))
                        for a in assignments[sym_id]:
                            if not self.has_side_effects(a.value):
                                stmts_to_remove.add(id(a))

            if stmts_to_remove:
                def remove_from_list(stmts: List[Statement]) -> None:
                    nonlocal any_removed, loop
                    i = 0
                    while i < len(stmts):
                        s = stmts[i]
                        if id(s) in stmts_to_remove:
                            stmts.pop(i)
                            any_removed = True
                            loop = True
                            continue
                        if isinstance(s, IfNode):
                            remove_from_list(s.then_block.statements)
                            if s.else_block:
                                remove_from_list(s.else_block.statements)
                        elif isinstance(s, WhileNode):
                            remove_from_list(s.body.statements)
                        elif isinstance(s, ForNode):
                            remove_from_list(s.body.statements)
                        elif isinstance(s, BlockNode):
                            remove_from_list(s.statements)
                        elif isinstance(s, FunctionNode):
                            remove_from_list(s.body.statements)
                        elif isinstance(s, StructNode):
                            for m in s.methods:
                                remove_from_list(m.body.statements)
                        i += 1

                remove_from_list(program.statements)

        return any_removed
