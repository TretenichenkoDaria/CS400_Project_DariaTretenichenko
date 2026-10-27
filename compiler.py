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
)
from parser import Parser
from semantics import SemanticAnalyzer
from codegen import CodeGenerator


def compile_file(source_path: str, dump_ast: bool = False, output_path: str = None) -> ProgramNode:
    with open(source_path, "rb") as source_file:
        source_data = source_file.read()

    token_lines = lex(source_data)
    program_ast = Parser(token_lines).parse_program()

    if dump_ast:
        program_ast.dump()
        return program_ast

    analyzer = SemanticAnalyzer()
    analyzer.analyze(program_ast)

    generator = CodeGenerator(analyzer)
    ir_text = generator.generate(program_ast)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as out:
            out.write(ir_text)

    return program_ast


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--ast":
        compile_file(sys.argv[2], dump_ast=True)
    elif len(sys.argv) == 3:
        compile_file(sys.argv[1], dump_ast=False, output_path=sys.argv[2])
    else:
        sys.stderr.write("usage:\n  python3 compiler.py --ast <input.txt>\n  python3 compiler.py <input.txt> <output.ll>\n")
        sys.exit(1)


if __name__ == "__main__":
    main()