from __future__ import annotations

import sys

from lucoa.cli import main as cli_main


def main() -> int:
    """Mantem compatibilidade com `python main.py arquivo.ls1`."""

    argv = sys.argv[1:]
    if argv and argv[0] not in {"exec", "version", "new", "install", "update"}:
        argv = ["exec", *argv]
    return cli_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
