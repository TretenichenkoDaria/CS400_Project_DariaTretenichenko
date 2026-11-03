import sys
from tokens import Token, TokenKind
from lexer import Lexer, lex
from ast_nodes import (
    ASTNode,
    ProgramNode,
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
    WhileNode,
    ForNode,
    BreakNode,
)
from parser import Parser
from semantics import SemanticAnalyzer
from codegen import CodeGenerator
from optimizer import Optimizer


def compile_file(
    source_path: str,
    dump_ast: bool = False,
    optimize: bool = False,
    output_path: str = None,
) -> ProgramNode:
    with open(source_path, "rb") as source_file:
        source_data = source_file.read()

    token_lines = lex(source_data)
    program_ast = Parser(token_lines).parse_program()

    if dump_ast and not optimize:
        program_ast.dump()
        return program_ast

    analyzer = SemanticAnalyzer()
    analyzer.analyze(program_ast)

    if optimize:
        program_ast = Optimizer().optimize(program_ast)
        analyzer = SemanticAnalyzer()
        analyzer.analyze(program_ast)

    if dump_ast:
        program_ast.dump()
        return program_ast

    generator = CodeGenerator(analyzer)
    ir_text = generator.generate(program_ast)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as out:
            out.write(ir_text)

    return program_ast


def main() -> None:
    args = sys.argv[1:]
    dump_ast = "--ast" in args
    optimize = "--optimize" in args
    positional = [a for a in args if not a.startswith("--")]

    if dump_ast and len(positional) == 1:
        compile_file(positional[0], dump_ast=True, optimize=optimize)
    elif not dump_ast and len(positional) == 2:
        compile_file(positional[0], dump_ast=False, optimize=optimize, output_path=positional[1])
    else:
        sys.stderr.write(
            "usage:\n"
            "  python3 compiler.py [--optimize] --ast <input.txt>\n"
            "  python3 compiler.py [--optimize] <input.txt> <output.ll>\n"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
