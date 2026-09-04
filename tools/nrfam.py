"""The NR family: reading and writing the ROM's system variables.

Both halves carry a copy of these, because a page cannot address the
ROM's variables directly -- they live at &4000-&5FFF, the same addresses
the page itself occupies.  The way round it is the same every time:

    IN A,(URPORT)     save HMPR
    XOR A
    OUT (URPORT),A    page 0, the ROM's system page, to &8000-&BFFF
    SET 7,H
    RES 6,H           turn &4000-&7FFF into &8000-&BFFF
    ...               read or write
    OUT (URPORT),A    put HMPR back

So &5A97 is reached as &9A97, which is why an address windowed this way
appears in the listing under the ROM's name for it.

The four NR entries take the variable's address in the two bytes after
the call and step over them on the way back.  They are documented below
with what they consume and what they leave, because that is the part a
reader needs and the part the code does not say.

DOC is keyed by label name rather than by address: the two pages hold
the same routines at different addresses.
"""

FAMILY = """\
%s

    CALL %s
    DEFW <address of a ROM system variable>

%s

Preserves:   %s
%s
Side effect: HMPR is set to 0 for the access and put back before the
             return.  Interrupts are not disabled, so an interrupt
             during the access sees the ROM's page at &8000."""


AFPRIME = ("Corrupts:    AF' -- the primitive under this entry uses the"
           ' alternate\n             accumulator to carry the saved HMPR'
           ' across the access\n')


def _entry(title, name, body, preserved, corrupts=AFPRIME):
    return FAMILY % (title, name, body, preserved, corrupts)


DOC = {

'NRRD': _entry(
    'Read one byte of a ROM system variable.',
    'NRRD',
    'Returns:     A = the byte at that address.',
    'HL, DE, BC'),

'NRRDD': _entry(
    'Read two bytes of a ROM system variable.',
    'NRRDD',
    'Returns:     BC = the word at that address, low byte first.\n'
    '             A is not the value; it is left holding the old HMPR.',
    'HL, DE'),

'NRWR': _entry(
    'Write one byte to a ROM system variable.',
    'NRWR',
    'Takes:       A = the byte to write.\n'
    'Returns:     A = that same byte, so the value can be used again\n'
    '             without reloading it.',
    "HL, DE, BC, and AF' as well: this is the one entry of the\n"
    '             four that calls no primitive.  Its write is inlined\n'
    '             and the saved HMPR travels in D, which is the point\n'
    '             of the authors own note, "replace CALL CMR:DW\n'
    '             NRREAD - faster".',
    ''),

'NRWRD': _entry(
    'Write two bytes to a ROM system variable.',
    'NRWRD',
    'Takes:       BC = the word to write, C stored first.',
    'HL, DE'),

'NRWRHL': """\
Write HL to a ROM system variable.

    CALL NRWRHL
    DEFW <address of a ROM system variable>

Copies HL into BC and falls into NRWRD, so everything that entry says
applies.  It exists because HL is where a pointer usually already is,
and reaching NRWRD directly would mean shuffling it first.""",

'GTHL': """\
Pick up the inline address and step past it.

Entry:   HL points at the two bytes after the call.
Returns: HL = the word they hold -- the address to be used.
         DE = the address after them, which becomes the return address.

Called by all four NR entries as their first act, once each has moved
the return address into HL with EX (SP),HL.""",

'RDA': """\
Read the byte at HL from the ROM's system page.

Entry:   HL = an address in &4000-&7FFF.
Returns: A = the byte there.
Corrupts HL, which is left windowed into &8000-&BFFF, and AF'.
HMPR is put back by BCRWC, which RDA falls into.

The primitive under NRRD.  Called directly where the address is already
in HL rather than in the two bytes after a call.""",

'RDBC': """\
Read the word at HL from the ROM's system page.

Entry:   HL = an address in &4000-&7FFF.
Returns: BC = the word there, C from the lower address.
Corrupts HL and AF'.  The primitive under NRRDD.""",

'WRTBC': """\
Write BC to the word at HL in the ROM's system page.

Entry:   HL = an address in &4000-&7FFF, BC = the value.
         C goes to the lower address.
Corrupts HL and AF'.  The primitive under NRWRD.""",

'WRA': """\
Write A to the byte at HL in the ROM's system page.

Entry:   HL = an address in &4000-&7FFF, A = the value.
Corrupts HL and AF'.

NRWR does not call this: it has the same code written out inline, using
D and E as the scratch it has already saved, which is how it manages to
give the written byte back in A.""",

'PPXR': """\
Restore the caller's registers and return past the inline word.

The shared exit of the four NR entries -- not of the primitives,
which end at BCRWC.  The caller's HL and DE come back off the stack,
and EX (SP),HL puts the stepped-on return address where the RET will
find it.

MasterBASIC has a routine of its own under this name that does
something else: there, PPXR is the tail that puts HMPR back.""",

}
