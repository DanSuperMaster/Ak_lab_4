import pytest

from utils.lexer import Lexer, Parser
from utils.compiler import Compiler
from machine.processor import Processor
from gen_golden import build_memory


def _unescape(raw: str) -> str:
    if not raw:
        return ""
    return raw.encode("latin1", "backslashreplace").decode("unicode_escape")


@pytest.mark.golden_test("*.yml")
def test_golden(golden):
    tokens = Lexer(golden["source"]).tokenize()
    program = Parser(tokens).parse()
    compiler = Compiler()
    compiler.compile(program)
    code, data = compiler.finalize()

    memory, data_offset = build_memory(code, data)
    input_buffer = [ord(ch) for ch in _unescape(golden["input"])]

    cpu = Processor(memory, input_buffer, data_offset=data_offset, log=False)
    cpu.run()

    assert cpu.dp.output_buffer == list(golden.out["output"])
    assert cpu.cu.tick == golden.out["ticks"]
