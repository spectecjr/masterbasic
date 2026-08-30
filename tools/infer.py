"""Name the extension page's immediates from what the code around them does.

This is not carrydoc.  There is no MasterBASIC source to carry from, so
nothing here is evidence in that sense: every name below is a *reading*
of the surrounding instructions, and the listing says so where it
defines them.  The bytes cannot change -- a name is only ever written
where it has the value already there -- but a wrong reading would put a
confident wrong word on the page, which is worse than a number.

So each rule has to point at something in the code, and the ones that
cannot are left as hex:

  wrappers   A routine that is only `CALL CMR / DEFW <rom> / RET` is that
             ROM routine under another name.  This one really is proof.
  PAGEMASK   AND &1F within a few instructions of an IN or OUT on the
             paging ports.  A SAM has 32 pages, and LMPR and HMPR hold
             the number in bits 0 to 4.
  UPPER      AND &DF applied to a byte just loaded from memory clears bit
             5, which folds a letter to upper case.
  tokens     CP against a value the ROM's keyword table names, where the
             comparison follows a call to one of the character fetchers
             above -- so what is in A is a token, not arithmetic.
  characters CP, SUB or ADD against printable ASCII in the same
             position.

The last two are why the chain test matters.  `ADD A,&10 / CP &FE` looks
like a test for the token &FE until you notice A came from adding to a
screen address, and `LD A,H / CP &FF` is a range check on a pointer.
Both are rejected because nothing loaded a character first.
"""

import re

# How far back to look for what put a value in A.
WINDOW = 4

PAGE_PORTS = ('&FA', '&FB', '&FC')      # LMPR, HMPR, VMPR

# Characters worth a name.  Anything not here stays as it is: naming
# every printable byte would put CH_A on an arithmetic constant.
CHARS = {
    0x0D: ('CH_CR', 'carriage return, the end of a BASIC line'),
    0x20: ('CH_SPACE', 'space'),
    0x22: ('CH_QUOTE', 'the string delimiter'),
    0x23: ('CH_HASH', 'the stream marker, as in PRINT #'),
    0x24: ('CH_DOLLAR', 'the string-variable suffix'),
    0x28: ('CH_LPAREN', 'open bracket'),
    0x29: ('CH_RPAREN', 'close bracket'),
    0x2C: ('CH_COMMA', 'the argument separator'),
    0x2E: ('CH_DOT', 'the decimal point'),
    0x30: ('CH_ZERO', 'ASCII "0", for digit conversion'),
    0x3A: ('CH_COLON', 'the statement separator'),
    0x3B: ('CH_SEMI', 'semicolon'),
    0x3D: ('CH_EQUALS', 'equals'),
}

PAGEMASK = ('PAGEMASK', 'the page number in LMPR and HMPR, bits 0 to 4')
UPPER = ('UPPER', 'clearing bit 5 folds a letter to upper case')
FN_PFX = ('FN_PFX', 'the byte before a function token')

LOADS_A = re.compile(r'^LD A,\((HL|DE|BC|IX|IY|&[0-9A-F]{4})')

# Anything that puts a new value in A ends the walk: what a fetcher
# returned is no longer there.
WRITES_A = re.compile(r'^(LD A,|ADD A,|ADC A,|SUB |SBC A,|AND |OR |XOR |'
                      r'INC A$|DEC A$|RLCA$|RRCA$|RLA$|RRA$|DAA$|CPL$|NEG$|'
                      r'POP AF$|EX AF|IN A,|RLD$|RRD$)')

# Only an unconditional one: `JR Z,nn` falls through with A untouched,
# which is exactly how a run of CP tests against different tokens works.
BREAKS = re.compile(r'^(RET$|RETI$|RETN$|HALT$|JP [^,]*$|JR [^,]*$|JP \()')

SYNTHETIC = re.compile(r'^L[0-9A-F]{4}$')


def wrappers(d, cmr, syms):
    """Routines that are nothing but a call through to the ROM.

    `CALL CMR / DEFW addr / RET` pages the ROM in, calls it and comes
    back.  The extension has a dozen of these and they are the busiest
    labels in the listing, so a name for each is worth having: L4461 is
    the ROM's NEXTCHAR and reads much better said that way.
    """
    out = {}
    for a, ins in sorted(d.insns.items()):
        if not ins.text.startswith('CALL ') or ins.target != cmr:
            continue
        rom = d.word(ins.end)
        after = d.insns.get(ins.end + 2)
        if rom is None or after is None or after.text != 'RET':
            continue
        name = syms.target(rom) if syms else None
        if not name or not re.match(r'^\w+$', name) or SYNTHETIC.match(name):
            continue
        out[a] = 'CALL_' + name
    return out


def chain(d, order, k):
    """What put the value in A, looking back over a few instructions.

    Returns 'token' if a character fetcher was called, 'load' if A came
    out of memory, or None -- including when the walk runs into an
    unconditional jump or return, since then the instructions above are
    not what ran.
    """
    for j in range(k - 1, max(-1, k - 1 - WINDOW), -1):
        text = d.insns[order[j]].text
        if text.startswith('CALL '):
            target = d.insns[order[j]].target
            if target is not None and d.fetchers and target in d.fetchers:
                return 'token'
            return None                     # some other call clobbered A
        if LOADS_A.match(text):
            return 'load'
        if WRITES_A.match(text) or BREAKS.match(text):
            return None
    return None


def paging_near(d, order, k):
    """True if a paging port is read or written close by."""
    for j in range(max(0, k - 3), min(len(order), k + 4)):
        text = d.insns[order[j]].text
        if text.startswith(('IN ', 'OUT ')) and any(p in text for p in PAGE_PORTS):
            return True
    return False


def name_immediates(d, tokens):
    """Write names over the 8-bit immediates the rules can account for."""
    order = sorted(d.insns)
    reasons = {}
    named = 0
    for k, a in enumerate(order):
        ins = d.insns[a]
        if ins.length != 2 or a in d.overrides:
            continue
        op, v = d.byte(a), d.byte(a + 1)
        got = None
        if op == 0xE6 and v == 0x1F and paging_near(d, order, k):
            got = PAGEMASK
        elif op == 0xE6 and v == 0xDF and chain(d, order, k) == 'load':
            got = UPPER
        elif op in (0xFE, 0xD6, 0xC6):
            kind = chain(d, order, k)
            if kind is not None:
                if v == 0xFF and kind == 'token':
                    got = FN_PFX
                elif 0x85 <= v <= 0xFE and kind == 'token':
                    word = tokens.cmd.get(v)
                    if word and word != '-' and re.match(r'^[A-Z ]+$', word):
                        got = ('T_' + word.replace(' ', '_'),
                               'the BASIC keyword %s' % word)
                elif v in CHARS:
                    got = CHARS[v]
        if got is None:
            continue
        name, why = got
        d.overrides[a] = re.sub(r'&%02X$' % v, name, ins.text)
        if d.overrides[a] == ins.text:
            del d.overrides[a]
            continue
        reasons[name] = (v, why)
        named += 1
    return named, reasons


def name_port_loads(d):
    """Write the port's name where C is loaded with its number.

    `LD C,&FA` followed by `OUT (C),A` is a write to LMPR, and saying so
    is no more of a guess than writing `OUT (LRPORT),A` for the one-byte
    form -- which the listing already does.  Only the register that
    carries the port is rewritten: in `OUT (C),r` the Z80 puts B on
    A8-A15, and the serial driver uses that to select a register on the
    UART, so a `LD B,&02` next to a port access is not a port at all.
    """
    order = sorted(d.insns)
    named = 0
    for k, a in enumerate(order):
        ins = d.insns[a]
        if a in d.overrides or not ins.text.startswith('LD C,&'):
            continue
        v = d.byte(a + 1)
        name = d.ports.get(v)
        if not name:
            continue
        # The load has to reach a port access with nothing in between
        # that reloads C.
        for j in range(k + 1, min(len(order), k + 6)):
            text = d.insns[order[j]].text
            if '(C)' in text and text.startswith(('IN ', 'OUT ')):
                d.overrides[a] = 'LD C,' + name
                named += 1
                break
            if text.startswith(('LD C,', 'LD BC,', 'POP BC', 'EXX', 'RET')):
                break
    return named


# The ROM's restarts, from the comments and labels in ref/samrom/main.asm.
# &30 and &38 are left as numbers: &30 is a call-with-inline-parameters
# mechanism with no name in the ROM source, and a RST &38 in the middle
# of a routine is an &FF byte being decoded as code -- naming it would
# dress up a misdisassembly as something deliberate.
RESTARTS = {
    0x08: ('ERR_HOOK', 'report an error, or call a DOS hook: the byte after '
                       'is\nan error number, or a hook code from 128 up'),
    0x10: ('PRINT_A', 'print the character in A'),
    0x18: ('GET_CHAR', 'the character at CHAD, control codes skipped'),
    0x20: ('NEXT_CHAR', 'step CHAD and get the character there'),
    0x28: ('FPCALC', 'the floating-point calculator; the bytes after it '
                     'are\nits literals, not instructions'),
}


def name_restarts(d):
    """Write the ROM's name for a restart instead of its address."""
    named = 0
    for a, ins in sorted(d.insns.items()):
        if a in d.overrides or not ins.text.startswith('RST &'):
            continue
        got = RESTARTS.get(ins.target)
        if not got:
            continue
        d.overrides[a] = 'RST ' + got[0]
        d.rst_equs[got[0]] = (ins.target, got[1])
        named += 1
    return named
