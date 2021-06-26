from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Type

from dolreader.dol import DolFile

from .gct import GCT


class CodeHandler(object):
    Binaries: Dict[str, bytes] = {}

    class Hook():
        WiiVIHook = b"\x7C\xE3\x3B\x78\x38\x87\x00\x34\x38\xA7\x00\x38\x38\xC7\x00\x4C"
        GCNVIHook = b"\x7C\x03\x00\x34\x38\x83\x00\x20\x54\x85\x08\x3C\x7C\x7F\x2A\x14\xA0\x03\x00\x00\x7C\x7D\x2A\x14\x20\xA4\x00\x3F\xB0\x03\x00\x00"
        WiiGXDrawHook = b"\x3C\xA0\xCC\x01\x38\x00\x00\x61\x3C\x80\x45\x00\x98\x05\x80\x00"
        GCNGXDrawHook = b"\x38\x00\x00\x61\x3C\xA0\xCC\x01\x3C\x80\x45\x00\x98\x05\x80\x00"
        WiiPADHook = b"\x3A\xB5\x00\x01\x3A\x73\x00\x0C\x2C\x15\x00\x04\x3B\x18\x00\x0C"
        GCNPADHook = b"\x3A\xB5\x00\x01\x2C\x15\x00\x04\x3B\x18\x00\x0C\x3B\xFF\x00\x0C"

    class GeckoType(Enum):
        LEGACY = 0
        LATEST = 1

    Version = GeckoType.LATEST

    def __init__(self): 
        self.gct: GCT = None
        self._populate_binaries()
        self.get_handler("dolphin")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__dict__})"

    def __str__(self) -> str:
        if self.gct:
            return f"Codehandler of 0x{len(self):X} bytes handling a {self.gct}"
        else:
            return f"Codehandler of 0x{len(self):X} bytes"

    def __len__(self) -> int:
        return len(self._binary)

    @property
    def handlerType(self) -> Type:
        return self._handlerType

    @handlerType.setter
    def handlerType(self, ty: Type):
        self._handlerType = ty

    def get_handler(self, name: str) -> bytes:
        """Return the codehandler binary specified as `bytes`"""
        try:
            binary = self.Binaries[name]
            self._name = name
            self._binary = binary
            return binary
        except KeyError:
            return None

    def apply(self, dol: DolFile) -> bool:
        """Apply codes to target dol"""
        self.gct.apply(dol)
        return True

    def _populate_binaries(self):
        for file in Path("handlers").iterdir():
            if file.is_file() and file.suffix.lower() == ".bin":
                self.Binaries[file.name] = file.read_bytes()


class HookHandler(object):
    Hooks = (
        CodeHandler.Hook.WiiVIHook,
        CodeHandler.Hook.GCNVIHook,
        CodeHandler.Hook.WiiGXDrawHook,
        CodeHandler.Hook.GCNGXDrawHook,
        CodeHandler.Hook.WiiPADHook,
        CodeHandler.Hook.GCNPADHook
    )

    def __init__(self, hook: Optional[CodeHandler.Hook] = None):
        self._hook = hook

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__dict__})"

    @property
    def hook(self) -> CodeHandler.Hook:
        return self._hook

    @hook.setter
    def hook(self, hook: CodeHandler.Hook):
        if hook not in HookHandler.Hooks:
            raise ValueError("Unknown hook passed to setter")
        self._hook = hook

    def search(self, data: bytes) -> int:
        """Return the index of the matching data, -1 if not found"""
        return data.find(self._hook)

    def search_dol(self, dol: DolFile) -> int:
        f"""Return the index of the matching data in a {dol.__class__.__name__} object, -1 if not found"""
        for section in dol.sections:
            packet = section.data.getvalue()
            offset = packet.find(self._hook)
            if offset < 0:
                continue
            return section.address + offset
        return -1

    @staticmethod
    def search_any(data: bytes) -> int:
        for hook in HookHandler.Hooks:
            offset = data.find(hook)
            if offset >= 0:
                return offset
        return -1

    @staticmethod
    def search_dol_any(dol: DolFile) -> int:
        for section in dol.sections:
            packet = section.data.getvalue()
            for hook in HookHandler.Hooks:
                offset = packet.find(hook)
                if offset >= 0:
                    return offset
        return -1