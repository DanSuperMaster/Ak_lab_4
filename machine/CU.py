from machine.Instruct import Instruction
from machine.datapath import DataPath
from common import MicroOp, MAX_TICKS, StopSignal, MC
from utils.isa import decode_instruction, OPCODE_NAMES, Opcode, OUT_PORT, IN_PORT
from typing import Optional
import struct


class ControlUnit:
    def __init__(self, datapath: DataPath, *, log: bool = True,
                 max_print_str: int = 4096) -> None:
        self.dp = datapath
        self.rom = MC
        self.tick = 0
        self.instr_count = 0
        self._log = log
        self.journal: list[str] = []
        self.max_print_str = max_print_str

    def _log_msg(self, stage: str, detail: str, with_state: bool = True) -> None:
        if not self._log:
            return
        if with_state:
            ds = self.dp.data_stack.snapshot(4)
            rs = self.dp.return_stack.snapshot(2)
            line = (
                f"tick={self.tick:6d} | PC={self.dp.pc:04d} "
                f"AR={self.dp.ar:04x} A={self.dp.a:04x} B={self.dp.b:04x} "
                f"C={self.dp.alu.c} "
                f"DS={ds} RS={rs} | {stage:7s} | {detail}"
            )
        else:
            line = f"tick={self.tick:6d} | {stage:7s} | {detail}"
        self.journal.append(line)

    def _fetch(self) -> Optional[Instruction]:
        if self.dp.halted:
            return None
        self.tick += 1
        pc = self.dp.pc
        if pc < 0 or pc >= len(self.dp.memory):
            raise IndexError(f"PC={pc} за пределами памяти")
        self.dp.ar = pc
        raw_word = self.dp.memory[pc]

        raw_bytes = struct.pack(">I", raw_word & 0xFFFFFFFF)
        opcode, arg = decode_instruction(raw_bytes)
        mn = OPCODE_NAMES.get(opcode, f"0x{opcode:02X}")
        self._log_msg("FETCH", f"{mn}({arg}) @ {pc}")
        self.dp.pc = pc + 1
        return Instruction(pc=pc, opcode=opcode, arg=arg)



    def _decode(self, st: Instruction) -> Instruction:
        st.micro_ops = list(self.rom.get(st.opcode, []))
        st.state = {}
        mn = OPCODE_NAMES.get(st.opcode, f"0x{st.opcode:02X}")
        self._log_msg("DECODE", f"{mn} -> {len(st.micro_ops)} мк-оп")
        return st



    def _execute(self, st: Instruction) -> None:
        if st.opcode == Opcode.PRINT_STR:
            while True:
                self.tick += 1
                done, _ = self._exec_print_str(st)
                if done:
                    return
                if self.tick >= MAX_TICKS:
                    return
            return

        for mu in st.micro_ops:
            self.tick += 1
            self._dispatch_microop(mu, st)
            if self.tick >= MAX_TICKS:
                return


    def _dispatch_microop(self, mu: MicroOp, st: Instruction) -> bool:

        dp = self.dp
        mn = OPCODE_NAMES.get(st.opcode, f"0x{st.opcode:02X}")

        mem_used = False

        if mu == MicroOp.AR_LATCH_PC:
            dp.ar = dp.pc
            self._log_msg("EXEC", f"{mn}: AR <- PC ({dp.pc})")
        elif mu == MicroOp.AR_LATCH_IR_ARG:
            dp.ar = st.arg
            self._log_msg("EXEC", f"{mn}: AR <- IR.arg ({st.arg})")
        elif mu == MicroOp.AR_LATCH_A:
            dp.ar = dp.a
            self._log_msg("EXEC", f"{mn}: AR <- A ({dp.a})")
        elif mu == MicroOp.AR_LATCH_B:
            dp.ar = dp.b
            self._log_msg("EXEC", f"{mn}: AR <- B ({dp.b})")
        elif mu == MicroOp.AR_LATCH_IN_PORT:
            dp.ar = IN_PORT
            self._log_msg("EXEC", f"{mn}: AR <- IN_PORT")
        elif mu == MicroOp.AR_LATCH_OUT_PORT:
            dp.ar = OUT_PORT
            self._log_msg("EXEC", f"{mn}: AR <- OUT_PORT")

        # ---- работа с MEMORY и IR ----
        elif mu == MicroOp.IR_FROM_MEM_PC:
            # Обычно FETCH у нас делается одним «толстым» тактом в _fetch,
            # но эта микрооперация оставлена на случай, если кто-то захочет
            # развести FETCH на 2 такта.
            raw = dp.mem_read(dp.ar)
            st.opcode, st.arg = decode_instruction(struct.pack(">I", raw & 0xFFFFFFFF))
            self._log_msg("EXEC", f"IR <- MEM[AR={dp.ar}]")
            mem_used = True

        elif mu == MicroOp.DS_PUSH_FROM_MEM:
            val = dp.mem_read(dp.ar)
            dp.data_stack.push(val)
            self._log_msg("EXEC", f"{mn}: DS push <- MEM[{dp.ar}] = {val}")
            mem_used = True

        elif mu == MicroOp.MEM_FROM_DS:
            val = dp.data_stack.pop()
            dp.mem_write(dp.ar, val)
            self._log_msg("EXEC", f"{mn}: MEM[{dp.ar}] <- pop DS = {val}")
            mem_used = True

        elif mu == MicroOp.A_LATCH_IR_ARG:
            dp.a = st.arg
            self._log_msg("EXEC", f"{mn}: A <- IR.arg ({st.arg})")
        elif mu == MicroOp.A_INC:
            dp.a += 1
            self._log_msg("EXEC", f"{mn}: A <- A+1 = {dp.a}")
        elif mu == MicroOp.B_LATCH_IR_ARG:
            dp.b = st.arg
            self._log_msg("EXEC", f"{mn}: B <- IR.arg ({st.arg})")
        elif mu == MicroOp.B_INC:
            dp.b += 1
            self._log_msg("EXEC", f"{mn}: B <- B+1 = {dp.b}")

        elif mu == MicroOp.DS_PUSH_IR_ARG:
            dp.data_stack.push(st.arg)
            self._log_msg("EXEC", f"{mn}: DS push IR.arg = {st.arg}")
        elif mu == MicroOp.DS_DUP:
            dp.data_stack.push(dp.data_stack.peek())
            self._log_msg("EXEC", f"{mn}: DUP")
        elif mu == MicroOp.DS_POP:
            dp.data_stack.pop()
            self._log_msg("EXEC", f"{mn}: POP")
        elif mu == MicroOp.DS_SWAP:
            x = dp.data_stack.pop()
            y = dp.data_stack.pop()
            dp.data_stack.push(x);
            dp.data_stack.push(y)
            self._log_msg("EXEC", f"{mn}: SWAP")

        elif mu in (MicroOp.ALU_ADD, MicroOp.ALU_SUB, MicroOp.ALU_MUL,
                    MicroOp.ALU_DIV, MicroOp.ALU_MOD,
                    MicroOp.ALU_EQ, MicroOp.ALU_LT, MicroOp.ALU_GT):
            right = dp.data_stack.pop()
            left = dp.data_stack.pop()
            r = dp.alu.binop(mu, left, right)
            dp.data_stack.push(r)
            self._log_msg("EXEC", f"{mn}: ALU {mu.name} ({left}, {right}) -> {r}, C={dp.alu.c}")

        elif mu == MicroOp.ALU_TEST_ZERO:
            v = dp.data_stack.pop()
            dp.alu.test_zero(v)
            self._log_msg("EXEC", f"{mn}: TEST_ZERO({v}) -> C={dp.alu.c}")

        elif mu == MicroOp.PC_LATCH_IR_ARG:
            dp.pc = st.arg
            self._log_msg("EXEC", f"{mn}: PC <- IR.arg ({st.arg})")
        elif mu == MicroOp.PC_LATCH_RS_POP:
            ret = dp.return_stack.pop()
            dp.pc = ret
            self._log_msg("EXEC", f"{mn}: PC <- RS.pop = {ret}")
        elif mu == MicroOp.PC_JZ_IR_ARG:
            if dp.alu.c == 1:
                dp.pc = st.arg
                self._log_msg("EXEC", f"{mn}: C=1, PC <- IR.arg ({st.arg})")
            else:
                self._log_msg("EXEC", f"{mn}: C=0, переход не выполнен")

        elif mu == MicroOp.RS_PUSH_PC:
            dp.return_stack.push(dp.pc)
            self._log_msg("EXEC", f"{mn}: RS push PC = {dp.pc}")

        elif mu == MicroOp.RS_PUSH_FROM_DS:
            val = dp.data_stack.pop()
            dp.return_stack.push(val)
            self._log_msg("EXEC", f"{mn}: RS push <- DS pop = {val}")

        elif mu == MicroOp.DS_PUSH_FROM_RS:
            val = dp.return_stack.pop()
            dp.data_stack.push(val)
            self._log_msg("EXEC", f"{mn}: DS push <- RS pop = {val}")

        elif mu == MicroOp.DS_PUSH_FROM_PORT_IN:
            v = dp.mem_read(IN_PORT)
            dp.data_stack.push(v)
            self._log_msg("IO",
                          f"{mn}: IN -> {v}"
                          + (f" ({chr(v)!r})" if 0 <= v < 0x110000 and chr(v).isprintable() else ""))
            mem_used = True
        elif mu == MicroOp.PORT_OUT_FROM_DS:
            v = dp.data_stack.pop()
            dp.mem_write(OUT_PORT, v)
            self._log_msg("IO",
                          f"{mn}: OUT <- {v}"
                          + (f" ({chr(v & 0xFF)!r})" if 0 <= v < 0x110000 and chr(v & 0xFF).isprintable() else ""))
            mem_used = True

        elif mu == MicroOp.PORT_OUT_INT_FROM_DS:
            v = dp.data_stack.pop()
            for ch in str(v):
                dp.mem_write(OUT_PORT, ord(ch))
            self._log_msg("IO", f"{mn}: PRINT_INT <- {v}")
            mem_used = True

        elif mu == MicroOp.HALT:
            dp.halted = True
            self._log_msg("EXEC", f"{mn}: HALT — процессор остановлен", with_state=False)
            raise StopSignal("HALT")

        else:
            raise ValueError(f"Неизвестная микрооперация: {mu}")

        return mem_used


    def _exec_print_str(self, st: Instruction) -> tuple[bool, bool]:

        dp = self.dp
        phase = st.state.get("phase", 0)
        count = st.state.get("count", 0)
        st.state["count"] = count + 1
        if count + 1 > self.max_print_str:
            raise RuntimeError("PRINT_STR: похоже на бесконечную строку")

        mn = "PRINT_STR"

        if phase == 0:
            dp.a = st.arg
            self._log_msg("EXEC", f"{mn}: A <- IR.arg = {st.arg}  (init cursor)")
            st.state["phase"] = 1
            return False, False

        if phase == 1:
            dp.ar = dp.a
            self._log_msg("EXEC", f"{mn}: AR <- A ({dp.a})")
            st.state["phase"] = 2
            return False, False

        if phase == 2:
            v = dp.mem_read(dp.ar)
            dp.data_stack.push(v)
            dp.alu.test_zero(v)
            self._log_msg("EXEC", f"{mn}: DS push MEM[{dp.ar}]={v}; C={dp.alu.c}")
            st.state["phase"] = 3
            return False, True

        if phase == 3:
            if dp.alu.c == 1:
                dp.data_stack.pop()
                self._log_msg("EXEC", f"{mn}: терминатор cstr, завершение")
                return True, False
            dp.ar = OUT_PORT
            self._log_msg("EXEC", f"{mn}: AR <- OUT_PORT")
            st.state["phase"] = 4
            return False, False

        if phase == 4:
            v = dp.data_stack.pop()
            dp.mem_write(OUT_PORT, v)
            self._log_msg("IO", f"{mn}: OUT <- {v} ({chr(v & 0xFF)!r})")
            st.state["phase"] = 5
            return False, True

        if phase == 5:
            dp.a += 1
            self._log_msg("EXEC", f"{mn}: A <- A+1 = {dp.a}")
            st.state["phase"] = 1
            return False, False

        return True, False


    def run(self) -> None:

        while not self.dp.halted and self.tick < MAX_TICKS:
            try:
                instr = self._fetch()
                if instr is None:
                    break
                self._decode(instr)
                self._execute(instr)
                self.instr_count += 1
            except StopSignal:
                break
            except (IndexError, OverflowError, ZeroDivisionError, ValueError) as exc:
                self._log_msg("ERROR", str(exc), with_state=False)
                break

        if self.tick >= MAX_TICKS:
            self._log_msg("WARN", f"Достигнут лимит тактов ({MAX_TICKS})", with_state=False)
