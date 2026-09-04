"""What each routine the dispatch tables point at is for.

The tables in the image prove which routine implements which keyword:
CTAB maps a command token to its address, FNVEC maps a function token to
its address, and SAMHK maps a hook code.  The MasterBASIC manual --
transcribed in docs/masterbasic-manual.md -- says what each keyword
does.  Putting the two together is what this file is: the text is a
precis of the manual, attached to the address the tables give.

Keyed by the label the tables give the routine, so a change in the
tables moves the commentary with it.
"""

FEATURES = {

'CMD_SORT': """\
SORT -- the SORT command, token 251.

    SORT [ABS] [INVERSE] a$

Sorts the strings of a string array, or the characters of a plain
string, in place.  Plain SORT ignores case: bit 5 of each character's
code is not considered.  ABS sorts strictly by character code, which is
what SVAL$-packed numbers need, and is slightly faster.  INVERSE
reverses the order.

Two slicers are allowed: the first selects which strings to sort, the
second which part of each string to compare on, so SORT a$()(2 TO )
orders the whole array on everything but the first character.

Manual: "Sorting data".""",

'CMD_JOIN': """\
JOIN -- the JOIN command, token 252.  Two unrelated jobs.

    JOIN [line]        join a program line to the one below it,
                       dropping the second line number and separating
                       the two with a colon
    JOIN TO a$,b$      append the second string or string array to the
                       first

JOIN TO is LET a$=a$+b$ but faster and in less free memory; the second
string is unchanged.  Arrays join when their strings are the same
length, and the first array grows by the number of strings in the
second.

Manual: "JOIN program lines" and "Joining strings and string arrays".""",

'CMD_ALTER': """\
ALTER -- the ALTER command, token 250.  Three unrelated jobs.

    ALTER (ref) TO (ref) [,first[,last]]   search and replace in the
                                           program text
    ALTER DEVICE logical TO physical       point a logical drive number
                                           at a different real drive
    ALTER DISPLAY s TO s LINE y            show the top of one screen
                                           and the bottom of another

The search-and-replace form follows REF's rules: a bare name matches
only whole words and is not found inside strings, a quoted string is
found anywhere, and brackets around a variable name mean "use its
value".  Altering a number changes the invisible five-byte form with
it.

Manual: "Program search and change", "ALTER DEVICE", "ALTER DISPLAY".""",

'CMD_TIME': """\
TIME -- the TIME command, token 248.

MasterDOS sets and reads the SAMBus clock with TIME; MasterBASIC adds
two forms:

    TIME +      switch the clock into its high-speed test mode
    TIME -      switch back

The test mode runs 5416.3 times faster than real time, which is what
makes TICS useful for timing.  MasterBASIC saves the real time and date
on the way in and corrects them on the way out, so ordinary use costs
nothing -- but more than about eight real minutes in the mode overruns
the correction.

Manual: "New timing facilities".""",

'CMD_DATE': """\
DATE -- the DATE command, token 249.  MasterDOS's command for setting
the calendar, taken over by MasterBASIC along with TIME so that the two
stay consistent across the fast-mode switch.

Manual: "New timing facilities".""",

'CMD_PRINT': """\
PRINT -- taken over from the ROM at token &BB.

MasterBASIC claims PRINT for PRINT REF, which lists the line numbers a
reference occurs in:

    PRINT REF (reference)[,first[,last]]

A line is listed once per occurrence, so a reference used twice in a
line gives that number twice.

Manual: "Listing program references".""",

'CMD_LPRINT': """\
LPRINT -- taken over from the ROM at token &BC.

Carries LPRINT REF, the printer form of PRINT REF, and the two commands
that set printing up:

    LPRINT CLEAR [size]   reserve a buffer for interrupt-driven
                          printing, in 1K units, up to 256K; 0 turns it
                          off and frees the space
    LPRINT MODE 1 | 2     parallel or serial output

With a buffer in place the computer feeds the printer 50 times a
second, so LLIST and DUMP hand control back at once.  The serial
settings come from XVAR 12-14 and are read when MODE 2 is next
selected.

Manual: "Interrupt-driven printing" and "Serial input and output".""",

'CMD_DUMP': """\
DUMP -- taken over from the ROM at token &BF.

    DUMP 1 | 2 | 3   small, medium and large shaded dumps; 3 is
                     sideways.  A second number magnifies one axis
                     separately from the other
    DUMP 4           medium unshaded dump, as the SAMDOS DUMP utility
    DUMP 5           text dump, read back off the screen with the ROM's
                     SCREEN$ routine
    DUMP INVERSE n   dark colours light and vice versa

Dumps 1-3 scan the screen palette, work out how bright each colour is
and print a dot pattern of about the right darkness.  Everything about
them -- strike count, dumped area, orientation and the Epson control
sequences -- is in XVAR 5 and XVAR 15 to 58.

INVERSE IS ONE PATCHED BYTE.  &67F8 loads the address of DUMP_INVERT,
which sits between the LD A,D that fetches a finished bit-image byte
and the call that prints it, and writes &00 (NOP) or &2F (CPL) into it.
Nothing else in the routine mentions INVERSE at all.

THE TWO NUMBERS ARE FETCHED IN THE ORDER THE CALCULATOR STACK GIVES
THEM, not the order they were written.  CALL_EXPNUM evaluates the first
and leaves it on the stack; INT_ARG_THEN_END evaluates the second and
takes it straight back off, which is why the 1-to-3 test at &6814
applies to the second number.  BYTE_ARGUMENT then pops what is left --
the first.  The ROM's GETINT returns "TO BC AND HL, A=C", so the PUSH
HL round the second call keeps the second number while the first is
fetched into A, and LD H,A at &6831 lands them as H = the first number
and L = the second.  With one number both halves get it, because GETINT
put the same value in A and in L: that is DUMP 3 magnifying both
directions at once.

DUMP 4 and DUMP 5 are not here at all.  They are copied into the ROM's
INSTBUF and run there -- see DUMP_TEXT and DUMP_UNSHADED.

Manual: "Screen dumps".""",

'CMD_BLITZ': """\
BLITZ -- taken over from the ROM at token &9D, for BLITZ SOUND.

    BLITZ SOUND a$

Hands a string recorded by RECORD SOUND to the interrupt-driven sound
buffer, after which the sound plays on its own while BASIC does
something else.  Fifty times a second the sound code takes data from
the buffer until it meets a PAUSE marker, then counts down that many
frames -- so timing in the original program must come from PAUSE, not
from FOR-NEXT loops.

Manual: "Sound commands".""",

'CMD_RECORD': """\
RECORD -- taken over from the ROM at token &EF, for RECORD SOUND.

    RECORD SOUND TO a$        add every SOUND and PAUSE to a$ as well
                              as performing it
    RECORD SOUND OFF TO a$    add them without performing them, which
                              is much faster
    RECORD SOUND STOP         stop adding

The string then holds everything that would have gone to the sound
chip, with markers where the PAUSEs were, ready for BLITZ SOUND.  SOUND
CLEAR sets the size of the buffer they are played back through.

Manual: "Sound commands".""",

'CMD_CLS': """\
CLS -- taken over from the ROM at token &9F, for CLS *.

    CLS *

Equivalent to PEN 0: PAPER 15: BORDER 15: CLS -- black on white, for
the many users who prefer it.  CLS # goes back to white on black.

Manual: "CLS *".""",

'CMD_LINE': """\
LINE -- taken over from the ROM at token &8C, for line number tracing.

    LINE           show each line and statement number as it runs
    LINE delay     the same, pausing; 1 is brief, 200 very long
    LINE STEP      wait for CNTRL before each line
    LINE OFF       stop

The trace appears at the lower right of the screen in PEN 0 on PAPER
15.  Other BASICs call this TRACE or TRON.

Manual: "Line number tracing".""",

'CMD_SAVE': """\
SAVE -- taken over from the ROM at token &94.

Carries the two SAVE extensions:

    SAVE MODE 1 | 2 | 3    file compression.  2 compresses SCREEN, CODE
                           and array files and needs a spare 16K page;
                           3 uses a slower, better routine for screens
                           and needs no spare page
    SAVE BOOT "name"       write the DOS and MasterBASIC back out as one
                           bootable CODE file, DVAR and XVAR changes
                           included

A compressed file expands again on loading without being asked to.  The
compressed state is not shown by DIR but FSTAT option 8 reports it, and
DVAR 154 holds the current setting.

Manual: "File compression with SAVE MODE" and "Saving the
DOS/MasterBASIC file".""",

'CMD_MERGE': """\
MERGE -- taken over from the ROM at token &96, for MERGE *.

    MERGE *"filename"

The ROM's MERGE handles arbitrary assortments of lines and variables,
one line at a time, shuffling memory as it goes.  MERGE * does the
common case -- a straight block of lines -- in one go.  Any existing
lines within the range the merged program spans are obliterated, and
variables in the merged file are lost.

Manual: "Faster MERGE".""",

'CMD_REF': """\
REF -- taken over from the ROM at token &CE.

    REF (reference)[,first[,last]]

Searches the program for a reference -- a variable, a number, or a
sequence of characters -- and puts the line it is in into the edit line
with the cursor just past it.  RETURN resumes the search.

A bare name matches only whole words and is not looked for inside
strings; a quoted string is found anywhere; brackets around a variable
name search for its value rather than its name; and a number is matched
together with the invisible five-byte form that follows it.

Manual: "Searching the program".""",

'FN_LOCN': """\
LOCN -- token FF 29.

    LOCN(start,length,a$[,ABS])

Searches memory for a string and returns the address, or 0.  A # in the
target matches anything.  Case-insensitive at about 90K a second; ABS
matches exactly and runs at over 200K a second.

Manual: "LOCN function - searching memory".""",

'FN_RESERVED': """\
RESERVED -- token FF 2A.

    RESERVED(n)

Claims n bytes of the system heap and returns the address; a negative n
gives them back.  Meant for the short paging stubs that call machine
code in another page.  The heap grows at the expense of BASIC's
GOSUB/DO/PROC stack, and freeing space someone else reserved will crash
the machine.

Manual: "RESERVED function - reserving Heap space".""",

'FN_EQU': """\
EQU -- token FF 2B.

    EQU(a$,b$)

Compares two strings ignoring case, so EQU(nm$,"Jones") accepts jONES
and jOnEs.  For checking input without forcing it into a format first.

Manual: "EQU - case-insensitive comparison".""",

'FN_TICS': """\
TICS -- token FF 2C.

Seconds elapsed in the month so far, 0 to 2678399, from the SAMBus
clock through MasterDOS.  Restarts at midnight on the last day of the
month.

Under TIME + it returns a floating-point value good to about 0.0002s:
MasterBASIC divides by the fast-mode factor of 5416.3 itself, and zeros
the reading when TIME + is selected.

Manual: "New timing facilities".""",

'FN_SHIFT_S': """\
SHIFT$ -- token FF 2D.

    SHIFT$(a$,n)

    1  force upper case          3  reverse case
    2  force lower case          4  make the string printable

Option 4 turns control codes into a full stop and strips the top bit
from characters above 127, so a block of memory can be PRINTed as text.
DVAR 24 and DVAR 25 change what it does with high characters and which
character stands in for a control code.  Strings must be 16383
characters or less.

Manual: "SHIFT$ - upper/lower case conversion".""",

'FN_SVAL_S': """\
SVAL$ -- token FF 2E.

    SVAL$(number,characters)

Packs a number into a 2, 3, 4 or 5-character string so it can sit in a
fixed-width field.  2 characters take whole numbers 0-65535; 3, 4 and 5
take the full range with about 5, 7 and 9 correct digits.  NVAL is the
inverse.

An array of these sorts about four times faster than the equivalent
numeric array, which is the manual's reason for SORT not supporting
numeric arrays at all.

Manual: "SVAL$ - converting numbers to strings".""",

'FN_USING_S': """\
USING$ -- token FF 2F.

    USING$(format$,number)

Formats a number to a fixed number of digits either side of the point.
A # in the format string means a leading space and a 0 a leading zero;
other leading characters are copied through.  Rounds to the last
printed digit, and marks overflow with %.  Unlike the PRINT USING other
BASICs offer the result is a string, so it can be LET into a field of a
record and sorted on.

Manual: "Formatting numbers with USING$".""",

'FN_SCRAD': """\
SCRAD -- token FF 37.

The address of the start of the current screen -- needed to POKE or
LOAD ... CODE to the screen in a program that has to work on both 256K
and 512K machines, where it is not in the same place.

Manual: "SCRAD function - screen address".""",

'FN_INARRAY': """\
INARRAY -- token FF 38.

    INARRAY(a$(start[,slicer]),target$[,ABS])

The array form of INSTR: searches a string array from the given element
and returns the number of the first string containing the target, or 0.
Case-insensitive unless ABS is given, which is also faster.  A slicer
limits the search to part of each string, which speeds it up and lets
different fields be searched separately.  A # in the target matches
anything, so two fields at fixed offsets can be matched at once.

The position within the matched string is left in IAPOS, XVAR 3.
Arrays of more than two dimensions are not supported.

Manual: "Searching string arrays with INARRAY".""",

}


# Features the manual describes that are not reached through a dispatch
# table, so there is no address to attach them to yet.
UNPLACED = """\
The manual also describes these, which no table points at, so they have
not been located in the code:

  Editing    word left and right on shifted cursors (CHR$ 24 and 25),
             and last line recall on CNTRL/up-arrow
  Graphics   PUT GRAB, and COPY SCREEN
  Structure  HIDE TO, and EXIT PROC / EXIT DO / EXIT FOR, which are
             statements and so arrive through CMDV rather than CTAB
  DOS        OPEN BLOCKS, and the comma syntax for COPY, RENAME, BACKUP
             and MOVE
  Functions  the FSTAT, DIR$ and INP$ extensions, which patch routines
             that stay in the MasterDOS page

Seven that were on this list have been found since.  Only the first was
found by a table after all, and only because the entry was not what it
looked like:

  splitting a line by typing / after the colon is CMD_SPLIT_LINE, which
  CTAB does point at -- its first entry, because &2F is ASCII "/" and
  sorts below every command token
  the faster PUT is INSTALL_EXTENDED_PUT, which assembles 298 bytes into
  the system page at &45A2 out of five runs, two of them lifted from the
  ROM's own PUT
  the extended CSIZE is PRINT_MAGNIFIED_CHAR, which has no caller in
  either page: the system page reaches it through PAGER
  BLOCKS 2 is HK_SWAPCHARS exchanging 328 bytes with the alternate
  character set at &7E64, the cursor kept out of the swap through HUDG
  the FORMAT improvements are BUILD_TRACK_IMAGE, which lays out a whole
  track for the controller and which only the DOS calls
  the DIR improvements are the single directory scan behind DIR, doing
  lookup and allocation alike
  the RAM disc speed-ups are the diversion at the first test of every
  read and write, where RDRSCT turns the transfer into an LDIR

notes/ has each of them, and docs/how-it-works.md puts them in order."""
