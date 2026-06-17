from __future__ import annotations

import os
import struct

from machine.CU import ControlUnit
from machine.datapath import DataPath
from common import ROM

try:
    from utils.isa import (
        IN_PORT, OUT_PORT, Opcode, OPCODE_NAMES,
        decode_instruction, encode_instruction, read_binary,
    )
except ImportError:
    print("isa file not exist")

MICROCODE_ROM = ROM


def read_input(src: str) -> list[int]:
    if not src:
        return []
    if os.path.isfile(src):
        with open(src, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        text = src
    return [ord(c) for c in text]


def load_program(bin_path: str) -> tuple[list[int], int]:
    instructions, data_section = read_binary(bin_path)
    memory: list[int] = []
    for op_int, arg in instructions:
        raw = encode_instruction(op_int, arg)
        memory.append(struct.unpack(">I", raw)[0])
    data_offset = len(memory)
    memory.extend(data_section)
    return memory, data_offset


class Processor:
    def __init__(self, memory: list[int], input_buffer: list[int],
                 *, data_offset: int = 0, log: bool = True) -> None:
        self.dp = DataPath(memory=list(memory),
                           input_buffer=list(input_buffer))
        self.cu = ControlUnit(self.dp, log=log)
        self.data_offset = data_offset

    def run(self) -> None:
        self.cu.run()

    def get_output_str(self) -> str:
        return "".join(chr(c & 0xFF) for c in self.dp.output_buffer)

    def append_final_dump(self) -> None:
        j = self.cu.journal
        j.append("=" * 60)
        j.append(f"stop: {self.cu.stop_reason or 'завершено'}")
        j.append(f"output_buffer: {list(self.dp.output_buffer)}")
        j.append(f"ticks: {self.cu.tick}  instructions: {self.cu.instr_count}")
        j.append("data memory dump (addr: value):")
        for addr in range(self.data_offset, len(self.dp.memory)):
            j.append(f"  [{addr:5d}] = {self.dp.memory[addr]}")

    def print_journal(self, max_lines: int = 500) -> None:
        lines = self.cu.journal
        if len(lines) > max_lines:
            half = max_lines // 2
            print(f"... журнал обрезан: {max_lines} из {len(lines)} строк ...")
            for ln in lines[:half]:
                print(ln)
            print("  ...")
            for ln in lines[-half:]:
                print(ln)
        else:
            for ln in lines:
                print(ln)

    def print_stats(self) -> None:
        print("\n=== Статистика ===")
        print(f"Тактов:       {self.cu.tick}")
        print(f"Инструкций:   {self.cu.instr_count}")
        if self.cu.instr_count:
            print(f"CPI:          {self.cu.tick / self.cu.instr_count:.2f}")
        print(f"Вывод:        {self.get_output_str()!r}")



def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Симулятор стекового процессора (STVM)")
    p.add_argument("binary", help="бинарный файл STVM")
    p.add_argument("--input", "-i", default="",
                   help="строка ввода ИЛИ путь к файлу со входом")
    p.add_argument("--log", "-l", action="store_true",
                   help="вывести полный журнал тактов")
    p.add_argument("--max-log", type=int, default=300,
                   help="максимум строк журнала (по умолчанию 300)")
    args = p.parse_args()

    input_buffer = read_input(args.input)

    memory, data_offset = load_program(args.binary)
    print(f"Загружено: {data_offset} инструкций, {len(memory) - data_offset} слов данных")
    print(f"Ввод: {''.join(chr(c) for c in input_buffer)!r}\n")

    cpu = Processor(memory, input_buffer, data_offset=data_offset, log=args.log)
    cpu.run()

    if args.log:
        cpu.append_final_dump()
        cpu.print_journal(max_lines=args.max_log)
    cpu.print_stats()


if __name__ == "__main__":
    main()
