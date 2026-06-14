from __future__ import annotations

from pathlib import Path

from .lexer import Lexer, LexerError
from .parser import Parser, ParserError
from .runtime import Runtime, RuntimeErrorLS1

LUCOA_ERRORS = (LexerError, ParserError, RuntimeErrorLS1)


def run_source(
    source_code: str,
    runtime: Runtime | None = None,
    base_directory: str | Path | None = None,
) -> Runtime:
    """Executa um trecho de codigo LS1 em um runtime existente ou novo."""

    active_runtime = runtime or Runtime(base_directory or Path.cwd())
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    program = parser.parse()
    active_runtime.run(program)
    return active_runtime


def run_file(source_path: str | Path, runtime: Runtime | None = None) -> Runtime:
    """Executa um arquivo .ls1 e devolve o runtime usado."""

    resolved_path = Path(source_path).resolve()
    source_code = resolved_path.read_text(encoding="utf-8")
    active_runtime = runtime or Runtime(resolved_path.parent)
    return run_source(source_code, runtime=active_runtime)
