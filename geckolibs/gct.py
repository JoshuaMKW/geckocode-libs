from io import BytesIO, StringIO
import sys
from typing import BinaryIO, Iterable, List, TextIO, Union

from dolreader.dol import DolFile

from .geckocode import GeckoCommand, InvalidGeckoCommandError


class GCT(object):

    MAGIC = b"\x00\xD0\xC0\xDE\x00\xD0\xC0\xDE"

    def __init__(self):
        self._codes: List[GeckoCommand] = []

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__dict__})"

    def __str__(self) -> str:
        return f"GCT containing {self.virtual_length()} codes, at 0x{len(self):X} bytes long"

    def __len__(self) -> int:
        return sum([len(c) for c in self]) + 16

    def __iter__(self):
        self._iterpos = 0
        return self

    def __next__(self) -> GeckoCommand:
        try:
            self._iterpos += 1
            return self[self._iterpos-1]
        except IndexError:
            raise StopIteration

    def __getitem__(self, index: int) -> GeckoCommand:
        return self._codes[index]

    def __setitem__(self, index: int, value: GeckoCommand):
        if not isinstance(value, GeckoCommand):
            raise InvalidGeckoCommandError(
                f"Cannot assign {value.__class__.__name__} as a child of {self.__class__.__name__}")

        self._codes[index] = value

    def __hash__(self) -> str:
        return sum([hash(c) for c in self])

    def __eq__(self, other: "GCT") -> bool:
        return hash(self) == hash(other)

    def __ne__(self, other: "GCT") -> bool:
        return hash(self) != hash(other)

    def __iadd__(self, other: Union["GCT", GeckoCommand]):
        if isinstance(other, GCT):
            for code in other:
                self.add_child(code)
        elif isinstance(other, GeckoCommand):
            self.add_child(other)
        else:
            raise TypeError(f"{other.__class__.__name__} cannot be added to a {self.__class__.__name__}")

    @classmethod
    def from_bytes(cls, f: Union[BinaryIO, bytes]) -> "GCT":
        if isinstance(f, bytes):
            f = BytesIO(f)

        magic = f.read(8)
        assert magic == GCT.MAGIC, f"GCT magic not found (0x{magic.hex()} != 0x{GCT.MAGIC.hex()})"

        gct = cls()
        while True:
            try:
                code = GeckoCommand.bytes_to_geckocommand(f)
                gct.add_child(code)
                if code.codetype == GeckoCommand.Type.EXIT:
                    break
            except Exception:
                break

        return gct

    @classmethod
    def from_text(cls, f: Union[TextIO, str]) -> "GCT":
        if isinstance(f, str):
            f = StringIO(f)

        magic = f.read(8)
        assert magic == GCT.MAGIC, f"GCT magic not found (0x{magic.hex()} != 0x{GCT.MAGIC.hex()})"

        gct = cls()
        while True:
            try:
                code = GeckoCommand.str_to_geckocommand(f)
                gct.add_child(code)
                if code.codetype == GeckoCommand.Type.EXIT:
                    break
            except Exception:
                break

        return gct

    @property
    def children(self) -> Iterable[GeckoCommand]:
        for code in self._codes:
            yield code
            if GeckoCommand.is_ifblock(code):
                yield from code.children

    def add_child(self, code: GeckoCommand):
        if len(self._codes) > 0:
            if self._codes[-1].codetype == GeckoCommand.Type.EXIT:
                if code.codetype != GeckoCommand.Type.EXIT:
                    self._codes.insert(len(self._codes) - 1, code)
                    return
        self._codes.append(code)

    def remove_child(self, code: GeckoCommand):
        return self._codes.remove(code)

    def virtual_length(self) -> int:
        return sum([c.virtual_length() for c in self])

    def apply(self, dol: DolFile) -> bool:
        for code in self:
            code.apply(dol)
        return True

    def as_bytes(self) -> bytes:
        magic = b"\x00\xD0\xC0\xDE\x00\xD0\xC0\xDE"
        packet = b""
        for code in self:
            packet += code.as_bytes()
        return magic + packet

    def as_text(self) -> str:
        magic = "00D0C0DE 00D0C0DE\n"
        packet = ""
        for code in self:
            packet += code.as_text() + "\n"
        return (magic + packet).strip()
        
    def print_map(self, buffer: TextIO = sys.stdout, indent: int = 2):
        def printer(code: GeckoCommand, indention: int):
            print(" "*indention + str(code), file=buffer)
            if GeckoCommand.is_ifblock(code):
                for child in code:
                    printer(child, indention + indent)
        for code in self:
            printer(code, 0)