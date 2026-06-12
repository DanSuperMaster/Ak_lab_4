from dataclasses import dataclass, field

from common import MicroOp


@dataclass
class Instruction:
    pc: int = 0
    opcode: int = 0
    arg: int = 0
    micro_ops: list[MicroOp] = field(default_factory=list)
    state: dict = field(default_factory=dict)