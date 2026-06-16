from typing import Literal
from dataclasses import dataclass
from .lexer import Token, TokenType, Span

# parser: declaração, atribuição, condição, repetição, expressões + recuperação
# semantico:

Op = str


def is_bin_op(op: str) -> bool:
    return op in "+-*/"


def is_prefix_op(op: str) -> bool:
    return op in {"++", "-"}


def is_postfix_op(op: str) -> bool:
    return op == "++"


@dataclass
class Node:
    line: int


class Stmt(Node):
    pass


class Expr(Stmt):
    pass


class Err(Node):
    pass


@dataclass
class UnOp(Expr):
    op: Op
    expr: Expr


@dataclass
class BinOp(Expr):
    left: Expr
    op: Op
    right: Expr


@dataclass
class LiteralExpr(Expr):
    value: int | float | str | bool
    type: Literal["int", "float", "char", "string", "var", "bool"]


@dataclass
class DeclStmt(Stmt):
    name: str
    type: str
    value: Expr | None


@dataclass
class AttributionStmt(Stmt):
    name: str
    value: Expr


@dataclass
class Block(Stmt):
    statements: list[Stmt]
    pass


@dataclass
class ForStmt(Stmt):
    decl: DeclStmt
    condition: Expr
    increment: Expr
    block: Block


@dataclass
class IfStmt(Stmt):
    condition: Expr
    block: Block
    otherwise: Block | None


class ParseError(Exception):
    line: int

    def __init__(self, msg: str, line: int):
        self.line = line
        super().__init__(msg)


class UnexpectedTokenError(ParseError):
    def __init__(self, expected: TokenType | list[TokenType], got: Token, line: int):
        self.expected = expected
        self.got = got
        super().__init__(f"Expected {expected}, got {got}", line)


class Parser:
    errors: list[ParseError]

    def __init__(self, text: str, tokens: list[Token]):
        self.tokens = [token for token in tokens if token.type != TokenType.WHITESPACE]
        self.text = text
        self.at = 0
        self.errors = []

    @property
    def line(self) -> int:
        try:
            start = self.peek().span[0]
        except IndexError:
            start = -1
        return self.text[:start].count("\n") + 1

    def peek(self) -> Token:
        return self.tokens[self.at]

    def expect_type(self, expect: TokenType):
        token = self.peek()
        if token.type != expect:
            raise UnexpectedTokenError(expect, token, self.line)
        self.next()

    def is_type(self, expect: TokenType) -> bool:
        return self.peek().type == expect

    def next(self):
        self.at += 1

    def semicolon(self):
        self.expect_type(TokenType.SEMICOLON)

    def _simple_expr(self) -> Expr:
        tk = self.peek()
        line = self.line
        match tk.type:
            case TokenType.OP:
                self.next()
                return UnOp(op=tk.text, expr=self.expr(), line=line)
            case TokenType.INT_LITERAL:
                self.next()
                return LiteralExpr(value=int(tk.text), type="int", line=line)
            case TokenType.FLOAT_LITERAL:
                self.next()
                return LiteralExpr(value=float(tk.text), type="float", line=line)
            case TokenType.BOOL_LITERAL:
                self.next()
                return LiteralExpr(value=bool(tk.text), type='bool', line=line)
            case TokenType.STRING_LITERAL:
                self.next()
                return LiteralExpr(value=tk.text, type="string", line=line)
            case TokenType.CHAR_LITERAL:
                self.next()
                return LiteralExpr(value=tk.text, type="char", line=line)
            case TokenType.IDENTIFIER:
                self.next()
                return LiteralExpr(value=tk.text, type="var", line=line)
            case _:
                raise ParseError(f"Got {tk}", self.line)

    def expr(self) -> Expr:
        left = self._simple_expr()
        while self.is_type(TokenType.OP):
            tk = self.peek()
            op = tk.text
            self.next()
            if is_bin_op(op):
                right = self.expr()
                left = BinOp(left=left, op=op, right=right, line=self.line)
            elif is_postfix_op(op):
                left = UnOp(expr=left, op=op, line=self.line)
            else:
                raise ParseError(f"Got {tk}", self.line)
        return left

    def decl(self) -> DeclStmt:
        type = self.peek().text
        self.expect_type(TokenType.TYPE)

        name = self.peek().text
        self.expect_type(TokenType.IDENTIFIER)

        value = None
        if self.is_type(TokenType.ASSIGN):
            self.next()

            value = self.expr()

        self.semicolon()

        return DeclStmt(name=name, type=type, value=value, line=self.line - 1)

    def attribution(self) -> AttributionStmt:
        name = self.peek().text
        self.expect_type(TokenType.IDENTIFIER)

        self.expect_type(TokenType.ASSIGN)

        value = self.expr()

        self.semicolon()

        return AttributionStmt(name=name, value=value, line=self.line - 1)

    def stmt(self) -> Stmt:
        here = self.at
        try:
            expr = self.expr()
            self.semicolon()
            return expr
        except ParseError:
            self.at = here

        tk = self.peek()
        match tk.type:
            case TokenType.KW_FOR:
                return self.repetition()
            case TokenType.KW_IF:
                return self.condition()
            case TokenType.TYPE:
                return self.decl()
            case TokenType.BLOCK_BEGIN:
                return self.block()
            case TokenType.IDENTIFIER:
                return self.attribution()
            case _:
                raise ParseError(f"Got {tk}", self.line)

    def condition(self) -> IfStmt:
        self.expect_type(TokenType.KW_IF)
        self.expect_type(TokenType.PARENTHESES_BEGIN)
        condition = self.expr()
        self.expect_type(TokenType.PARENTHESES_END)
        block = self.block()
        if self.is_type(TokenType.KW_ELSE):
            self.next()
            otherwise = self.block()

        return IfStmt(
            condition=condition, block=block, otherwise=otherwise, line=self.line
        )

    def block(self) -> Block:
        self.expect_type(TokenType.BLOCK_BEGIN)

        stmts = []
        while not self.is_type(TokenType.BLOCK_END):
            try:
                stmts.append(self.stmt())
            except ParseError as e:
                self.errors.append(e)
                self.at += 1
                pass

        self.next()

        return Block(statements=stmts, line=self.line)

    def repetition(self) -> ForStmt:
        self.expect_type(TokenType.KW_FOR)
        self.expect_type(TokenType.PARENTHESES_BEGIN)

        decl = self.decl()
        codition = self.expr()
        self.semicolon()
        increment = self.expr()

        self.expect_type(TokenType.PARENTHESES_END)

        block = self.block()

        return ForStmt(
            decl=decl,
            condition=codition,
            increment=increment,
            block=block,
            line=self.line,
        )
