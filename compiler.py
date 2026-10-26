"""Main driver for the survival language compiler."""

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


def compile_file(source_path: str, dump_ast: bool = True) -> ProgramNode:
    """Reads, tokenizes, and parses a source file into an AST."""
    with open(source_path, "rb") as source_file:
        source_data = source_file.read()

    token_lines = lex(source_data)
    program_ast = Parser(token_lines).parse_program()
    if dump_ast:
        program_ast.dump()
    return program_ast


def main() -> None:
    if len(sys.argv) < 3 or sys.argv[1] != "--ast":
        sys.stderr.write("usage: python3 compiler.py --ast <input.txt>\n")
        sys.exit(1)

    compile_file(sys.argv[2], dump_ast=True)


if __name__ == "__main__":
    main()