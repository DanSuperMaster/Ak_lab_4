import struct

from common import IN_PORT, StopSignal, OUT_PORT, ArSel, PcSel, SpDelta, TosSel, AluOp, AluSel
from machine.ALU import ALU
from machine.stack import Stack
from utils.isa import decode_instruction, OPCODE_NAMES


class DataPath:
    memory: list[int]
    pc: int = 0
    ir_opcode: int = 0
    ir_arg: int = 0
    ar: int = 0
    c: int = 0

    def __init__(self, memory: list[int], input_buffer: list[int] | None = None):
        self.memory = memory
        self.pc = 0
        self.ar = 0
        self.c = 0
        self.data_stack = Stack("DS")
        self.return_stack = Stack("RS")
        self.alu = ALU()
        self.input_buffer = list(input_buffer or [])
        self.output_buffer: list[int] = []
        self.halted = False

        # Выходы регистров, зафиксированные на текущем такте

        self.pc_o = 0
        self.tos_o = 0
        self.nos_o = 0
        self.rs_o = 0

        self.alu_out = 0
        self.alu_carry = 0

    def start_cycle(self) -> None:

        ds, rs = self.data_stack, self.return_stack
        self.pc_o = self.pc
        self.tos_o = ds.peek(0) if len(ds) >= 1 else 0
        self.nos_o = ds.peek(1) if len(ds) >= 2 else 0
        self.rs_o = rs.peek(0) if len(rs) >= 1 else 0


    def mem_read(self, addr: int) -> int:
        if addr == IN_PORT:
            if not self.input_buffer:
                raise StopSignal("Конец входного буфера")
            return self.input_buffer.pop(0)
        if addr == OUT_PORT:
            raise ValueError("Чтение из OUT_PORT недопустимо")
        if 0 <= addr < len(self.memory):
            return self.memory[addr]
        return 0

    def mem_write(self, addr: int, value: int) -> None:
        if addr == OUT_PORT:
            self.output_buffer.append(value & 0xFFFFFFFF)
            return
        if addr == IN_PORT:
            raise ValueError("Запись в IN_PORT недопустима")
        self.memory[addr] = value

    def signal_latch_ir(self) -> int:
        self.ir_opcode, self.ir_arg = decode_instruction(struct.pack(">I", self.mem_read(self.ar) & 0xFFFFFFFF))
        return self.ir_opcode


    def signal_latch_ar(self, ar_sel: ArSel) -> None:
        if ar_sel == ArSel.PC:
            self.ar = self.pc_o
        elif ar_sel == ArSel.ARG:
            self.ar = self.ir_arg
        elif ar_sel == ArSel.DS:
            self.ar = self.tos_o

    def signal_alu(self, alu_op: AluOp, alu_sel: AluSel) -> None:
        left = 0 if alu_sel == AluSel.ZERO else self.nos_o
        self.alu_out, self.alu_carry = self.alu.binop(
            alu_op, left, self.tos_o, self.c)

    def signal_latch_c(self) -> None:
        self.c = self.alu_carry

    def signal_mem_write(self) -> None:
        self.mem_write(self.ar, self.tos_o)

    def signal_mem_read(self) -> None:
        self.mem_read(self.ar)

    def signal_latch_tos(self, tos_sel: TosSel, dsp_delta: SpDelta) -> None:
        if tos_sel == TosSel.NOS:
            new_tos = self.nos_o
        elif tos_sel == TosSel.MEM:
            new_tos = self.mem_read(self.ar)
        elif tos_sel == TosSel.ARG:
            new_tos = self.ir_arg
        elif tos_sel == TosSel.ALU:
            new_tos = self.alu_out
        else:
            new_tos = self.tos_o

        ds = self.data_stack
        if dsp_delta == SpDelta.INC:
            ds.push(new_tos)
        elif dsp_delta == SpDelta.DEC:
            ds.pop()
            if len(ds) >= 1:
                ds.set_top(new_tos)
        else:
            if len(ds) >= 1:
                ds.set_top(new_tos)

    def signal_latch_nos(self) -> None:
        self.data_stack.set_nos(self.tos_o)

    def signal_latch_rs(self, rsp_delta: SpDelta) -> None:
        if rsp_delta == SpDelta.INC:
            self.return_stack.push(self.pc_o)
        elif rsp_delta == SpDelta.DEC:
            self.return_stack.pop()

    def signal_latch_pc(self, pc_sel: PcSel) -> None:
        if pc_sel == PcSel.INC:
            self.pc = self.pc_o + 1
        elif pc_sel == PcSel.ARG:
            self.pc = self.ir_arg
        elif pc_sel == PcSel.RS:
            self.pc = self.rs_o

    def signal_halt(self) -> None:
        self.halted = True
