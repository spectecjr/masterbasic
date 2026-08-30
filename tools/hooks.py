"""The hooks MasterBASIC adds: codes 155 to 157 and 175 to 185.

The DOS's own hook codes are named in its source and described in
ref/masterdos/docs/hook-interface.md.  These fourteen are not: they are
MasterBASIC's, and the MasterBASIC manual never mentions the hook
interface at all -- no occurrence of "hook", "RST" or "&08" anywhere in
it, which is consistent with it being a user manual rather than a
technical one.  So each name below comes from reading the routine.

They are called from a block at &7B00-&7E6A that runs in the ROM's own
page: it reaches ROM system variables directly, calls the ROM's HLJUMP
at &0005, and cannot see the extension page, which is why it has to come
back through RST &08 rather than call anything here.

Codes 155 to 157 sit among the DOS's own, in four slots MasterDOS fills
with HDUMMY; MasterBASIC points three of them at routines of its own.

Names describe what each routine demonstrably does.  Where that is not
the same as knowing what it is *for*, the header says so.  Three are
certain -- 180 and 181 are the serial driver, confirmed against the
SCC2691 datasheet, and 156 swaps a block that is exactly 41 character
definitions and ends exactly where PALTAB begins.  182 is nearly so.
The rest are readings.
"""

NAMES = {
    0x6534: 'HK_PIXELCELL',
    0x7159: 'HK_SWAPCHARS',
    0x732A: 'HK_PROGPREP',
    0x53C3: 'HK_MERGECOMPFLG',
    0x5AE3: 'HK_FARSCAN',
    0x52FD: 'HK_TOKENARG',
    0x6F62: 'HK_SKIPNAME',
    0x4E37: 'HK_PUTARG',
    0x4300: 'HK_SERSEND',
    0x4315: 'HK_SERRECV',
    0x5973: 'HK_SUBCHAR',
    0x6F3E: 'HK_COMADENT',
    0x5293: 'HK_VARSPACE',
    0x71FE: 'HK_SETUPREGS',
}

DOCS = {

0x6534: """Hook code 155.  Turn a pixel position into a character cell.

Parses two values, keeps one in D and works on the other.  That one is
range-checked to 6..176 and anything outside is abandoned, which is the
usable height of the screen rather than its full 0..191.  Three RRCAs
and AND &1F then divide it by eight and keep five bits -- the character
row -- and a result below 3 is forced to 0.  The other coordinate is
masked with AND 7 straight after, which is the pixel offset within a
cell.

Named for the arithmetic, which is unmistakable.  What the cell is then
used for is not established here.""",

0x7159: """Hook code 156.  Swap the top of the character set for another.

Takes an integer and rejects 3 or more with "Integer out of range", so
the argument is 0, 1 or 2.  If it differs from the byte kept at XVAR
&4074, that byte is updated and 328 bytes are *exchanged* -- not
copied -- between &5490 in the ROM's system page and a buffer at &7E64
in this page, a byte at a time through the alternate accumulator.

Those 328 bytes are 41 characters of eight rows each.  The ROM's
character set starts at CHARSVAL, &5190, and the block swapped begins
&300 bytes into it, which is 96 characters along, and ends exactly
where PALTAB begins.  Counting from CHR$ 32, that is CHR$ 128 upwards:
the block graphics and the user-defined characters.

So this swaps one set of graphics characters for another and remembers
which is in place.  Exchanging rather than copying is what lets it
swap back with the same code.""",

0x732A: """Hook code 157.  Prepare the ROM for a program that is about to change.

Pages the ROM's system page in, clears bits 0 and 2 of the byte at
&5BB6 -- which is DCT, though the label here reads DOS_PCN2 because
&9BB6 is also an address in the other page -- and calls a helper with
those bits down.  The old value is kept on the stack and its bit 0
decides what happens next: either the ROM vector at &4D11 is pointed
at EXPT1NUM, or a routine in the DOS page is called and its result,
plus one, is written to PROG.

PROG is the ROM's start-of-program pointer, so the second path moves
where BASIC thinks the program begins.  That is the strongest clue to
what this is for, and it is still only a clue.""",
0x53C3: """\
Hook code 175.  Carry one bit of COMPFLG into DCT.

Reads COMPFLG -- the ROM's "flag bits used by label/FN/PROC compiler" --
keeps bit 0, ORs it into DCT, sets bit 2 as well, writes DCT back and
clears COMPFLG.  Both are reached through NRRD and NRWR, so both are
ROM system variables rather than anything of the extension's.

What the merged bit means is not established here; the routine is named
for the operation, not for a purpose.""",

0x5AE3: """\
Hook code 176.  Scan memory in another page.

Saves HMPR, masks the page number to five bits and pages it in before
walking the bytes, so it reads memory outside the extension's own page.
The surrounding routines compare bytes against a length-prefixed string.

This is very likely the engine behind INSTRING, which the manual says
searches "over 200K/second" and can be pointed at any part of memory
including the program and variables areas -- but that identification is
from context rather than from anything in the routine itself.""",

0x52FD: """\
Hook code 177.  Read the argument after one of MasterBASIC's keywords.

Fetches the next character and subtracts &26, then branches on the next
three values in turn, so it dispatches on tokens &26, &27 and &28 --
which are in the range MasterBASIC gives its own functions.  A fourth
path tests for &15 and calls POINTC in the DOS page; anything else
reports "Not understood".""",

0x6F62: """\
Hook code 178.  Step over a name and say whether it is a string.

Takes the current character, then reads forward while the classifier at
L4555 keeps saying the character belongs to a name.  CHADD is updated to
where it stopped, and the character that ended it is compared with "$".""",

0x4E37: """\
Hook code 179.  Read the argument of a PUT.

Tests for "P", evaluates an integer, and points HL at PUTSWA -- XVAR 0,
which the manual describes as the address of the PUT dispatch byte,
"POKE it 0 for the ROM PUT, 172 for ours".  It reads LMPR, calls into
the DOS page, and returns the ROM's STKEND in DE.""",

0x4300: """\
Hook code 180.  Send one character over the serial line.

See SERINIT for the register map.  C is SPORT and B selects the
register: it polls SR for bit 3, TxEMT, then writes the character to
THR.  Waiting for TxEMT rather than TxRDY gives up the chip's
one-character lookahead and sends strictly one at a time.

The poll calls ESCCHK, so a line with nothing listening can be escaped
from instead of hanging the machine.""",

0x4315: """\
Hook code 181.  Read one character from the serial line.

The mirror of the hook above: polls SR for bit 0, RxRDY, then reads RHR.
RxRDY is set while any of the receiver's three FIFO positions is full, so
this drains characters that arrived earlier.  SR bits 4 to 7 -- overrun,
parity, framing and received break -- are never looked at, so a line
error is not reported; it just yields a wrong character.""",

0x5973: """\
Hook code 182.  Substitute a character on its way to the printer.

Compares the character with MODCHAR1 and MODCHAR2 -- XVARs 60 and 61,
which the manual gives as the pound sign and the hash -- and on a match
sends MODMSG1 or MODMSG2 in its place.  That is the mechanism behind the
manual's account of making a printer produce the right symbol for
characters whose codes differ between the SAM and the printer.""",

0x6F3E: """\
Hook code 183.  Find an entry through COMAD.

If the test at L44DF fails, &FF is written to the ROM variable at &5A60
first.  Then COMAD is read as a word and &6C added to it, and LMPR is
read.  &6C is a fixed displacement into whatever COMAD points at.

Named for what it computes.  What lives at COMAD+&6C is not established
here.""",

0x5293: """\
Hook code 184.  Check the room above the variables area.

Reads NVARS as a word and gives up unless its high byte is &BB or more,
then gathers NVARSP and RAMTOP.  Those are the ROM's pointers to the
variables area and the top of BASIC's memory.

The manual's RESERVED function allocates heap space "at the expense of
BASIC's GOSUB/DO/PROC stack" and warns that over-allocating gives "Out
of memory", which is the kind of test this makes -- but the connection
is inference, not something the routine states.""",

0x71FE: """\
Hook code 185.  Set up four bytes in the DOS page, then a table.

Pages HMPR to zero, copies four bytes into the DOS page at &4D50, and
goes on to a second block at L7E03.  Saving and restoring HMPR around
the copy is the usual sign of reaching into a page the caller had
mapped elsewhere.

It is called from the block at &7BE0, on the path taken when FLAGX bit
5 is set -- the ROM's INPUT-in-progress flag -- so it belongs to the
editing and INPUT path rather than to anything on the command side.""",
}
