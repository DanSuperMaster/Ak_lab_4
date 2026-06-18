import struct

from machine.datapath import DataPath
from common import (
    MAX_TICKS, StopSignal,
    ROM, OPCODE_TO_UADDR, decode_u,
    Cond, ArSel,
)
from utils.isa import decode_instruction, OPCODE_NAMES


class ControlUnit:
    def __init__(self, datapath: DataPath, *, log: bool = True,
                 max_print_str: int = 4096) -> None:
        self.dp = datapath
        self.mpc = 0
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
                f"tick={self.tick:6d} | MPC={self.mpc:02d} PC={self.dp.pc:04d} "
                f"AR={self.dp.ar:04x} "
                f"C={self.dp.c} "
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
        dp.signal_latch_ir(opcode, arg)
        self.instr_count += 1
        mn = OPCODE_NAMES.get(opcode, f"0x{opcode:02X}")
        self.log_msg("FETCH", f"{mn}({arg}) @ {addr}")

    def exec_word(self, m: dict) -> int:
        dp = self.dp
        mpc = self.mpc
        mn = OPCODE_NAMES.get(dp.ir_opcode, f"0x{dp.ir_opcode:02X}")

        # Фронт синхросигнала: датапас фиксирует выходы своих регистров.
        dp.start_cycle()

        if m["ir_latch"]:
            self.do_fetch()
            mn = OPCODE_NAMES.get(dp.ir_opcode, f"0x{dp.ir_opcode:02X}")

        if m["ar_latch"]:
            dp.signal_latch_ar(m["ar_sel"])

        dp.signal_alu(m["alu_op"], m["alu_sel"])
        if m["c_latch"]:
            dp.signal_latch_c()

        if m["mem_latch"]:
            dp.signal_mem_write()

        dp.signal_latch_tos(m["tos_sel"], m["dsp_delta"])

        if m["ns_latch"]:
            dp.signal_latch_nos()

        dp.signal_latch_rs(m["rsp_delta"])

        if m["pc_latch"]:
            dp.signal_latch_pc(m["pc_sel"])

        if m["halt"]:
            dp.signal_halt()
            self.log_msg("EXEC", f"{mn}: HALT", with_state=False)
            raise StopSignal("HALT")

        if not m["ir_latch"]:
            if m["ar_latch"] and m["ar_sel"] == ArSel.PC and m["cond"] == Cond.SEQ:
                self.log_msg("FETCH", "AR <- PC")
            else:
                self.log_msg("EXEC", f"{mn}: {self.fmt_signals(m)}")

        cond = m["cond"]
        if cond == Cond.SEQ:
            return mpc + 1
        if cond == Cond.NEXT:
            return m["next_addr"]
        if cond == Cond.DISPATCH:
            try:
                return OPCODE_TO_UADDR[dp.ir_opcode]
            except KeyError:
                raise ValueError(f"Неизвестный опкод: 0x{dp.ir_opcode:02X}")
        if cond == Cond.IF_C:
            return m["next_addr"] if dp.c == 1 else mpc + 1
        if cond == Cond.IF_NC:
            return m["next_addr"] if dp.c == 0 else mpc + 1
        raise ValueError(f"Неизвестный cond={cond}")

    @staticmethod
    def fmt_signals(m: dict) -> str:
        active = [f"{k}={v}" for k, v in m.items()
                  if v and k not in ("cond", "next_addr")]
        return " ".join(active) if active else "(нет сигналов)"

    def run(self) -> None:
        while not self.dp.halted and self.tick < MAX_TICKS:
            self.tick += 1
            m = decode_u(ROM[self.mpc])
            try:
                self.mpc = self.exec_word(m)
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
