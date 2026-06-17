from enum import IntEnum

IN_PORT = 0x7FFFFE
OUT_PORT = 0x7FFFFF

MAX_STACK_DEPTH = 1024
MAX_TICKS = 5_000_000


class StopSignal(Exception):
    pass


class Opcode(IntEnum):
    PUSH = 0x01
    LOAD = 0x02
    STORE = 0x03
    LOAD_IND = 0x04

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
    RS_PUSH = 0x34
    RS_POP = 0x35

    DUP = 0x50
    POP = 0x51

    HALT = 0xFF


class Cond(IntEnum):
    SEQ = 0
    NEXT = 1
    DISPATCH = 2
    IF_C = 3
    IF_NC = 4


class ArSel(IntEnum):
    NONE = 0
    PC = 1
    ARG = 2
    DS = 3


class DsOp(IntEnum):
    NONE = 0
    PUSH_MEM = 1
    POP_MEM = 2
    PUSH_ARG = 3
    DUP = 4
    POP = 5
    PUSH_RS = 7


class RsOp(IntEnum):
    NONE = 0
    PUSH_PC = 1
    PUSH_DS = 2


class PcOp(IntEnum):
    NONE = 0
    ARG = 1
    RS = 2
    ARG_IF_C = 3


class AluOp(IntEnum):
    NONE = 0
    ADD = 1
    SUB = 2
    MUL = 3
    DIV = 4
    MOD = 5
    EQ = 6
    LT = 7
    GT = 8
    TEST_ZERO = 9


_FIELDS = {
    "next_addr": (0, 0x3F),
    "cond": (6, 0x7),
    "alu_op": (9, 0xF),
    "ar_sel": (13, 0x7),
    "ds_op": (16, 0x7),
    "rs_op": (19, 0x3),
    "pc_op": (21, 0x3),
    "fetch": (23, 0x1),
    "halt": (24, 0x1),
}


def encode_u(**fields) -> int:
    word = 0
    for name, value in fields.items():
        shift, mask = _FIELDS[name]
        word |= (int(value) & mask) << shift
    return word


def decode_u(word: int) -> dict:
    return {name: (word >> shift) & mask
            for name, (shift, mask) in _FIELDS.items()}


class _MicroAsm:
    def __init__(self) -> None:
        self.words: list[tuple] = []
        self.labels: dict[str, int] = {}
        self.op_start: dict[int, int] = {}

    def label(self, name: str) -> None:
        self.labels[name] = len(self.words)

    def op(self, opcode: int) -> None:
        self.op_start[int(opcode)] = len(self.words)

    def emit(self, *, target: str | None = None, **fields) -> None:
        self.words.append((fields, target))

    def assemble(self) -> tuple[list[int], dict[int, int]]:
        rom: list[int] = []
        for fields, target in self.words:
            if target is not None:
                fields = dict(fields, next_addr=self.labels[target])
            rom.append(encode_u(**fields))
        return rom, dict(self.op_start)


def _build_microcode() -> tuple[list[int], dict[int, int]]:
    a = _MicroAsm()

    a.label("FETCH")
    a.emit(ar_sel=ArSel.PC, cond=Cond.SEQ)      # такт 1: AR <- PC (защёлка адреса)
    a.emit(fetch=1, cond=Cond.DISPATCH)         # такт 2: IR <- mem[AR], PC <- PC+1

    end = {"cond": Cond.NEXT, "target": "FETCH"}

    a.op(Opcode.PUSH)
    a.emit(ds_op=DsOp.PUSH_ARG, **end)

    a.op(Opcode.LOAD)
    a.emit(ar_sel=ArSel.ARG)
    a.emit(ds_op=DsOp.PUSH_MEM, **end)

    a.op(Opcode.STORE)
    a.emit(ar_sel=ArSel.ARG)
    a.emit(ds_op=DsOp.POP_MEM, **end)

    a.op(Opcode.LOAD_IND)
    a.emit(ar_sel=ArSel.DS, ds_op=DsOp.POP)
    a.emit(ds_op=DsOp.PUSH_MEM, **end)

    for opcode, alu in (
            (Opcode.ADD, AluOp.ADD), (Opcode.SUB, AluOp.SUB),
            (Opcode.MUL, AluOp.MUL), (Opcode.DIV, AluOp.DIV),
            (Opcode.MOD, AluOp.MOD), (Opcode.EQ, AluOp.EQ),
            (Opcode.LT, AluOp.LT), (Opcode.GT, AluOp.GT),
    ):
        a.op(opcode)
        a.emit(alu_op=alu, **end)

    a.op(Opcode.JMP)
    a.emit(pc_op=PcOp.ARG, **end)

    a.op(Opcode.JZ)
    a.emit(alu_op=AluOp.TEST_ZERO)
    a.emit(pc_op=PcOp.ARG_IF_C, **end)

    a.op(Opcode.CALL)
    a.emit(rs_op=RsOp.PUSH_PC)
    a.emit(pc_op=PcOp.ARG, **end)

    a.op(Opcode.RET)
    a.emit(pc_op=PcOp.RS, **end)

    a.op(Opcode.RS_PUSH)
    a.emit(rs_op=RsOp.PUSH_DS, **end)

    a.op(Opcode.RS_POP)
    a.emit(ds_op=DsOp.PUSH_RS, **end)

    a.op(Opcode.DUP)
    a.emit(ds_op=DsOp.DUP, **end)

    a.op(Opcode.POP)
    a.emit(ds_op=DsOp.POP, **end)

    a.op(Opcode.HALT)
    a.emit(halt=1)

    return a.assemble()


ROM, OPCODE_TO_UADDR = _build_microcode()
