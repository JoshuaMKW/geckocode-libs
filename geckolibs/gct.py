import sys
from enum import Enum
from io import BytesIO, StringIO
from pathlib import Path
from typing import BinaryIO, Dict, Iterable, List, TextIO, Union

from dolreader.dol import DolFile

from .geckocode import GeckoCode, GeckoCommand, InvalidGeckoCommandError


class GeckoTextType(Enum):
    DOLPHIN = "DOLPHIN"
    OCARINA = "OCARINA"
    RAW = "RAW"


class GeckoCodeTable(object):
    """
    A class representing the popular \"GCT\" format used for applying patches to a Gamecube/Wii game.

    Data:\n
    `gameID`:                The 6 character string representing the ID of the game this GCT is meant for.
    `gameName`:              The name of the game this GCT is meant for.
    `children`:              The `GeckoCode`s that this GCT contains.

    Static Methods:\n
    `detect_codelist_type`:  Detect the type of codelist given to this method.
    `from_data`:             Create and return a new `GeckoCodeTable` that is populated using the bytes given to this method.
    `from_text`:             Create and return a new `GeckoCodeTable` that is populated using the text given to this method.

    Methods:\n
    `add_child`:             Add a `GeckoCode` to this GCT.
    `remove_child`:          Remove a `GeckoCode` from this GCT.
    `virtual_length`:        Returns the length of this GCT in Gecko \"lines\".
    `apply`:                 Apply this GCT to the `DolFile` given to this method.
    `apply_f`:               Apply this GCT to the DOL at the path given to this method.
    `as_bytes`:              Returns the raw data representation of this GCT.
    `as_text`:               Returns the textual representation of this GCT.
    `as_codelist`:           Returns this GCT as a codelist of the type given to this method.
    `print_map`:             Prints an indented map of each `GeckoCommand` in this GCT in human readable form.
    """

    gameID: str
    gameName: str

    MAGIC = b"\x00\xD0\xC0\xDE\x00\xD0\xC0\xDE"

    def __init__(self, gameID: str = "GECK01", gameName: str = "geckocode-libs"):
        self.gameID = gameID
        self.gameName = gameName
        self._codes: Dict[str, GeckoCode] = {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__dict__})"

    def __str__(self) -> str:
        return f"GeckoCodeTable containing {self.virtual_length()} codes, at 0x{len(self):X} bytes long"

    def __len__(self) -> int:
        return sum([len(c) for c in self]) + 16

    def __iter__(self):
        self._iterpos = 0
        return self

    def __next__(self) -> GeckoCode:
        try:
            self._iterpos += 1
            return self._codes.values()[self._iterpos-1]
        except IndexError:
            raise StopIteration

    def __getitem__(self, key: str) -> GeckoCode:
        return self._codes[key]

    def __setitem__(self, key: str, value: GeckoCode):
        if not isinstance(value, GeckoCode):
            raise InvalidGeckoCommandError(
                f"Cannot assign {value.__class__.__name__} as a child of {self.__class__.__name__}")

        self._codes[key] = value

    def __hash__(self) -> str:
        return sum([hash(c) for c in self])

    def __eq__(self, other: "GeckoCodeTable") -> bool:
        return hash(self) == hash(other)

    def __ne__(self, other: "GeckoCodeTable") -> bool:
        return hash(self) != hash(other)

    def __iadd__(self, other: Union["GeckoCodeTable", GeckoCommand]):
        if isinstance(other, GeckoCodeTable):
            for code in other:
                self.add_child(code)
        elif isinstance(other, GeckoCommand):
            self.add_child(other)
        else:
            raise TypeError(
                f"{other.__class__.__name__} cannot be added to a {self.__class__.__name__}")

    @staticmethod
    def detect_codelist_type(f: Union[Path, TextIO, str]) -> GeckoTextType:
        """Return the type of codelist that was detected"""
        if isinstance(f, str):
            f = StringIO(f)
        elif isinstance(f, Path):
            f = StringIO(f.read_text())

        for line in f.readlines():
            line = line.strip()
            if line == "":
                continue
            elif line == "[Gecko]":
                return GeckoTextType.DOLPHIN
            elif len(line) == 6:
                return GeckoTextType.OCARINA
            else:
                return GeckoTextType.RAW

    @classmethod
    def from_bytes(cls, f: Union[BinaryIO, bytes]) -> "GeckoCodeTable":
        """Create a new `GeckoCodeTable` from raw bytes"""
        if isinstance(f, bytes):
            f = BytesIO(f)

        magic = f.read(8)
        assert magic == GeckoCodeTable.MAGIC, f"GeckoCodeTable magic not found (0x{magic.hex()} != 0x{GeckoCodeTable.MAGIC.hex()})"

        gct = cls()
        gct.add_child(GeckoCode.from_bytes(f))
        return gct

    @classmethod
    def from_text(cls, f: Union[TextIO, str]) -> "GeckoCodeTable":
        """Create a new `GeckoCodeTable` from a textual codelist"""
        if not isinstance(f, StringIO):
            if isinstance(f, str):
                f = StringIO(f)
            else:
                f = StringIO(f.read())

        gct = cls()
        enabledCodes = set()

        mode = GeckoCodeTable.detect_codelist_type(f)
        if mode == GeckoTextType.DOLPHIN:
            f.seek(0)
            for line in f.readlines():
                if line == "[Gecko_Enabled]":
                    while (name := f.readline()).startswith("$"):
                        enabledCodes.add(name[1:].strip())
                    break

        data = ""
        name = ""
        author = ""
        desc = ""
        _gameInfoCollected = False
        while True:
            if f.tell() == len(f.getvalue()):
                break

            line = f.readline().strip()
            if mode == GeckoTextType.DOLPHIN:
                if line == "":
                    continue
                elif line.startswith("$"):
                    n = line[::-1].find("[") - 1
                    name = line[:n].lstrip("$").strip()
                    author = line[n+1:-1].strip()
                    while True:
                        line = f.readline().strip()
                        if line.startswith("*"):
                            desc += f"{line[1:].strip()}\n"
                        elif line != "":
                            data += f"{line}\n"
                        else:
                            gct.add_child(GeckoCode.from_text(
                                data.rstrip(), name, author, desc))
                            data = ""
                            name = ""
                            author = ""
                            desc = ""
                            break
            elif mode == GeckoTextType.OCARINA:
                if line == "":
                    continue
                elif not _gameInfoCollected:
                    gct.gameID = line.strip()
                    gct.gameName = f.readline().strip()
                    continue

                n = line[::-1].find("[") - 1
                name = line[:n].lstrip("$").strip()
                author = line[n+1:-1].strip()
                while True:
                    if line.startswith("*"):
                        data += f"{line[1:].strip()}\n"
                    elif line != "":
                        desc += f"{line}\n"
                    else:
                        gct.add_child(GeckoCode.from_text(
                            data.rstrip(), name, author, desc))
                        data = ""
                        name = ""
                        author = ""
                        desc = ""
                        break
            else:
                if line == "":
                    if data != "":
                        gct.add_child(GeckoCode.from_text(data.rstrip()))
                    data = ""
                else:
                    data += f"{line}\n"

        return gct

    @property
    def children(self) -> Iterable[GeckoCommand]:
        for code in self._codes.values():
            yield code
            yield from code.children

    def add_child(self, code: GeckoCode):
        """Adds the given `GeckoCode` to the list"""
        self._codes[code.name] = code

    def remove_child(self, code: Union[GeckoCode, str]):
        """Removes the given `GeckoCode` from the list"""
        if isinstance(code, GeckoCode):
            self._codes.pop(code.name)
        else:
            self._codes.pop(code)

    def get_child(self, name: str) -> GeckoCode:
        """Returns the `GeckoCode` with the given name, or `None` if not found"""
        try:
            return self._codes[name]
        except KeyError:
            return None

    def virtual_length(self) -> int:
        """Returns the length of this GCT in Gecko \"lines\""""
        return sum([c.virtual_length() for c in self])

    def apply(self, dol: DolFile) -> bool:
        """Apply this GCT directly to a DOL if supported as provided by a `DolFile`

           Return True if the command is successfully applied"""
        status = False
        for code in self:
            status |= code.apply(dol)
        return status

    def apply_f(self, dolpath: str) -> bool:
        """Apply this GCT directly to a DOL if supported as provided by a file path

           Return True if the command is successfully applied"""
        with open(str(dolpath), "rb") as f:
            dol = DolFile(f)

        success = self.apply(dol)
        if not success:
            return False

        with open(str(dolpath), "wb") as f:
            dol.save(f)

        return True

    def as_bytes(self) -> bytes:
        """Return the raw data representation of this GCT"""
        magic = b"\x00\xD0\xC0\xDE\x00\xD0\xC0\xDE"
        packet = b""
        for code in self:
            packet += code.as_bytes()
        return magic + packet

    def as_text(self) -> str:
        """Return the textual representation of this GCT"""
        magic = "00D0C0DE 00D0C0DE\n"
        packet = ""
        for code in self:
            packet += f"{code.as_text()}\n"
        return (magic + packet).strip()

    def as_codelist(self, ty: GeckoTextType = GeckoTextType.DOLPHIN) -> str:
        """Return this GCT as a textual codelist of the type specified by `ty`"""
        if ty == GeckoTextType.DOLPHIN:
            codelist = "[Gecko]\n"
            enableds = "[Gecko_Enabled]\n"
            for code in self:
                codelist += f"${code.name} [{code.author}]\n{code.as_text()}\n*{'\n*'.join(code.desc.split('\n'))}\n"
                if code.is_enabled():
                    enableds += f"${code.name}\n"
            return f"{codelist}{enableds.rstrip()}"
        elif ty == GeckoTextType.OCARINA:
            codelist = f"{self.gameID.strip()}\n{self.gameName.strip()}\n\n"
            for code in self:
                codelist += f"{code.name} [{code.author}]\n* {'\n* '.join(code.as_text().split('\n'))}\n{code.desc}\n"
            return codelist.rstrip()
        else:
            codelist = ""
            for code in self:
                codelist += f"{code.as_text()}\n\n"
            return codelist.rstrip()

    def print_map(self, buffer: TextIO = sys.stdout, indent: int = 2):
        """Print a human readable indented map of this GCT"""
        def printer(command: GeckoCommand, indention: int):
            print(" "*indention + str(command), file=buffer)
            if command.is_ifblock():
                for child in command:
                    printer(child, indention + indent)
        for code in self:
            for command in code:
                printer(command, 0)
