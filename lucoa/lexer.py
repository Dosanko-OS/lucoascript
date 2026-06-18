from __future__ import annotations

from dataclasses import dataclass


class LexerError(Exception):
    """Erro levantado quando o codigo-fonte contem simbolos invalidos."""


@dataclass(frozen=True)
class Token:
    token_type: str
    value: object
    line: int
    column: int


class Lexer:
    """Converte o texto-fonte em uma sequencia de tokens."""

    KEYWORDS = {
        "if": "IF",
        "elif": "ELIF",
        "else": "ELSE",
        "loop": "LOOP",
        "from": "FROM",
        "to": "TO",
        "use": "USE",
        "write": "WRITE",
        "insert": "INSERT",
        "respond": "RESPOND",
        "time": "TIME",
        "and": "AND",
        "or": "OR",
        "not": "NOT",
        "true": "TRUE",
        "false": "FALSE",
    }

    SIMPLE_TOKENS = {
        "(": "LPAREN",
        ")": "RPAREN",
        "[": "LBRACKET",
        "]": "RBRACKET",
        "{": "LBRACE",
        "}": "RBRACE",
        ":": "COLON",
        ",": "COMMA",
        ".": "DOT",
        "+": "PLUS",
        "-": "MINUS",
        "*": "STAR",
        "/": "SLASH",
    }

    def __init__(self, source: str) -> None:
        self.source = source
        self.index = 0
        self.line = 1
        self.column = 1

        self.depth = {
            "LPAREN": 0,
            "LBRACKET": 0,
            "LBRACE": 0,
        }

    # -------------------------------------------------------------------------
    # Bug 1 corrigido: as últimas duas linhas do método estavam fora dele
    #   (indentação incorreta no original — ficavam ao nível da classe).
    # Sugestão aplicada: NEWLINE consecutivos também são suprimidos.
    # -------------------------------------------------------------------------
    def _newline_is_whitespace(self, tokens: list[Token]) -> bool:
        # estamos dentro de (), [] ou {}?
        if (
            self.depth["LPAREN"] > 0
            or self.depth["LBRACKET"] > 0
            or self.depth["LBRACE"] > 0
        ):
            return True

        # começo do arquivo
        if not tokens:
            return True

        previous = tokens[-1].token_type

        # NEWLINE consecutivos (linhas em branco) são irrelevantes
        if previous == "NEWLINE":
            return True

        # operadores / vírgula: a expressão ainda está "aberta"
        return previous in {
            "ASSIGN",
            "PLUS",
            "MINUS",
            "STAR",
            "SLASH",
            "COMMA",
            "DOT",
            "AND",
            "OR",
            "NOT",
            "EQ",
            "NEQ",
            "GT",
            "LT",
            "GTE",
            "LTE",
        }

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []

        while not self._is_at_end():
            current = self._peek()

            if current in " \t\r":
                self._advance()
                continue

            # Bug 2 corrigido: _newline_is_whitespace() nunca era chamado;
            # o NEWLINE era emitido incondicionalmente.
            if current == "\n":
                if not self._newline_is_whitespace(tokens):
                    tokens.append(self._make_token("NEWLINE", "\n"))
                self._advance()
                continue

            if current == "#":
                self._skip_comment()
                continue

            if current == '"':
                tokens.append(self._read_string())
                continue

            if current.isdigit():
                tokens.append(self._read_number())
                continue

            if current.isalpha() or current == "_":
                tokens.append(self._read_identifier())
                continue

            # Bug 4 corrigido: prints de debug removidos daqui.
            tokens.append(self._read_symbol())

        tokens.append(Token("EOF", None, self.line, self.column))
        return tokens

    def _read_string(self) -> Token:
        line, column = self.line, self.column
        self._advance()
        characters: list[str] = []

        escapes = {
            "n": "\n",
            "t": "\t",
            '"': '"',
            "\\": "\\",
        }

        while not self._is_at_end() and self._peek() != '"':
            if self._peek() == "\\":
                self._advance()
                if self._is_at_end():
                    raise LexerError(
                        f"Linha {line}, coluna {column}: string nao terminada."
                    )

                escaped = self._peek()
                characters.append(escapes.get(escaped, escaped))
                self._advance()
                continue

            characters.append(self._peek())
            self._advance()

        if self._is_at_end():
            raise LexerError(f"Linha {line}, coluna {column}: string nao terminada.")

        self._advance()
        return Token("STRING", "".join(characters), line, column)

    def _read_number(self) -> Token:
        line, column = self.line, self.column
        start = self.index
        has_decimal = False

        while not self._is_at_end() and self._peek().isdigit():
            self._advance()

        if (
            not self._is_at_end()
            and self._peek() == "."
            and self._peek_next().isdigit()
        ):
            has_decimal = True
            self._advance()
            while not self._is_at_end() and self._peek().isdigit():
                self._advance()

        raw_value = self.source[start : self.index]
        value = float(raw_value) if has_decimal else int(raw_value)
        return Token("NUMBER", value, line, column)

    def _read_identifier(self) -> Token:
        line, column = self.line, self.column
        start = self.index

        while not self._is_at_end() and (self._peek().isalnum() or self._peek() == "_"):
            self._advance()

        value = self.source[start : self.index]
        keyword_type = self.KEYWORDS.get(value.lower())
        if keyword_type is not None:
            return Token(keyword_type, value, line, column)

        return Token("IDENTIFIER", value, line, column)

    # -------------------------------------------------------------------------
    # Bug 3 corrigido: o bloco de atualização de self.depth, o self._advance()
    # final e o return Token(...) estavam fora do método (indentação incorreta
    # no original — ficavam ao nível da classe).
    # -------------------------------------------------------------------------
    def _read_symbol(self) -> Token:
        line, column = self.line, self.column

        two_char_symbols = {
            "==": "EQ",
            "/=": "NEQ",
            ">_": "GTE",
            "<_": "LTE",
        }

        pair = self.source[self.index : self.index + 2]
        if pair in two_char_symbols:
            self._advance()
            self._advance()
            return Token(two_char_symbols[pair], pair, line, column)

        current = self._peek()
        if current == "=":
            self._advance()
            return Token("ASSIGN", "=", line, column)
        if current == ">":
            self._advance()
            return Token("GT", ">", line, column)
        if current == "<":
            self._advance()
            return Token("LT", "<", line, column)

        token_type = self.SIMPLE_TOKENS.get(current)
        if token_type is None:
            raise LexerError(
                f"Linha {line}, coluna {column}: simbolo inesperado '{current}'."
            )

        # atualiza profundidades
        if token_type == "LPAREN":
            self.depth["LPAREN"] += 1
        elif token_type == "RPAREN":
            self.depth["LPAREN"] -= 1
        elif token_type == "LBRACKET":
            self.depth["LBRACKET"] += 1
        elif token_type == "RBRACKET":
            self.depth["LBRACKET"] -= 1
        elif token_type == "LBRACE":
            self.depth["LBRACE"] += 1
        elif token_type == "RBRACE":
            self.depth["LBRACE"] -= 1

        self._advance()
        return Token(token_type, current, line, column)

    def _skip_comment(self) -> None:
        while not self._is_at_end() and self._peek() != "\n":
            self._advance()

    def _make_token(self, token_type: str, value: object) -> Token:
        return Token(token_type, value, self.line, self.column)

    def _is_at_end(self) -> bool:
        return self.index >= len(self.source)

    def _peek(self) -> str:
        return self.source[self.index]

    def _peek_next(self) -> str:
        next_index = self.index + 1
        if next_index >= len(self.source):
            return "\0"
        return self.source[next_index]

    def _advance(self) -> str:
        character = self.source[self.index]
        self.index += 1

        if character == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        return character