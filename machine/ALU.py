from common import MicroOp


class ALU:
    def __init__(self) -> None:
        self.c: int = 0

    def binop(self, op: MicroOp, left: int, right: int) -> int:
        if op == MicroOp.ALU_ADD:
            r = left + right
        elif op == MicroOp.ALU_SUB:
            r = left - right
        elif op == MicroOp.ALU_MUL:
            r = left * right
        elif op == MicroOp.ALU_DIV:
            if right == 0:
                raise ZeroDivisionError("ALU: деление на ноль")
            r = int(left / right)
        elif op == MicroOp.ALU_MOD:
            if right == 0:
                raise ZeroDivisionError("ALU: остаток от деления на ноль")
            r = left % right
        elif op == MicroOp.ALU_EQ:
            r = 1 if left == right else 0
        elif op == MicroOp.ALU_LT:
            r = 1 if left < right else 0
        elif op == MicroOp.ALU_GT:
            r = 1 if left > right else 0
        else:
            raise ValueError(f"ALU: неизвестная binop {op}")
        self.c = 1 if r == 0 else 0
        return r

    def test_zero(self, value: int) -> None:
        self.c = 1 if value == 0 else 0