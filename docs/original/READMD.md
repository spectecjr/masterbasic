# READ ME

This directory holds the original MasterBASIC documentation as published, kept
here unedited so that anything the disassembly claims can be checked against
what the authors actually wrote.

| | |
|---|---|
| `MasterBASIC User Manual.md` | the manual, transcribed |
| `SAM Coupé MasterBASIC Manual.pdf` | the scan it was transcribed from |
| `MasterBASIC Change Log.txt` | the author's own change log |
| `ERRATA.md` | corrections, several of which the code confirms |
| `LICENSE and COPYRIGHT.md` | who owns this and on what terms |

SAM Coupe MasterBASIC Manual copied from http://www.samcoupe-pro-dos.co.uk/sammanual.html

http://www.samcoupe-pro-dos.co.uk/contactme.html

## Looking for the disassembly?

Start at [clean/masterbasic.asm](../../clean/masterbasic.asm) and
[clean/masterdos.asm](../../clean/masterdos.asm) — the reading copy, with every
routine headed by what it does and why.

[disasm/](../../disasm/) has the same code with the working notes left in: where
a name came from, what an earlier reading got wrong, which claims are still
open. Read that one when you want the argument rather than the answer.

Where the manual and the code disagree, the disagreement is written down rather
than resolved silently — [docs/bugs.md](../bugs.md) collects the cases where the
code is wrong, and `docs/original/ERRATA.md` the cases where the manual is.
