from common import AluOp

WORD_MASK = 0xFFFFFFFF
SIGN_BIT = 0x80000000


def to_u32(value: int) -> int:
    return value & WORD_MASK


def to_s32(bits: int) -> int:
    bits &= WORD_MASK
    return bits - (1 << 32) if bits & SIGN_BIT else bits


class ALU:
    def binop(self, op: AluOp, left: int, right: int, carry_in: int = 0) -> tuple[int, int]:
        if op == AluOp.ADD:
            total = to_u32(left) + to_u32(right)
            return to_s32(total), total >> 32
        if op == AluOp.ADDC:
            total = to_u32(left) + to_u32(right) + carry_in
            return to_s32(total), total >> 32
        if op == AluOp.SUB:
            diff = to_u32(left) - to_u32(right)
            return to_s32(diff), 1 if diff < 0 else 0
        if op == AluOp.SUBB:
            diff = to_u32(left) - to_u32(right) - carry_in
            return to_s32(diff), 1 if diff < 0 else 0

        if op == AluOp.MUL:
            r = left * right
        elif op == AluOp.DIV:
            if right == 0:
                raise ZeroDivisionError("ALU: деление на ноль")
            r = int(left / right)
        elif op == AluOp.MOD:
            if right == 0:
                raise ZeroDivisionError("ALU: остаток от деления на ноль")
            r = left % right
        elif op == AluOp.EQ:
            r = 1 if left == right else 0
        elif op == AluOp.LT:
            r = 1 if left < right else 0
        elif op == AluOp.GT:
            r = 1 if left > right else 0
        else:
            raise ValueError(f"ALU: неизвестная binop {op}")
        return r, 0
