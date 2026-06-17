from common import MAX_STACK_DEPTH


class Stack:
    def __init__(self, name: str) -> None:
        self._name = name
        self._data: list[int] = []

    def push(self, value: int) -> None:
        if len(self._data) >= MAX_STACK_DEPTH:
            raise OverflowError(f"{self._name} переполнен")
        self._data.append(value)

    def pop(self) -> int:
        if not self._data:
            raise IndexError(f"{self._name} пуст")
        return self._data.pop()

    def peek(self, depth: int = 0) -> int:
        if len(self._data) <= depth:
            raise IndexError(f"{self._name}: недостаточно элементов")
        return self._data[-1 - depth]

    def set_top(self, value: int) -> None:
        if not self._data:
            raise IndexError(f"{self._name}: пуст")
        self._data[-1] = value

    def set_nos(self, value: int) -> None:
        if len(self._data) < 2:
            raise IndexError(f"{self._name}: нет NOS")
        self._data[-2] = value

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return f"{self._name}{self._data}"

    def snapshot(self, n: int = 4) -> list[int]:
        return list(self._data[-n:])