from typing import ClassVar, overload
from dataclasses import dataclass, asdict

from enum import auto, Enum


class CType(Enum):
    INT = auto()
    CHAR = auto()
    FLOAT = auto()
    STRING = auto()
    VOID = auto()


@dataclass(kw_only=True)
class VarState:
    type: CType
    depth: int
    init: bool = False

Vars = dict[str, VarState]

@dataclass(kw_only=True)
class SemanticError:
    msg: ClassVar[str]
    line: int

    def __str__(self) -> str:
        return (self.msg.format(asdict(self)))

@dataclass(kw_only=True)
class UndeclaredError(SemanticError):
    var: str
    msg = 'Undeclared variable "{var}"'

@dataclass(kw_only=True)
class AlreadyDeclaredError(SemanticError):
    var: str
    msg = 'Already declared variable "{var}"'

@dataclass(kw_only=True)
class InvalidVarType(SemanticError):
    type: CType
    msg = '{type} is not allowed as a type here'
    

