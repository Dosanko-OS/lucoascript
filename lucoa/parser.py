from __future__ import annotations

from dataclasses import dataclass

from .lexer import Token


class ParserError(Exception):
    """Erro sintatico encontrado durante a criacao da AST."""


@dataclass
class Program:
    statements: list["Statement"]


class Statement:
    pass


class Expression:
    pass


@dataclass
class WriteStatement(Statement):
    expression: Expression


@dataclass
class InsertStatement(Statement):
    expression: Expression


@dataclass
class AssignmentStatement(Statement):
    name: str
    expression: Expression


@dataclass
class ExpressionStatement(Statement):
    expression: Expression


@dataclass
class UseStatement(Statement):
    module_name: str


@dataclass
class TimeStatement(Statement):
    duration: Expression


@dataclass
class IfBranch:
    condition: Expression
    body: list[Statement]


@dataclass
class IfStatement(Statement):
    branches: list[IfBranch]
    else_body: list[Statement] | None


@dataclass
class LoopStatement(Statement):
    variable_name: str
    start_expression: Expression
    end_expression: Expression
    body: list[Statement]


@dataclass
class Literal(Expression):
    value: object


@dataclass
class Variable(Expression):
    name: str


@dataclass
class RespondExpression(Expression):
    pass


@dataclass
class UnaryExpression(Expression):
    operator: str
    operand: Expression


@dataclass
class BinaryExpression(Expression):
    left: Expression
    operator: str
    right: Expression


@dataclass
class MemberAccessExpression(Expression):
    target: Expression
    member_name: str


@dataclass
class CallExpression(Expression):
    callee: Expression
    arguments: list[Expression]


class Parser:
    """Transforma a lista de tokens em uma AST navegavel pelo runtime."""

    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.index = 0

    def parse(self) -> Program:
        statements: list[Statement] = []
        self._skip_newlines()

        while not self._check("EOF"):
            statements.append(self._parse_statement())
            self._skip_newlines()

        return Program(statements)

    def _parse_statement(self) -> Statement:
        if self._match("WRITE"):
            statement = WriteStatement(self._parse_expression())
            self._consume_statement_end()
            return statement

        if self._match("INSERT"):
            statement = InsertStatement(self._parse_expression())
            self._consume_statement_end()
            return statement

        if self._match("USE"):
            module_name = self._expect("IDENTIFIER", "Esperava o nome do modulo.")
            self._consume_statement_end()
            return UseStatement(module_name.value)

        if self._match("TIME"):
            statement = TimeStatement(self._parse_expression())
            self._consume_statement_end()
            return statement

        if self._match("IF"):
            return self._parse_if_statement()

        if self._match("LOOP"):
            return self._parse_loop_statement()

        if self._check("IDENTIFIER") and self._check_next("ASSIGN"):
            name = self._advance().value
            self._advance()
            expression = self._parse_expression()
            self._consume_statement_end()
            return AssignmentStatement(name, expression)

        if self._check("ELIF") or self._check("ELSE") or self._check("RPAREN"):
            token = self._current()
            raise ParserError(
                f"Linha {token.line}, coluna {token.column}: bloco inesperado."
            )

        expression = self._parse_expression()
        self._consume_statement_end()
        return ExpressionStatement(expression)

    def _parse_if_statement(self) -> IfStatement:
        branches = [IfBranch(self._parse_expression(), self._parse_block())]
        else_body: list[Statement] | None = None
        self._skip_newlines()

        while self._match("ELIF"):
            branches.append(IfBranch(self._parse_expression(), self._parse_block()))
            self._skip_newlines()

        if self._match("ELSE"):
            else_body = self._parse_block()
            self._skip_newlines()

        return IfStatement(branches, else_body)

    def _parse_loop_statement(self) -> LoopStatement:
        variable_name = self._expect(
            "IDENTIFIER", "Esperava o nome da variavel do loop."
        ).value
        self._expect("FROM", "Esperava a palavra-chave 'from'.")
        start_expression = self._parse_expression()
        self._expect("TO", "Esperava a palavra-chave 'to'.")
        end_expression = self._parse_expression()
        body = self._parse_block()
        self._skip_newlines()
        return LoopStatement(variable_name, start_expression, end_expression, body)

    def _parse_block(self) -> list[Statement]:
        self._expect("LPAREN", "Esperava '(' para abrir o bloco.")
        self._skip_newlines()
        statements: list[Statement] = []

        while not self._check("RPAREN"):
            if self._check("EOF"):
                token = self._current()
                raise ParserError(
                    f"Linha {token.line}, coluna {token.column}: bloco nao foi fechado."
                )

            statements.append(self._parse_statement())
            self._skip_newlines()

        self._advance()
        return statements

    def _parse_expression(self) -> Expression:
        return self._parse_or()

    def _parse_or(self) -> Expression:
        expression = self._parse_and()
        while self._match("OR"):
            operator = self._previous().token_type
            right = self._parse_and()
            expression = BinaryExpression(expression, operator, right)
        return expression

    def _parse_and(self) -> Expression:
        expression = self._parse_equality()
        while self._match("AND"):
            operator = self._previous().token_type
            right = self._parse_equality()
            expression = BinaryExpression(expression, operator, right)
        return expression

    def _parse_equality(self) -> Expression:
        expression = self._parse_comparison()
        while self._match("EQ", "NEQ"):
            operator = self._previous().token_type
            right = self._parse_comparison()
            expression = BinaryExpression(expression, operator, right)
        return expression

    def _parse_comparison(self) -> Expression:
        expression = self._parse_term()
        while self._match("GT", "LT", "GTE", "LTE"):
            operator = self._previous().token_type
            right = self._parse_term()
            expression = BinaryExpression(expression, operator, right)
        return expression

    def _parse_term(self) -> Expression:
        expression = self._parse_factor()
        while self._match("PLUS", "MINUS"):
            operator = self._previous().token_type
            right = self._parse_factor()
            expression = BinaryExpression(expression, operator, right)
        return expression

    def _parse_factor(self) -> Expression:
        expression = self._parse_unary()
        while self._match("STAR", "SLASH"):
            operator = self._previous().token_type
            right = self._parse_unary()
            expression = BinaryExpression(expression, operator, right)
        return expression

    def _parse_unary(self) -> Expression:
        if self._match("NOT", "MINUS"):
            operator = self._previous().token_type
            operand = self._parse_unary()
            return UnaryExpression(operator, operand)

        return self._parse_call()

    def _parse_call(self) -> Expression:
        expression = self._parse_primary()

        while True:
            # Em cabecalhos como "if condicao (" o parenteses abre bloco, nao chamada.
            if self._check("LPAREN") and not self._check_next("NEWLINE"):
                self._advance()
                arguments: list[Expression] = []
                if not self._check("RPAREN"):
                    arguments.append(self._parse_expression())
                    while self._match("COMMA"):
                        arguments.append(self._parse_expression())
                self._expect("RPAREN", "Esperava ')' para fechar a chamada.")
                expression = CallExpression(expression, arguments)
                continue

            if self._match("DOT"):
                member_name = self._expect_member_name()
                expression = MemberAccessExpression(expression, member_name)
                continue

            break

        return expression

    def _expect_member_name(self) -> str:
        allowed_types = {
            "IDENTIFIER",
            "WRITE",
            "INSERT",
            "RESPOND",
            "USE",
            "TIME",
            "IF",
            "ELIF",
            "ELSE",
            "LOOP",
            "FROM",
            "TO",
            "AND",
            "OR",
            "NOT",
            "TRUE",
            "FALSE",
        }
        token = self._current()
        if token.token_type in allowed_types:
            self._advance()
            return str(token.value)

        raise ParserError(
            f"Linha {token.line}, coluna {token.column}: Esperava o nome do membro apos '.'."
        )

    def _parse_primary(self) -> Expression:
        if self._match("NUMBER"):
            return Literal(self._previous().value)

        if self._match("STRING"):
            return Literal(self._previous().value)

        if self._match("TRUE"):
            return Literal(True)

        if self._match("FALSE"):
            return Literal(False)

        if self._match("RESPOND"):
            return RespondExpression()

        if self._match("IDENTIFIER"):
            return Variable(self._previous().value)

        if self._match("LPAREN"):
            expression = self._parse_expression()
            self._expect("RPAREN", "Esperava ')' para fechar a expressao.")
            return expression

        token = self._current()
        raise ParserError(
            f"Linha {token.line}, coluna {token.column}: expressao invalida."
        )

    def _consume_statement_end(self) -> None:
        if self._match("NEWLINE"):
            self._skip_newlines()
            return

        if self._check("EOF") or self._check("RPAREN"):
            return

        token = self._current()
        raise ParserError(
            f"Linha {token.line}, coluna {token.column}: fim de linha esperado."
        )

    def _skip_newlines(self) -> None:
        while self._match("NEWLINE"):
            pass

    def _match(self, *token_types: str) -> bool:
        if self._check(*token_types):
            self._advance()
            return True
        return False

    def _expect(self, token_type: str, message: str) -> Token:
        if self._check(token_type):
            return self._advance()

        token = self._current()
        raise ParserError(f"Linha {token.line}, coluna {token.column}: {message}")

    def _check(self, *token_types: str) -> bool:
        if self._is_at_end():
            return "EOF" in token_types
        return self._current().token_type in token_types

    def _check_next(self, token_type: str) -> bool:
        next_index = self.index + 1
        if next_index >= len(self.tokens):
            return token_type == "EOF"
        return self.tokens[next_index].token_type == token_type

    def _advance(self) -> Token:
        if not self._is_at_end():
            self.index += 1
        return self.tokens[self.index - 1]

    def _previous(self) -> Token:
        return self.tokens[self.index - 1]

    def _current(self) -> Token:
        return self.tokens[self.index]

    def _is_at_end(self) -> bool:
        return self._current().token_type == "EOF"
