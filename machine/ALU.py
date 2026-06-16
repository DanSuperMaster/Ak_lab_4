from common import AluOp


class ALU:
    def __init__(self) -> None:
        self.c: int = 0

    def binop(self, op: AluOp, left: int, right: int) -> int:
        if op == AluOp.ADD:
            r = left + right
        elif op == AluOp.SUB:
            r = left - right
        elif op == AluOp.MUL:
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
        self.c = 1 if r == 0 else 0
        return r

    def test_zero(self, value: int) -> None:
        self.c = 1 if value == 0 else 0