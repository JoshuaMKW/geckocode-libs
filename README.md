# geckocode-libs

Python library for parsing and editing Gecko Codes for the Wii/GCN

## Installation

`pip install geckolibs`

## Usage

With `geckocode-libs`, file parsing is simple to do.

You can read a textual codelist into a `GeckoCodeTable` using the method `GeckoCodeTable.from_text(our_text)`, which automatically detects the type of codelist being read and handles all the dirty work for you! This returns a new GeckoCodeTable object.

You can also read a raw codelist from a GCT using the method `GeckoCodeTable.from_bytes(our_bytes)`, which parses the raw bytes given to the method into a new GeckoCodeTable object.

When you are done editing your GCT, you can convert the object back into a codelist, text, or raw data using the methods `GeckoCodeTable.as_codelist(codelist_type)`, `GeckoCodeTable.as_text()`, and `GeckoCodeTable.as_bytes()` respectively.

You can also create your own codes using the library itself, an example shown here:

```python
gct = GeckoCodeTable()                      # Empty GCT
code = GeckoCode("Our awesome code", "Me")  # Empty GeckoCode named "Our awesome code", created by "Me"
command = Write32(0x60000000, 0x80231480)   # Individual command

code.add_child(command)                     # Add a command to the code
gct.add_child(code)                         # Add a code to the GCT
```

Type checking of codes can be done in 3 ways:

```python
code = Write8(69, 0x80203932)

code == Write8                              # True
code == Write8.codetype                     # True
code.codetype == Write8.codetype            # True
code.codetype == GeckoCommand.Type.WRITE_8  # True
```

It should be noted that in order to check multiple codetypes at once, `code.codetype` should be used.

## Example

```python
>>> from geckolibs.geckocode import *
>>> from geckolibs.gct import *
>>> 
>>> ifblock = IfEqual32(0x00D0C0DE, 0x80204158)
>>>
>>> code = WriteString(b"\x00\x01\x02\x03\x04\x05", 0x80023994)
>>> ifblock.add_child(code)
>>>
>>> code = AsmInsert(b"\x38\x03\x00\x01\x38\x00\x00\x18", 0x80291358)
>>> ifblock.add_child(code)
>>>
>>> geckocode = GeckoCode("Test Code", "JoshuaMK", "Testing our new code!", ifblock)
>>> geckocode.add_child(Terminator(0x80008000))
>>>
>>> print(geckocode)

Test Code [JoshuaMK]
  Testing our new code!

>>> print(geckocode.as_text())

20204158 00D0C0DE
06023994 00000006
00010203 04050000
C2291358 00000002
38030001 38000018
60000000 00000000
E0000000 80008000

>>> for command in geckocode:  
...     print(command)        
...

(20) If the word at address (0x00204158 + the base address) is equal to 0x00D0C0DE:
    (06) Write 6 bytes to 0x00023994 + the base address
    (C2) Inject (b / b) the designated ASM at 0x00291358 + the base address
(E0) Clear the code execution status. Set the base address to 80000000. Set the pointer address to 80000000.
```


## Notes

Please give credit to this project when using it! :)
