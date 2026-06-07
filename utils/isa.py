import struct
from enum import IntEnum

IN_PORT = 0xFFFFFE
OUT_PORT = 0xFFFFFF

WORD_SIZE = 32
INSTRUCTION_SIZE = 4
ARG_MASK = 0x00FFFFFF
ARG_SIGN_BIT = 0x800000


class Opcode(IntEnum):
    PUSH = 0x01
    LOAD = 0x02
    STORE = 0x03

    ADD = 0x10
    SUB = 0x11
    MUL = 0x12
    DIV = 0x13
    MOD = 0x14

    EQ = 0x20
    LT = 0x21
    GT = 0x22

    JMP = 0x30
    JZ = 0x31
    CALL = 0x32
    RET = 0x33

    IN = 0x40
    OUT = 0x41

    DUP = 0x50
    POP = 0x51
    SWAP = 0x52

    PRINT_STR = 0x60

    HALT = 0xFF


OPCODE_NAMES: dict[int, str] = {op.value: op.name for op in Opcode}
OPCODE_BY_NAME: dict[str, int] = {op.name: op.value for op in Opcode}


def encode_instruction(opcode: int, arg: int = 0) -> bytes:
    arg_24 = arg & ARG_MASK
    word = (opcode << 24) | arg_24
    return struct.pack(">I", word)


def decode_instruction(data: bytes) -> tuple[int, int]:
    word = struct.unpack(">I", data)[0]
    opcode = (word >> 24) & 0xFF
    arg = word & ARG_MASK
    if arg & ARG_SIGN_BIT:
        arg -= (1 << 24)
    return opcode, arg


def write_binary(code: list[tuple], data_section: list[int], path: str) -> None:
    with open(path, "wb") as f:
        f.write(struct.pack(">I", len(code)))
        f.write(struct.pack(">I", len(data_section)))
        for instr in code:
            opcode = instr[0]
            arg = instr[1] if len(instr) > 1 else 0
            if isinstance(opcode, str):
                op_int = OPCODE_BY_NAME[opcode]
            else:
                op_int = int(opcode)
            f.write(encode_instruction(op_int, arg))
        for word in data_section:
            f.write(struct.pack(">i", word))


def read_binary(path: str) -> tuple[list[tuple[int, int]], list[int]]:
    with open(path, "rb") as f:
        n_instr = struct.unpack(">I", f.read(4))[0]
        n_data = struct.unpack(">I", f.read(4))[0]
        instructions: list[tuple[int, int]] = []
        for _ in range(n_instr):
            raw = f.read(4)
            instructions.append(decode_instruction(raw))
        data_section: list[int] = []
        for _ in range(n_data):
            raw = f.read(4)
            data_section.append(struct.unpack(">i", raw)[0])
    return instructions, data_section


def dump_text(code: list[tuple], data_section: list[int], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("=== Instruction memory ===\n")
        for i, instr in enumerate(code):
            opcode_raw = instr[0]
            arg = instr[1] if len(instr) > 1 else 0
            if isinstance(opcode_raw, str):
                op_int = OPCODE_BY_NAME.get(opcode_raw, 0)
                mnemonic = opcode_raw
            else:
                op_int = int(opcode_raw)
                mnemonic = OPCODE_NAMES.get(op_int, f"0x{op_int:02X}")
            raw = encode_instruction(op_int, arg)
            hex_code = raw.hex().upper()
            if arg != 0:
                f.write(f"{i * 4:04d} - {hex_code} - {mnemonic} {arg}\n")
            else:
                f.write(f"{i * 4:04d} - {hex_code} - {mnemonic}\n")
        f.write("\n=== Data memory ===\n")
        for i, word in enumerate(data_section):
            f.write(f"{i * 4:04d} - {word}\n")
