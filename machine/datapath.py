from common import IN_PORT, StopSignal, OUT_PORT
from machine.ALU import ALU
from machine.stack import Stack


class DataPath:
    memory: list[int]
    pc: int = 0
    ir_opcode: int = 0
    ir_arg: int = 0
    ar: int = 0

    def __init__(self, memory: list[int], input_buffer: list[int] | None = None):
        self.memory = memory
        self.pc = 0
        self.ar = 0
        self.data_stack = Stack("DS")
        self.return_stack = Stack("RS")
        self.alu = ALU()
        self.input_buffer = list(input_buffer or [])
        self.output_buffer: list[int] = []
        self.halted = False


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
        # while addr >= len(self.memory):
        #     self.memory.extend([0] * 1024)
        self.memory[addr] = value