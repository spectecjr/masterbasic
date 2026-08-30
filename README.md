# MD+MBAS17

A disassembly of `MasterDOS 2.3 + MasterBASIC 1.7` for the SAM Coupé, built as
assembler source that can be proved correct: assembling it reproduces the
original file byte for byte.

## What the file is

`file/MasterBasicMasterDos.bin` is a SAM Coupé CODE file of 32640 bytes: a
nine-byte header followed by the 32631 bytes it declares.

The sector chain has already been followed. A disc sector holds 510 bytes of
payload and two link bytes naming the next one, and those links are **not** in
this file — 64 × 510 is exactly 32640, where 64 × 512 would be 32768. So it is
the payloads concatenated, nothing more.

The header is part of the loaded image rather than something to skip: it sits at
offset 0 of the first half, so `BOOT` begins at `&4009` and `&4000`–`&4008` is
the header itself.

It is **two 16320-byte halves that end up in different RAM pages**, and that is
the one thing to understand before reading any of it:

| | |
|---|---|
| file `0`–`16319` | MasterDOS 2.3, with MasterBASIC's patches spliced in |
| file `16320`–`32639` | MasterBASIC 1.7 |

**Both halves are assembled to run at `&4000`–`&7FBF`**, and each is written to
see the other at `&8000`–`&BFBF`. Which is which depends on the paging at the
time: with the DOS at `&4000` the extension is at `&8000`, and when the extension
takes over the two swap. That is why the DOS's message pointer at `&4210` holds
`&9200` while the extension calls `&BD79` — each is reaching into the other page.

So it is two address spaces, not one, and it is disassembled as two files. A
reference to `&8000`–`&BFBF` is resolved against the other half and written with
its label under a `DOS_` or `MB_` prefix.

## Which one to read

**Read `disasm/`.** Those two files hold what can be shown: names carried from
sources that assemble to the same bytes, tables read from the ROM, and
descriptions from the MasterBASIC manual. Where something could not be
established, they say so rather than guessing.

**`speculate/` is a reading, not a record.** It is the same two listings with a
derived register contract on every routine and a machine-composed guess at what
each one is for, every guess marked with a leading `?`. It is useful for finding
your way around 2,177 routines; it is not evidence. Its
[README](speculate/README.md) sets out where it is wrong and why.

**`postinstall/` is a third kind again: a reconstruction.** MasterBASIC
copies two blocks into the ROM's own system page at boot and points
CMDV, EDITV, RST8V and five more vectors at them, so the code the ROM
actually calls lives at &46CC and &484D and appears in `disasm/` only at
the addresses it was stored at. `tools/syspage.py` builds that page and
disassembles it where it really runs. It cannot be verified by
assembling -- there is no original to compare it with -- and it says so
at the top of itself.

Both `disasm/` and `speculate/` assemble to the original bytes — everything added is a comment — so all
four files are checked on every build.

## Rebuilding

```sh
python -m pip install pyz80
tools/build.sh
```

Exit status is 0 only if all four listings come back byte-identical:

```text
masterdos.asm: BYTE-IDENTICAL
masterbasic.asm: BYTE-IDENTICAL
speculate/masterdos.asm: BYTE-IDENTICAL
speculate/masterbasic.asm: BYTE-IDENTICAL
```

The build assembles the annotated MasterDOS source and the SAM ROM first, for
their symbol tables and BASIC token tables, then disassembles the image against
them, then reassembles everything it wrote and compares. Nothing is left to be
checked by eye.

The two reference trees are submodules:

```sh
git submodule update --init
```

## Where things live

| | |
|---|---|
| `file/` | the image being disassembled |
| `disasm/` | the two listings — **start here** |
| `speculate/` | the same, with a reading of every routine |
| `postinstall/` | the ROM's system page as MasterBASIC leaves it |
| `notes/` | hand-written names and descriptions, fed into both |
| `tools/` | the disassembler and the passes that annotate it |
| `docs/` | how it works, how it is built, the manual, the write-ups |
| `docs/original/` | the MasterBASIC manual as scanned, and its errata |
| `ref/masterdos/` | annotated MasterDOS 2.3 source (submodule) |
| `ref/samrom/` | SAM Coupé ROM 3.0 source (submodule) |
| `dsks/` | the original disk images |

[docs/how-it-works.md](docs/how-it-works.md) is the narrative: what
MasterBASIC does, how it gets the ROM to call it, how it finds the ROM in
the first place, and what is still unexplained. Read that before the
listings.

[docs/disassembly.md](docs/disassembly.md) is the other long form: how the
listings are built, what each pass contributes, and what is still open.

## Adding your own knowledge

`notes/*.txt` is the way in for anything you work out yourself. Adding a name
costs one line and no code:

```text
MB &5934 SERINIT
    Set up the SCC2691 for LPRINT MODE 2.

AFTER CHECK_WRITE_STATUS : read the controller status through the patched port
RENAME ULA BORDER
EQU STKEND : end of the calculator stack
DOS &4220-&42BC data DVAR
DOS &4835 value DISKCTL_0_BASE
```

Nine kinds of entry, by address or by label name. Hand-written entries beat
anything the tools worked out, and a disagreement is reported rather than
resolved silently — as is a name that matches nothing, or one that matches an
address in both pages. A typo is reported and skipped; it cannot break the build.
The rules are at the top of [tools/notes.py](tools/notes.py), with examples in
[notes/example.txt](notes/example.txt).

## Where it stands

Every one of the 32640 bytes is accounted for:

| | bytes |
|---|---|
| Code | 29064 (89.0%) |
| Variables and other data | 2630 |
| Inline call parameters | 717 |
| Message and keyword text | 590 |
| `RST &08` codes | 31 |
| Pointer tables | 10 |
| Unclassified | 0 |

No label lands inside an instruction. 648 routines carry a description above
them -- some written by hand after reading the code, the rest the annotated
MasterDOS author's, carried across where the two instruction streams still
agree. That is a minority of the 2,177 the disassembler segments, and the
remainder are named but not explained.

## Credit

MasterDOS and MasterBASIC were written by Andrew J. A. Wright — the author of the
SAM Coupé ROM itself, which is why the DOS calls internal ROM addresses under the
ROM's own label names. The manual in `docs/original/` was scanned by Steve
Parry-Thomas; the annotated MasterDOS and ROM sources are separate projects,
included here as submodules.
