"""The hooks MasterBASIC adds: codes 154 to 157 and 175 to 185.

The DOS's own hook codes are named in its source and described in
ref/masterdos/docs/hook-interface.md.  These fifteen are not: they are
MasterBASIC's, and the MasterBASIC manual never mentions the hook
interface at all -- no occurrence of "hook", "RST" or "&08" anywhere in
it, which is consistent with it being a user manual rather than a
technical one.  So each name below comes from reading the routine.

They are called from a block at &7B00-&7E6A that runs in the ROM's own
page: it reaches ROM system variables directly, calls the ROM's HLJUMP
at &0005, and cannot see the extension page, which is why it has to come
back through RST &08 rather than call anything here.

Codes 154 to 157 sit among the DOS's own, in four slots MasterDOS fills
with HDUMMY; MasterBASIC points all four at routines of its own.  HDUMMY
is the DOS's name for a reserved slot, not a description of anything, so
none of the four keeps it here.

Names describe what each routine demonstrably does.  Where that is not
the same as knowing what it is *for*, the header says so.  Three are
certain -- 180 and 181 are the serial driver, confirmed against the
SCC2691 datasheet, and 156 swaps a block that is exactly 41 character
definitions and ends exactly where PALTAB begins.  182 is nearly so.
The rest are readings.
"""

NAMES = {
    0x5B81: 'HOOK_LPRINT_BYTE',
    0x6534: 'HOOK_CSIZE',
    0x7159: 'HOOK_SWAPCHARS',
    0x732A: 'HOOK_PROGPREP',
    0x53C3: 'HOOK_MERGECOMPFLG',
    0x5AE3: 'HOOK_FARSCAN',
    0x52FD: 'HOOK_TOKENARG',
    0x6F62: 'HOOK_SKIPNAME',
    0x4E37: 'HOOK_XVARNVAL',
    0x4300: 'HOOK_SERSEND',
    0x4315: 'HOOK_SERRECV',
    0x5973: 'HOOK_SUBCHAR',
    0x6F3E: 'HOOK_COMADENT',
    0x5293: 'HOOK_VARSPACE',
    0x71FE: 'HOOK_SETUPREGS',
}

DOCS = {

0x5B81: """Hook code 154.  Put one byte in the interrupt-driven printer
buffer, waiting if it is full.

This is the writing half of the background printer.  The reading half is
PRINTER_FEED_TICK at &59FC, which runs from the interrupt fifty times a
second and sends what is here to the port.

A RING OF 1K SLOTS WITH TWO POINTERS.  V4085/V4086 are the page and
address the tick reads from (it runs in the system page with this half in
the window, and so spells them &8085/&8086), and V4088/V4089 are the page
and address written here.  Equal pointers mean empty, so the writer must
never let its pointer catch the reader's -- hence the wait at &5BBB.

The manual promises exactly that wait: "If the buffer becomes full, the
computer will wait for the printer to deal with some of the data before
finishing the LLIST, DUMP or LPRINT."

The body from &5B8E to &5BBA is the same twenty-five instructions as
WINDOW_SOUND_POINTER at &5B22, which does the same job for the sound
buffer; the only difference is that this stores one byte where that
stores a register number and a value.

Hook 154 is HDUMMY in the DOS's table, a reserved slot; this is what
MasterBASIC put in it.""",

0x6534: """Hook code 155.  CSIZE, the manual's "Improved CSIZE command".

SAM BASIC's own CSIZE takes a width of 6 or 8 and a height of 6 to 32.
This takes any width and a height of 6 to 176, and magnifies the
character to fill it.

THE TWO NUMBERS BECOME MULTIPLICATION FACTORS, not sizes.  The height
is range-checked at &6544 and &6548, then three RRCAs and AND &1F
divide it by eight -- the manual's "INT(height/8) gives the height
multiplication factor" -- and the SUB 6 loop at &656A does the same for
the width in sixes.  Each factor is written to SYS_CHAR_HEIGHT or
SYS_CHAR_WIDTH, and a factor of zero means the ROM can manage this size
unaided.

THE ROM'S OWN CSIZE IS THEN ENTERED PAST ITS RANGE CHECKS.  The
installer at &761F searches the ROM for D6 06 32 -- "SUB 6 / LD
(FL6OR8),A" inside the ROM's WIDTH -- and patches the address five bytes
on into the operand at &6594, so the CALL lands after the checks this
routine has already done for itself.  Only the ROM's window arithmetic
runs.  Everything from &6596 to &65E6 then undoes the parts of that
arithmetic which do not suit a magnified character.

Hook 155 is HDUMMY in the DOS's table, a reserved slot; this is what
MasterBASIC put in it.""",

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

0x732A: """Hook code 157.  Rebuild the compile pass for a program that has changed.

Pages the ROM's system page in, clears bits 0 and 2 of the byte at
&5BB6 -- which is DCT, though the label here reads DOS_PCN2 because
&9BB6 is also an address in the other page -- and calls
BUILD_COMPILER with those bits down, which assembles the replacement
for the ROM's compile pass at CDBUFF+&11.  See notes/mb-compiler.txt.

The old value of the byte is kept on the stack, and if its bit 0 was
clear the two bytes &18 &01 are written over the start of what was
just built.  That is JR +1, laid over the CALL the ROM's routine
begins with, so the copy jumps over the third byte of it and the
ROM's CALL SCOMP never runs.

Both paths then call into the DOS page and write its result, plus
one, to PROG, the ROM's start-of-program pointer.

An earlier reading of this had &4D11 as a ROM vector being pointed at
EXPT1NUM, on the strength of &0118 being an address in the ROM's jump
table.  It is not a vector: BUILD_COMPILER copies code there, and
&0118 is two instruction bytes.""",
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
Hook code 179.  The XVAR and NVAL functions.

The two values the stub at &7E03 lets through are F_XVAR - FN_TOKEN_BIAS
and F_NVAL - FN_TOKEN_BIAS -- &4E and &50.  XVAR and NVAL are the two
MasterBASIC functions that take an argument with no bracket, which is why
the token printer at &50CE singles the same pair out.  The &50 that looks
like the letter "P" is NVAL's, and it goes to FN_NVAL.

THE BIAS IS THE ROM'S, NOT A CHOSEN CONSTANT.  ABOVLETS reads the byte
after the FF and does SUB &1A -- "ADJUST 3B-83H TO 21H-69H" -- before
calling through EVALUV, so every function hook is handed its token less
that.  The assembler checks the subtraction on every build.

F_XVAR - FN_TOKEN_BIAS is XVAR n.  It evaluates the integer, points HL
at PUTSWA -- this page's &4000, which is XVAR 0 -- and enters the DOS at
&6579, just past that routine's own LD HL,DVAR.  So XVAR n is the DOS's DVAR code aimed
at MasterBASIC's page instead of its own.  The ROM's STKEND comes back
in DE either way.

The &1A is read off the two constants, not from the ROM.""",

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
Hook code 185.  Build a routine in the ROM's code buffer.

It writes HL to XPTR, then pages HMPR to zero and copies into &4D50.
That is not the DOS page: with HMPR zero an &8xxx is the ROM's system
page, and &4D50 there is CDBUFF+&50 -- the buffer the ROM's variable
table describes as being for e.g. MULTI-LDI, max length &181.

What it copies is code.  The four bytes at V7221 are &21 &60 &5A &7E,
which is LD HL,&5A60 followed by LD A,(HL), and the &61 bytes from
L7E03 are appended straight after them.  So a routine is assembled
head-first in the buffer, and &4D50 -- its address -- is then handed to
STORE_BC_AT_XVAR76, which writes it through the pointer in V4076.  The
routine at &735D builds into the same buffer at &4D11, far enough
along to overlap this one, so the two are alternative uses of it
rather than both being live at once.

It is called from the block at &7BE0, on the path taken when FLAGX bit
5 is set -- the ROM's INPUT-in-progress flag -- so it belongs to the
editing and INPUT path rather than to anything on the command side.""",
}
