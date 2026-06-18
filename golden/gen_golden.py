import argparse
import os
import struct
import tempfile

from utils.isa import (OPCODE_BY_NAME, encode_instruction, dump_text)
from utils.lexer import Lexer, Parser
from utils.compiler import Compiler
from machine.processor import Processor

HEAD_LINES = 24
MIN_TAIL_LINES = 40


def build_memory(code, data):
    memory = []
    for instr in code:
        op = instr[0]
        arg = instr[1] if len(instr) > 1 else 0
        op_int = OPCODE_BY_NAME[op] if isinstance(op, str) else int(op)
        memory.append(struct.unpack(">I", encode_instruction(op_int, arg))[0])
    data_offset = len(memory)
    memory.extend(data)
    return memory, data_offset


def dump_listing(code, data):
    fd, path = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    try:
        dump_text(code, data, path)
        with open(path, encoding="utf-8") as f:
            return f.read().rstrip("\n")
    finally:
        os.remove(path)


def trim_log(lines):
    marker = None
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith("=========="):
            marker = i
            break
    tail = MIN_TAIL_LINES
    if marker is not None:
        tail = max(MIN_TAIL_LINES, len(lines) - marker + 8)
    if len(lines) <= HEAD_LINES + tail:
        return lines
    skipped = len(lines) - HEAD_LINES - tail
    ell = f"  ...  ({skipped} строк журнала пропущено для краткости)  ..."
    return lines[:HEAD_LINES] + [ell] + lines[-tail:]


def indent(text, n=2):
    pad = " " * n
    return "\n".join(pad + line if line else pad.rstrip() for line in text.split("\n"))


def main():
    p = argparse.ArgumentParser(description="Сборка golden-теста")
    p.add_argument("--name", required=True)
    p.add_argument("--src", required=True)
    p.add_argument("--input", default="")
    p.add_argument("--input-file")
    args = p.parse_args()

    with open(args.src, encoding="utf-8") as f:
        source = f.read()

    if args.input_file:
        with open(args.input_file, encoding="utf-8") as f:
            in_str = f.read()
    else:
        in_str = args.input
    input_buffer = [ord(c) for c in in_str]

    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    compiler = Compiler()
    compiler.compile(program)
    code, data = compiler.finalize()

    listing = dump_listing(code, data)
    memory, data_offset = build_memory(code, data)

    cpu = Processor(memory, input_buffer, data_offset=data_offset, log=True)
    cpu.run()
    cpu.append_final_dump()

    out_str = cpu.get_output_str()
    out_bytes = list(cpu.dp.output_buffer)
    log = "\n".join(trim_log(cpu.cu.journal))

    yml = (
        f"# golden-тест: {args.name}\n"
        f"source: |\n{indent(source.rstrip(chr(10)))}\n\n"
        f"input: {in_str!r}\n\n"
        f"translator_output: |\n"
        f"  instructions: {len(code)}\n"
        f"  data words: {len(data)}\n\n"
        f"machine_code: |\n{indent(listing)}\n\n"
        f"machine_output: |\n{indent(out_str.rstrip(chr(10)))}\n\n"
        f"output: {out_bytes}\n"
        f"ticks: {cpu.cu.tick}\n\n"
        f"log: |\n{indent(log)}\n"
    )

    out_path = os.path.join("golden", f"{args.name}.yml")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(yml)
    print(f"golden: {out_path}  (вывод: {out_str!r}, тактов: {cpu.cu.tick})")


if __name__ == "__main__":
    main()
