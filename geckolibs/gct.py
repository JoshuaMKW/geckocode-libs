import sys
from enum import Enum
from io import BytesIO, StringIO
from pathlib import Path
from typing import BinaryIO, Dict, Iterable, TextIO, Union

from dolreader.dol import DolFile

from .geckocode import Exit, GeckoCode, GeckoCommand, InvalidGeckoCodeError


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

    Magic = b"\x00\xD0\xC0\xDE\x00\xD0\xC0\xDE"
    VolatileToken = "[[volatile]]"

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
            return list(self._codes.values())[self._iterpos-1]
        except IndexError:
            raise StopIteration

    def __getitem__(self, key: Union[str, int]) -> GeckoCode:
        if isinstance(key, str):
            return self._codes[key]
        else:
            return list(self._codes.values())[key]

    def __setitem__(self, key: str, value: GeckoCode):
        if not isinstance(value, GeckoCode):
            raise InvalidGeckoCodeError(
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
        assert magic == GeckoCodeTable.Magic, f"GeckoCodeTable magic not found (0x{magic.hex()} != 0x{GeckoCodeTable.Magic.hex()})"

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
        _foundEnabled = False

        mode = GeckoCodeTable.detect_codelist_type(f)
        if mode == GeckoTextType.DOLPHIN:
            f.seek(0)
            while f.tell() < len(f.getvalue()):
                line = f.readline().strip()
                if line == "[Gecko_Enabled]":
                    _foundEnabled = True
                    line = f.readline().strip()
                    while line.startswith("$"):
                        enabledCodes.add(line[1:].strip())
                        line = f.readline().strip()
                    break

        f.seek(0)

        name = ""
        author = ""
        desc = []
        data = []
        _gameInfoCollected = False
        while f.tell() < len(f.getvalue()):
            line = f.readline()
            sLine = line.strip()
            isPreApplicable = True
            if sLine.lower().endswith(GeckoCodeTable.VolatileToken):
                isPreApplicable = False
                sLine = sLine[:-len(GeckoCodeTable.VolatileToken)].strip()
            if mode == GeckoTextType.DOLPHIN:
                if line == "":
                    continue
                elif line.startswith("$"):
                    if len(data) > 0:
                        code = GeckoCode.from_text(
                            "\n".join(data).strip(), name.strip(), author, "\n".join(desc), enabled=(name in enabledCodes or not _foundEnabled), preapplicable=isPreApplicable)
                        gct.add_child(code)
                        data.clear()
                        desc.clear()
                    n = sLine[::-1].find("[") + 1
                    if n == 0:
                        name = sLine[1:]
                        author = None
                    else:
                        name = sLine[1:-n].strip()
                        author = sLine[-n+1:-1].strip()
                elif line.startswith("*"):
                    desc.append(line[1:-1])
                else:
                    if "".join(sLine.split()).isalnum():
                        data.append(sLine)
            elif mode == GeckoTextType.OCARINA:
                if sLine == "":
                    name = ""
                    author = ""
                    desc.clear()
                    data.clear()
                    continue
                elif not _gameInfoCollected:
                    gct.gameID = line.strip()
                    gct.gameName = f.readline().strip()
                    _gameInfoCollected = True
                    continue

                n = sLine[::-1].find("[") + 1
                if n == 0:
                    name = sLine
                    author = None
                else:
                    name = sLine[:-n].strip()
                    author = sLine[-n+1:-1].strip()

                _firstPass = True
                _enabled = False
                _descReading = False
                while f.tell() < len(f.getvalue()):
                    sLine = f.readline().strip()
                    if _firstPass:
                        _enabled = sLine.startswith("*")
                    elif len(sLine.lstrip("*").strip()) == 17 and not _descReading:
                        data.append(f"{sLine[1:].strip()}")
                    elif sLine != "":
                        _descReading = True
                        desc.append(sLine)
                    else:
                        gct.add_child(GeckoCode.from_text(
                            "\n".join(data), name, author, "\n".join(desc), _enabled), preapplicable=isPreApplicable)
                        name = ""
                        author = ""
                        desc.clear()
                        data.clear()
                        break
                    _firstPass = False
            else:
                if sLine != "":
                    data.append(sLine)
                else:
                    data.clear()

                if f.tell() >= len(f.getvalue()):
                    if len(data) > 0:
                        gct.add_child(GeckoCode.from_text(
                            "\n".join(data).strip()))
                    data.clear()

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
        packet = b""
        for code in self:
            packet += code.as_bytes()
        return GeckoCodeTable.Magic + packet + b"\xF0\x00\x00\x00\x00\x00\x00\x00"

    def as_text(self) -> str:
        """Return the textual representation of this GCT"""
        magic = "00D0C0DE 00D0C0DE\n"
        packet = ""
        for code in self:
            packet += f"{code.as_text()}\n"
        return (magic + packet + "F0000000 00000000").strip()

    def as_codelist(self, ty: GeckoTextType = GeckoTextType.DOLPHIN) -> str:
        """Return this GCT as a textual codelist of the type specified by `ty`"""
        if ty == GeckoTextType.DOLPHIN:
            codelist = "[Gecko]\n"
            enableds = "[Gecko_Enabled]\n"
            for code in self:
                author = ""
                desc = "*\n"
                token = ""
                if code.author:
                    author = f" [{code.author}]"
                if code.desc:
                    desc = "*" + "\n*".join(code.desc.split("\n")) + "\n"
                if not code.is_preapplicable():
                    token = " " + GeckoCodeTable.VolatileToken
                codelist += f"${code.name}{author}{token}\n{code.as_text()}\n{desc}"
                if code.is_enabled():
                    enableds += f"${code.name}\n"
            return f"{codelist}{enableds.rstrip()}"
        elif ty == GeckoTextType.OCARINA:
            codelist = f"{self.gameID.strip()}\n{self.gameName.strip()}\n\n"
            for code in self:
                author = ""
                desc = ""
                token = ""
                if code.author:
                    author = f" [{code.author}]"
                if code.desc:
                    desc = code.desc + "\n"
                if not code.is_preapplicable():
                    token = " " + GeckoCodeTable.VolatileToken
                data = '\n* '.join(code.as_text().split('\n'))
                codelist += f"{code.name}{author}{token}\n* {data}\n{desc}\n"
            return codelist.rstrip()
        else:
            codelist = ""
            for code in self:
                codelist += f"{code.as_text()}\n\n"
            return codelist.rstrip()

    def print_map(self, buffer: TextIO = sys.stdout, indent: int = 2, startindent: int = 0):
        """Print a human readable indented map of this GCT"""
        _prev = GeckoCommand._IndentionWidth
        GeckoCommand._IndentionWidth = indent
        GeckoCommand._IndentionStart = startindent
        for code in self:
            for command in code:
                print(command)
        GeckoCommand._IndentionWidth = _prev
        print(str(Exit()), file=buffer)
