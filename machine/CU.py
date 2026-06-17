import struct
from typing import Optional

from machine.datapath import DataPath
from common import (
    MAX_TICKS, StopSignal,
    ROM, OPCODE_TO_UADDR, decode_u,
    Cond, ArSel, AluOp, TosSel, SpDelta, PcSel,
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

    def log_msg(self, stage: str, detail: str, with_state: bool = True) -> None:
        if not self._log:
            return
        if with_state:
            ds = self.dp.data_stack.snapshot(4)
            rs = self.dp.return_stack.snapshot(2)
            line = (
                f"tick={self.tick:6d} | uPC={self.upc:02d} PC={self.dp.pc:04d} "
                f"AR={self.dp.ar:04x} "
                f"C={self.dp.alu.c} "
                f"DS={ds} RS={rs} | {stage:7s} | {detail}"
            )
        else:
            line = f"tick={self.tick:6d} | {stage:7s} | {detail}"
        self.journal.append(line)

    def do_fetch(self) -> None:
        dp = self.dp
        addr = dp.ar
        if addr < 0 or addr >= len(dp.memory):
            raise IndexError(f"AR={addr} за пределами памяти")
        raw = dp.memory[addr]
        opcode, arg = decode_instruction(struct.pack(">I", raw & 0xFFFFFFFF))
        dp.ir_opcode = opcode
        dp.ir_arg = arg
        self.instr_count += 1
        mn = OPCODE_NAMES.get(opcode, f"0x{opcode:02X}")
        self.log_msg("FETCH", f"{mn}({arg}) @ {addr}")

    def exec_word(self, m: dict) -> int:
        dp = self.dp
        upc = self.upc
        ds = dp.data_stack
        rs = dp.return_stack
        mn = OPCODE_NAMES.get(dp.ir_opcode, f"0x{dp.ir_opcode:02X}")

        old_tos = ds.peek(0) if len(ds) >= 1 else 0
        old_nos = ds.peek(1) if len(ds) >= 2 else 0
        old_rs_top = rs.peek(0) if len(rs) >= 1 else 0
        old_pc = dp.pc

        if m["ir_we"]:
            self.do_fetch()
            mn = OPCODE_NAMES.get(dp.ir_opcode, f"0x{dp.ir_opcode:02X}")

        ar_sel = m["ar_sel"]
        if ar_sel == ArSel.PC:
            dp.ar = old_pc
        elif ar_sel == ArSel.ARG:
            dp.ar = dp.ir_arg
        elif ar_sel == ArSel.DS:
            dp.ar = old_tos

        alu_op = m["alu_op"]
        alu_out = 0
        if alu_op == AluOp.TEST_ZERO:
            dp.alu.test_zero(old_tos)
        elif alu_op != AluOp.NONE:
            alu_out = dp.alu.binop(alu_op, old_nos, old_tos)

        if m["mem_we"]:
            dp.mem_write(dp.ar, old_tos)

        tos_sel = m["tos_sel"]
        if tos_sel == TosSel.NOS:
            new_tos = old_nos
        elif tos_sel == TosSel.MEM:
            new_tos = dp.mem_read(dp.ar)
        elif tos_sel == TosSel.ARG:
            new_tos = dp.ir_arg
        elif tos_sel == TosSel.ALU:
            new_tos = alu_out
        else:
            new_tos = old_tos

        dsp = m["dsp_delta"]
        if dsp == SpDelta.INC:
            ds.push(new_tos)
        elif dsp == SpDelta.DEC:
            ds.pop()
            if len(ds) >= 1:
                ds.set_top(new_tos)
        else:
            if len(ds) >= 1:
                ds.set_top(new_tos)

        if m["ns_we"]:
            ds.set_nos(old_tos)

        rsp = m["rsp_delta"]
        if rsp == SpDelta.INC:
            rs.push(old_pc)
        elif rsp == SpDelta.DEC:
            rs.pop()

        if m["pc_we"]:
            pc_sel = m["pc_sel"]
            if pc_sel == PcSel.INC:
                dp.pc = old_pc + 1
            elif pc_sel == PcSel.ARG:
                dp.pc = dp.ir_arg
            elif pc_sel == PcSel.RS:
                dp.pc = old_rs_top

        if m["halt"]:
            dp.halted = True
            self.log_msg("EXEC", f"{mn}: HALT", with_state=False)
            raise StopSignal("HALT")

        if not m["ir_we"]:
            if m["ar_sel"] == ArSel.PC and m["cond"] == Cond.SEQ:
                self.log_msg("FETCH", "AR <- PC")
            else:
                self.log_msg("EXEC", f"{mn}: {self.fmt_signals(m)}")

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
    def fmt_signals(m: dict) -> str:
        active = [f"{k}={v}" for k, v in m.items()
                  if v and k not in ("cond", "next_addr")]
        return " ".join(active) if active else "(нет сигналов)"

    def run(self) -> None:
        while not self.dp.halted and self.tick < MAX_TICKS:
            self.tick += 1
            m = decode_u(ROM[self.upc])
            try:
                self.upc = self.exec_word(m)
            except StopSignal as exc:
                self.stop_reason = str(exc)
                break
            except (IndexError, OverflowError, ZeroDivisionError, ValueError) as exc:
                self.stop_reason = f"ERROR: {exc}"
                self.log_msg("ERROR", str(exc), with_state=False)
                break

        if self.tick >= MAX_TICKS:
            self.stop_reason = f"Достигнут лимит тактов ({MAX_TICKS})"
            self.log_msg("WARN", self.stop_reason, with_state=False)

        self.log_msg("STOP", self.stop_reason or "завершено", with_state=False)
