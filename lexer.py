import sys
from typing import List, Optional
from tokens import Token

MAX_64BIT_INT = 9223372036854775807

KEYWORDS = {
    "infect": "mut_modifier",
    "immune": "const_modifier",
    "exit": "keyword",
    "alive": "boolean",
    "dead": "boolean",
    "survive": "keyword",
    "perish": "keyword",
    "ritual": "keyword",
    "fn": "keyword",
    "shelter": "keyword",
    "struct": "keyword",
    "yield": "keyword",
    "return": "keyword",
    "read": "keyword",
    "print": "keyword",
}

EMOJI_TOKENS = {
    "🩸".encode("utf-8"): ("typename", "🩸"),
    "🫀".encode("utf-8"): ("typename", "🫀"),
    "💊".encode("utf-8"): ("typename", "💊"),
    "💉".encode("utf-8"): ("operator", "💉"),
    "⏳".encode("utf-8"): ("operator", "⏳"),
}


class Lexer:
    def __init__(self, source_bytes: bytes):
        self.data = source_bytes
        self.length = len(source_bytes)
        self.index = 0
        self.current_line = 1
        self.current_column = 1

    def error(self, line: int, column: int, message: str) -> None:
        sys.stderr.write(f"compilation error: line {line}:{column}: {message}\n")
        sys.exit(1)

    def peek_byte(self, offset: int = 0) -> Optional[int]:
        pos = self.index + offset
        if pos < self.length:
            return self.data[pos]
        return None

    def tokenize(self) -> List[List[Token]]:
        lines: List[List[Token]] = []
        current_line_tokens: List[Token] = []

        while self.index < self.length:
            byte = self.data[self.index]

            if byte in (32, 9):
                self.index += 1
                self.current_column += 1
                continue

            if byte == 10:
                if current_line_tokens:
                    lines.append(current_line_tokens)
                    current_line_tokens = []
                self.index += 1
                self.current_line += 1
                self.current_column = 1
                continue

            matched_emoji = False
            for emoji_bytes, (token_kind, token_text) in EMOJI_TOKENS.items():
                emoji_len = len(emoji_bytes)
                if self.data[self.index : self.index + emoji_len] == emoji_bytes:
                    token = Token(token_kind, token_text, self.current_line, self.current_column)
                    current_line_tokens.append(token)
                    self.index += emoji_len
                    self.current_column += emoji_len
                    matched_emoji = True
                    break

            if matched_emoji:
                continue

            if byte in (123, 125):
                token = Token("brace", chr(byte), self.current_line, self.current_column)
                current_line_tokens.append(token)
                self.index += 1
                self.current_column += 1
                continue

            if byte in (40, 41):
                token = Token("paren", chr(byte), self.current_line, self.current_column)
                current_line_tokens.append(token)
                self.index += 1
                self.current_column += 1
                continue

            if byte == 44:  # ','
                token = Token("comma", ",", self.current_line, self.current_column)
                current_line_tokens.append(token)
                self.index += 1
                self.current_column += 1
                continue

            if byte == 46:  # '.'
                token = Token("dot", ".", self.current_line, self.current_column)
                current_line_tokens.append(token)
                self.index += 1
                self.current_column += 1
                continue

            # String literal: "..."
            if byte == 34:  # '"'
                start_column = self.current_column
                self.index += 1
                self.current_column += 1
                str_chars = []
                closed = False
                while self.index < self.length:
                    b = self.data[self.index]
                    if b == 10:
                        self.error(self.current_line, start_column, "unclosed string literal")
                    if b == 34:  # '"'
                        self.index += 1
                        self.current_column += 1
                        closed = True
                        break
                    str_chars.append(b)
                    self.index += 1
                    self.current_column += 1

                if not closed:
                    self.error(self.current_line, start_column, "unclosed string literal")

                string_val = bytes(str_chars).decode("utf-8")
                token = Token("string", string_val, self.current_line, start_column)
                current_line_tokens.append(token)
                continue

            # Arrow '->' or minus '-'
            if byte == 45:  # '-'
                token_col = self.current_column
                self.index += 1
                self.current_column += 1
                if self.peek_byte() == 62:  # '>'
                    self.index += 1
                    self.current_column += 1
                    token = Token("operator", "->", self.current_line, token_col)
                    current_line_tokens.append(token)
                    continue
                else:
                    token = Token("operator", "-", self.current_line, token_col)
                    current_line_tokens.append(token)
                    continue

            if byte in (43, 42):
                token = Token("operator", chr(byte), self.current_line, self.current_column)
                current_line_tokens.append(token)
                self.index += 1
                self.current_column += 1
                continue

            if byte == 61:  # '='
                token_col = self.current_column
                self.index += 1
                self.current_column += 1
                next_byte = self.peek_byte()
                if next_byte == 61:
                    token = Token("operator", "==", self.current_line, token_col)
                    current_line_tokens.append(token)
                    self.index += 1
                    self.current_column += 1
                    continue
                else:
                    self.error(self.current_line, token_col, "expected '=='")

            if byte == 33:  # '!'
                token_col = self.current_column
                self.index += 1
                self.current_column += 1
                next_byte = self.peek_byte()
                if next_byte == 61:
                    token = Token("operator", "!=", self.current_line, token_col)
                    current_line_tokens.append(token)
                    self.index += 1
                    self.current_column += 1
                    continue
                else:
                    token = Token("operator", "!", self.current_line, token_col)
                    current_line_tokens.append(token)
                    continue

            if (65 <= byte <= 90) or (97 <= byte <= 122) or (byte == 95):
                start_index = self.index
                start_column = self.current_column
                while self.index < self.length:
                    current = self.data[self.index]
                    if (
                        (65 <= current <= 90)
                        or (97 <= current <= 122)
                        or (48 <= current <= 57)
                        or (current == 95)
                    ):
                        self.index += 1
                        self.current_column += 1
                    else:
                        break

                word = self.data[start_index : self.index].decode("ascii")
                token_kind = KEYWORDS.get(word, "identifier")
                token = Token(token_kind, word, self.current_line, start_column)
                current_line_tokens.append(token)
                continue

            if 48 <= byte <= 57:
                start_index = self.index
                start_column = self.current_column
                while self.index < self.length and 48 <= self.data[self.index] <= 57:
                    self.index += 1
                    self.current_column += 1

                if self.index < self.length:
                    following_byte = self.data[self.index]
                    if (65 <= following_byte <= 90) or (97 <= following_byte <= 122) or (following_byte == 95):
                        self.error(self.current_line, self.current_column, "letter in number")

                constant_str = self.data[start_index : self.index].decode("ascii")

                if int(constant_str) > MAX_64BIT_INT:
                    self.error(
                        self.current_line,
                        start_column,
                        f"integer overflow: value {constant_str} exceeds 64-bit integer limit",
                    )

                token = Token("constant", constant_str, self.current_line, start_column)
                current_line_tokens.append(token)
                continue

            try:
                char_repr = chr(byte)
            except Exception:
                char_repr = f"\\x{byte:02x}"
            self.error(self.current_line, self.current_column, f"bad byte '{char_repr}'")

        if current_line_tokens:
            lines.append(current_line_tokens)

        return lines


def lex(source_bytes: bytes) -> List[List[Token]]:
    return Lexer(source_bytes).tokenize()
