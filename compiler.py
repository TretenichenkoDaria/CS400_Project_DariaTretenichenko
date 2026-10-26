import sys

class token:
    def __init__(self, k, t, l, c): self.kind, self.text, self.line, self.col = k, t, l, c

def lex(data: bytes):
    lines, tokens = [], []
    state, start, line, col, i = "start", 0, 1, 1, 0

    kws = \
        {
        "🩸": "typename",
        "🫀": "typename",
        "💊": "typename",
        "infect": "mut_modifier",
        "immune": "const_modifier",
        "exit": "keyword",
        "alive": "boolean",
        "dead": "boolean",
        "survive": "keyword",
        "perish": "keyword",
        "💉": "operator",
        "⏳": "operator"
    }

    while i <= len(data):
        b = data[i] if i < len(data) else None
        if state == "start":
            if b is None:
                break
            if b in (32, 9):
                pass
            elif 65 <= b <= 90 or 97 <= b <= 122 or b == 95 or b >= 128:
                state, start = "ident", i
            elif 48 <= b <= 57:
                state, start = "number", i
            elif b == 10:
                if tokens: lines.append(tokens)
                tokens, line, col = [], line + 1, 0
            elif b in (123, 125):
                tokens.append(token("brace", chr(b), line, col))
            elif b in (43, 45, 42):
                tokens.append(token("operator", chr(b), line, col))
            elif b == 61:
                state = "eq1"
            elif b == 33:
                state = "neq1"
            else:
                sys.stderr.write(f"compilation error: line {line}:{col}: bad byte '{chr(b)}'\n")
                sys.exit(1)
        elif state == "eq1":
            if b == 61:
                tokens.append(token("operator", "==", line, col - 1));
                state = "start"
            else:
                sys.stderr.write(f"compilation error: line {line}:{col - 1}: expected '=='\n")
                sys.exit(1)
        elif state == "neq1":
            if b == 61:
                tokens.append(token("operator", "!=", line, col - 1));
                state = "start"
            else:
                tokens.append(token("operator", "!", line, col - 1))
                state = "start";
                continue
        elif state == "ident":
            if b is None or not (65 <= b <= 90 or 97 <= b <= 122 or b == 95 or 48 <= b <= 57 or b >= 128):
                w = data[start:i].decode("utf-8")
                tokens.append(token(kws.get(w, "identifier"), w, line, col - (i - start)))
                state = "start";
                continue
        elif state == "number":
            if b is not None and (65 <= b <= 90 or 97 <= b <= 122 or b == 95):
                sys.stderr.write(f"compilation error: line {line}:{col}: letter in number\n")
                sys.exit(1)
            if b is None or not (48 <= b <= 57):
                w = data[start:i].decode("ascii")
                tokens.append(token("constant", w, line, col - (i - start)))
                state = "start";
                continue
        i += 1;
        col += 1

    if tokens: lines.append(tokens)
    return lines

class programnode:
    def __init__(self, s, e): self.stmts, self.exit_node = s, e
    def dump(self, ind=""):
        print(ind + "program")
        for s in self.stmts: s.dump(ind + "  ")
        self.exit_node.dump(ind + "  ")

class declnode:
    def __init__(self, l, c, t, n, m, i):
        self.line, self.col, self.type_name, self.name, self.mut, self.init = l, c, t, n, m, i
        self.type = None
    def dump(self, ind=""):
        print(ind + f"decl {self.name} {self.type_name} {'mut' if self.mut else 'const'}")
        self.init.dump(ind + "  ")

class assignnode:
    def __init__(self, l, c, n, v):
        self.line, self.col, self.name, self.value = l, c, n, v
        self.decl = None
    def dump(self, ind=""):
        print(ind + f"assign {self.name}"); self.value.dump(ind + "  ")

class ifnode:
    def __init__(self, l, c, cond, tb, eb):
        self.line, self.col, self.cond, self.then_block, self.else_block = l, c, cond, tb, eb
    def dump(self, ind=""):
        print(ind + "if")
        self.cond.dump(ind + "  ")
        self.then_block.dump(ind + "  ")
        if self.else_block: self.else_block.dump(ind + "  ")

class blocknode:
    def __init__(self, l, c, stmts):
        self.line, self.col, self.stmts = l, c, stmts
    def dump(self, ind=""):
        print(ind + "block")
        for s in self.stmts: s.dump(ind + "  ")

class notnode:
    def __init__(self, l, c, val):
        self.line, self.col, self.val = l, c, val
    def dump(self, ind=""):
        print(ind + "not")
        self.val.dump(ind + "  ")

class exitnode:
    def __init__(self, l, c, v): self.line, self.col, self.value = l, c, v
    def dump(self, ind=""):
        print(ind + "exit"); self.value.dump(ind + "  ")

class binopnode:
    def __init__(self, l, c, o, left, right):
        self.line, self.col, self.op, self.left, self.right = l, c, o, left, right
        self.type = None
    def dump(self, ind=""):
        print(ind + f"binop {self.op}"); self.left.dump(ind + "  "); self.right.dump(ind + "  ")

class varnode:
    def __init__(self, l, c, n):
        self.line, self.col, self.name = l, c, n
        self.type, self.decl = None, None
    def dump(self, ind=""): print(ind + f"var {self.name}")

class constnode:
    def __init__(self, l, c, v):
        self.line, self.col, self.value = l, c, v
        self.type = None
    def dump(self, ind=""): print(ind + f"const {self.value}")

class boolnode:
    def __init__(self, l, c, v):
        self.line, self.col, self.value = l, c, v
        self.type = "bool"
    def dump(self, ind=""): print(ind + f"bool {self.value}")

class parser:
    def __init__(self, lines):
        self.lines = [l for l in lines if l]
        self.lpos, self.tpos = 0, 0
        self.ll, self.lc = 0, 0

    def peek(self):
        if self.lpos < len(self.lines) and self.tpos < len(self.lines[self.lpos]):
            return self.lines[self.lpos][self.tpos]
        return None

    def eat(self):
        t = self.peek()
        if t:
            self.ll, self.lc = t.line, t.col
            self.tpos += 1
        return t

    def eol(self):
        return self.lpos >= len(self.lines) or self.tpos >= len(self.lines[self.lpos])

    def next_line(self):
        if self.tpos > 0:
            self.lpos += 1
            self.tpos = 0

    def check_eol(self):
        if not self.eol():
            t = self.peek()
            sys.stderr.write(f"compilation error: line {t.line}:{t.col}: junk at end\n")
            sys.exit(1)
        self.next_line()

    def exp(self, k, m):
        t = self.peek()
        if not t or t.kind != k and t.text != m:
            l = t.line if t else self.ll
            c = t.col if t else self.lc + 1
            sys.stderr.write(f"compilation error: line {l}:{c}: expected {m}\n")
            sys.exit(1)
        return self.eat()

    def parse_program(self):
        stmts, ex = [], None
        while self.lpos < len(self.lines):
            t = self.peek()
            if ex:
                sys.stderr.write(f"compilation error: line {t.line}:{t.col}: unreachable code\n")
                sys.exit(1)
            if t and t.kind == "keyword" and t.text == "exit":
                ex = self.parse_exit()
            else:
                stmts.append(self.parse_statement())

        if not ex:
            l = self.ll if self.ll else 0
            c = self.lc if self.lc else 0
            sys.stderr.write(f"compilation error: line {l}:{c}: no exit\n")
            sys.exit(1)
        return programnode(stmts, ex)

    def parse_statement(self):
        t = self.peek()
        if t and (t.text == "infect" or t.text == "immune"):
            return self.parse_decl()
        elif t and t.kind == "identifier":
            return self.parse_assign()
        elif t and t.text == "survive":
            return self.parse_if()
        elif t and t.text == "perish":
            sys.stderr.write(f"compilation error: line {t.line}:{t.col}: 'perish' without a 'survive'\n")
            sys.exit(1)
        else:
            l = t.line if t else self.ll
            c = t.col if t else self.lc + 1
            sys.stderr.write(f"compilation error: line {l}:{c}: bad statement\n")
            sys.exit(1)

    def parse_decl(self):
        mod = self.eat()
        mut = (mod.text == "infect")

        t = self.peek()
        if not t or t.text not in ("🩸", "🫀", "💊"):
            l = t.line if t else self.ll
            c = t.col if t else self.lc + 1
            sys.stderr.write(f"compilation error: line {l}:{c}: expected type\n")
            sys.exit(1)
        self.eat()

        n = self.exp("identifier", "name")
        o = self.exp("operator", "💉")
        if o.text != "💉":
            sys.stderr.write(f"compilation error: line {o.line}:{o.col}: expected '💉'\n")
            sys.exit(1)

        i = self.parse_expr()

        e = self.exp("operator", "⏳")
        if e.text != "⏳":
            sys.stderr.write(f"compilation error: line {e.line}:{e.col}: expected '⏳'\n")
            sys.exit(1)

        self.check_eol()
        return declnode(n.line, n.col, t.text, n.text, mut, i)

    def parse_assign(self):
        n = self.exp("identifier", "name")
        o = self.exp("operator", "💉")
        if o.text != "💉":
            sys.stderr.write(f"compilation error: line {o.line}:{o.col}: expected '💉'\n")
            sys.exit(1)

        val = self.parse_expr()

        e = self.exp("operator", "⏳")
        if e.text != "⏳":
            sys.stderr.write(f"compilation error: line {e.line}:{e.col}: expected '⏳'\n")
            sys.exit(1)

        self.check_eol()
        return assignnode(n.line, n.col, n.text, val)

    def parse_if(self):
        i = self.eat()
        cond = self.parse_expr()

        t = self.peek()
        if not t or t.text != "{":
            l = t.line if t else self.ll
            c = t.col if t else self.lc + 1
            sys.stderr.write(f"compilation error: line {l}:{c}: expected '{{'\n")
            sys.exit(1)

        then_b = self.parse_block()
        else_b = None

        t = self.peek()
        if t and t.text == "perish":
            t2 = self.peek()
            if not t2 or t2.text != "{":
                l = t2.line if t2 else self.ll
                c = t2.col if t2 else self.lc + 1
                sys.stderr.write(f"compilation error: line {l}:{c}: expected '{{' after perish\n")
                sys.exit(1)
            else_b = self.parse_block()

        return ifnode(i.line, i.col, cond, then_b, else_b)

    def parse_block(self):
        lb = self.eat()
        if not self.eol():
            t = self.peek()
            sys.stderr.write(f"compilation error: line {t.line}:{t.col}: unexpected '{t.text}' after '{{'\n")
            sys.exit(1)
        self.next_line()

        stmts = []
        while self.lpos < len(self.lines):
            t = self.peek()
            if t and t.text == "}":
                break
            stmts.append(self.parse_statement())

        t = self.peek()
        if not t or t.text != "}":
            sys.stderr.write(f"compilation error: line {lb.line}:{lb.col}: '{{' is never closed\n")
            sys.exit(1)
        self.eat()

        if self.eol():
            self.next_line()

        if not stmts:
            sys.stderr.write(f"compilation error: line {lb.line}:{lb.col}: empty block\n")
            sys.exit(1)

        return blocknode(lb.line, lb.col, stmts)

    def parse_exit(self):
        e = self.eat()
        val = self.parse_expr()

        op = self.exp("operator", "⏳")
        if op.text != "⏳":
            sys.stderr.write(f"compilation error: line {op.line}:{op.col}: expected '⏳'\n")
            sys.exit(1)

        self.check_eol()
        return exitnode(e.line, e.col, val)

    def parse_expr(self):
        n = self.parse_arith()
        if self.peek() and self.peek().text in ("==", "!="):
            t = self.eat()
            n = binopnode(t.line, t.col, t.text, n, self.parse_arith())
        return n

    def parse_arith(self):
        n = self.parse_term()
        while self.peek() and self.peek().text in ("+", "-"):
            t = self.eat()
            n = binopnode(t.line, t.col, t.text, n, self.parse_term())
        return n

    def parse_term(self):
        n = self.parse_factor()
        while self.peek() and self.peek().text == "*":
            t = self.eat()
            n = binopnode(t.line, t.col, t.text, n, self.parse_factor())
        return n

    def parse_factor(self):
        t = self.peek()
        if not t:
            sys.stderr.write(f"compilation error: line {self.ll}:{self.lc + 1}: need val\n")
            sys.exit(1)
        if t.text == "!":
            op = self.eat()
            return notnode(op.line, op.col, self.parse_factor())
        if t.kind == "constant": return constnode(self.eat().line, t.col, t.text)
        if t.kind == "boolean": return boolnode(self.eat().line, t.col, t.text)
        if t.kind == "identifier": return varnode(self.eat().line, t.col, t.text)
        sys.stderr.write(f"compilation error: line {t.line}:{t.col}: bad val\n")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] != "--ast":
        sys.stderr.write("usage: python3 compiler.py --ast <input.txt>\n")
        sys.exit(1)

    with open(sys.argv[2], "rb") as f:
        data = f.read()

    tokens = lex(data)
    tree = parser(tokens).parse_program()
    tree.dump()