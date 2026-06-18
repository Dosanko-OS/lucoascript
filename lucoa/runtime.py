from __future__ import annotations

import importlib
import importlib.util
import time as time_module
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .parser import (
    AssignmentStatement,
    BinaryExpression,
    CallExpression,
    Expression,
    ExpressionStatement,
    IfStatement,
    InsertStatement,
    Literal,
    LoopStatement,
    MemberAccessExpression,
    Program,
    RespondExpression,
    Statement,
    TimeStatement,
    UnaryExpression,
    UseStatement,
    Variable,
    WriteStatement,
    ListLiteral,
    ObjectLiteral,
    IndexExpression,
)


class RuntimeErrorLS1(Exception):
    """Erro gerado durante a execucao do programa LS1."""


class Environment:
    """Armazena variaveis e prepara escopos futuros."""

    def __init__(self, parent: "Environment | None" = None) -> None:
        self.parent = parent
        self.values: dict[str, Any] = {}

    def define(self, name: str, value: Any) -> None:
        self.values[name] = value

    def assign(self, name: str, value: Any) -> None:
        if name in self.values:
            self.values[name] = value
            return

        if self.parent is not None and self.parent.contains(name):
            self.parent.assign(name, value)
            return

        self.values[name] = value

    def get(self, name: str) -> Any:
        if name in self.values:
            return self.values[name]

        if self.parent is not None:
            return self.parent.get(name)

        raise RuntimeErrorLS1(f"Variavel '{name}' nao foi definida.")

    def contains(self, name: str) -> bool:
        if name in self.values:
            return True
        return self.parent.contains(name) if self.parent is not None else False


@dataclass
class BuiltinFunction:
    """Wrapper para funcoes nativas do runtime."""

    name: str
    handler: Any

    def __call__(self, runtime: "Runtime", arguments: list[Any]) -> Any:
        return self.handler(runtime, arguments)


class LSFile:
    """Abstracao simples sobre arquivos locais abertos pelo LS1."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.handle = file_path.open("a+", encoding="utf-8")
        self.handle.seek(0)

    def read(self) -> str:
        self.handle.seek(0)
        return self.handle.read()

    def write(self, content: Any) -> None:
        self.handle.seek(0, 2)
        self.handle.write(str(content))
        self.handle.flush()

    def close(self) -> None:
        self.handle.close()


class ModuleLoader:
    """Carrega modulos locais, internos do Lucoa ou instalados externamente."""

    def __init__(self, runtime: "Runtime") -> None:
        self.runtime = runtime
        self.loaded_modules: set[str] = set()

    def load(self, module_name: str) -> None:
        if module_name in self.loaded_modules:
            return

        module = self._load_local_module(module_name)
        if module is None:
            module = self._load_internal_module(module_name)
        if module is None:
            try:
                module = importlib.import_module(module_name)
            except ModuleNotFoundError as exc:
                raise RuntimeErrorLS1(
                    f"Modulo '{module_name}' nao foi encontrado."
                ) from exc

        self._register_exports(module_name, module)
        self.loaded_modules.add(module_name)

    # Bug 2 corrigido: _load_local_module estava duplicado; a segunda definição
    # (idêntica à primeira) foi removida.
    def _load_local_module(self, module_name: str) -> Any | None:
        module_path = self.runtime.base_directory / "modules" / f"{module_name}.py"
        if not module_path.exists():
            return None

        spec = importlib.util.spec_from_file_location(
            f"ls1_module_{module_name}", module_path
        )
        if spec is None or spec.loader is None:
            raise RuntimeErrorLS1(
                f"Nao foi possivel carregar o modulo local '{module_name}'."
            )

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _load_internal_module(self, module_name: str) -> Any | None:
        internal_name = f"lucoa.modules.{module_name}"

        try:
            return importlib.import_module(internal_name)

        except ModuleNotFoundError as exc:
            if exc.name == internal_name:
                return None
            raise

    def _register_exports(self, module_name: str, module: Any) -> None:
        if hasattr(module, "register"):
            module.register(self.runtime)
            return

        exports = getattr(module, "EXPORTS", None)
        if isinstance(exports, dict):
            for name, value in exports.items():
                self.runtime.environment.define(name, value)
            return

        # expõe o módulo inteiro
        self.runtime.environment.define(module_name, module)

        # expõe todos os membros públicos
        for attr in dir(module):
            if not attr.startswith("_"):
                try:
                    self.runtime.environment.define(
                        attr,
                        getattr(module, attr)
                    )
                except Exception:
                    pass


class Runtime:
    """Executa a AST produzida pelo parser."""

    def __init__(self, base_directory: str | Path) -> None:
        self.base_directory = Path(base_directory).resolve()
        self.environment = Environment()
        self.module_loader = ModuleLoader(self)
        self._register_builtins()

    def run(self, program: Program) -> None:
        for statement in program.statements:
            self.execute_statement(statement)

    # -------------------------------------------------------------------------
    # Bug 1 corrigido: execute_statement estava completamente ausente da classe.
    #
    # ATENÇÃO — nomes de atributos assumidos com base nos imports do parser:
    #   AssignmentStatement : .name (str),         .value (Expression)
    #   WriteStatement      : .expression (Expression)
    #   ExpressionStatement : .expression (Expression)
    #   UseStatement        : .module_name (str)
    #   IfStatement         : .condition (Expression)
    #                         .then_body (list[Statement])
    #                         .elif_clauses (list[tuple[Expression, list[Statement]]])
    #                         .else_body (list[Statement] | None)
    #   LoopStatement       : .variable (str)
    #                         .start (Expression)   ← keyword FROM
    #                         .end   (Expression)   ← keyword TO
    #                         .body  (list[Statement])
    #   InsertStatement     : .value (Expression), .target (Expression)
    #   TimeStatement       : .body (list[Statement])
    #
    # Se algum nome divergir do seu parser, ajuste só esse atributo.
    # -------------------------------------------------------------------------
    def execute_statement(self, statement: Statement) -> None:
        if isinstance(statement, AssignmentStatement):
            value = self.evaluate_expression(statement.expression)
            self.environment.assign(statement.name, value)
            return

        if isinstance(statement, WriteStatement):
            value = self.evaluate_expression(statement.expression)
            print(self.stringify(value))
            return

        if isinstance(statement, ExpressionStatement):
            self.evaluate_expression(statement.expression)
            return

        if isinstance(statement, UseStatement):
            self.module_loader.load(statement.module_name)
            return

        if isinstance(statement, IfStatement):
            if self.is_truthy(self.evaluate_expression(statement.condition)):
                for stmt in statement.then_body:
                    self.execute_statement(stmt)
                return

            for elif_condition, elif_body in statement.elif_clauses:
                if self.is_truthy(self.evaluate_expression(elif_condition)):
                    for stmt in elif_body:
                        self.execute_statement(stmt)
                    return

            if statement.else_body:
                for stmt in statement.else_body:
                    self.execute_statement(stmt)
            return

        if isinstance(statement, LoopStatement):
            start = int(self.evaluate_expression(statement.start))
            end = int(self.evaluate_expression(statement.end))
            for i in range(start, end + 1):
                self.environment.define(statement.variable, i)
                for stmt in statement.body:
                    self.execute_statement(stmt)
            return

        if isinstance(statement, InsertStatement):
            value = self.evaluate_expression(statement.value)
            target = self.evaluate_expression(statement.target)
            if isinstance(target, list):
                target.append(value)
            elif isinstance(target, LSFile):
                target.write(value)
            else:
                raise RuntimeErrorLS1(
                    "insert espera uma lista ou arquivo como destino,"
                    f" recebeu {type(target).__name__}."
                )
            return

        if isinstance(statement, TimeStatement):
            start = time_module.perf_counter()
            for stmt in statement.body:
                self.execute_statement(stmt)
            elapsed = time_module.perf_counter() - start
            print(f"Tempo: {elapsed:.6f}s")
            return

        raise RuntimeErrorLS1(
            f"Statement nao suportado: {type(statement).__name__}."
        )

    def evaluate_expression(self, expression: Expression) -> Any:
        if isinstance(expression, Literal):
            return expression.value

        if isinstance(expression, Variable):
            return self.environment.get(expression.name)

        if isinstance(expression, RespondExpression):
            return input()

        if isinstance(expression, UnaryExpression):
            value = self.evaluate_expression(expression.operand)

            if expression.operator == "NOT":
                return not self.is_truthy(value)

            if expression.operator == "MINUS":
                return -self._coerce_float_or_int(value)

            raise RuntimeErrorLS1(f"Operador unario invalido: {expression.operator}.")

        if isinstance(expression, ListLiteral):
            return [
                self.evaluate_expression(element) for element in expression.elements
            ]

        if isinstance(expression, BinaryExpression):
            return self._evaluate_binary(expression)

        if isinstance(expression, MemberAccessExpression):
            target = self.evaluate_expression(expression.target)

            if isinstance(target, dict):
                try:
                    return target[expression.member_name]

                except KeyError as exc:
                    raise RuntimeErrorLS1(
                        f"O objeto nao possui '{expression.member_name}'."
                    ) from exc

            try:
                return getattr(target, expression.member_name)

            except AttributeError as exc:
                raise RuntimeErrorLS1(
                    f"O valor nao possui o membro '{expression.member_name}'."
                ) from exc

        if isinstance(expression, CallExpression):
            callee = self.evaluate_expression(expression.callee)

            arguments = [
                self.evaluate_expression(argument)
                for argument in expression.positional_arguments
            ]

            named_arguments = {}

            for argument in expression.named_arguments:
                named_arguments[argument.name] = (
                    self.evaluate_expression(argument.value)
                )

            return self._call(
                callee,
                arguments,
                named_arguments
            )

    def _evaluate_binary(self, expression: BinaryExpression) -> Any:
        if expression.operator == "AND":
            left = self.evaluate_expression(expression.left)
            if not self.is_truthy(left):
                return False
            return self.is_truthy(self.evaluate_expression(expression.right))

        if expression.operator == "OR":
            left = self.evaluate_expression(expression.left)
            if self.is_truthy(left):
                return True
            return self.is_truthy(self.evaluate_expression(expression.right))

        left = self.evaluate_expression(expression.left)
        right = self.evaluate_expression(expression.right)

        operations = {
            "EQ": lambda a, b: a == b,
            "NEQ": lambda a, b: a != b,
            "GT": lambda a, b: a > b,
            "LT": lambda a, b: a < b,
            "GTE": lambda a, b: a >= b,
            "LTE": lambda a, b: a <= b,
            "PLUS": lambda a, b: a + b,
            "MINUS": lambda a, b: a - b,
            "STAR": lambda a, b: a * b,
            "SLASH": lambda a, b: a / b,
        }

        operation = operations.get(expression.operator)
        if operation is None:
            raise RuntimeErrorLS1(f"Operador invalido: {expression.operator}.")

        try:
            return operation(left, right)
        except Exception as exc:
            raise RuntimeErrorLS1(str(exc)) from exc

    def _call(
    self,
    callee: Any,
    arguments: list[Any],
    named_arguments: dict[str, Any]
    ) -> Any:
        if isinstance(callee, BuiltinFunction):
            return callee(self, arguments)

        if callable(callee):
            try:
                return callee(
                    *arguments,
                    **named_arguments
                )
            except TypeError as exc:
                raise RuntimeErrorLS1(str(exc)) from exc

        raise RuntimeErrorLS1("Tentativa de chamar um valor que nao e uma funcao.")

    def _register_builtins(self) -> None:
        builtins = {
            "num": BuiltinFunction("num", self._builtin_num),
            "dec": BuiltinFunction("dec", self._builtin_dec),
            "text": BuiltinFunction("text", self._builtin_text),
            "bool": BuiltinFunction("bool", self._builtin_bool),
            "openlocal": BuiltinFunction("openlocal", self._builtin_openlocal),
        }

        for name, function in builtins.items():
            self.environment.define(name, function)

    def stringify(self, value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if value is None:
            return "null"
        return str(value)

    def is_truthy(self, value: Any) -> bool:
        return bool(value)

    def resolve_path(self, path: str | Path) -> Path:
        raw_path = Path(path)
        if raw_path.is_absolute():
            return raw_path.resolve()
        return (self.base_directory / raw_path).resolve()

    def change_directory(self, path: str | Path) -> Path:
        resolved_path = self.resolve_path(path)
        if not resolved_path.exists():
            raise RuntimeErrorLS1(f"Diretorio '{resolved_path}' nao foi encontrado.")
        if not resolved_path.is_dir():
            raise RuntimeErrorLS1(f"'{resolved_path}' nao e um diretorio.")
        self.base_directory = resolved_path
        return self.base_directory

    def _coerce_int(self, value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise RuntimeErrorLS1(
                f"Nao foi possivel converter '{value}' para inteiro."
            ) from exc

    def _coerce_float(self, value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise RuntimeErrorLS1(
                f"Nao foi possivel converter '{value}' para decimal."
            ) from exc

    def _coerce_float_or_int(self, value: Any) -> Any:
        if isinstance(value, (int, float)):
            return value
        return self._coerce_float(value)

    def _expect_arguments(
        self, function_name: str, arguments: list[Any], expected_count: int
    ) -> None:
        if len(arguments) != expected_count:
            raise RuntimeErrorLS1(
                f"{function_name} espera {expected_count} argumento(s), recebeu {len(arguments)}."
            )

    def _builtin_num(self, runtime: "Runtime", arguments: list[Any]) -> int:
        runtime._expect_arguments("num", arguments, 1)
        return runtime._coerce_int(arguments[0])

    def _builtin_dec(self, runtime: "Runtime", arguments: list[Any]) -> float:
        runtime._expect_arguments("dec", arguments, 1)
        return runtime._coerce_float(arguments[0])

    def _builtin_text(self, runtime: "Runtime", arguments: list[Any]) -> str:
        runtime._expect_arguments("text", arguments, 1)
        return runtime.stringify(arguments[0])

    def _builtin_bool(self, runtime: "Runtime", arguments: list[Any]) -> bool:
        runtime._expect_arguments("bool", arguments, 1)
        value = arguments[0]

        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"false", "0", "", "no", "nao"}:
                return False
            if normalized in {"true", "1", "yes", "sim"}:
                return True

        return runtime.is_truthy(value)

    def _builtin_openlocal(self, runtime: "Runtime", arguments: list[Any]) -> LSFile:
        runtime._expect_arguments("openlocal", arguments, 1)
        file_path = runtime.resolve_path(str(arguments[0]))

        if (
            runtime.base_directory not in file_path.parents
            and file_path != runtime.base_directory
        ):
            raise RuntimeErrorLS1(
                "openlocal so pode acessar arquivos dentro do projeto."
            )

        file_path.parent.mkdir(parents=True, exist_ok=True)
        return LSFile(file_path)