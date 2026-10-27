from enum import Enum


class TokenKind(Enum):
    # Keywords
    INFECT = "infect"
    IMMUNE = "immune"
    EXIT = "exit"
    ALIVE = "alive"
    DEAD = "dead"
    SURVIVE = "survive"
    PERISH = "perish"
    RITUAL = "ritual"
    FN = "fn"
    SHELTER = "shelter"
    STRUCT = "struct"
    YIELD = "yield"
    RETURN = "return"
    READ = "read"
    PRINT = "print"

    # Type keywords
    TYPE_I32 = "🩸"
    TYPE_I64 = "🫀"
    TYPE_BOOL = "💊"

    # Delimiters and operators
    ASSIGN = "💉"
    TERMINATOR = "⏳"
    LBRACE = "{"
    RBRACE = "}"
    LPAREN = "("
    RPAREN = ")"
    COMMA = ","
    DOT = "."
    ARROW = "->"
    EQ = "=="
    NEQ = "!="
    PLUS = "+"
    MINUS = "-"
    STAR = "*"
    NOT = "!"

    # Literals and identifiers
    IDENTIFIER = "identifier"
    CONSTANT = "constant"
    BOOLEAN = "boolean"
    STRING = "string"


class Token:
    def __init__(self, kind: str, text: str, line: int, column: int):
        self.kind = kind
        self.text = text
        self.line = line
        self.column = column

    def __repr__(self) -> str:
        return f"Token({self.kind!r}, {self.text!r}, line={self.line}, col={self.column})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Token):
            return False
        return (
            self.kind == other.kind
            and self.text == other.text
            and self.line == other.line
            and self.column == other.column
        )
