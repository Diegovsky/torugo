from enum import auto, Enum
from typing import Literal, ClassVar
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from .lexer import Token, TokenType


class CType(Enum):
    INT = auto()
    CHAR = auto()
    FLOAT = auto()
    BOOL = auto()
    VOID = auto()


Op = str


def is_bin_op(op: str) -> bool:
    return op in "+-*/<>"


def is_prefix_op(op: str) -> bool:
    return op in {"++", "-"}


def is_postfix_op(op: str) -> bool:
    return op == "++"


@dataclass(kw_only=True)
class SemanticError:
    msg: ClassVar[str]
    line: int

    def __str__(self) -> str:
        return self.msg.format(**asdict(self))


@dataclass(kw_only=True)
class IllegalCommandError(SemanticError):
    command: str
    msg = "Illegal command `{command}`"


@dataclass(kw_only=True)
class UndeclaredError(SemanticError):
    var: str
    msg = 'Undeclared variable "{var}"'


@dataclass(kw_only=True)
class UninitializedVarError(SemanticError):
    var: str
    msg = 'Use of uninitialized variable "{var}"'


@dataclass(kw_only=True)
class UnusedVarError(SemanticError):
    var: str
    msg = 'Variable "{var}" is declared but not used'


@dataclass(kw_only=True)
class AlreadyDeclaredError(SemanticError):
    var: str
    msg = 'Already declared variable "{var}"'


@dataclass(kw_only=True)
class InvalidVarType(SemanticError):
    type: CType
    msg = "{type} is not allowed as a type here"


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


@dataclass(kw_only=True)
class VarState:
    type: CType
    depth: int
    line: int
    init: bool = False
    used: bool = False


Vars = dict[str, VarState]


@dataclass
class Node:
    line: int


class Stmt(Node):
    pass


class Expr(Stmt):
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
class FuncCallExpr(Expr):
    name: str
    args: list[Expr]


@dataclass
class LiteralExpr(Expr):
    value: int | float | str | bool
    type: Literal["int", "float", "char", "string", "var", "bool"]


@dataclass
class ReturnStmt(Stmt):
    expr: Expr


class BreakStmt(Stmt):
    pass


class ContinueStmt(Stmt):
    pass


@dataclass
class DeclStmt(Stmt):
    name: str
    type: CType
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
class Arg(Node):
    type: CType
    name: str


@dataclass
class FuncDef(Stmt):
    name: str
    type: CType
    args: list[Arg]
    block: Block


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


class Parser:
    errors: list[ParseError | SemanticError]
    warnings: list[SemanticError]
    in_for: bool
    at: int
    text: str
    tokens: list[Token]
    scope: Vars
    depth: int

    def __init__(self, text: str, tokens: list[Token]):
        self.tokens = tokens
        self.text = text
        self.at = 0
        self.depth = 0
        self.errors = []
        self.warnings = []
        self.scope = {}
        self.in_for = False

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

    def declare(self, name: str, type: CType):
        var = self.scope.get(name, None)
        if var is not None:
            if var.depth == self.depth:
                self.errors.append(AlreadyDeclaredError(line=self.line, var=name))
                return

        self.scope[name] = VarState(type=type, depth=self.depth, line=self.line)

    def define(self, name: str):
        var = self.scope.get(name, None)
        if var is None:
            self.errors.append(UndeclaredError(line=self.line, var=name))
            return

        var.init = True

    def use(self, name: str):
        var = self.scope.get(name, None)
        if var is None:
            self.errors.append(UndeclaredError(line=self.line, var=name))
            return
        if not var.init:
            self.warnings.append(UninitializedVarError(line=self.line, var=name))

        var.used = True

    def is_type(self, expect: TokenType) -> bool:
        return self.peek().type == expect

    def next(self):
        self.at += 1

    def semicolon(self):
        self.expect_type(TokenType.SEMICOLON)

    def type(self) -> CType:
        type = self.peek().text
        self.expect_type(TokenType.TYPE)
        return CType[type.upper()]

    def ident(self) -> str:
        ident = self.peek().text
        self.expect_type(TokenType.IDENTIFIER)
        return ident

    @contextmanager
    def _new_scope(self: "Parser"):
        prev_scope = self.scope.copy()
        self.depth += 1
        try:
            yield
        finally:
            for k, v in self.scope.items():
                if v.depth < self.depth:
                    prev_scope[k] = v
                else:
                    if not v.used:
                        self.warnings.append(UnusedVarError(line=v.line, var=k))

            self.scope = prev_scope
            self.depth -= 1

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
                return LiteralExpr(value=bool(tk.text), type="bool", line=line)
            case TokenType.STRING_LITERAL:
                self.next()
                return LiteralExpr(value=tk.text, type="string", line=line)
            case TokenType.CHAR_LITERAL:
                self.next()
                return LiteralExpr(value=tk.text, type="char", line=line)
            case TokenType.IDENTIFIER:
                self.next()
                if self.is_type(TokenType.PARENTHESES_BEGIN):
                    self.next()
                    args = []
                    while not self.is_type(TokenType.PARENTHESES_END):
                        args.append(self.expr())
                        match self.peek().type:
                            case TokenType.COMMA:
                                self.next()
                                continue
                            case TokenType.PARENTHESES_END:
                                break

                    self.next()
                    return FuncCallExpr(name=tk.text, line=self.line, args=args)

                else:
                    self.use(tk.text)
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

    def decl_stmt(self) -> DeclStmt:
        type = self.type()
        name = self.ident()
        self.declare(name, type)

        if type == CType.VOID:
            self.errors.append(InvalidVarType(line=self.line, type=type))

        value = None
        if self.is_type(TokenType.ASSIGN):
            self.next()

            value = self.expr()
            self.define(name)

        self.semicolon()

        return DeclStmt(name=name, type=type, value=value, line=self.line - 1)

    def attribution_stmt(self) -> AttributionStmt:
        name = self.peek().text
        self.expect_type(TokenType.IDENTIFIER)
        self.expect_type(TokenType.ASSIGN)

        self.define(name)

        value = self.expr()
        self.semicolon()

        return AttributionStmt(name=name, value=value, line=self.line - 1)

    def stmt(self) -> Stmt:
        tk = self.peek()
        match tk.type:
            case TokenType.KW_FOR:
                return self.for_stmt()
            case TokenType.KW_IF:
                return self.if_stmt()
            case TokenType.TYPE:
                return self.decl_stmt()
            case TokenType.BLOCK_BEGIN:
                return self.block()
            case TokenType.IDENTIFIER:
                if self.tokens[self.at + 1].type == TokenType.ASSIGN:
                    return self.attribution_stmt()
                else:
                    expr = self.expr()
                    self.semicolon()
                    return expr

            case TokenType.KW_RETURN:
                self.next()
                expr = self.expr()
                self.semicolon()
                return ReturnStmt(line=self.line - 1, expr=expr)

            case TokenType.KW_BREAK:
                self.next()
                self.semicolon()
                if not self.in_for:
                    self.errors.append(
                        IllegalCommandError(command=tk.text, line=self.line)
                    )
                return BreakStmt(line=self.line - 1)

            case TokenType.KW_CONTINUE:
                self.next()
                self.semicolon()
                if not self.in_for:
                    self.errors.append(
                        IllegalCommandError(command=tk.text, line=self.line)
                    )
                return ContinueStmt(line=self.line - 1)
            case _:
                raise ParseError(f"Parsing statement, got {tk}", self.line)

    def if_stmt(self) -> IfStmt:
        self.expect_type(TokenType.KW_IF)
        self.expect_type(TokenType.PARENTHESES_BEGIN)
        condition = self.expr()
        self.expect_type(TokenType.PARENTHESES_END)
        with self._new_scope():
            block = self.block()

        otherwise = None
        if self.is_type(TokenType.KW_ELSE):
            self.next()
            with self._new_scope():
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

    def for_stmt(self) -> ForStmt:
        with self._new_scope():
            self.expect_type(TokenType.KW_FOR)
            self.expect_type(TokenType.PARENTHESES_BEGIN)

            decl = self.decl_stmt()
            codition = self.expr()
            self.semicolon()
            increment = self.expr()

            self.expect_type(TokenType.PARENTHESES_END)

            old_in_for = self.in_for
            try:
                self.in_for = True
                block = self.block()
            finally:
                self.in_for = old_in_for

            return ForStmt(
                decl=decl,
                condition=codition,
                increment=increment,
                block=block,
                line=self.line,
            )

    def func_def(self) -> FuncDef:
        type = self.type()
        fname = self.ident()

        line = self.line

        with self._new_scope():
            args = []
            self.expect_type(TokenType.PARENTHESES_BEGIN)
            while not self.is_type(TokenType.PARENTHESES_END):
                type = self.type()
                argname = self.ident()
                self.declare(argname, type)

                if type == CType.VOID:
                    self.errors.append(InvalidVarType(line=self.line, type=type))

                args.append(Arg(type=type, name=argname, line=self.line))

                match self.peek().type:
                    case TokenType.COMMA:
                        self.next()
                        continue
            self.next()
            block = self.block()

            return FuncDef(name=fname, type=type, args=args, block=block, line=line)

    def parse(self) -> list[FuncDef | DeclStmt]:
        vals = []
        while self.at + 2 < len(self.tokens):
            peek3 = self.tokens[self.at + 2]
            match peek3.type:
                case TokenType.SEMICOLON | TokenType.ASSIGN:
                    vals.append(self.decl_stmt())
                case TokenType.PARENTHESES_BEGIN:
                    vals.append(self.func_def())
                case _:
                    self.errors.append(
                        UnexpectedTokenError(
                            line=self.line,
                            got=peek3,
                            expected=[
                                TokenType.SEMICOLON,
                                TokenType.ASSIGN,
                                TokenType.PARENTHESES_BEGIN,
                            ],
                        )
                    )
                    self.at += 1

        return vals

    def print_diagnostics(self):
        if self.errors:
            print("Errors:")
            for warn in self.errors:
                print("\t", warn)
                print("\t\tLine: ", warn.line)
        if self.warnings:
            print("Warnings:")
            for warn in self.warnings:
                print("\t", warn)
                print("\t\tLine: ", warn.line)
