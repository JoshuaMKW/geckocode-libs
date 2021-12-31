from pathlib import Path
import sys
import time

from io import StringIO
from geckolibs.gct import GeckoCodeTable, GeckoTextType

VERBOSE = False

def assert_output_equality(_type: GeckoTextType, inFile: Path, outFile: Path, asMap: bool = False, lengthRestricted: bool = False):
    if inFile.suffix.lower() == ".gct":
        with inFile.open("rb") as f:
            _gct = GeckoCodeTable.from_bytes(f)
    else:
        with inFile.open("r") as f:
            _gct = GeckoCodeTable.from_text(f)
    test = outFile.read_text().strip()
    if asMap:
        buf = StringIO()
        _gct.print_map(buffer=buf)
        text = buf.getvalue()
    else:
        text = _gct.as_codelist(_type)
    if lengthRestricted:
        test = test[:len(text)]
    if VERBOSE:
        print(text.strip(), test, sep="\n\n")
    if text.strip() != test:
        print(f"Test case {inFile.name} failed")
    else:
        print(f"Test case {inFile.name} succeeded")




assert_output_equality(GeckoTextType.OCARINA, Path("tests/ocarina.txt"), Path("tests/ocarina.txt"))
assert_output_equality(GeckoTextType.DOLPHIN, Path("tests/dolphin.txt"), Path("tests/dolphin.txt"), lengthRestricted=True)
assert_output_equality(GeckoTextType.RAW, Path("tests/raw.txt"), Path("tests/raw.txt"))
assert_output_equality(GeckoTextType.RAW, Path("tests/print_map.gct"), Path("tests/print_map_output.txt"), asMap=True)