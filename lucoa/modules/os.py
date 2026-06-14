from __future__ import annotations

import os as python_os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..runtime import Runtime, RuntimeErrorLS1


@dataclass
class LucoaOSModule:
    """Facade do modulo os para manter a integracao com o runtime atual."""

    runtime: Runtime

    def mkdir(self, path: Any) -> None:
        target = self._resolve_path_argument(path)
        python_os.mkdir(target)

    def remove(self, path: Any) -> None:
        target = self._resolve_path_argument(path)
        python_os.remove(target)

    def rename(self, source: Any, destination: Any) -> None:
        source_path = self._resolve_path_argument(source)
        destination_path = self._resolve_path_argument(destination)
        python_os.rename(source_path, destination_path)

    def listdir(self) -> list[str]:
        return sorted(python_os.listdir(self.runtime.base_directory))

    def getcwd(self) -> str:
        return str(self.runtime.base_directory)

    def chdir(self, path: Any) -> str:
        return str(self.runtime.change_directory(self._coerce_text(path)))

    def exists(self, path: Any) -> bool:
        target = self._resolve_path_argument(path)
        return python_os.path.exists(target)

    def _resolve_path_argument(self, value: Any) -> Path:
        path = self._coerce_text(value)
        return self.runtime.resolve_path(path)

    def _coerce_text(self, value: Any) -> str:
        if not isinstance(value, str):
            raise RuntimeErrorLS1("O modulo os espera caminhos em formato de texto.")
        return value


def register(runtime: Runtime) -> None:
    """Registra o modulo interno `os` no ambiente atual do LS1."""

    runtime.environment.define("os", LucoaOSModule(runtime))
