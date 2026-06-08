import argparse

from utils.isa import Opcode, write_binary, dump_text
from utils.lexer import Lexer, Parser


class Compiler:
    def __init__(self):
        self.code = []
        self.variables = {}
        self.next_addr = 0
        self.data_section = []
        self.string_pool = {}
        self.functions = {}
        self._pending = []
        self.label_counter = 0

    def emit(self, opcode, arg=None):
        pos = len(self.code)
        if arg is None:
            self.code.append((opcode,))
        else:
            self.code.append((opcode, arg))
        return pos

    def new_label(self):
        label = f"L{self.label_counter}"
        self.label_counter += 1
        return label

    def alloc_var(self, name):
        if name not in self.variables:
            self.variables[name] = self.next_addr
            self.data_section.append(0)
            self.next_addr += 1
        return self.variables[name]

    def _data_arg(self, data_offset):
        return -(data_offset + 1)

    def emit_load_var(self, name):
        data_off = self.variables[name]
        pos = self.emit(Opcode.LOAD, self._data_arg(data_off))
        self._pending.append(("__data__", pos))
        return pos

    def emit_store_var(self, name):
        data_off = self.variables[name]
        pos = self.emit(Opcode.STORE, self._data_arg(data_off))
        self._pending.append(("__data__", pos))
        return pos

    def alloc_string(self, s):
        if s in self.string_pool:
            return self.string_pool[s]
        offset = len(self.data_section)
        for ch in s:
            self.data_section.append(ord(ch))
        self.data_section.append(0)
        self.string_pool[s] = offset
        return offset

    def compile(self, program):
        for expr in program:
            if isinstance(expr, list) and len(expr) >= 1:
                if str(expr[0]).upper() == "DEFUN":
                    self.functions[str(expr[1]).upper()] = None

        for expr in program:
            if isinstance(expr, list) and len(expr) >= 1 and str(expr[0]).upper() == "DEFUN":
                self._compile_defun(expr)
            else:
                self.compile_expr(expr)

        self.emit(Opcode.HALT)
        return self.code

    def compile_expr(self, expr):
        if isinstance(expr, int):
            self.emit(Opcode.PUSH, expr)
            return
        if isinstance(expr, str):
            if expr == "T":
                self.emit(Opcode.PUSH, 1)
                return

            if expr == "NIL":
                self.emit(Opcode.PUSH, 0)
                return

            if expr in self.variables:
                self.emit_load_var(expr)
                return

            raise Exception(f"Unknown symbol: {expr}")

        if not isinstance(expr, list):
            raise Exception(f"Invalid expression: {expr}")

        if len(expr) == 0:
            return

        op = str(expr[0]).upper()

        if op == '+':
            self.compile_expr(expr[1])
            self.compile_expr(expr[2])
            self.emit(Opcode.ADD)
            return

        if op == '-':
            self.compile_expr(expr[1])
            self.compile_expr(expr[2])
            self.emit(Opcode.SUB)
            return

        if op == '*':
            self.compile_expr(expr[1])
            self.compile_expr(expr[2])
            self.emit(Opcode.MUL)
            return

        if op == '/':
            self.compile_expr(expr[1])
            self.compile_expr(expr[2])
            self.emit(Opcode.DIV)
            return

        if op == '%':
            self.compile_expr(expr[1])
            self.compile_expr(expr[2])
            self.emit(Opcode.MOD)
            return

        if op == '=':
            self.compile_expr(expr[1])
            self.compile_expr(expr[2])
            self.emit(Opcode.EQ)
            return

        if op == '<':
            self.compile_expr(expr[1])
            self.compile_expr(expr[2])
            self.emit(Opcode.LT)
            return

        if op == '>':
            self.compile_expr(expr[1])
            self.compile_expr(expr[2])
            self.emit(Opcode.GT)
            return

        if op == 'SETQ':
            name = expr[1]
            value = expr[2]
            self.compile_expr(value)
            self.alloc_var(name)
            self.emit_store_var(name)
            self.emit_load_var(name)
            return

        if op == 'PRINT':
            arg = expr[1]
            if isinstance(arg, str) and arg not in ('T', 'NIL') and arg not in self.variables:
                self._compile_print_str(arg)
            else:
                self.compile_expr(arg)
                self.emit(Opcode.OUT)
            return

        if op == 'READ':
            self.emit(Opcode.IN)
            return

        if op == 'PROGN':
            for subexpr in expr[1:]:
                self.compile_expr(subexpr)
            return

        if op == 'IF':
            condition = expr[1]
            true_branch = expr[2]
            false_branch = expr[3] if len(expr) > 3 else "NIL"

            self.compile_expr(condition)

            jz_pos = len(self.code)
            self.emit(Opcode.JZ, None)

            self.compile_expr(true_branch)

            jmp_pos = len(self.code)
            self.emit(Opcode.JMP, None)

            false_addr = len(self.code)

            self.compile_expr(false_branch)

            end_addr = len(self.code)

            self.code[jz_pos] = (Opcode.JZ, false_addr)
            self.code[jmp_pos] = (Opcode.JMP, end_addr)
            return

        if op == 'WHILE':
            condition = expr[1]
            body = expr[2]
            loop_start = len(self.code)
            self.compile_expr(condition)
            jz_pos = len(self.code)
            self.emit(Opcode.JZ, None)
            self.compile_expr(body)
            self.emit(Opcode.JMP, loop_start)
            loop_end = len(self.code)

            self.code[jz_pos] = (Opcode.JZ, loop_end)
            return

        if op == 'COND':
            end_jumps = []
            clauses = expr[1:]

            for clause in clauses:
                condition = clause[0]
                body = clause[1]

                self.compile_expr(condition)

                jz_pos = len(self.code)
                self.emit(Opcode.JZ, None)

                self.compile_expr(body)

                end_jump = len(self.code)
                self.emit(Opcode.JMP, None)
                end_jumps.append(end_jump)

                next_clause = len(self.code)
                self.code[jz_pos] = (Opcode.JZ, next_clause)

            end_addr = len(self.code)

            for pos in end_jumps:
                self.code[pos] = (Opcode.JMP, end_addr)

            return

        if op == 'DEFUN':
            raise Exception("DEFUN is only allowed at the top level")


        for arg in expr[1:]:
            self.compile_expr(arg)

        if op in self.functions and self.functions[op] is not None:
            self.emit(Opcode.CALL, self.functions[op])
        else:
            pos = self.emit(Opcode.CALL, 0)
            self._pending.append((op, pos))

    def _compile_print_str(self, s):
        offset = self.alloc_string(s)
        pos = self.emit(Opcode.PRINT_STR, self._data_arg(offset))
        self._pending.append(("__data__", pos))


    def _compile_defun(self, expr):
        name = str(expr[1]).upper()
        params = [str(p) for p in expr[2]]
        body = expr[3]

        jmp_over = len(self.code)
        self.emit(Opcode.JMP, None)

        func_addr = len(self.code)
        self.functions[name] = func_addr

        for param in reversed(params):
            self.alloc_var(param)
            self.emit_store_var(param)

        self.compile_expr(body)

        self.emit(Opcode.RET)

        after_func = len(self.code)
        self.code[jmp_over] = (Opcode.JMP, after_func)


    def finalize(self):
        n_instr = len(self.code)

        for kind, pos in self._pending:
            instr = self.code[pos]
            opcode = instr[0]
            arg = instr[1] if len(instr) > 1 else 0

            if kind == '__data__':
                data_offset = -(arg + 1)
                self.code[pos] = (opcode, n_instr + data_offset)

            elif kind in self.functions:
                func_addr = self.functions[kind]
                if func_addr is None:
                    raise Exception(f"Function '{kind}' declared but never defined")
                self.code[pos] = (opcode, func_addr)

            else:
                raise Exception(
                    f"Unresolved label: '{kind}' at position {pos}. "
                    f"Known functions: {list(self.functions.keys())}"
                )

        return self.code, self.data_section



def main():
    parser = argparse.ArgumentParser(
        description="Транслятор Lisp -> стековая машина"
    )
    parser.add_argument("source", help="Исходный файл (.lisp)")
    parser.add_argument("output", help="Выходной бинарный файл (.bin)")
    parser.add_argument(
        "--dump", "-d", metavar="FILE",
        help="Записать текстовый дамп машинного кода"
    )
    args = parser.parse_args()

    with open(args.source, "r", encoding="utf-8") as f:
        source = f.read()

    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()

    compiler = Compiler()
    compiler.compile(program)
    code, data_section = compiler.finalize()

    write_binary(code, data_section, args.output)

    print(f"Compiled: {len(code)} instructions, {len(data_section)} data words")
    print(f"Output:   {args.output}")

    if args.dump:
        dump_text(code, data_section, args.dump)
        print(f"Dump:     {args.dump}")


if __name__ == "__main__":
    main()
