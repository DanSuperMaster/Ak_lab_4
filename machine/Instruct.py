from dataclasses import dataclass, field


@dataclass
class Instruction:
    pc: int = 0
    opcode: int = 0
    arg: int = 0
    state: dict = field(default_factory=dict)