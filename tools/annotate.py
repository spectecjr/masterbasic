"""Names and commentary for the routines that have been worked out.

Everything here was established by reading the disassembly against the
two source trees in ref/ -- MasterDOS's own equivalents of these routines
are named and documented in its annotated source, and MasterDOS's
docs/functions.md describes the four ROM vectors the scheme rests on.
MasterBASIC reuses that scheme wholesale, so where a MasterBASIC routine
is the same shape as a MasterDOS one it is given the same name.

Each entry is  address: (label, comment)  in one of the two pages.
Either half may be None.
"""

import re

from features import FEATURES, UNPLACED
from serial_note import OPSR_DOC
from serial import SERINIT_DOC, SERCMD_DOC, ESCCHK_DOC
import hooks

CALL_OTHER = """\
Call a routine in the other page.

    CALL CALLMB
    DEFW <address in the other page>

Reads the word after the call, switches LMPR so that the other page
covers &4000-&7FFF, and jumps to it; the return goes through the stub
below, which puts LMPR back.  The &00 in the `LD H,&00` two instructions
down is a placeholder: the boot sector pokes the other page's number,
less one, into it once it knows which page that is.  &7FFC holds the
ROM's stack pointer as it stood when the DOS was entered.

The parameter is read after the paging has changed, so a value of
&4000 or more is an address in the other page, and is written here as
that page's own label less &4000 -- the mirror of the +&4000 used for
the bit-15 pointers in the tables.  Everywhere else in this file an
inline DEFW is a ROM address, and reading this one that way would name
it for a page that is no longer mapped: DOS_POINT would come out as one
of the ROM variables that share &4FAC.  Below &4000 there is nothing to
correct -- the switch leaves ROM0 in place, so NRREAD really is the ROM
routine at &0010."""

CMR_DOC = """\
Call the main ROM.

    CALL CMR
    DEFW <ROM address>

The mirror of the routine above: it pages the ROM back in rather than
the other half, saves the current HMPR into the code that restores it,
and returns through a stub that undoes both."""

NR_DOC = """\
Read or write one of the ROM's system variables.

    CALL NRRD                 ; A  <- byte at the address that follows
    DEFW <ROM variable>

Three of the four differ only in the primitive they call: NRRDD reads a
word into BC, NRRD a byte into A, NRWRD writes BC and NRWR writes A.
Each reads the address out of the word after the call and steps the
return address past it.

The variables cannot simply be addressed, because this page occupies the
same &4000-&7FFF that they live in.  The primitives get at them by
setting HMPR to 0 and turning the address into the &8000-&BFFF window --
`SET 7,H` then `RES 6,H` -- so &5A97 is reached as &9A97.  HMPR is put
back before returning."""

HOOK_DOC = """\
The RST &08 hook handler, reached from the JP at page offset &0200.

The code byte after the RST is doubled to index SAMHK, which discards
bit 7 in the process, so codes 128 upwards map onto entries 0 upwards.
Both register sets are saved first, then INDJP jumps to the entry."""

INDJP_DOC = """\
Indexed jump through a table of addresses, with L as the index.

    LD DE,<table>
    LD A,<index>
    CALL INDJP

An entry with bit 15 set does not live in this page.  The bit is
cleared, leaving the address as the *other* page numbers it, and the
call goes through CALLMB instead of a plain JP -- which is how the hook
table and the command table below reach the routines MasterBASIC has
taken over."""

CTAB_DOC = """\
CTAB -- the commands the DOS claims from the ROM.

Three bytes per entry: the token, then the address of the routine.  The
byte before the table is the number of entries; the last entry's token
is zero, which nothing matches, so an unrecognised command always falls
through to CNF.  SYNTAX walks it with the token in A.

What is in A is whatever GCHR returned at the start of the statement, so
an entry is a command token only because that is how a statement usually
begins.  The table is in ascending order, and the first entry is &2F --
not a token at all but the character "/", which is why it sorts below
everything else.  That is MasterBASIC's SPLIT: a slash as the first
non-space character after a colon cuts the line in two.

As with SAMHK, an address with bit 15 set belongs to the MasterBASIC
page: the bit is cleared and the routine is called through CALLMB.  That
is how MasterBASIC takes over PRINT, LPRINT, SAVE, MERGE, DUMP, REF,
RECORD, BLITZ, CLS and LINE, and how its own commands at tokens &F7-&FC
are reached."""

SAMHK_DOC = """\
SAMHK -- the RST &08 hook table.  Entry i is code 128+i.

Codes 169, 171 and 173 point into the MasterBASIC page, with bit 15
set.  They are what the three ROM vectors MasterBASIC repoints at boot
end up reaching -- print a token, match a keyword while tokenising, and
dispatch a command.  The vectors themselves hold the addresses of short
stubs planted in the ROM's system page at &4BA0, each of which filters
on the token and then does RST &08 with the code.  Code 172, the
function evaluator, is still the DOS's own HKLEN."""

HGTTK_DOC = """\
Hook 171 -- match a keyword while tokenising.  The ROM's MTOKV vector
points here, so the ROM calls it for any word its own token tables did
not recognise.

It maps its own page in at &8000 as well as &4000 (HMPR := LMPR+1) so
the ROM can see the keyword list, then hands the ROM's own matcher --
GETTOKEN, through the jump table at &018A -- the 28 names at MBKEYS.
GETTOKEN returns 1 for the first name, 2 for the second and so on, or Z
if nothing matched.

The arithmetic that follows turns that index into a token:

    index 1-19   token = index + &25       &26-&38, a function token
    index 20     token = &68               the ROM's spare FPC slots
    index 21     token = &6A
    index 22-28  A = index + &A6           a command; the ROM's own
                                           tokeniser adds &3B, giving
                                           247-253

Carry out means "this is a function", which needs an &FF prefix in front
of the token.  The ROM's tokeniser has no way to write a two-byte token
from outside its own tables, so GTDT below is copied into a buffer and
the tokeniser is re-entered seventeen bytes further on, having put the
&FF into the line itself.  The token comes back in B."""

GTDT_DOC = """\
The fourteen bytes HGTTK copies into the ROM's workspace and runs there:

    POP IY / LD BC,17 / ADD IY,BC     point 17 bytes into the tokeniser
    POP DE / ADD HL,DE / EX DE,HL     work out where the line is
    LD (HL),&FF                       write the function prefix
    JP (IY)                           and rejoin the ROM

This is the same trick MasterDOS plays in its own GTDT, and the reason
MasterBASIC's functions can be two-byte tokens at all."""

MBKEYS_DOC = """\
The 28 names MasterBASIC adds to SAM BASIC, each ended by bit 7 of its
last character, in the order HGTTK's index numbers them:

     1 EXIT PROC  &26     11 TIME$      &30     21 NVAL       &6A
     2 EXIT DO    &27     12 DATE$      &31     22 BACKUP     247
     3 EXIT FOR   &28     13 INP$       &32     23 TIME       248
     4 LOCN       &29     14 DIR$       &33     24 DATE       249
     5 RESERVED   &2A     15 FSTAT      &34     25 ALTER      250
     6 EQU        &2B     16 DSTAT      &35     26 SORT       251
     7 TICS       &2C     17 FPAGES     &36     27 JOIN       252
     8 SHIFT$     &2D     18 SCRAD      &37     28 EDIT       253
     9 SVAL$      &2E     19 INARRAY    &38
    10 USING$     &2F     20 XVAR       &68

The first twenty-one are functions, written into a line as &FF followed
by the token; the last seven are commands and are single bytes.

Three of the tokens are slots the SAM ROM reserved and never used, and
MasterBASIC has filled them with the names the ROM's own source pencils
in against them: INARRAY at &38 in the immediate-function list, and XVAR
and NVAL at &68 and &6A in the floating-point list.  Seven more --
TIME$, DATE$, INP$, DIR$, FSTAT, DSTAT and FPAGES at &30-&36 -- are
MasterDOS's, kept at the values MasterDOS gave them so that programs
written for the DOS alone still tokenise the same way.  SCRAD at &37 is
a name MasterDOS's source has commented out; MasterBASIC has finished
it."""

PRTOK_DOC = """\
Hook 169 -- print one of MasterBASIC's tokens.  The ROM's PRTOKV vector
points here, so LIST and the error printer come through it.

`SUB &E1` turns a command token back into its index into MBKEYS, which
is the inverse of the `+ &A6` and the ROM's `+ &3B` in HGTTK."""

CMDV_DOC = """\
Hook 173 -- dispatch one of MasterBASIC's commands.  The ROM's CMDV
vector points here.

It reads the ROM's COMAD, records the token in CURCMD, and indexes a
table by token minus &90 to find the routine.  Six of the ROM's own
commands are then tested for by name and leave here for a routine of
MasterBASIC's:

    &AA MODE     &C2 PAUSE        &D1 KEYIN
    &AE SOUND    &C9 DEF KEYCODE  &E1 POKE

notes/mb-cmdintercept.txt says what each of them does with it.

Everything else takes the default path from &4ED4, which calls nothing.
It assembles a routine in the ROM's code buffer out of three pieces --
CMDBUF_PROLOGUE, eighty-eight bytes from wherever the table entry
points, and CMDBUF_EPILOGUE -- fills in two operands, splices the
result into the middle of the copied block, and hands the buffer's
address to STORE_BC_AT_XVAR76.  A dump of a booted machine has all of
it; notes/mb-cmdbuf.txt goes through it byte by byte."""

HEVV_DOC = """\
Hook 172 -- evaluate a function.  The ROM's EVALUV vector points here,
and this one is still MasterDOS's own, under its own name: MasterBASIC
did not need to replace it.

The ROM passes the function token less &1A, which `CP &34-&1A` in
MasterDOS's source pins down.  &13 to &19 are the seven functions whose
result is a string, and are handled here; everything else goes to HEVV2,
which range-checks, subtracts another &0F and indexes FNVEC.  So FNVEC
entry i is token &29+i.  A value of &25 is token &3F, the ROM's own
LENGTH, which is what this routine is named for."""

SYNTAX_DOC = """\
The unrecognised-command entry, reached from the JP at page offset
&0203.  The ROM calls it with the error number that made it give up --
29 "not understood" or 53 "no DOS" -- and CHADD pointing at the
statement.

It moves to the DOS's own stack, pushes ENDS as the return address so
that every command routine ends there, and looks the token up in CTAB."""


FNVEC_DOC = """The table HEVV2 dispatches a function token through, sixteen entries,
every one of them in the MasterBASIC page.

HEVV2 range-checks the value it is given, subtracts &0F and uses the
result as the index.  Which slot belongs to which token has not been
worked out -- the ROM adjusts the token before it reaches EVALUV, and
that adjustment has not been traced."""

REPORT_DOC = """Report the BASIC error whose number is in A.

The entry points above it are a chain: each loads its own number into A
and then falls through, with LD HL,nn swallowing the next two bytes so
that the following LD A,n is never executed.  &21 on its own in the
listing is one of those skips.

It calls &51A0 in the DOS page, which stashes A and goes to DERR."""

# Runs where `LD HL,nn` is used to skip two bytes rather than to load HL.
# MasterBASIC's error entry points are chained this way: each sets A and
# falls through to REPORT.  The trace splits the entries something jumps
# to, which is what shows the run for what it is; these are the bounds of
# the whole chain so the rest can be split too.
SKIP_CHAINS = {'MB': ((0x43A7, 0x43BE),)}

DVAR_DOC = """DVAR -- the DOS variables, at page offset &0220.

`DVAR n` returns the *address* of the nth byte of this block, so a
program reads it with PEEK DVAR n and writes it with POKE DVAR n,x.
The index each byte answers to is the number in its comment, carried
from the annotated MasterDOS source.

This is MasterDOS's configuration interface: nearly every default it
has is a byte in here -- step rates, the directory column layout, the
date and time templates, the clock port, the beep, and the addresses
of the hooks.

None of it is code, although a good deal of it decodes as plausible
instructions.  The date template at &4280 is the six characters of
"00/00/00", which reads as JR NC and LD A,(&3030); the clock port at
&42B6 holds &EF, which reads as RST &28 and was being followed as a
call into the floating-point calculator.  The block is marked as data
from its documented start to CALLMB, which is where code begins."""


DOS = {
    0x4220: ('DVAR', DVAR_DOC),
    0x6A72: ('OPSR', OPSR_DOC),
    0x42BD: ('CALLMB', CALL_OTHER),
    0x42EA: ('CTABN', CTAB_DOC),
    0x42EB: ('CTAB', None),
    0x434E: (None, SYNTAX_DOC),
    0x4433: (None, HOOK_DOC),
    0x44A6: ('SAMHK', SAMHK_DOC),
    0x78CD: ('INDJP', INDJP_DOC),
    0x78EB: ('FNVEC', FNVEC_DOC),
    0x7893: ('HKLEN', HEVV_DOC),
    0x7BB2: (None, CMR_DOC),
    0x5053: (None, NR_DOC),
    0x51A0: ('REPORTA', None),
}

MB = {
    # The DOS's entry is &42BD, where LD IY,(&7FFC) restores the ROM's
    # IY before falling into the shared code.  This page has five zero
    # bytes there instead and starts at &42C1, which is where all
    # forty-five of its call sites go.
    0x42C1: ('CALLDOS', CALL_OTHER.replace('CALLMB', 'CALLDOS')),
    0x5934: ('SERINIT', SERINIT_DOC),
    # MasterBASIC's own hook codes, 175 to 185 -- see tools/hooks.py
    **dict((a, (hooks.NAMES[a], hooks.DOCS[a])) for a in hooks.NAMES),
    0x596E: ('SERCMD', SERCMD_DOC),
    0x5B75: ('ESCCHK', ESCCHK_DOC),
    0x44F0: ('CMR', CMR_DOC),
    0x455F: ('NRRDD', NR_DOC),
    0x456A: ('NRRD', None),
    0x4577: ('NRWRD', None),
    0x4582: ('NRWR', None),
    0x45A4: ('WRA', None),
    0x45B3: ('WRTBC', None),
    0x45C2: ('RDBC', None),
    0x45D1: ('RDA', None),
    0x45DC: ('BCRWC', None),
    0x45E1: ('GTHL', None),
    0x4E96: ('HCMDV', CMDV_DOC),
    0x43BE: ('REPORT', REPORT_DOC),
    0x4FB7: ('HGTTK', HGTTK_DOC),
    0x500E: ('HPRTOK', PRTOK_DOC),
    0x5000: ('GTDT', GTDT_DOC),
    0x50D8: (None, MBKEYS_DOC),
}


def apply(page, table):
    """Add the names and comments for one page, before autolabelling."""
    for addr, (name, doc) in table.items():
        if name:
            page.labels[addr] = name
        if doc:
            body = '\n'.join(';; ' + line if line else ';;'
                             for line in doc.rstrip().split('\n'))
            rule = ';; ' + '-' * 68
            page.headers[addr] = rule + '\n' + body + '\n' + rule


# The tokens HGTTK assigns, worked out from its arithmetic and confirmed
# against CTAB: the six command entries at &F7-&FC land on exactly the
# names the last entries of MBKEYS give, and &30-&36 land on MasterDOS's.
MB_TOKENS = {
    0x26: 'EXIT PROC', 0x27: 'EXIT DO', 0x28: 'EXIT FOR', 0x29: 'LOCN',
    0x2A: 'RESERVED', 0x2B: 'EQU', 0x2C: 'TICS', 0x2D: 'SHIFT$',
    0x2E: 'SVAL$', 0x2F: 'USING$', 0x30: 'TIME$', 0x31: 'DATE$',
    0x32: 'INP$', 0x33: 'DIR$', 0x34: 'FSTAT', 0x35: 'DSTAT',
    0x36: 'FPAGES', 0x37: 'SCRAD', 0x38: 'INARRAY',
    0x68: 'XVAR', 0x6A: 'NVAL',
    0xF7: 'BACKUP', 0xF8: 'TIME', 0xF9: 'DATE', 0xFA: 'ALTER',
    0xFB: 'SORT', 0xFC: 'JOIN', 0xFD: 'EDIT',
}


def _where(page, word):
    """How to describe a table entry's target.

    Bit 15 set means the other page, so the name to show is that page's
    label, not one of this page's.
    """
    if word & 0x8000:
        a = word & 0x7FFF
        peer = page.peer
        name = peer.labels.get(a) if peer else None
        return '%s %s' % (peer.tag if peer else 'other page',
                          name or '&%04X' % a)
    return page.labels.get(word) or '&%04X' % word


def _entry(page, word):
    """A table entry written as a label where one covers it.

    An entry with bit 15 set lives in the other page.  That page's labels
    are equated for &8000-&BFBF, which is where this page sees it, but
    the stored word is &4000 higher again -- so the entry is written
    NAME+NOT_IN_THIS_PAGE, the same form the listing already uses for
    every other bit-15 pointer.  Without a label the number stands as it
    is.
    """
    if word & 0x8000:
        a = word & 0x7FFF
        if page.peer and page.peer.inside(a):
            name = page.peer_name(a - 0x4000 + 0x8000)
            if name:
                page.used_page_flag = True
                return name + '+NOT_IN_THIS_PAGE', True
        return '&%04X' % word, False
    name = page.labels.get(word)
    return (name, True) if name else ('&%04X' % word, False)


def _rows(lines):
    return '\n'.join(lines) + '\n'


def render_ctab(dos, toks, start=0x42EA, end=0x434E):
    """CTAB as its real shape: a count, then token/address triples."""
    n = dos.byte(start)
    out = ['%-14s DEFB %-25s ; %04X %d entries' % ('', n, start, n)]
    a = start + 1
    for _ in range(n):
        tok = dos.byte(a)
        addr = dos.word(a + 1)
        # SYNTAX searches this table with the byte at the start of the
        # statement, so an entry is a command token only when a statement
        # can begin with one.  Below &85 it is a literal character.
        if tok and tok < 0x85:
            name = repr(chr(tok)) if 32 <= tok < 127 else ''
        else:
            name = toks.cmd.get(tok) or ''
            if name in ('', '-'):
                name = MB_TOKENS.get(tok, '')
        value, named = _entry(dos, addr)
        out.append(('%-14s DEFB %-25s ; %04X %-10s'
                    % ('', '&%02X' % tok, a, name if tok else '(end)'))
                   + ('' if named else ' -> ' + _where(dos, addr)))
        out.append('%-14s DEFW %s' % ('', value))
        a += 3
    return a, _rows(out)


def render_samhk(dos, start=0x44A6, count=58):
    """SAMHK as one line per hook code."""
    out = []
    for i in range(count):
        a = start + 2 * i
        v = dos.word(a)
        value, named = _entry(dos, v)
        # The value carries the name now, so the arrow is only worth
        # printing when it could not be written symbolically.
        out.append(('%-14s DEFW %-25s ; %04X code %d' % ('', value, a, 128 + i))
                   + ('' if named else ' -> ' + _where(dos, v)))
    return start + 2 * count, _rows(out)


# One line each for the names in MBKEYS, from the MasterBASIC manual in
# docs/original.  The token numbers are Appendix A's, which agree exactly
# with what HGTTK's arithmetic produces.
KEYWORDS = [
    ('EXIT PROC', 0x26, 'leave a DEF PROC early, even from inside a loop'),
    ('EXIT DO', 0x27, 'leave a DO loop, jumping past any nested ones'),
    ('EXIT FOR', 0x28, 'leave a FOR loop; the control variable keeps its value'),
    ('LOCN', 0x29, 'LOCN(start,length,a$[,ABS]) -- find a string in memory'),
    ('RESERVED', 0x2A, 'RESERVED(n) -- claim n bytes of heap, return the address'),
    ('EQU', 0x2B, 'EQU(a$,b$) -- compare two strings ignoring case'),
    ('TICS', 0x2C, 'seconds elapsed in the month, from the SAMBus clock'),
    ('SHIFT$', 0x2D, 'SHIFT$(a$,n) -- force case, or make control codes printable'),
    ('SVAL$', 0x2E, 'SVAL$(number,chars) -- pack a number into 2-5 characters'),
    ('USING$', 0x2F, 'USING$(format$,number) -- format a number to a fixed width'),
    ('TIME$', 0x30, "the time as hh:mm:ss -- MasterDOS's"),
    ('DATE$', 0x31, "the date as dd/mm/yy -- MasterDOS's"),
    ('INP$', 0x32, "INP$(#stream,n) -- read n characters; n=0 reads to a CR"),
    ('DIR$', 0x33, "DIR$(name$[?]) -- the catalogue; ? includes subdirectories"),
    ('FSTAT', 0x34, "FSTAT(name$,n) -- a file's number, length, type, date, flags"),
    ('DSTAT', 0x35, "a drive's free space, free slots, file count, readiness"),
    ('FPAGES', 0x36, 'free 16K pages in the machine'),
    ('SCRAD', 0x37, 'the address of the current screen'),
    ('INARRAY', 0x38, 'INARRAY(a$(n[,slice]),target$[,ABS]) -- find a string in an array'),
    ('XVAR', 0x68, "XVAR n -- the address of one of MasterBASIC's own variables"),
    ('NVAL', 0x6A, 'NVAL a$ -- turn an SVAL$ string back into a number'),
    ('BACKUP', 0xF7, "MasterDOS's BACKUP; MasterBASIC only adds the comma syntax"),
    ('TIME', 0xF8, 'TIME + / TIME - switch the clock to and from fast test mode'),
    ('DATE', 0xF9, "MasterDOS's DATE, for setting the calendar"),
    ('ALTER', 0xFA, 'ALTER ref TO ref, ALTER DEVICE d TO d, ALTER DISPLAY n TO n LINE y'),
    ('SORT', 0xFB, 'SORT [ABS] [INVERSE] a$ -- sort a string or string array'),
    ('JOIN', 0xFC, 'JOIN [line] joins program lines; JOIN TO a$,b$ appends strings'),
    ('EDIT', 0xFD, 'EDIT var -- INPUT with the present value offered for editing'),
]


def render_mbkeys(mb, start=0x50D8):
    """MBKEYS with each name's token and what it does."""
    out, a = [], start
    for i, (name, tok, gloss) in enumerate(KEYWORDS):
        code = 'FF %02X' % tok if tok < 0x85 else '%d' % tok
        out.append(';')
        out.append('; %2d  %-7s  %-9s %s' % (i + 1, code, name, gloss))
        body = ''.join(chr(mb.byte(a + j)) for j in range(len(name) - 1))
        out.append('%-14s DEFM %-25s ; %04X' % ('', '"%s"' % body, a))
        out.append('%-14s DEFB "%s"+&80' % ('', name[-1]))
        a += len(name)
    return a, _rows(out)


def render_fnvec(dos, start=0x78EB, count=16):
    """The table HEVV2 dispatches a function token through.

    Entry i is token &29+i; the names are in FN_TOKENS below.
    """
    out = []
    for i in range(count):
        a = start + 2 * i
        v = dos.word(a)
        kw = FN_TOKENS[i] if i < len(FN_TOKENS) else ''
        value, named = _entry(dos, v)
        out.append(('%-14s DEFW %-25s ; %04X &%02X %-9s'
                    % ('', value, a, FN_BASE + i, kw))
                   + ('' if named else ' -> ' + _where(dos, v)))
    return start + 2 * count, _rows(out)


# HKLEN's `CP &34-&1A` fixes the base: the ROM hands it the function token
# less &1A.  HEVV2 range-checks that, subtracts &0F and indexes FNVEC, so
# entry i is token &29+i -- sixteen entries for the sixteen function
# tokens LOCN to INARRAY.  The split is confirmed by the table itself:
# entries 7-13 are TIME$ to FPAGES and point into the DOS page, which is
# exactly the seven functions MasterDOS provides.
FN_TOKENS = ['LOCN', 'RESERVED', 'EQU', 'TICS', 'SHIFT$', 'SVAL$', 'USING$',
             'TIME$', 'DATE$', 'INP$', 'DIR$', 'FSTAT', 'DSTAT', 'FPAGES',
             'SCRAD', 'INARRAY']
FN_BASE = 0x29


def sym(name):
    """A keyword turned into something that will assemble."""
    return name.replace('$', '_S').replace(' ', '_')


def hooks_from_source(path):
    """code -> name, from the DEFW list under SAMHK in MasterDOS's source."""
    out, seen, n = {}, False, 128
    for line in open(path, encoding='latin-1'):
        text = line.split(';')[0].rstrip()
        if text.startswith('SAMHK:'):
            seen = True
        elif seen and not text.strip():
            continue
        if not seen:
            continue
        m = re.search(r'\bDEFW\s+([A-Za-z_]\w*)\s*$', text)
        if m:
            out[n] = m.group(1)
            n += 1
        elif out and re.match(r'^\w+:', text):
            break
    return out


def name_tables(dos, mb, toks, hooks, ctab=0x42EA, samhk=0x44A6,
                samhk_len=58, fnvec=0x78EB):
    """Name the routines the three dispatch tables point at.

    Each table proves what the routine it points at is for, which is worth
    more than a synthetic address label -- particularly in the MasterBASIC
    page, where nothing else supplies a name.
    """
    def target(page, word):
        """(page, address) an entry refers to; bit 15 means the other one."""
        return (page.peer, word & 0x7FFF) if word & 0x8000 else (page, word)

    used = {p.tag: set(p.labels.values()) for p in (dos, mb)}

    def give(page, addr, name, alt=None):
        """Name `addr`, falling back to `alt` if the name is taken.

        MasterDOS points four hook codes at the same HDUMMY, but here
        they are four different routines, so the second and later need a
        name of their own rather than to go unnamed.
        """
        if not page.inside(addr) or addr in page.labels:
            return 0
        if name in used[page.tag]:
            if not alt or alt in used[page.tag]:
                return 0
            name = alt
        page.labels[addr] = name
        used[page.tag].add(name)
        return 1

    added = 0
    for i, kw in enumerate(FN_TOKENS):
        page, a = target(dos, dos.word(fnvec + 2 * i))
        added += give(page, a, 'FN_' + sym(kw))

    n = dos.byte(ctab)
    for i in range(n):
        e = ctab + 1 + 3 * i
        tok, word = dos.byte(e), dos.word(e + 1)
        # The ROM's table has '-' for the tokens it reserved and never
        # used, which is exactly where MasterBASIC's own commands live,
        # so a '-' has to fall through to MB_TOKENS rather than count as
        # a name.
        # An entry below &85 is a character a statement may start with,
        # not a token -- looking it up in a keyword table would name the
        # routine after a keyword it has nothing to do with.  &2F is "/",
        # the SPLIT command, and is named from notes/ instead.
        if tok < 0x85:
            continue
        name = toks.cmd.get(tok)
        if not name or name == '-':
            name = MB_TOKENS.get(tok)
        if not name:
            continue
        page, a = target(dos, word)
        added += give(page, a, 'CMD_' + sym(name))

    # MasterDOS names codes 128-174; this build's table runs to 185, and
    # the extra eleven are MasterBASIC's own, so they go by number.
    for code in range(128, 128 + samhk_len):
        word = dos.word(samhk + 2 * (code - 128))
        page, a = target(dos, word)
        name = hooks.get(code)
        added += give(page, a, 'HK_' + name if name else 'HK_%d' % code,
                      'HK_%d' % code)
    return added


# The XVAR block, from the manual's "XVAR function - extra system variables".
# XVAR n is MasterBASIC's own &4000+n: the manual says PUTSWA "is located right
# at the start of MasterBASIC" and that PRINT XVAR 0 therefore gives the start
# of the program.  Every documented default in this build agrees -- VERSION is
# 17 for 1.7, ILPC 15, SPORT 236, BAUD 187, DBITS 147, SBITS 31, SDRHS 255,
# SDTOP 191, ACRSU 10, and GCMX2 is the documented byte sequence.
#   (offset, size, name, what it is)
XVARS = [
    (0,  2, 'PUTSWA',   'address of the PUT dispatch byte; POKE it 0 for the ROM PUT, 172 for ours'),
    (2,  1, 'SOFV',     'screen blanking delay; 12 is about a minute, 0 the normal 22'),
    (3,  2, 'IAPOS',    'where the last INARRAY match was found within the string'),
    (5,  1, 'DTTH',     'DUMP times to hit the paper; 2 or more for a darker copy'),
    (6,  1, 'SORP',     'zero after LPRINT MODE 1, non-zero after MODE 2; read at BOOT'),
    (7,  1, 'VERSION',  "MasterBASIC's version times ten"),
    (8,  1, 'ILPC',     'characters sent to the printer per interrupt'),
    (9,  2, 'ILPD',     'how long to wait for a not-ready printer, in ~25us units'),
    (11, 1, 'SPORT',    "the serial driver's port"),
    (12, 1, 'BAUD',     'baud rate code; 187 is 9600'),
    (13, 1, 'DBITS',    'data bits; 147 is 8'),
    (14, 1, 'SBITS',    'stop bits; 31 is 2'),
    (15, 1, 'SDORI',    'shaded DUMP orientation: sideways, mirrored, forced upright'),
    (16, 1, 'SDLHS',    'shaded DUMP left-hand side'),
    (17, 1, 'SDRHS',    'shaded DUMP right-hand side'),
    (18, 1, 'SDTOP',    'shaded DUMP top'),
    (19, 1, 'SDBOT',    'shaded DUMP bottom'),
    (20, 8, 'GCMX2',    'sent before the bit-image data of DUMP 1-3'),
    (28, 3, 'GCMX4',    'sent at the end of each line of DUMP 1-3'),
    (31, 4, 'DPVARS',   'DUMP 4 length, width, width and height multipliers'),
    (35, 9, 'GCMX1',    'sent before a DUMP: left margin and line advance'),
    (44, 8, 'GCMX2B',   'as GCMX2 but for DUMP 4; copied to the ROM at BOOT'),
    (52, 6, 'GCMX3',    'sent at the end of DUMP 4; copied to the ROM at BOOT'),
    (58, 2, 'DMPTL',    'DUMP 4 top-left address, copied to SVAR 45'),
    (60, 1, 'MODCHAR1', 'first character to substitute when LPRINTed: pound, 96'),
    (61, 1, 'MODCHAR2', 'second character to substitute: hash, 35'),
    (63, 8, 'MODMSG1',  'what to send instead of MODCHAR1'),
    (71, 8, 'MODMSG2',  'what to send instead of MODCHAR2'),
    (87, 2, 'ALTUDG',   'displacement from XVAR 0 of the alternative UDG set'),
    (89, 1, 'ACRSU',    'copied to SVAR 15 at BOOT: the auto line feed after CR'),
]

XVAR_DOC = """\
MasterBASIC's own variables -- the XVAR block.

XVAR n is this page's &4000+n, which is what the manual means when it
says PUTSWA sits "right at the start of MasterBASIC" and that PRINT
XVAR 0 therefore gives the address the program was loaded at.  Every
default the manual quotes matches the bytes here: VERSION is 17 for
version 1.7, SPORT 236, BAUD 187, ACRSU 10, and GCMX2 is the documented
Epson sequence.  MODMSG1 holds 4,27,82,3,35,0,0,0 -- the value the
errata correct the manual to, not the 4,27,82,2,... the manual prints,
so this build is a post-errata one.

The names and descriptions come from the manual's XVAR section; the
values are whatever was in the image when it was saved."""


def render_xvars(mb, start=0x4000):
    """The XVAR block, one line per documented variable."""
    out, a = [], start
    for off, size, name, what in XVARS:
        at = start + off
        if at > a:
            n = at - a
            out.append('%-14s DEFB %-25s ; %04X'
                       % ('', ','.join('&%02X' % mb.byte(x) for x in range(a, at)),
                          a) + '  (%d unused)' % n)
            a = at
        raw = [mb.byte(at + i) for i in range(size)]
        out.append(';')
        out.append('; XVAR %-3d %-8s %s' % (off, name, what))
        if at != start:               # emit() prints the label for the first
            out.append('%s:' % name)
        if size == 2:                 # a two-byte XVAR is a little-endian word
            out.append('%-14s DEFW %-25s ; %04X'
                       % ('', '&%04X' % (raw[0] | raw[1] << 8), at))
        else:
            out.append('%-14s DEFB %-25s ; %04X = %s'
                       % ('', ','.join('&%02X' % x for x in raw), at,
                          str(raw[0]) if size == 1
                          else ','.join(str(x) for x in raw)))
        a = at + size
    return a, _rows(out)


def name_xvars(mb, start=0x4000):
    """Give each documented XVAR its name."""
    n = 0
    for off, _size, name, _what in XVARS:
        a = start + off
        if mb.inside(a) and a not in mb.labels:
            mb.labels[a] = name
            n += 1
    return n


def banner(text):
    """A doc comment wrapped in a rule, for use as a page header."""
    rule = ';; ' + '-' * 68
    body = '\n'.join(';; ' + line if line else ';;'
                     for line in text.rstrip().split('\n'))
    return rule + '\n' + body + '\n' + rule


XVAR_DOC_BANNER = banner(XVAR_DOC)


def document_features(pages):
    """Attach the manual's description to each routine a table names.

    Returns the count and the keys that matched no label.  A key is a
    label name, so renaming the label leaves the description behind with
    nothing to attach it to and no complaint -- which is how the entry
    for CTAB_USING_S went on saying the question had not been worked out
    for as long as it did, after the label had become CMD_SPLIT_LINE and
    the answer had been written down.
    """
    n, matched = 0, set()
    for page in pages:
        for addr, name in page.labels.items():
            text = FEATURES.get(name)
            if not text:
                continue
            matched.add(name)
            if addr not in page.headers:
                page.headers[addr] = banner(text)
                n += 1
    return n, sorted(set(FEATURES) - matched)


HEADER_DOC = """\
The nine-byte header, which is part of the image the boot sector loads
rather than something stripped off it.  It is the DISCiPLE/+D header the
SAM DOSes inherited, which is why the execute field is never written:
that word is a Spectrum autostart field, and SAMDOS spent it on two page
bytes instead.

    type      19, SAM CODE
    length    bytes within the last page, 14 bits
    start     the address it was saved from
    exec      never written; always &FFFF
    pages     whole 16K pages, so the length is pages*16384 + length
    page      the page the start address is in

The &8000 start is where the file was saved from, not where it runs; see
the note at the top of this listing.  Once the DOS is running this is
overwritten by NSAM, the free-sector map."""


def render_header(dos, start=0x4000):
    """The SAM file header.  Three of its six fields are words."""
    b = [dos.byte(start + i) for i in range(9)]

    def word(i):
        return b[i] | b[i + 1] << 8

    out = [
        '%-14s DEFB %-25s ; %04X type %d, SAM CODE'
        % ('', '&%02X' % b[0], start, b[0]),
        '%-14s DEFW %-25s ; %04X length within the last page'
        % ('', '&%04X' % word(1), start + 1),
        '%-14s DEFW %-25s ; %04X start address'
        % ('', '&%04X' % word(3), start + 3),
        '%-14s DEFW %-25s ; %04X execute address: never written'
        % ('', '&%04X' % word(5), start + 5),
        '%-14s DEFB %-25s ; %04X whole 16K pages, so %d bytes in all'
        % ('', '&%02X' % b[7], start + 7, b[7] * 16384 + word(1)),
        '%-14s DEFB %-25s ; %04X start page (%d)'
        % ('', '&%02X' % b[8], start + 8, b[8]),
    ]
    return start + 9, _rows(out)


HEADER_DOC_BANNER = banner(HEADER_DOC)


MBVARS2_DOC = """The rest of MasterBASIC's variable block, which the manual does not
document -- the XVARs it lists stop at ACRSU, XVAR 89.

Every address below that the code actually reads or writes has a label
and a line of its own, with the cross-reference list naming the routines
that use it; the runs in between are the bytes nothing refers to.  The
names are addresses because nothing here says what these variables are
for, but which are live and who touches them is worth having.

References reach them three ways, all of which resolve to the same
label: straight from this page as &40xx or &41xx, from the DOS page as
&80xx or &81xx -- the window the other half sees this one through -- and
as an inline DEFW parameter.  Nothing reaches them at &C0xx."""


MBVARS2_BANNER = banner(MBVARS2_DOC)


# The boot sector copies 943 bytes from &75E1 in the MasterBASIC page to
# &BC00 -- the DOS page, as the boot sector has it mapped, which is &7C00
# in these listings.  The block is not only an installer: MasterBASIC goes
# on calling into the copy afterwards, &7D79 alone from 27 sites.  So an
# address in the copy is named for the MasterBASIC address it came from.
NL = chr(10)
COPY_DST, COPY_SRC, COPY_LEN = 0x7C00, 0x75E1, 0x3AF


def name_copied_block(dos, mb):
    """Name the copied helpers on both sides of the copy."""
    calls = {}
    for a, ins in mb.insns.items():
        if not ins.text.startswith(('CALL', 'JP ', 'JR ')):
            continue
        p = mb.peer_addr(ins.target, a) if ins.target else None
        if p is not None and COPY_DST <= p < COPY_DST + COPY_LEN:
            calls.setdefault(p, set()).add(a)

    n = 0
    mb.copied_blocks = []
    for dst, sites in sorted(calls.items()):
        src = COPY_SRC + (dst - COPY_DST)
        if dst not in dos.labels:
            dos.labels[dst] = 'MBCOPY_%04X' % src
            n += 1
        mb.copied_blocks.append((src, dst, len(sites)))
    return n


def describe_copied_block(dos, mb):
    """Say of each copied helper where it runs and who calls it there.

    Written after notes/ has had its say, because the banner names the
    label and several of these are renamed there: one that baked in
    MBCOPY_775A when the label was made went on saying so long after the
    label itself had become FIND_ROM_CODE.  A DOC in notes/ still wins,
    as everywhere else.
    """
    n = 0
    for src, dst, sites in getattr(mb, 'copied_blocks', ()):
        if not mb.inside(src) or src in mb.headers:
            continue
        mb.headers[src] = banner(NL.join([
            'Copied to &%04X in the DOS page by the boot sector, and' % dst,
            'called there from %d site%s in this page as DOS_%s.  The'
            % (sites, '' if sites == 1 else 's', dos.labels.get(dst, '?')),
            'bytes the file holds at &%04X in the DOS page are not' % dst,
            'these: they are whatever was in its buffers when the image',
            'was saved, and the copy overwrites them at boot.']))
        n += 1
    return n


DOSBUF_DOC = """The DOS's variables and buffers -- and, from &7C00, the landing ground
for the block the boot sector copies out of the MasterBASIC page.

Routines all over the DOS reach into the lower part of this with
LD HL,&7Cxx and LD (&7Cxx),A, and nothing in the DOS page calls or
jumps into any of it, so as far as this listing goes it is not code.

That is only half the story.  The LDIR at the end of BOOT copies 943
bytes from &75E1 in the MasterBASIC page to &BC00 -- this address, as
the boot sector has the pages mapped -- and jumps to it.  MasterBASIC
then goes on calling into the copy: &7D79 from twenty-seven sites, and
four more addresses once each.  Those are marked MBCOPY_xxxx, named for
the MasterBASIC address they were copied from, which is where the code
that actually runs there can be read.

So the bytes below are whatever was in the DOS's buffers when the image
was saved.  None of them is ever executed."""
