from enum import Enum
from typing import Type

from dolreader.dol import DolFile

from .gct import GCT

class CodeHandler(object):
    class Binary():
        Riivolution = b""
        Wit = b""
        Dolphin = b""

    class GeckoType(Enum):
        LEGACY = 0
        LATEST = 1

    class Type(Enum):
        RIIVOLUTION = 0
        WIT = 1
        DOLPHIN = 2

    Version = GeckoType.LATEST

    def __init__(self):
        self._handlerType: bytes = CodeHandler.Type.DOLPHIN
        self.gct: GCT = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__dict__})"

    def __str__(self) -> str:
        if self.gct:
            return f"Codehandler of 0x{self.handler:X} bytes handling a {self.gct}"
        else:
            return f"Codehandler of 0x{self.handler:X} bytes"

    def __len__(self) -> int:
        return len(self.handler)

    @property
    def handlerType(self) -> Type:
        return self._handlerType

    @handlerType.setter
    def handlerType(self, ty: Type):
        self._handlerType = ty

    @property
    def handler(self):
        if self.handlerType == CodeHandler.Type.RIIVOLUTION:
            return CodeHandler.Binary.Riivolution
        elif self.handlerType == CodeHandler.Type.WIT:
            return CodeHandler.Binary.Wit
        elif self.handlerType == CodeHandler.Type.DOLPHIN:
            return CodeHandler.Binary.Dolphin
        return None

    def apply(self, dol: DolFile) -> bool:
        self.gct.apply(dol)
        return True