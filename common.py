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
    ADDC = 0x15
    SUBB = 0x16

    EQ = 0x20
    LT = 0x21
    GT = 0x22

    JMP = 0x30
    JZ = 0x31
    CALL = 0x32
    RET = 0x33

    DUP = 0x50
    POP = 0x51
    SWAP = 0x52

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
    ADDC = 10
    SUBB = 11


class TosSel(IntEnum):
    HOLD = 0
    NOS = 1
    MEM = 2
    ARG = 3
    ALU = 4


class SpDelta(IntEnum):
    HOLD = 0
    INC = 1
    DEC = 2


class PcSel(IntEnum):
    INC = 0
    ARG = 1
    RS = 2


FIELDS = {
    "next_addr": (0, 0x3F),
    "cond": (6, 0x7),
    "alu_op": (9, 0xF),
    "ar_sel": (13, 0x3),
    "tos_sel": (15, 0x7),
    "dsp_delta": (18, 0x3),
    "ds_we": (20, 0x1),
    "rsp_delta": (22, 0x3),
    "rs_we": (24, 0x1),
    "pc_sel": (25, 0x3),
    "pc_we": (27, 0x1),
    "mem_we": (28, 0x1),
    "ir_we": (29, 0x1),
    "halt": (30, 0x1),
    "ns_we": (31, 0x1),
}


def encode_u(**fields) -> int:
    word = 0
    for name, value in fields.items():
        shift, mask = FIELDS[name]
        word |= (int(value) & mask) << shift
    return word


def decode_u(word: int) -> dict:
    return {name: (word >> shift) & mask
            for name, (shift, mask) in FIELDS.items()}


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
    a.emit(ar_sel=ArSel.PC, cond=Cond.SEQ)
    a.emit(ir_we=1, pc_sel=PcSel.INC, pc_we=1, cond=Cond.DISPATCH)

    end = {"cond": Cond.NEXT, "target": "FETCH"}

    a.op(Opcode.PUSH)
    a.emit(tos_sel=TosSel.ARG, dsp_delta=SpDelta.INC, ds_we=1, **end)

    a.op(Opcode.LOAD)
    a.emit(ar_sel=ArSel.ARG, cond=Cond.SEQ)
    a.emit(tos_sel=TosSel.MEM, dsp_delta=SpDelta.INC, ds_we=1, **end)

    a.op(Opcode.STORE)
    a.emit(ar_sel=ArSel.ARG, cond=Cond.SEQ)
    a.emit(mem_we=1, tos_sel=TosSel.NOS, dsp_delta=SpDelta.DEC, **end)

    a.op(Opcode.LOAD_IND)
    a.emit(ar_sel=ArSel.DS, cond=Cond.SEQ)
    a.emit(tos_sel=TosSel.MEM, dsp_delta=SpDelta.HOLD, **end)

    for opcode, alu in (
            (Opcode.ADD, AluOp.ADD), (Opcode.SUB, AluOp.SUB),
            (Opcode.MUL, AluOp.MUL), (Opcode.DIV, AluOp.DIV),
            (Opcode.MOD, AluOp.MOD), (Opcode.EQ, AluOp.EQ),
            (Opcode.LT, AluOp.LT), (Opcode.GT, AluOp.GT),
            (Opcode.ADDC, AluOp.ADDC), (Opcode.SUBB, AluOp.SUBB),
    ):
        a.op(opcode)
        a.emit(alu_op=alu, tos_sel=TosSel.ALU, dsp_delta=SpDelta.DEC, **end)

    a.op(Opcode.JMP)
    a.emit(pc_sel=PcSel.ARG, pc_we=1, **end)

    a.op(Opcode.JZ)
    a.emit(alu_op=AluOp.TEST_ZERO, tos_sel=TosSel.NOS, dsp_delta=SpDelta.DEC,
           cond=Cond.IF_C, target="JZ_TAKE")
    a.emit(**end)
    a.label("JZ_TAKE")
    a.emit(pc_sel=PcSel.ARG, pc_we=1, **end)

    a.op(Opcode.CALL)
    a.emit(rsp_delta=SpDelta.INC, rs_we=1, cond=Cond.SEQ)
    a.emit(pc_sel=PcSel.ARG, pc_we=1, **end)

    a.op(Opcode.RET)
    a.emit(pc_sel=PcSel.RS, pc_we=1, rsp_delta=SpDelta.DEC, **end)

    a.op(Opcode.DUP)
    a.emit(tos_sel=TosSel.HOLD, dsp_delta=SpDelta.INC, ds_we=1, **end)

    a.op(Opcode.POP)
    a.emit(tos_sel=TosSel.NOS, dsp_delta=SpDelta.DEC, **end)

    a.op(Opcode.SWAP)
    a.emit(tos_sel=TosSel.NOS, ns_we=1, dsp_delta=SpDelta.HOLD, **end)

    a.op(Opcode.HALT)
    a.emit(halt=1)

    return a.assemble()


ROM, OPCODE_TO_UADDR = _build_microcode()
