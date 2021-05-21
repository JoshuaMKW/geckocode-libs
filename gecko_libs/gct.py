import sys
from typing import IO, Iterable, List, TextIO

from dolreader.dol import DolFile

from .geckocode import GeckoCode, InvalidGeckoCodeError


class GCT(object):

    MAGIC = b"\x00\xD0\xC0\xDE\x00\xD0\xC0\xDE"

    def __init__(self):
        self._codes: List[GeckoCode] = []

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__dict__})"

    def __str__(self) -> str:
        return f"GCT containing {self.virtual_length()} codes, at 0x{len(self):X} bytes long"

    def __len__(self) -> int:
        return sum([len(c) for c in self]) + 16

    def __iter__(self):
        self._iterpos = 0
        return self

    def __next__(self) -> GeckoCode:
        try:
            self._iterpos += 1
            return self[self._iterpos-1]
        except IndexError:
            raise StopIteration

    def __getitem__(self, index: int) -> GeckoCode:
        return self._codes[index]

    def __setitem__(self, index: int, value: GeckoCode):
        if not isinstance(value, GeckoCode):
            raise InvalidGeckoCodeError(
                f"Cannot assign {value.__class__.__name__} as a child of {self.__class__.__name__}")

        self._codes[index] = value

    def __hash__(self) -> str:
        return "".join([str(c) for c in self])

    @classmethod
    def from_bytes(cls, f: IO) -> "GCT":
        magic = f.read(8)
        assert magic == GCT.MAGIC, f"GCT magic not found (0x{magic.hex()} != 0x{GCT.MAGIC.hex()})"

        gct = cls()
        while True:
            try:
                code = GeckoCode.bytes_to_geckocode(f)
                gct.add_child(code)
                if code.codetype == GeckoCode.Type.EXIT:
                    break
            except Exception:
                break

        return gct

    @property
    def children(self) -> Iterable[GeckoCode]:
        for code in self._codes:
            yield code
            if GeckoCode.is_ifblock(code):
                yield from code.children

    def add_child(self, code: GeckoCode):
        self._codes.append(code)

    def remove_child(self, code: GeckoCode):
        return self._codes.remove(code)

    def virtual_length(self) -> int:
        return sum([c.virtual_length() for c in self])

    def apply(self, dol: DolFile) -> bool:
        for code in self:
            code.apply(dol)
        return True

    def as_bytes(self) -> bytes:
        start = b"\x00\xD0\xC0\xDE\x00\xD0\xC0\xDE"
        end = b"\xF0\x00\x00\x00\x00\x00\x00\x00"
        packet = b""
        for code in self:
            packet += code.as_bytes()
        return start + packet + end

    def as_text(self) -> str:
        start = "00D0C0DE00D0C0DE"
        end = "F000000000000000"
        packet = ""
        for code in self:
            packet += code.as_text()
        return start + packet + end
        
    def print_map(self, buffer: TextIO = sys.stdout, indent: int = 2):
        def printer(code: GeckoCode, indention: int):
            print(" "*indention + str(code), file=buffer)
            if GeckoCode.is_ifblock(code):
                for child in code:
                    printer(child, indention + indent)
        for code in self:
            printer(code, 0)