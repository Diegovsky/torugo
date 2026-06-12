from typing import Match
import pprint
from dataclasses import dataclass
import re
from enum import Enum, auto


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
    FP_LITERAL = auto()
    INT_LITERAL = auto()
    OP = auto()
    BLOCK_BEGIN = auto()
    BLOCK_END = auto()
    CHAR_LITERAL = auto()
    STRING_LITERAL = auto()
    IDENTIFIER = auto()
    SEMICOLON = auto()


@dataclass
class Token:
    text: str
    span: tuple[int, int]
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
    TokenDef(re.compile(r"char|double|float|int|void|bool"), TokenType.TYPE),
    TokenDef(re.compile("break"), TokenType.KW_BREAK),
    TokenDef(re.compile("continue"), TokenType.KW_CONTINUE),
    TokenDef(re.compile("else"), TokenType.KW_ELSE),
    TokenDef(re.compile("for"), TokenType.KW_FOR),
    TokenDef(re.compile("if"), TokenType.KW_IF),
    TokenDef(re.compile("return"), TokenType.KW_RETURN),
    TokenDef(re.compile(r"[0-9]*\.[0-9]+"), TokenType.FP_LITERAL),
    TokenDef(re.compile(r"[0-9]+"), TokenType.INT_LITERAL),
    TokenDef(re.compile(r"[-*/+]"), TokenType.OP),
    TokenDef(re.compile(r"[\[{(]"), TokenType.BLOCK_BEGIN),
    TokenDef(re.compile(r"[})\]]"), TokenType.BLOCK_END),
    TokenDef(re.compile(r"'.'"), TokenType.CHAR_LITERAL),
    TokenDef(re.compile(r'".*"'), TokenType.STRING_LITERAL),
    TokenDef(re.compile(r"[A-Za-z_][A-Za-z_0-9]*"), TokenType.IDENTIFIER),
    TokenDef(re.compile(r";"), TokenType.SEMICOLON),
]


def tokenize(text: str) -> list[Token]:
    result = []
    offset = 0
    while offset < len(text):
        for token_def in tokenizer_list:
            m: Match = token_def.regex.match(text, offset)
            if m is not None:
                span = m.span(0)
                offset = span[1]
                result.append(Token(text=m.group(0), span=span, type=token_def.type))
                break

    return result


with open("input.txt") as f:
    text = f.read()
    pprint.pprint(tokenize(text))
