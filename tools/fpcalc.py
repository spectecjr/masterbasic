"""The floating-point calculator's literal stream.

`RST FPCALC` is followed by a list of one-byte operations, not by
instructions.  The ROM's entry at &0028 does `EX (SP),IX` so that IX
points at the byte after the RST, and FPCMAIN walks it from there,
stepping IX past each literal and any bytes that literal consumes.

Decoding those bytes as Z80 is how &25 &27 came out as `DEC H` / `DAA`.

Everything here is read out of ref/samrom/fpcmain.asm rather than typed
in.  Its table is a run of

    DW FPMULT     ;00 MULT

so the code and the ROM's own name for it are both in the source, and
the parse below takes them from there.  The counts of trailing bytes
come from the routines themselves -- FP5LIT does `LD B,5`, FPSOMELIT
reads a count first, LKADDRSR reads a word -- and are listed here
because that is not something a table can be read off.
"""

import os
import re

# The first entry carries the table's label -- FPATAB: DW FPMULT ;00
# MULT -- so the line does not begin with whitespace, and requiring
# that dropped code &00 from the table entirely.
TABLE = re.compile(r'^(?:\w+:)?\s+DW\s+\w+\s*;([0-9A-F]{2})\s+(\S.*?)\s*$')
CLEAN = re.compile(r'^[A-Za-z][A-Za-z0-9]*$')

# Literals that eat bytes of their own.  SOMELIT is special: its first
# byte is a count of the bytes after it.
INLINE = {
    0x1E: 1,        # JPTRUE   displacement
    0x1F: 1,        # JPFALSE  displacement
    0x20: 1,        # JUMP     displacement
    0x21: 1,        # LDBREG   the value for B
    0x26: 1,        # ONELIT   one byte, stacked as a small integer
    0x27: 5,        # FIVELIT  a five-byte floating point number
    0x29: 2,        # LKADDRB  address to peek
    0x2A: 2,        # LKADDRW  address to dpeek
}
SOMELIT = 0x28

# &33 returns to just past the list; &34 and the spares after it drop the
# calculator's caller as well, so nothing follows them here.
EXIT, EXIT2 = 0x33, 0x34
ENDS = (0x33, 0x34, 0x35, 0x36, 0x37, 0x38)


def names(root):
    """code -> the ROM's name for it."""
    path = os.path.join(root, 'ref', 'samrom', 'fpcmain.asm')
    out = {}
    for line in open(path, encoding='latin-1'):
        m = TABLE.match(line)
        if m:
            out.setdefault(int(m.group(1), 16), m.group(2))
    for base, n, sym, why in RANGES:
        for i in range(n):
            out.setdefault(base + i, (sym % i) + ' -- ' + (why % i))
    return out


# Four ranges the table does not cover: FPCMAIN reaches them by adding
# &20 and then &08 at a time and branching on carry, so &E0-&FF are the
# thirty-two constants, &D8-&DF recall, &D0-&D7 store, and &C8-&CF store
# with delete.
RANGES = ((0xE0, 32, 'CONST%d', 'stack constant %d'),
          (0xD8, 8, 'RCL%d', 'recall memory %d'),
          (0xD0, 8, 'STO%d', 'store to memory %d'),
          (0xC8, 8, 'STOD%d', 'store to memory %d, deleting'))


def symbol(name):
    """A label for a literal, where its name can be one."""
    word = name.split()[0]
    return 'FPC_' + word.upper() if CLEAN.match(word) else None


def value(b):
    """The number in five bytes of the ROM's floating-point form.

    A zero exponent means the small-integer form STACKC builds: sign
    byte, then the value low byte first.  Otherwise the exponent is
    biased by 128, the mantissa is the four bytes that follow with an
    implicit leading 1 restored in place of the sign bit, and the value
    is that fraction times two to the power of the exponent.
    """
    if len(b) != 5:
        return None
    if b[0] == 0:
        n = b[2] | (b[3] << 8)
        return -((0x10000 - n) & 0xFFFF) if b[1] else n
    m = ((b[1] | 0x80) << 24) | (b[2] << 16) | (b[3] << 8) | b[4]
    v = (m / float(1 << 32)) * (2.0 ** (b[0] - 128))
    return -v if b[1] & 0x80 else v


def show(v):
    """A number as a reader wants to see it, not as a float repr."""
    if isinstance(v, int) or v == int(v):
        return '%d' % int(v)
    return ('%.9g' % v)


def note(code, extra, at, name=None):
    """What the bytes after a literal mean, for the comment."""
    if code == 0x26 and extra:                    # ONELIT
        return '= %d' % extra[0]
    if code == 0x21 and extra:                    # LDBREG
        return 'B = %d' % extra[0]
    if code in (0x1E, 0x1F, 0x20) and extra:      # JPTRUE, JPFALSE, JUMP
        d = extra[0] - 256 if extra[0] > 127 else extra[0]
        # The jump is relative to the displacement byte itself: IX still
        # points at it when FPJUMP does ADD IX,BC.
        return 'to &%04X (%+d)' % (at + 1 + d, d)
    if code in (0x29, 0x2A) and len(extra) == 2:  # LKADDRB, LKADDRW
        addr = extra[0] | (extra[1] << 8)
        return 'at ' + (name(addr) if name else '&%04X' % addr)
    if code == 0x27 and len(extra) == 5:          # FIVELIT
        v = value(extra)
        return '= ' + show(v) if v is not None else ''
    if code == SOMELIT and len(extra) > 1:
        nums = [value(extra[1 + i:6 + i]) for i in range(0, len(extra) - 1, 5)]
        nums = [show(v) for v in nums if v is not None]
        return '= ' + ', '.join(nums) if nums else ''
    return ''


_TABLES = {}


def load(root):
    """Read the ROM's tables once, so scan() can check what it finds."""
    if not _TABLES:
        _TABLES['names'] = names(root)
        _TABLES['consts'] = constants(root)
    return _TABLES['names'], _TABLES['consts']


def plausible(code):
    """Could this byte be a calculator literal at all?

    A code the ROM does not name, or a constant index that reads past
    the end of FPCTAB, means the RST that led here is a byte being
    decoded as an instruction.  Two of the ten RST &28s in this image
    are exactly that, and without the check they came out as lists full
    of `NOT PRIORITY 4` and `HEX$`.
    """
    if not _TABLES:
        return True
    if _TABLES['names'].get(code) is None:
        return False
    if code >= 0xE0 and (code - 0xE0) + 5 > len(_TABLES['consts']):
        return False
    return True


def scan(d, a, limit=64):
    """Walk a literal list from `a`.

    Returns (end, resumes, items) where items are (addr, code, extra) and
    `resumes` says whether execution carries on at `end` -- it does after
    EXIT, but EXIT2 returns past the caller, so nothing follows it.
    """
    items, p = [], a
    for _ in range(limit):
        if not d.inside(p):
            return None
        code = d.byte(p)
        if not plausible(code):
            return None
        n = INLINE.get(code, 0)
        if code == SOMELIT:
            if not d.inside(p + 1):
                return None
            n = 1 + d.byte(p + 1)
        if not d.inside(p + n):
            return None
        items.append((p, code, n))
        p += 1 + n
        if code in ENDS:
            return p, code == EXIT, items
    return None


def render(d, items, syms):
    """The list as assembler, one literal to a line."""
    out = []
    for at, code, n in items:
        name = syms.get(code, '')
        sym = symbol(name) if name else None
        if sym:
            d.basic_equs[sym] = code
            head = sym
        else:
            head = '&%02X' % code
        extra = [d.byte(at + 1 + i) for i in range(n)]
        if extra:
            head += ',' + ','.join('&%02X' % b for b in extra)
        why = note(code, extra, at, d.mem16)
        out.append(('%-14s DEFB %-25s ; %04X %s %s'
                    % ('', head, at, name, why)).rstrip())
    return '\n'.join(out) + '\n'


CTAB = re.compile(r'^\s+DB\s+(.+?)\s*(?:;.*)?$')
BYTE = re.compile(r'^(?:&([0-9A-Fa-f]+)|(\d+))$')


def constants(root):
    """FPCTAB, the packed table the CONSTn literals index.

    The index is a byte offset, not a slot, so the constants overlap and
    the ROM's own comment says "many values of C make no sense".  The
    table is 21 bytes; anything above &10 reads past it into FPEXIT, so
    a stream that uses one is not a calculator stream at all.
    """
    path = os.path.join(root, 'ref', 'samrom', 'fpcmain.asm')
    lines = open(path, encoding='latin-1').read().split('\n')
    at = next(i for i, l in enumerate(lines) if l.startswith('FPCTAB:'))
    out = []
    for line in lines[at:]:
        if line.startswith('FPEXIT'):
            break
        body = line.split(':', 1)[-1] if line.startswith('FPCTAB:') else line
        m = CTAB.match(body if body.startswith(' ') else '  ' + body.strip())
        if not m:
            continue
        for part in m.group(1).split(','):
            b = BYTE.match(part.strip())
            if b:
                out.append(int(b.group(1), 16) if b.group(1) else int(b.group(2)))
    return out


BINARY = {
    'MULT': '%s * %s', 'ADDN': '%s + %s', 'CONCAT': '%s + %s',
    'SUBN': '%s - %s', 'POWER': '%s ^ %s', 'DIVN': '%s / %s',
    'MOD': '%s MOD %s', 'IDIV': '%s DIV %s', 'BOR': '%s BOR %s',
    'BAND': '%s BAND %s', 'OR': '%s OR %s', 'AND': '%s AND %s',
}
COMPARE = {'NNOTE': '<>', 'NLESE': '<=', 'NGRTE': '>=', 'NLESS': '<',
           'NEQUAL': '=', 'NGRTR': '>'}
UNARY = {'LESS0': '%s < 0', 'LESE0': '%s <= 0', 'GRTR0': '%s > 0',
         'GRTE0': '%s >= 0', 'TRUNC': 'INT %s', 'POWR2': '2 ^ %s',
         'NEGATE': '-%s', 'ABS': 'ABS %s', 'INT': 'INT %s'}
KEEP = ('RESTACK', 'REDARG')          # change the form, not the value


class Stack:
    """The calculator stack, holding expressions instead of numbers."""

    def __init__(self):
        self.items = []
        self.taken = 0                # values that were already there

    NAMES = ('x', 'y', 'z', 'w')

    def need(self, n):
        while len(self.items) < n:
            i = self.taken
            self.taken += 1
            self.items.insert(0, self.NAMES[i] if i < len(self.NAMES)
                              else 'v%d' % (i + 1))

    def pop(self):
        self.need(1)
        return self.items.pop()

    def push(self, v):
        self.items.append(v)

    def swap(self, a, b):
        self.need(max(a, b))
        i, j = -a, -b
        self.items[i], self.items[j] = self.items[j], self.items[i]


def wrap(e):
    return e if re.match(r'^[\w.$&]+$', e) else '(%s)' % e


def fold(sign, a, b):
    """Work a sub-expression out when both sides are already numbers."""
    try:
        x, y = float(a), float(b)
    except ValueError:
        return None
    if sign == '+':
        return show(x + y)
    if sign == '-':
        return show(x - y)
    if sign == '*':
        return show(x * y)
    if sign == '/' and y:
        return show(x / y)
    return None


def binary(st, word, name):
    """Apply a two-operand literal to the stack."""
    b, a = st.pop(), st.pop()
    if word in COMPARE:
        st.push('%s %s %s' % (wrap(a), COMPARE[word], wrap(b)))
        return True
    form = BINARY.get(word)
    if not form:
        return False
    sign = form.replace('%s', '').strip()
    done = fold(sign, a, b) if len(sign) == 1 else None
    st.push(done if done else form % (wrap(a), wrap(b)))
    return True


def summarise(items, names, consts, d):
    """What a literal list computes, where that can be said.

    Returns None when the list cannot be one: an unnamed code, or a
    constant index past the end of FPCTAB.  Either means the RST that
    starts it is a byte being read as an instruction rather than a real
    call, and summarising nonsense is worse than saying nothing.
    """
    st, mem, branch = Stack(), {}, None
    for at, code, n in items:
        name = names.get(code)
        if not name:
            return None
        word = name.split()[0]
        extra = [d.byte(at + 1 + i) for i in range(n)]
        if code in ENDS:
            break

        if 0xE0 <= code:                                   # CONSTn
            i = code - 0xE0
            if i + 5 > len(consts):
                return None                                # past the table
            st.push(show(value(consts[i:i + 5])))
        elif 0xD8 <= code < 0xE0:                          # RCLn
            st.push(mem.get(code - 0xD8, 'memory %d' % (code - 0xD8)))
        elif 0xD0 <= code < 0xD8:                          # STOn
            st.need(1)
            mem[code - 0xD0] = st.items[-1]
        elif 0xC8 <= code < 0xD0:                          # STODn
            mem[code - 0xC8] = st.pop()
        elif word == 'DUP':
            st.need(1)
            st.push(st.items[-1])
        elif word == 'DROP':
            st.pop()
        elif word == 'SWOP':
            st.swap(1, 2)
        elif word == 'SWOP13':
            st.swap(1, 3)
        elif word == 'SWOP23':
            st.swap(2, 3)
        elif word in KEEP:
            pass
        elif word in UNARY:
            st.push(UNARY[word] % wrap(st.pop()))
        elif word in ('JPTRUE', 'JPFALSE'):
            if branch is not None:
                return None                     # one branch is all this handles
            branch = (st.pop(), word == 'JPTRUE', list(st.items))
        elif word in ('ONELIT', 'FIVELIT', 'SOMELIT', 'LKADDRB', 'LKADDRW'):
            st.push(literal_text(code, extra, d))
        elif binary(st, word, name):
            pass
        else:
            return None                         # something not modelled
    return phrase(st, branch)


def literal_text(code, extra, d):
    """The value a literal stacks, as it should read in an expression."""
    if code in (0x29, 0x2A) and len(extra) == 2:
        word = 'PEEK' if code == 0x29 else 'DPEEK'
        return '%s %s' % (word, d.mem16(extra[0] | (extra[1] << 8)))
    if code == 0x26 and extra:                       # ONELIT
        return '%d' % extra[0]
    if code == 0x27 and len(extra) == 5:             # FIVELIT
        v = value(extra)
        return show(v) if v is not None else 'a number'
    if code == SOMELIT and len(extra) > 1:           # several at once
        return 'numbers'
    return 'a value'


def phrase(st, branch):
    """The stack, and any branch, put into words."""
    def listing(items):
        return ', '.join(items) if items else 'nothing'

    if branch is not None:
        cond, on_true, kept = branch
        if not on_true:
            cond = 'not (%s)' % cond
        same = kept == st.items
        if same:
            return '= %s' % listing(st.items)
        return ('= %s when %s, otherwise %s'
                % (listing(kept), cond, listing(st.items)))
    if len(st.items) == 1:
        return '= %s' % st.items[0]
    return 'leaves %s (last on top)' % listing(st.items)
