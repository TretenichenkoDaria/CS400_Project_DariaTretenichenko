import sys
from typing import Dict, List, Optional, Tuple, Any

import llvmlite.ir as ir
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
from semantics import SemanticAnalyzer, StructInfo, FunctionInfo

MAX_32BIT_INT = 2147483647
MAX_64BIT_INT = 9223372036854775807


class CodeGenerator:
    def __init__(self, semantics: SemanticAnalyzer):
        self.semantics = semantics
        self.module = ir.Module(name="survival_module")

        self.i32 = ir.IntType(32)
        self.i64 = ir.IntType(64)
        self.i1 = ir.IntType(1)
        self.i8 = ir.IntType(8)
        self.i8p = ir.IntType(8).as_pointer()
        self.void = ir.VoidType()

        self.llvm_struct_types: Dict[str, ir.IdentifiedStructType] = {}
        self.llvm_functions: Dict[str, ir.Function] = {}
        self.llvm_methods: Dict[Tuple[str, str], ir.Function] = {}

        self.builder: Optional[ir.IRBuilder] = None
        self.scopes: List[Dict[str, Tuple[ir.Value, str]]] = [{}]  # name -> (pointer, type_name)
        self.current_struct: Optional[StructInfo] = None
        self.current_this_ptr: Optional[ir.Value] = None
        self.str_constants_count = 0

        self.setup_runtime()

    def setup_runtime(self) -> None:
        c_vararg_type = ir.FunctionType(self.i32, [self.i8p], var_arg=True)
        self.printf = ir.Function(self.module, c_vararg_type, name="printf")
        self.scanf = ir.Function(self.module, c_vararg_type, name="scanf")

        self.fmt_i32 = self.add_global_string("fmt_i32", "%d\n")
        self.fmt_i64 = self.add_global_string("fmt_i64", "%lld\n")
        self.fmt_str = self.add_global_string("fmt_str", "%s\n")
        self.fmt_read = self.add_global_string("fmt_read", "%d")
        self.str_true = self.add_global_string("str_true", "true\n")
        self.str_false = self.add_global_string("str_false", "false\n")

    def add_global_string(self, name: str, text: str) -> ir.Value:
        text_bytes = (text + "\0").encode("utf-8")
        c_type = ir.ArrayType(self.i8, len(text_bytes))
        c_val = ir.Constant(c_type, bytearray(text_bytes))
        g_var = ir.GlobalVariable(self.module, c_type, name=name)
        g_var.linkage = "internal"
        g_var.global_constant = True
        g_var.initializer = c_val
        return g_var

    def get_str_ptr(self, g_var: ir.GlobalVariable) -> ir.Value:
        zero = ir.Constant(self.i32, 0)
        return self.builder.gep(g_var, [zero, zero])

    def to_llvm_type(self, type_name: str) -> ir.Type:
        if type_name == "🩸":
            return self.i32
        if type_name == "🫀":
            return self.i64
        if type_name == "💊":
            return self.i1
        if type_name in self.llvm_struct_types:
            return self.llvm_struct_types[type_name]
        return self.i32

    def enter_scope(self) -> None:
        self.scopes.append({})

    def exit_scope(self) -> None:
        self.scopes.pop()

    def declare_variable(self, name: str, ptr: ir.Value, type_name: str) -> None:
        self.scopes[-1][name] = (ptr, type_name)

    def lookup_variable(self, name: str) -> Optional[Tuple[ir.Value, str]]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def generate(self, program: ProgramNode) -> str:
        for s_name, s_info in self.semantics.structs.items():
            self.llvm_struct_types[s_name] = self.module.context.get_identified_type(s_name)

        for s_name, s_info in self.semantics.structs.items():
            field_types = [self.to_llvm_type(s_info.fields[f].type_name) for f in s_info.field_order]
            self.llvm_struct_types[s_name].set_body(*field_types)

        for f_name, f_info in self.semantics.functions.items():
            ret_type = self.to_llvm_type(f_info.return_type)
            param_types = [self.to_llvm_type(ptype) for (_, ptype, _) in f_info.params]
            fn_type = ir.FunctionType(ret_type, param_types)
            self.llvm_functions[f_name] = ir.Function(self.module, fn_type, name=f"f_{f_name}")

        for s_name, s_info in self.semantics.structs.items():
            s_type = self.llvm_struct_types[s_name]
            for m_name, m_info in s_info.methods.items():
                ret_type = self.to_llvm_type(m_info.return_type)
                param_types = [s_type.as_pointer()] + [self.to_llvm_type(ptype) for (_, ptype, _) in m_info.params]
                fn_type = ir.FunctionType(ret_type, param_types)
                self.llvm_methods[(s_name, m_name)] = ir.Function(
                    self.module, fn_type, name=f"f_{s_name}_{m_name}"
                )

        for f_name, f_info in self.semantics.functions.items():
            self.generate_function_body(f_info)

        for s_name, s_info in self.semantics.structs.items():
            for m_name, m_info in s_info.methods.items():
                self.generate_method_body(s_info, m_info)

        main_type = ir.FunctionType(self.i32, [])
        main_fn = ir.Function(self.module, main_type, name="main")
        entry_block = main_fn.append_basic_block("entry")
        self.builder = ir.IRBuilder(entry_block)

        self.enter_scope()
        for stmt in program.statements:
            if not isinstance(stmt, (FunctionNode, StructNode)):
                self.generate_statement(stmt)

        self.generate_statement(program.exit_node)
        self.exit_scope()

        if not self.builder.block.is_terminated:
            self.builder.ret(ir.Constant(self.i32, 0))

        return str(self.module)

    def generate_function_body(self, f_info: FunctionInfo) -> None:
        fn = self.llvm_functions[f_info.name]
        block = fn.append_basic_block("entry")
        prev_builder = self.builder
        self.builder = ir.IRBuilder(block)
        self.enter_scope()

        for arg, (pname, ptype, _) in zip(fn.args, f_info.params):
            llvm_type = self.to_llvm_type(ptype)
            ptr = self.builder.alloca(llvm_type, name=pname)
            self.builder.store(arg, ptr)
            self.declare_variable(pname, ptr, ptype)

        for stmt in f_info.node.body.statements:
            self.generate_statement(stmt)

        if not self.builder.block.is_terminated:
            ret_type = self.to_llvm_type(f_info.return_type)
            if isinstance(ret_type, ir.VoidType):
                self.builder.ret_void()
            else:
                self.builder.ret(ir.Constant(ret_type, 0))

        self.exit_scope()
        self.builder = prev_builder

    def generate_method_body(self, s_info: StructInfo, m_info: MethodInfo) -> None:
        fn = self.llvm_methods[(s_info.name, m_info.name)]
        block = fn.append_basic_block("entry")
        prev_builder = self.builder
        prev_struct = self.current_struct
        prev_this = self.current_this_ptr

        self.builder = ir.IRBuilder(block)
        self.current_struct = s_info
        self.current_this_ptr = fn.args[0]
        self.enter_scope()

        for arg, (pname, ptype, _) in zip(fn.args[1:], m_info.params):
            llvm_type = self.to_llvm_type(ptype)
            ptr = self.builder.alloca(llvm_type, name=pname)
            self.builder.store(arg, ptr)
            self.declare_variable(pname, ptr, ptype)

        for stmt in m_info.node.body.statements:
            self.generate_statement(stmt)

        if not self.builder.block.is_terminated:
            ret_type = self.to_llvm_type(m_info.return_type)
            if isinstance(ret_type, ir.VoidType):
                self.builder.ret_void()
            else:
                self.builder.ret(ir.Constant(ret_type, 0))

        self.exit_scope()
        self.current_this_ptr = prev_this
        self.current_struct = prev_struct
        self.builder = prev_builder

    def generate_statement(self, stmt: Statement) -> None:
        if self.builder.block.is_terminated:
            return

        if isinstance(stmt, DeclarationNode):
            llvm_type = self.to_llvm_type(stmt.type_name)
            ptr = self.builder.alloca(llvm_type, name=stmt.name)
            val = self.generate_expression(stmt.initializer)
            if stmt.type_name in self.semantics.structs and isinstance(val.type, ir.PointerType):
                val = self.builder.load(val)
            self.builder.store(val, ptr)
            self.declare_variable(stmt.name, ptr, stmt.type_name)

        elif isinstance(stmt, AssignmentNode):
            res = self.lookup_variable(stmt.name)
            if res is not None:
                ptr, _ = res
            elif self.current_struct and stmt.name in self.current_struct.fields:
                f_idx = self.current_struct.fields[stmt.name].index
                ptr = self.builder.gep(
                    self.current_this_ptr,
                    [ir.Constant(self.i32, 0), ir.Constant(self.i32, f_idx)],
                )
            else:
                return
            val = self.generate_expression(stmt.value)
            self.builder.store(val, ptr)

        elif isinstance(stmt, ChainAssignNode):
            if isinstance(stmt.target, (CallNode, MemberCallNode)):
                self.generate_expression(stmt.target)
                return
            ptr = self.get_lvalue_ptr(stmt.target)
            val = self.generate_expression(stmt.value)
            self.builder.store(val, ptr)

        elif isinstance(stmt, IfNode):
            cond_val = self.generate_expression(stmt.condition)
            func = self.builder.function

            then_bb = func.append_basic_block("then")
            else_bb = func.append_basic_block("else") if stmt.else_block else None
            merge_bb = func.append_basic_block("if_merge")

            target_else = else_bb if else_bb else merge_bb
            self.builder.cbranch(cond_val, then_bb, target_else)

            self.builder.position_at_end(then_bb)
            self.enter_scope()
            for s in stmt.then_block.statements:
                self.generate_statement(s)
            self.exit_scope()
            if not self.builder.block.is_terminated:
                self.builder.branch(merge_bb)

            if stmt.else_block:
                self.builder.position_at_end(else_bb)
                self.enter_scope()
                for s in stmt.else_block.statements:
                    self.generate_statement(s)
                self.exit_scope()
                if not self.builder.block.is_terminated:
                    self.builder.branch(merge_bb)

            self.builder.position_at_end(merge_bb)

        elif isinstance(stmt, ExitNode):
            val = self.generate_expression(stmt.value)
            if val.type == self.i64:
                val = self.builder.trunc(val, self.i32)
            self.builder.ret(val)

        elif isinstance(stmt, ReturnNode):
            val = self.generate_expression(stmt.value)
            self.builder.ret(val)

        elif isinstance(stmt, PrintNode):
            self.generate_print(stmt.expr)

    def generate_print(self, expr: Expression) -> None:
        expr_type = self.semantics.analyze_expression(expr)

        if expr_type == "🩸":
            val = self.generate_expression(expr)
            fmt_ptr = self.get_str_ptr(self.fmt_i32)
            self.builder.call(self.printf, [fmt_ptr, val])

        elif expr_type == "🫀":
            val = self.generate_expression(expr)
            fmt_ptr = self.get_str_ptr(self.fmt_i64)
            self.builder.call(self.printf, [fmt_ptr, val])

        elif expr_type == "💊":
            val = self.generate_expression(expr)
            true_ptr = self.get_str_ptr(self.str_true)
            false_ptr = self.get_str_ptr(self.str_false)
            str_ptr = self.builder.select(val, true_ptr, false_ptr)
            self.builder.call(self.printf, [str_ptr])

        elif expr_type == "string":
            if isinstance(expr, StringLiteralNode):
                self.str_constants_count += 1
                g_str = self.add_global_string(f"str_{self.str_constants_count}", expr.value)
                str_val = self.get_str_ptr(g_str)
                fmt_ptr = self.get_str_ptr(self.fmt_str)
                self.builder.call(self.printf, [fmt_ptr, str_val])

        elif expr_type in self.semantics.structs:
            s_info = self.semantics.structs[expr_type]
            obj_ptr = self.get_lvalue_ptr(expr)
            for f_name in s_info.field_order:
                f_info = s_info.fields[f_name]
                f_ptr = self.builder.gep(
                    obj_ptr,
                    [ir.Constant(self.i32, 0), ir.Constant(self.i32, f_info.index)],
                )
                f_val = self.builder.load(f_ptr)
                if f_info.type_name == "🩸":
                    fmt = self.get_str_ptr(self.fmt_i32)
                    self.builder.call(self.printf, [fmt, f_val])
                elif f_info.type_name == "🫀":
                    fmt = self.get_str_ptr(self.fmt_i64)
                    self.builder.call(self.printf, [fmt, f_val])
                elif f_info.type_name == "💊":
                    true_ptr = self.get_str_ptr(self.str_true)
                    false_ptr = self.get_str_ptr(self.str_false)
                    str_ptr = self.builder.select(f_val, true_ptr, false_ptr)
                    self.builder.call(self.printf, [str_ptr])

    def get_lvalue_ptr(self, expr: Expression) -> ir.Value:
        if isinstance(expr, VariableNode):
            res = self.lookup_variable(expr.name)
            if res is not None:
                return res[0]
            if self.current_struct and expr.name in self.current_struct.fields:
                f_idx = self.current_struct.fields[expr.name].index
                return self.builder.gep(
                    self.current_this_ptr,
                    [ir.Constant(self.i32, 0), ir.Constant(self.i32, f_idx)],
                )
        if isinstance(expr, FieldAccessNode):
            base_ptr = self.get_lvalue_ptr(expr.target)
            base_type = self.semantics.analyze_expression(expr.target)
            s_info = self.semantics.structs[base_type]
            f_idx = s_info.fields[expr.field_name].index
            return self.builder.gep(
                base_ptr,
                [ir.Constant(self.i32, 0), ir.Constant(self.i32, f_idx)],
            )
        # Struct instantiation temporary
        if isinstance(expr, StructInitNode):
            s_type = self.llvm_struct_types[expr.struct_name]
            obj_ptr = self.builder.alloca(s_type)
            s_info = self.semantics.structs[expr.struct_name]
            for idx, arg_expr in enumerate(expr.args):
                arg_val = self.generate_expression(arg_expr)
                f_ptr = self.builder.gep(
                    obj_ptr,
                    [ir.Constant(self.i32, 0), ir.Constant(self.i32, idx)],
                )
                self.builder.store(arg_val, f_ptr)
            return obj_ptr

        raise RuntimeError(f"Cannot get lvalue pointer for {expr}")

    def generate_expression(self, expr: Expression) -> ir.Value:
        if isinstance(expr, ConstantNode):
            val = int(expr.value)
            if val <= MAX_32BIT_INT:
                return ir.Constant(self.i32, val)
            return ir.Constant(self.i64, val)

        if isinstance(expr, BooleanNode):
            val = 1 if expr.value == "alive" else 0
            return ir.Constant(self.i1, val)

        if isinstance(expr, ReadNode):
            slot = self.builder.alloca(self.i32)
            fmt_ptr = self.get_str_ptr(self.fmt_read)
            self.builder.call(self.scanf, [fmt_ptr, slot])
            return self.builder.load(slot)

        if isinstance(expr, VariableNode):
            res = self.lookup_variable(expr.name)
            if res is not None:
                ptr, _ = res
                return self.builder.load(ptr)
            if self.current_struct and expr.name in self.current_struct.fields:
                f_idx = self.current_struct.fields[expr.name].index
                ptr = self.builder.gep(
                    self.current_this_ptr,
                    [ir.Constant(self.i32, 0), ir.Constant(self.i32, f_idx)],
                )
                return self.builder.load(ptr)

        if isinstance(expr, UnaryOpNode):
            op_val = self.generate_expression(expr.operand)
            if expr.operator == "!":
                return self.builder.not_(op_val)

        if isinstance(expr, BinaryOpNode):
            left_val = self.generate_expression(expr.left)
            right_val = self.generate_expression(expr.right)

            if expr.operator == "+":
                return self.builder.add(left_val, right_val)
            if expr.operator == "-":
                return self.builder.sub(left_val, right_val)
            if expr.operator == "*":
                return self.builder.mul(left_val, right_val)
            if expr.operator == "==":
                return self.builder.icmp_signed("==", left_val, right_val)
            if expr.operator == "!=":
                return self.builder.icmp_signed("!=", left_val, right_val)

        if isinstance(expr, CallNode):
            fn = self.llvm_functions[expr.callee]
            arg_vals = [self.generate_expression(a) for a in expr.args]
            return self.builder.call(fn, arg_vals)

        if isinstance(expr, StructInitNode):
            ptr = self.get_lvalue_ptr(expr)
            return self.builder.load(ptr)

        if isinstance(expr, FieldAccessNode):
            ptr = self.get_lvalue_ptr(expr)
            return self.builder.load(ptr)

        if isinstance(expr, MemberCallNode):
            target_type = self.semantics.analyze_expression(expr.target)
            target_ptr = self.get_lvalue_ptr(expr.target)
            fn = self.llvm_methods[(target_type, expr.method_name)]
            arg_vals = [target_ptr] + [self.generate_expression(a) for a in expr.args]
            return self.builder.call(fn, arg_vals)

        raise RuntimeError(f"Unhandled expression in codegen: {expr}")
