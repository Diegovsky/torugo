from dataclasses import dataclass
from enum import auto, Enum
from minic.parser import Expr, DeclStmt


class CType(Enum):
    INT = auto()
    CHAR = auto()
    FLOAT = auto()
    STRING = auto()


@dataclass
class VarState:
    type: CType
    init: bool


@dataclass
class ScopeTable:
    vars: dict[str, VarState]

    def add(self, decl: DeclStmt):
        self.vars[decl.name] = VarState(
            type=CType(decl.type.upper()), init=decl.value is not None
        )

    def init(self, name: str):
        self.vars[name].init = True
