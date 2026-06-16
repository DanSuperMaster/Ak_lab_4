import struct
from typing import Optional

from machine.datapath import DataPath
from common import (
    MAX_TICKS, StopSignal,
    ROM, OPCODE_TO_UADDR, decode_u,
    Cond, ArSel, DsOp, RsOp, RegOp, PcOp, AluOp,
)
from utils.isa import decode_instruction, OPCODE_NAMES


class ControlUnit:
    def __init__(self, datapath: DataPath, *, log: bool = True,
                 max_print_str: int = 4096) -> None:
        self.dp = datapath
        self.upc = 0
        self.tick = 0
        self.instr_count = 0
        self._log = log
        self.journal: list[str] = []
        self.max_print_str = max_print_str
        self.stop_reason: str | None = None

    def _log_msg(self, stage: str, detail: str, with_state: bool = True) -> None:
        if not self._log:
            return
        if with_state:
            ds = self.dp.data_stack.snapshot(4)
            rs = self.dp.return_stack.snapshot(2)
            line = (
                f"tick={self.tick:6d} | uPC={self.upc:02d} PC={self.dp.pc:04d} "
                f"AR={self.dp.ar:04x} A={self.dp.a:04x} B={self.dp.b:04x} "
                f"C={self.dp.alu.c} "
                f"DS={ds} RS={rs} | {stage:7s} | {detail}"
            )
        else:
            line = f"tick={self.tick:6d} | {stage:7s} | {detail}"
        self.journal.append(line)

    def _do_fetch(self) -> None:
        dp = self.dp
        pc = dp.pc
        if pc < 0 or pc >= len(dp.memory):
            raise IndexError(f"PC={pc} за пределами памяти")
        dp.ar = pc
        raw = dp.memory[pc]
        opcode, arg = decode_instruction(struct.pack(">I", raw & 0xFFFFFFFF))
        dp.ir_opcode = opcode
        dp.ir_arg = arg
        dp.pc = pc + 1
        self.instr_count += 1
        mn = OPCODE_NAMES.get(opcode, f"0x{opcode:02X}")
        self._log_msg("FETCH", f"{mn}({arg}) @ {pc}")

    def _exec_word(self, m: dict) -> int:
        dp = self.dp
        upc = self.upc
        mn = OPCODE_NAMES.get(dp.ir_opcode, f"0x{dp.ir_opcode:02X}")

        if m["fetch"]:
            self._do_fetch()
            mn = OPCODE_NAMES.get(dp.ir_opcode, f"0x{dp.ir_opcode:02X}")

        ar_sel = m["ar_sel"]
        if ar_sel == ArSel.PC:
            dp.ar = dp.pc
        elif ar_sel == ArSel.ARG:
            dp.ar = dp.ir_arg
        elif ar_sel == ArSel.A:
            dp.ar = dp.a
        elif ar_sel == ArSel.B:
            dp.ar = dp.b
        elif ar_sel == ArSel.DS:
            dp.ar = dp.data_stack.peek()

        reg_op = m["reg_op"]
        if reg_op == RegOp.A_ARG:
            dp.a = dp.ir_arg
        elif reg_op == RegOp.A_INC:
            dp.a += 1
        elif reg_op == RegOp.B_ARG:
            dp.b = dp.ir_arg
        elif reg_op == RegOp.B_INC:
            dp.b += 1

        ds_op = m["ds_op"]
        if ds_op == DsOp.PUSH_MEM:
            dp.data_stack.push(dp.mem_read(dp.ar))
        elif ds_op == DsOp.POP_MEM:
            dp.mem_write(dp.ar, dp.data_stack.pop())
        elif ds_op == DsOp.PUSH_ARG:
            dp.data_stack.push(dp.ir_arg)
        elif ds_op == DsOp.DUP:
            dp.data_stack.push(dp.data_stack.peek())
        elif ds_op == DsOp.POP:
            dp.data_stack.pop()
        elif ds_op == DsOp.SWAP:
            x = dp.data_stack.pop()
            y = dp.data_stack.pop()
            dp.data_stack.push(x)
            dp.data_stack.push(y)
        elif ds_op == DsOp.PUSH_RS:
            dp.data_stack.push(dp.return_stack.pop())

        alu_op = m["alu_op"]
        if alu_op == AluOp.TEST_ZERO:
            v = dp.data_stack.pop()
            dp.alu.test_zero(v)
        elif alu_op != AluOp.NONE:
            right = dp.data_stack.pop()
            left = dp.data_stack.pop()
            r = dp.alu.binop(alu_op, left, right)
            dp.data_stack.push(r)

        rs_op = m["rs_op"]
        if rs_op == RsOp.PUSH_PC:
            dp.return_stack.push(dp.pc)
        elif rs_op == RsOp.PUSH_DS:
            dp.return_stack.push(dp.data_stack.pop())

        pc_op = m["pc_op"]
        if pc_op == PcOp.ARG:
            dp.pc = dp.ir_arg
        elif pc_op == PcOp.RS:
            dp.pc = dp.return_stack.pop()
        elif pc_op == PcOp.ARG_IF_C:
            if dp.alu.c == 1:
                dp.pc = dp.ir_arg

        if m["halt"]:
            dp.halted = True
            self._log_msg("EXEC", f"{mn}: HALT", with_state=False)
            raise StopSignal("HALT")

        if not m["fetch"]:
            self._log_msg("EXEC", f"{mn}: {self._fmt_signals(m)}")

        cond = m["cond"]
        if cond == Cond.SEQ:
            return upc + 1
        if cond == Cond.NEXT:
            return m["next_addr"]
        if cond == Cond.DISPATCH:
            try:
                return OPCODE_TO_UADDR[dp.ir_opcode]
            except KeyError:
                raise ValueError(f"Неизвестный опкод: 0x{dp.ir_opcode:02X}")
        if cond == Cond.IF_C:
            return m["next_addr"] if dp.alu.c == 1 else upc + 1
        if cond == Cond.IF_NC:
            return m["next_addr"] if dp.alu.c == 0 else upc + 1
        raise ValueError(f"Неизвестный cond={cond}")

    @staticmethod
    def _fmt_signals(m: dict) -> str:
        active = [f"{k}={v}" for k, v in m.items()
                  if v and k not in ("cond", "next_addr")]
        return " ".join(active) if active else "(нет сигналов)"

    def run(self) -> None:
        while not self.dp.halted and self.tick < MAX_TICKS:
            self.tick += 1
            m = decode_u(ROM[self.upc])
            try:
                self.upc = self._exec_word(m)
            except StopSignal as exc:
                self.stop_reason = str(exc)
                break
            except (IndexError, OverflowError, ZeroDivisionError, ValueError) as exc:
                self.stop_reason = f"ERROR: {exc}"
                self._log_msg("ERROR", str(exc), with_state=False)
                break

        if self.tick >= MAX_TICKS:
            self.stop_reason = f"Достигнут лимит тактов ({MAX_TICKS})"
            self._log_msg("WARN", self.stop_reason, with_state=False)

        self._log_msg("STOP", self.stop_reason or "завершено", with_state=False)
