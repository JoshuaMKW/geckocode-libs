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
code.codetype == Write8.codetype            # True
code.codetype == GeckoCommand.Type.WRITE_8  # True
```

It should be noted that in order to check multiple codetypes at once, `code.codetype` should be used.


## Notes
Please give credit to this project when using it! :)