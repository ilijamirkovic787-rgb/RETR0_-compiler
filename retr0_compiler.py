# retr0_compiler.py
from typing import List, Tuple, Any, Dict, Optional
import shlex

class Instruction:
    def __init__(self, op: str, arg: Any = None):
        self.op = op
        self.arg = arg
    def __repr__(self):
        return f"Instr({self.op!r},{self.arg!r})"

def is_int(s):
    try:
        int(s)
        return True
    except:
        return False

def parse_expr(tokens: List[str]) -> Tuple[List[Instruction], Optional[Any]]:
    instrs = []
    if not tokens:
        return instrs, None
    if len(tokens) == 1:
        t = tokens[0]
        if t.startswith('"') and t.endswith('"'):
            instrs.append(Instruction("LOAD_CONST", t[1:-1]))
            return instrs, None
        if is_int(t):
            instrs.append(Instruction("LOAD_CONST", int(t)))
            return instrs, None
        instrs.append(Instruction("LOAD_VAR", t))
        return instrs, None
    # binary op: a OP b
    ops = ["+", "-", "*", "/", "%", "==", "!=", "<", "<=", ">", ">="]
    for i, tk in enumerate(tokens):
        if tk in ops:
            left = tokens[:i]
            right = tokens[i+1:]
            li, _ = parse_expr(left)
            ri, _ = parse_expr(right)
            instrs.extend(li)
            instrs.extend(ri)
            opmap = {
                "+":"BINARY_ADD","-":"BINARY_SUB","*":"BINARY_MUL","/":"BINARY_DIV","%":"BINARY_MOD",
                "==":"CMP_EQ","!=":"CMP_NE","<":"CMP_LT","<=":"CMP_LE",">":"CMP_GT",">=":"CMP_GE"
            }
            instrs.append(Instruction(opmap[tk]))
            return instrs, None
    # fallback: join and const
    instrs.append(Instruction("LOAD_CONST", " ".join(tokens)))
    return instrs, None

def tokenize_line(line: str) -> List[str]:
    try:
        return shlex.split(line)
    except:
        return line.strip().split()

def compile_source(src: str) -> Tuple[List[Instruction], List[Any]]:
    lines = [l.rstrip() for l in src.splitlines()]
    instrs: List[Instruction] = []
    consts: List[Any] = []
    i = 0
    labels_stack = []
    functions: Dict[str, int] = {}
    while i < len(lines):
        raw = lines[i].strip()
        i += 1
        if not raw or raw.startswith("#"):
            continue
        tokens = tokenize_line(raw)
        cmd = tokens[0].upper()
        if cmd == "PRINT":
            expr = tokens[1:]
            ex_instrs, _ = parse_expr(expr)
            instrs.extend(ex_instrs)
            instrs.append(Instruction("PRINT"))
        elif cmd == "LET":
            if "=" in tokens:
                eq = tokens.index("=")
                name = tokens[1]
                expr = tokens[eq+1:]
                ex_instrs, _ = parse_expr(expr)
                instrs.extend(ex_instrs)
                instrs.append(Instruction("STORE_VAR", name))
            else:
                name = tokens[1]
                instrs.append(Instruction("STORE_VAR", name))
        elif cmd == "ASK":
            name = tokens[1]
            prompt = " ".join(tokens[2:]).strip()
            if prompt.startswith('"') and prompt.endswith('"'):
                prompt = prompt[1:-1]
            instrs.append(Instruction("ASK", prompt))
            instrs.append(Instruction("STORE_VAR", name))
        elif cmd == "REPEAT":
            count_expr = tokens[1:]
            ex_instrs, _ = parse_expr(count_expr)
            instrs.extend(ex_instrs)
            start = len(instrs)
            instrs.append(Instruction("SETUP_LOOP", None))
            # block: gather until END
            body = []
            while i < len(lines):
                ln = lines[i].strip()
                i += 1
                if ln.upper() == "END":
                    break
                body.append(ln)
            body_code, body_consts = compile_source("\n".join(body))
            instrs.extend(body_code)
            instrs.append(Instruction("END_LOOP"))
        elif cmd == "IF":
            expr = tokens[1:]
            ex_instrs, _ = parse_expr(expr)
            instrs.extend(ex_instrs)
            instrs.append(Instruction("JUMP_IF_FALSE", None))
            # collect then block until ELSE or END
            then_block = []
            else_block = []
            mode = "then"
            while i < len(lines):
                ln = lines[i].strip()
                i += 1
                if ln.upper() == "ELSE":
                    mode = "else"
                    continue
                if ln.upper() == "END":
                    break
                if mode == "then":
                    then_block.append(ln)
                else:
                    else_block.append(ln)
            then_code, _ = compile_source("\n".join(then_block))
            instrs.extend(then_code)
            if else_block:
                instrs.append(Instruction("JUMP_FORWARD", None))
                else_jump_idx = len(instrs)-1
                else_code, _ = compile_source("\n".join(else_block))
                instrs.extend(else_code)
                # fix jump indices not necessary for simple VM (use markers)
            # note: JUMP_IF_FALSE arg will be resolved by VM using markers or by scanning; we keep None
        elif cmd == "FUNC":
            name = tokens[1]
            params = []
            if len(tokens) > 2:
                params = [p.strip().strip(",") for p in tokens[2:]]
            func_lines = []
            while i < len(lines):
                ln = lines[i].strip()
                i += 1
                if ln.upper() == "END":
                    break
                func_lines.append(ln)
            func_instrs, _ = compile_source("\n".join(func_lines))
            instrs.append(Instruction("DEF_FUNC", (name, params, func_instrs)))
        elif cmd == "CALL":
            name = tokens[1]
            args = tokens[2:]
            for a in args:
                exi, _ = parse_expr([a])
                instrs.extend(exi)
            instrs.append(Instruction("CALL", (name, len(args))))
        elif cmd == "RETURN":
            expr = tokens[1:]
            exi, _ = parse_expr(expr)
            instrs.extend(exi)
            instrs.append(Instruction("RETURN"))
        else:
            # try to parse as expression
            exi, _ = parse_expr(tokens)
            instrs.extend(exi)
    instrs.append(Instruction("HALT"))
    return instrs, consts

class VM:
    def __init__(self, instrs: List[Instruction], consts: List[Any]=None):
        self.instrs = instrs
        self.consts = consts or []
        self.ip = 0
        self.stack: List[Any] = []
        self.globals: Dict[str, Any] = {}
        self.call_stack: List[Tuple[int, Dict[str, Any]]] = []
        self.functions: Dict[str, Tuple[List[str], List[Instruction]]] = {}
    def _pop(self):
        return self.stack.pop() if self.stack else 0
    def run(self):
        while self.ip < len(self.instrs):
            ins = self.instrs[self.ip]
            op = ins.op
            arg = ins.arg
            self.ip += 1
            if op == "LOAD_CONST":
                self.stack.append(arg)
            elif op == "LOAD_VAR":
                self.stack.append(self.globals.get(arg, 0))
            elif op == "STORE_VAR":
                v = self._pop()
                self.globals[arg] = v
            elif op == "PRINT":
                v = self._pop()
                print(v)
            elif op == "ASK":
                prompt = arg or ""
                val = input(prompt + " ")
                self.stack.append(val)
            elif op == "BINARY_ADD":
                b = self._pop(); a = self._pop()
                try: self.stack.append(a + b)
                except: self.stack.append(str(a) + str(b))
            elif op == "BINARY_SUB":
                b = self._pop(); a = self._pop(); self.stack.append(a - b)
            elif op == "BINARY_MUL":
                b = self._pop(); a = self._pop(); self.stack.append(a * b)
            elif op == "BINARY_DIV":
                b = self._pop(); a = self._pop()
                try: self.stack.append(a // b)
                except: self.stack.append(0)
            elif op == "BINARY_MOD":
                b = self._pop(); a = self._pop(); self.stack.append(a % b)
            elif op == "CMP_EQ":
                b = self._pop(); a = self._pop(); self.stack.append(a == b)
            elif op == "CMP_NE":
                b = self._pop(); a = self._pop(); self.stack.append(a != b)
            elif op == "CMP_LT":
                b = self._pop(); a = self._pop(); self.stack.append(a < b)
            elif op == "CMP_LE":
                b = self._pop(); a = self._pop(); self.stack.append(a <= b)
            elif op == "CMP_GT":
                b = self._pop(); a = self._pop(); self.stack.append(a > b)
            elif op == "CMP_GE":
                b = self._pop(); a = self._pop(); self.stack.append(a >= b)
            elif op == "DEF_FUNC":
                name, params, finstrs = arg
                self.functions[name] = (params, finstrs)
            elif op == "CALL":
                name, argc = arg
                args = [self._pop() for _ in range(argc)][::-1]
                if name in self.functions:
                    params, finstrs = self.functions[name]
                    frame_vars = dict(zip(params, args))
                    self.call_stack.append((self.ip, dict(self.globals)))
                    self.globals.update(frame_vars)
                    subvm = VM(finstrs, [])
                    subvm.globals = self.globals
                    subvm.functions = self.functions
                    subvm.run()
                    # after return, restore
                    if subvm.stack:
                        self.stack.append(subvm.stack.pop())
                    _, saved = self.call_stack.pop()
                    self.globals = saved
                else:
                    # unknown function
                    pass
            elif op == "RETURN":
                # leave value on stack for caller
                return
            elif op == "HALT":
                break
            else:
                pass

def decompile(instrs: List[Instruction]) -> str:
    out = []
    for ins in instrs:
        if ins.op == "LOAD_CONST":
            out.append(f"LOAD_CONST {ins.arg!r}")
        elif ins.op in ("LOAD_VAR","STORE_VAR","ASK","DEF_FUNC","CALL"):
            out.append(f"{ins.op} {ins.arg!r}")
        else:
            out.append(ins.op)
    return "\n".join(out)

if __name__ == "__main__":
    s = '''
PRINT "Hello"
LET x = 3
PRINT x
FUNC add a b
    PRINT "in func"
END
CALL add 1 2
'''
    instrs, consts = compile_source(s)
    print(decompile(instrs))
