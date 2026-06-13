from enum import IntEnum, auto



IN_PORT = 0xFFFFFE
OUT_PORT = 0xFFFFFF

MAX_STACK_DEPTH = 1024
MAX_TICKS = 5_000_000


class MicroOp(IntEnum):
    AR_LATCH_PC = auto()
    AR_LATCH_IR_ARG = auto()
    AR_LATCH_A = auto()
    AR_LATCH_B = auto()
    AR_LATCH_IN_PORT = auto()
    AR_LATCH_OUT_PORT = auto()
    IR_FROM_MEM_PC = auto()
    DS_PUSH_FROM_MEM = auto()
    MEM_FROM_DS = auto()
    A_LATCH_IR_ARG = auto()
    A_INC = auto()
    B_LATCH_IR_ARG = auto()
    B_INC = auto()
    DS_PUSH_IR_ARG = auto()
    DS_DUP = auto()
    DS_POP = auto()
    DS_SWAP = auto()
    ALU_ADD = auto()
    ALU_SUB = auto()
    ALU_MUL = auto()
    ALU_DIV = auto()
    ALU_MOD = auto()
    ALU_EQ = auto()
    ALU_LT = auto()
    ALU_GT = auto()
    ALU_TEST_ZERO = auto()
    PC_LATCH_IR_ARG = auto()
    PC_LATCH_RS_POP = auto()
    PC_JZ_IR_ARG = auto()
    RS_PUSH_PC = auto()
    RS_PUSH_FROM_DS = auto()
    DS_PUSH_FROM_RS = auto()
    DS_PUSH_FROM_PORT_IN = auto()
    PORT_OUT_FROM_DS = auto()
    PORT_OUT_INT_FROM_DS = auto()
    HALT = auto()


class StopSignal(Exception):
    pass



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
    RS_PUSH = 0x34
    RS_POP = 0x35

    IN = 0x40
    OUT = 0x41

    DUP = 0x50
    POP = 0x51
    SWAP = 0x52

    PRINT_STR = 0x60
    PRINT_INT = 0x61

    HALT = 0xFF


MC = {
    Opcode.PUSH: [MicroOp.DS_PUSH_IR_ARG],

    Opcode.LOAD: [MicroOp.AR_LATCH_IR_ARG,
                  MicroOp.DS_PUSH_FROM_MEM],

    Opcode.STORE: [MicroOp.AR_LATCH_IR_ARG,
                   MicroOp.MEM_FROM_DS],

    Opcode.ADD: [MicroOp.ALU_ADD],
    Opcode.SUB: [MicroOp.ALU_SUB],
    Opcode.MUL: [MicroOp.ALU_MUL],
    Opcode.DIV: [MicroOp.ALU_DIV],
    Opcode.MOD: [MicroOp.ALU_MOD],
    Opcode.EQ: [MicroOp.ALU_EQ],
    Opcode.LT: [MicroOp.ALU_LT],
    Opcode.GT: [MicroOp.ALU_GT],

    Opcode.JMP: [MicroOp.PC_LATCH_IR_ARG],

    Opcode.JZ: [MicroOp.ALU_TEST_ZERO,
                MicroOp.PC_JZ_IR_ARG],

    Opcode.CALL: [MicroOp.RS_PUSH_PC,
                  MicroOp.PC_LATCH_IR_ARG],

    Opcode.RET: [MicroOp.PC_LATCH_RS_POP],

    Opcode.RS_PUSH: [MicroOp.RS_PUSH_FROM_DS],
    Opcode.RS_POP:  [MicroOp.DS_PUSH_FROM_RS],

    Opcode.IN: [MicroOp.AR_LATCH_IN_PORT,
                MicroOp.DS_PUSH_FROM_PORT_IN],

    Opcode.OUT: [MicroOp.AR_LATCH_OUT_PORT,
                 MicroOp.PORT_OUT_FROM_DS],

    Opcode.DUP: [MicroOp.DS_DUP],
    Opcode.POP: [MicroOp.DS_POP],
    Opcode.SWAP: [MicroOp.DS_SWAP],

    Opcode.PRINT_STR: [MicroOp.A_LATCH_IR_ARG],
    Opcode.PRINT_INT: [MicroOp.PORT_OUT_INT_FROM_DS],

    Opcode.HALT: [MicroOp.HALT],
}