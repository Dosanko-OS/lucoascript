from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import INTERPRETER_NAME, VERSION
from .interpreter import LUCOA_ERRORS, run_file, run_source
from .runtime import Runtime


class LucoaCLI:
    """CLI principal do LucoaScript com registro simples de subcomandos."""

    def __init__(self) -> None:
        self.parser = argparse.ArgumentParser(
            prog="lucoa",
            description="Ferramenta de linha de comando do LucoaScript.",
        )
        self.subparsers = self.parser.add_subparsers(dest="command")
        self._register_commands()

    def _register_commands(self) -> None:
        self._register_exec_command()
        self._register_version_command()
        self._register_future_command("new", "Cria um novo projeto LucoaScript.", "project_name")
        self._register_future_command("install", "Instala um modulo LucoaScript.", "module_name")
        self._register_future_command("update", "Atualiza ferramentas ou modulos do LucoaScript.")

    def _register_exec_command(self) -> None:
        exec_parser = self.subparsers.add_parser(
            "exec",
            help="Executa um arquivo .ls1.",
            description="Executa um programa LucoaScript a partir de um arquivo .ls1.",
        )
        exec_parser.add_argument("source_file", help="Arquivo .ls1 que sera executado.")
        exec_parser.set_defaults(handler=self._handle_exec)

    def _register_version_command(self) -> None:
        version_parser = self.subparsers.add_parser(
            "version",
            help="Mostra a versao do LucoaScript.",
            description="Mostra a versao atual do LucoaScript.",
        )
        version_parser.set_defaults(handler=self._handle_version)

    def _register_future_command(
        self,
        command_name: str,
        help_text: str,
        argument_name: str | None = None,
    ) -> None:
        future_parser = self.subparsers.add_parser(
            command_name,
            help=help_text,
            description=help_text,
        )
        if argument_name is not None:
            future_parser.add_argument(argument_name)
        future_parser.set_defaults(handler=self._handle_future_command)

    def run(self, argv: list[str] | None = None) -> int:
        normalized_argv = self._normalize_argv(argv)
        args = self.parser.parse_args(normalized_argv)
        handler = getattr(args, "handler", None)
        if handler is None:
            return self._handle_repl()
        return handler(args)

    def _normalize_argv(self, argv: list[str] | None) -> list[str] | None:
        if argv is None:
            argv = sys.argv[1:]

        if not argv:
            return argv

        known_commands = {"exec", "version", "new", "install", "update"}
        first_argument = argv[0]

        # Permite "lucoa programa.ls1" alem de "lucoa exec programa.ls1".
        if first_argument not in known_commands and not first_argument.startswith("-"):
            return ["exec", *argv]

        return argv

    def _handle_exec(self, args: argparse.Namespace) -> int:
        source_path = Path(args.source_file).resolve()

        if source_path.suffix.lower() != ".ls1":
            print("Erro: use um arquivo com extensao .ls1.", file=sys.stderr)
            return 1

        if not source_path.exists():
            print(f"Erro: arquivo '{source_path}' nao foi encontrado.", file=sys.stderr)
            return 1

        try:
            run_file(source_path)
        except LUCOA_ERRORS as exc:
            print(f"Erro no LucoaScript: {exc}", file=sys.stderr)
            return 1

        return 0

    def _handle_version(self, _args: argparse.Namespace) -> int:
        print(f"{INTERPRETER_NAME} {VERSION}")
        return 0

    def _handle_repl(self) -> int:
        repl = LucoaREPL()
        return repl.run()

    def _handle_future_command(self, args: argparse.Namespace) -> int:
        print(
            f"O comando '{args.command}' ja esta reservado na CLI, mas ainda nao foi implementado."
        )
        return 0


class LucoaREPL:
    """REPL simples que reutiliza o mesmo runtime entre comandos."""

    def __init__(self, base_directory: str | Path | None = None) -> None:
        self.runtime = Runtime(base_directory or Path.cwd())
        self.buffer: list[str] = []

    def run(self) -> int:
        print(f"{INTERPRETER_NAME} Interpreter {VERSION}")

        while True:
            prompt = "> " if not self.buffer else "... "
            try:
                line = input(prompt)
            except EOFError:
                print()
                return 0
            except KeyboardInterrupt:
                print()
                self.buffer.clear()
                continue

            if not self.buffer and line.strip().lower() in {"exit", "quit"}:
                return 0

            self.buffer.append(line)
            source = "\n".join(self.buffer)

            if self._needs_more_input(source):
                continue

            try:
                run_source(f"{source}\n", runtime=self.runtime)
            except LUCOA_ERRORS as exc:
                print(f"Erro no LucoaScript: {exc}")
            finally:
                self.buffer.clear()

    def _needs_more_input(self, source: str) -> bool:
        balance = 0
        in_string = False
        escaped = False
        in_comment = False

        for character in source:
            if in_comment:
                if character == "\n":
                    in_comment = False
                continue

            if in_string:
                if escaped:
                    escaped = False
                    continue
                if character == "\\":
                    escaped = True
                    continue
                if character == '"':
                    in_string = False
                continue

            if character == "#":
                in_comment = True
                continue

            if character == '"':
                in_string = True
                continue

            if character == "(":
                balance += 1
                continue

            if character == ")":
                balance -= 1

        return balance > 0


def main(argv: list[str] | None = None) -> int:
    return LucoaCLI().run(argv)
