from typing import Match
from dataclasses import dataclass
import re
from enum import Enum, auto

Span = tuple[int, int]


class TokenType(Enum):
    WHITESPACE = auto()
    COMMENT = auto()
    TYPE = auto()
    KW_BREAK = auto()
    KW_CONTINUE = auto()
    KW_ELSE = auto()
    KW_FOR = auto()
    KW_IF = auto()
    KW_RETURN = auto()
    BOOL_LITERAL = auto()
    FLOAT_LITERAL = auto()
    INT_LITERAL = auto()
    ASSIGN = auto()
    OP = auto()
    BLOCK_BEGIN = auto()
    BLOCK_END = auto()
    PARENTHESES_BEGIN = auto()
    PARENTHESES_END = auto()
    CHAR_LITERAL = auto()
    STRING_LITERAL = auto()
    IDENTIFIER = auto()
    SEMICOLON = auto()
    ERROR = auto()

    def __repr__(self) -> str:
        return f"<{self.name}>"


@dataclass
class Token:
    text: str
    span: Span
    type: TokenType

    def __repr__(self):
        text = self.text.replace("\n", r"\n")
        return f"(token_id: {self.type}, token_string: '{text}')"


@dataclass
class TokenDef:
    regex: re.Pattern
    type: TokenType


tokenizer_list: list[TokenDef] = [
    TokenDef(re.compile(r"\s+"), TokenType.WHITESPACE),
    TokenDef(re.compile(r"//.*$"), TokenType.COMMENT),
    TokenDef(re.compile(r"char|double|float|int"), TokenType.TYPE),
    TokenDef(re.compile(r";"), TokenType.SEMICOLON),
    TokenDef(re.compile("break"), TokenType.KW_BREAK),
    TokenDef(re.compile("continue"), TokenType.KW_CONTINUE),
    TokenDef(re.compile("else"), TokenType.KW_ELSE),
    TokenDef(re.compile("for"), TokenType.KW_FOR),
    TokenDef(re.compile("if"), TokenType.KW_IF),
    TokenDef(re.compile("return"), TokenType.KW_RETURN),
    TokenDef(re.compile("="), TokenType.ASSIGN),
    TokenDef(re.compile(r"true|false"), TokenType.BOOL_LITERAL),
    TokenDef(re.compile(r"[0-9]*\.[0-9]+"), TokenType.FLOAT_LITERAL),
    TokenDef(re.compile(r"[0-9]+"), TokenType.INT_LITERAL),
    TokenDef(re.compile(r"(\+\+)|([-*/+<>])"), TokenType.OP),
    TokenDef(re.compile(r"\{"), TokenType.BLOCK_BEGIN),
    TokenDef(re.compile(r"\}"), TokenType.BLOCK_END),
    TokenDef(re.compile(r"\("), TokenType.PARENTHESES_BEGIN),
    TokenDef(re.compile(r"\)"), TokenType.PARENTHESES_END),
    TokenDef(re.compile(r"'.'"), TokenType.CHAR_LITERAL),
    TokenDef(re.compile(r'".*"'), TokenType.STRING_LITERAL),
    TokenDef(re.compile(r"[A-Za-z_][A-Za-z_0-9]*"), TokenType.IDENTIFIER),
]


def tokenize(text: str) -> list[Token]:
    result = []
    error_start = -1
    offset = 0
    while offset < len(text):
        for token_def in tokenizer_list:
            m: Match = token_def.regex.match(text, offset)
            # Regex do token bateu
            if m is not None:
                span = m.span(0)

                # Porem estava em um erro
                if error_start != -1:
                    # Adiciona o erro a lista de tokens
                    result.append(
                        Token(
                            span=(error_start, offset - 1),
                            text=text[error_start:offset],
                            type=TokenType.ERROR,
                        )
                    )
                    # Limpa o erro
                    error_start = -1

                # Adiciona o token na lista
                offset = span[1]
                result.append(Token(text=m.group(0), span=span, type=token_def.type))
                break
        else:
            if error_start == -1:
                error_start = offset
            offset += 1

    return result
