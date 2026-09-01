"""Names for the addresses and constants outside the image.

Four sources, in the order they are trusted:

* the inline parameters in MasterDOS's own source.  `CALL NRRDD / DEFW
  CHADD` names a ROM system variable and `CALL CMR / DEFW BEEPR` a ROM
  routine, so the listing gives an authoritative value-to-name map for
  exactly the ROM addresses this code base touches, under the names its
  author used.
* the SAM ROM's map file, which holds real labels only.  Its export file
  holds equates as well, and those include plain constants -- `LONG: EQU
  16` -- so equates are used only for the &4000-&5FFF variable area,
  where a value that large is an address rather than a count.
* the ROM's jump table at &0100, whose entries are mostly unlabelled but
  each name their target.
* MasterDOS's port equates, taken from how the source uses them.

Nothing here is guessed: every name is read out of one of the two source
trees in ref/.
"""

import os
import pickle
import re

JUMP_TABLE = (0x0100, 0x0190)
SYSVARS = (0x4000, 0x6000)          # the ROM's variable area, hidden behind the DOS page
ROM0 = (0x0000, 0x4000)
ROM1 = (0xC000, 0x10000)


def load_pickle(path):
    with open(path, 'rb') as f:
        return pickle.load(f)


def load_map(path):
    """address -> [label, ...] from a pyz80 map file (labels only)."""
    out = {}
    for line in open(path):
        line = line.strip()
        if '=' in line:
            a, n = line.split('=', 1)
            try:
                out.setdefault(int(a, 16), []).append(n)
            except ValueError:
                pass
    return out


def _pick(names):
    """One name out of a set of aliases: the shortest, ties broken by name."""
    return sorted(names, key=lambda n: (len(n), n))[0]


class Symbols:
    """Value -> (expression, defining name, defining value).

    The expression is what goes in the operand and the pair after it is
    the EQU that has to be emitted for it, so that `XPTR+1` can be
    written as the source wrote it while only `XPTR` is defined.
    """

    def __init__(self):
        self.code = {}          # for jump and call targets outside the image
        self.data = {}          # for inline parameters: also the variable area
        self.vars = {}
        self.lowvars = {}          # ROM system variables, for memory operands

    def _add(self, table, value, expr, name=None, base=None):
        if value in table:
            return
        table[value] = (expr, name if name else expr, value if base is None else base)

    # -- sources ----------------------------------------------------------
    def from_mdos_listing(self, path):
        """Inline DEFW parameters from the MasterDOS listing."""
        pat = re.compile(r'^([0-9A-F]{4}) ((?:[0-9A-F]{2} )+)\s*\t(.*)$')
        inline = False
        for line in open(path, encoding='latin-1'):
            m = pat.match(line)
            src = (m.group(3) if m else line.split('\t')[-1]).split(';')[0].rstrip()
            if inline and m:
                d = re.match(r'\s*DEFW\s+([A-Za-z_]\w*)\s*(?:\+\s*(\d+)\s*)?$', src)
                by = m.group(2).split()
                if d and len(by) >= 2:
                    value = int(by[0], 16) | int(by[1], 16) << 8
                    off = int(d.group(2)) if d.group(2) else 0
                    expr = d.group(1) + ('+%d' % off if off else '')
                    self._add(self.data, value, expr, d.group(1), value - off)
                    if value < 0x4000 or value >= 0xC000:
                        self._add(self.code, value, expr, d.group(1), value - off)
            inline = bool(re.match(r'\s*(?:\w+:)?\s*CALL\s+(CMR|NRRDD?|NRWRD?)\s*$',
                                   src, re.I))

    def from_rom_map(self, path):
        """Real ROM labels, for code addresses only."""
        for addr, names in load_map(path).items():
            if ROM0[0] <= addr < ROM0[1] or ROM1[0] <= addr < ROM1[1]:
                self._add(self.code, addr, _pick(names))
                self._add(self.data, addr, _pick(names))

    def add_rom_entry(self, value, name):
        """A ROM address named by a comment rather than by a label.

        The restarts are the case: ref/samrom/main.asm heads &0010 with
        ";RST 10H - PRINT A" and gives the code after it no label at all,
        so a CALL CMR / DEFW &0010 -- the same entry reached the long way
        round -- had nothing to be called.
        """
        self._add(self.code, value, name)
        self._add(self.data, value, name)

    def from_vars_file(self, path):
        """The ROM's own variable list, for page-0 addresses below &5000.

        `vars.asm` is where the ROM names the system page, and below
        &5000 those names have to be kept apart from ordinary code
        labels: DKP2 and INSTBUF are both &4F00, and picking the shorter
        of the two gives the DEF KEY routine where the buffer is meant.
        Code that runs with the system page at &4000 wants the variable,
        so keep them in a table of their own and let that branch ask for
        it first.
        """
        pat = re.compile(r'^(\w+):\s*EQU\s+&?([0-9A-Fa-f]{1,4})H?')
        for line in open(path, encoding='latin-1'):
            m = pat.match(line)
            if not m:
                continue
            addr = int(m.group(2), 16)
            if SYSVARS[0] <= addr < 0x5000:
                # Three addresses carry two names: INTSTK/BUFF256,
                # FPSB/CDBUFF and ISPVAL/INSTBUF.  In each the list
                # gives the stack or pointer meaning first and the
                # buffer second, and an operand pointing at one of
                # them means the buffer, so the later name wins.
                self.lowvars[addr] = m.group(1)

    def lowvar(self, value):
        return self.lowvars.get(value)

    def from_mdos_comments(self):
        """Names MasterDOS's source gives ROM addresses in comments."""
        for value, (name, _note) in FROM_MDOS_COMMENTS.items():
            self._add(self.data, value, name)
            self.vars.setdefault(value, name)

    def from_rom_equates(self, path):
        """ROM equates, for the variable area the DOS page hides.

        These also go in `vars`, which is what a plain memory operand is
        checked against.  A page and the ROM's variables both occupy
        &4000-&7FFF, so `LD A,(&5ACF)` is ambiguous in principle -- but
        the DOS reaches its own page's bytes through labels the trace
        found, and the names that turn up here (CHAD, XPTR, ELINE,
        LASTK, the printer settings) are unmistakably the ROM's.  Code
        that does this is running with the ROM's map paged in, as the
        vector installer at MB &76E7 demonstrably is.
        """
        rev = {}
        for name, value in load_pickle(path).items():
            if isinstance(value, int) and SYSVARS[0] <= value < SYSVARS[1]:
                rev.setdefault(value, []).append(name)
        for addr, names in rev.items():
            self._add(self.data, addr, _pick(names))
            if addr >= 0x5000:
                self.vars[addr] = _pick(names)

    def from_jump_table(self, rom, mapfile):
        """&0100-&018F: `RST &30 / DW target-&8000`, or `JP target`.

        Only a handful of the entries carry a label of their own, so the
        rest are named after the routine they lead to.
        """
        rev = {}
        for addr, names in load_map(mapfile).items():
            rev.setdefault(addr, _pick(names))
        for a in range(JUMP_TABLE[0], JUMP_TABLE[1], 3):
            op = rom[a]
            word = rom[a + 1] | (rom[a + 2] << 8)
            if op == 0xF7:                      # RST &30, address relative to &8000
                target = (word + 0x8000) & 0xFFFF
            elif op == 0xC3:                    # JP
                target = word
            else:
                continue
            name = rev.get(target)
            if name:
                self._add(self.code, a, 'J_' + name)
                self._add(self.data, a, 'J_' + name)

    def finalise(self, reserved):
        """Make every defining name unique and clear of `reserved`.

        The image has labels of its own, several of which the ROM also
        uses -- both call something CHKHL -- and the ROM map itself
        repeats a name at more than one address.  Anything that clashes
        gets a ROM_ prefix, and a number after that if it still clashes.
        """
        taken = dict()
        for addr in sorted(self.vars):
            name = self.vars[addr]
            if taken.get(name, addr) != addr or name in reserved:
                name = 'ROM_' + name
            taken[name] = addr
            self.vars[addr] = name
        for table in (self.code, self.data):
            for value in sorted(table):
                expr, name, base = table[value]
                if taken.get(name, base) == base and name not in reserved:
                    taken[name] = base
                    continue
                new = 'ROM_' + name
                n = 2
                while taken.get(new, base) != base or new in reserved:
                    new = 'ROM_%s%d' % (name, n)
                    n += 1
                taken[new] = base
                table[value] = (expr.replace(name, new, 1), new, base)

    # -- lookup -----------------------------------------------------------
    # Address zero is the ROM's reset entry, which the ROM's own source
    # calls L0000 because it had no better name for it either.  Nothing
    # in a DOS or an extension calls it, so a zero here is the number
    # zero -- an unset vector, an empty table entry -- and naming it
    # turns `DEFW 0` into `DEFW L0000`, which reads as a pointer.
    def target(self, value):
        if not value:
            return None
        e = self.code.get(value)
        return e[0] if e else None

    def datum(self, value):
        if not value:
            return None
        e = self.data.get(value)
        return e[0] if e else None

    def var(self, value):
        return self.vars.get(value)

    def equates(self, used):
        """The EQU lines needed by the expressions in `used`."""
        out = {}
        for table in (self.code, self.data):
            for expr, name, base in table.values():
                if expr in used:
                    out[name] = base
        for table in (self.vars, self.lowvars):
            for addr, name in table.items():
                if name in used:
                    out[name] = addr
        return out


PORT_LOW = 0x80     # every SAM port number is &80 or above


def ports(sources, sym_paths):
    """Port numbers, from the names the two source trees give them.

    A symbol counts as a port if it is written as the operand of IN or
    OUT, or loaded into C for the `OUT (C)` form, and its value fits in a
    byte.  The SAM ROM's own names are used where both trees have one:
    LRPORT and URPORT rather than anything invented here.
    """
    direct, viac = set(), set()
    io = re.compile(r"""(?:IN\s+\w+\s*,\s*\(|OUT\s*\(\s*)([A-Za-z_]\w*)\s*\)""", re.I)
    ldc = re.compile(r'LD\s+C\s*,\s*([A-Za-z_]\w*)\s*$', re.I)
    block = re.compile(r'\b(IN|OUT|INI|OUTI|IND|OUTD|INIR|OTIR|INDR|OTDR)\b', re.I)
    for path in sources:
        pending, ttl = None, 0      # an LD C,sym waiting to be confirmed
        for line in open(path, encoding='latin-1'):
            line = line.split(';')[0].rstrip()
            if not line.strip():
                continue
            direct.update(m.group(1).upper() for m in io.finditer(line))
            # `LD C,DTRQ` names a port only if an I/O instruction follows
            # soon after; plenty of other constants get loaded into C.
            if pending and block.search(line):
                viac.add(pending)
                pending = None
            m = ldc.search(line)
            if m:
                pending, ttl = m.group(1).upper(), 5
            elif pending:
                ttl -= 1
                if ttl <= 0:
                    pending = None
    out, claimed = {}, {}

    def offer(name, value):
        # The two trees disagree about some names -- STPIN is &59 in one and
        # &5B in the other -- so a name may only ever stand for one value.
        if value is None or not PORT_LOW <= value < 0x100:
            return
        if value in out or claimed.get(name, value) != value:
            return
        out[value] = name
        claimed[name] = value

    tables = [{k.upper(): v for k, v in load_pickle(p).items() if isinstance(v, int)}
              for p in sym_paths]

    def lookup(name):
        for sym in tables:
            if name in sym:
                return sym[name]
        return None

    # A name written straight into an IN or OUT wins over one merely loaded
    # into C: &80 is the MegaRAM port MRPRT and also the disk controller's
    # read-sector command DRSEC.
    for n in sorted(direct):
        offer(n, lookup(n))
    for sym in tables:
        for n, v in sorted(sym.items()):
            if n.endswith('PORT'):
                offer(n, v)
    for n in sorted(viac):
        offer(n, lookup(n))
    return out


def hook_names(dis, table, count=64):
    """Hook codes for `RST &08`, from the image's own hook table.

    `HOOK` doubles the code to index this table, discarding bit 7, so
    entry i is code 128+i.  Where the routine it points at already has a
    name the hook takes it.

    Twenty-four entries do not point into this page at all.  They hold
    an address &8000 higher -- &D00E for &500E -- which is the extension
    seen through the window, because MasterBASIC has taken those hooks
    over.  Resolving them against the peer is what gives the extension's
    own hooks their names; without it every one of them stayed a bare
    number.
    """
    out = {}
    peer = getattr(dis, 'peer', None)
    for i in range(count):
        a = table + 2 * i
        if not dis.inside(a + 1):
            break
        target = dis.word(a)
        home = dis
        if not dis.inside(target):
            if peer is None or not peer.inside(target - 0x8000):
                continue
            target -= 0x8000
            home = peer
        name = home.labels.get(target)
        base = name if name else '%04X' % target
        out[128 + i] = base if base.startswith('HK_') else 'HK_' + base
    return out


def error_names(path):
    """DOS error codes, from the message list in the MasterDOS docs."""
    out = {}
    row = re.compile(r'^\|\s*(\d+)\s*\|\s*\d+\s*\|\s*`([^`]+)`\s*\|')
    for line in open(path, encoding='utf-8'):
        m = row.match(line.strip())
        if m:
            slug = re.sub(r'[^A-Za-z0-9]+', '_', m.group(2)).strip('_').upper()
            if slug and not slug[0].isdigit():
                out[int(m.group(1))] = 'ERR_' + slug[:20]
    return out


def rom_error_names(path):
    """The ROM's error messages, expanded, from ERRMVAL in text.asm.

    The table is compressed: a message is a mix of literal text and codes
    that index a dictionary of common substrings, which is built the same
    way -- a run of characters ended by bit 7, then `NAME: EQU n`.  The
    result checks out against three uses that were already identified
    independently: 19 is the "Loading error" MasterDOS's boot sector
    raises, 29 the "Not understood" SYNTAX tests for, and 53 "No DOS".
    """
    lines = open(path, encoding='latin-1').read().splitlines()
    names, subs, parts = {}, {}, []
    for line in lines:
        code = line.partition(';')[0]
        m = re.match(r'\s*(\w+):\s*EQU\s+(\d+)\s*$', code)
        if m:
            subs[int(m.group(2))] = ''.join(parts)
            names[m.group(1)] = int(m.group(2))
            parts = []
            continue
        if re.match(r'\s*(DM|DB)\b', code):
            parts.extend(t.group(1) for t in re.finditer(r'"([^"]*)"', code))
    subs.pop(0, None)                       # everything before the first EQU

    def expand(items):
        out = []
        for it in items:
            it = it.strip()
            if it.startswith('"'):
                out.append(re.match(r'"([^"]*)"', it).group(1))
            else:
                sym = re.match(r'(\w+)', it)
                if sym and sym.group(1) in names:
                    out.append(subs.get(names[sym.group(1)], ''))
        return ''.join(out)

    try:
        start = next(i for i, l in enumerate(lines) if l.startswith('ERRMVAL:'))
    except StopIteration:
        return {}
    out, buf = {}, []
    for line in lines[start + 1:start + 400]:
        code, _, cmt = line.partition(';')
        if re.match(r'\s*(DM|DB)\b', code):
            buf.extend(re.sub(r'\s*(DM|DB)\s*', '', code, count=1).split(','))
        m = re.match(r'\s*(\d+)\s*$', cmt.strip())
        if m:
            text = expand(buf).strip()
            if text:
                out[int(m.group(1))] = text
            buf = []
        if re.match(r'^\w+:', line) and not line.startswith('ERRMVAL'):
            break
    return out


def error_symbol(code, text, taken):
    """A unique EQU name for an error code."""
    slug = re.sub(r'[^A-Za-z0-9]+', '_', text).strip('_').upper()[:22]
    name = 'ERR_' + (slug if slug and not slug[0].isdigit() else '%d' % code)
    while name in taken and taken[name] != code:
        name += '_%d' % code
    taken[name] = code
    return name


# A trailing comment in these sources is not always a description.  The
# ROM's author wrote sizes as `;(2)`, MasterDOS's wrote usage counts as
# `;3*`, and both wrote timings.  Those are stripped or refused.
_LEAD = re.compile(r'^(\(\d+\)|\d+\*|;)+\s*')
_JUNK = re.compile(r'^(\(\d+\)|[\d\s,()*=-]+|.{0,3})$')
_EQU = re.compile(r'^(\w+):\s+EQU\s+[^;]*;\s*(\S.*?)\s*$')
_LAB = re.compile(r'^(\w+):\s+\S[^;]*;\s*(\S.*?)\s*$')
_JP = re.compile(r'^\s+JP\s+(\w+)\s*;\s*[0-9A-F]{4}\s*(\S.*?)\s*$')
_CONT = re.compile(r'^\s+;\s{2,}(\S.*?)\s*$')
_TIMING = re.compile(r'\b(T STATES|T-STATES|ARRIVE IN|CYCLES)\b', re.I)


def _tidy(text):
    """A description, or '' if the comment was not one."""
    out = _LEAD.sub('', re.sub(r'\s+', ' ', text.strip())).strip(' .')
    if _JUNK.match(out) or _TIMING.search(out):
        return ''
    return out


def descriptions(paths):
    """name -> a one-line description, taken from the sources' comments.

    Four shapes carry one: an EQU with a trailing comment, a label with
    a trailing comment, the ROM's jump table (whose entries wrap onto
    following comment lines), and a whole-line comment sitting directly
    above a label.  The first of those found for a name wins, so a
    specific comment beats a generic banner above it.
    """
    out = {}
    for path in paths:
        if not os.path.exists(path):
            continue
        lines = open(path, encoding='latin-1').read().split('\n')
        for i, line in enumerate(lines):
            name = desc = None
            m = _JP.match(line)
            if m:
                name, desc = m.group(1), m.group(2)
                j = i + 1
                while j < len(lines) and _CONT.match(lines[j]):
                    desc += ' ' + _CONT.match(lines[j]).group(1)
                    j += 1
            if name is None:
                for pat in (_EQU, _LAB):
                    m = pat.match(line)
                    if m:
                        name, desc = m.group(1), m.group(2)
                        break
            if name is None:
                m = re.match(r'^(\w+):', line)
                if m and i and lines[i - 1].strip().startswith(';'):
                    name, desc = m.group(1), lines[i - 1].strip()
            if name and desc:
                got = _tidy(desc)
                # The sources name a pointer and its page as a pair:
                # `ELINP: page holding the edit line` and then
                # `ELINE: (2) address of it`.  On its own the second is
                # useless, so `it` is resolved from the line above.
                m = re.match(r'^address of (it|them)$', got or '')
                if m and i:
                    prev = _tidy(lines[i - 1].split(';', 1)[-1])                         if ';' in lines[i - 1] else ''
                    subject = re.match(r'^page holding (.+)$', prev)
                    if subject:
                        got = 'address of ' + subject.group(1)
                if got and name not in out:
                    out[name] = got
    return out


# The Coupe's own ports, from the SAM Coupe Technical Manual v3.0.  The
# ROM's source names them but does not say what they are.
PORT_NOTES = {
    0xF8: 'base of the colour look-up table: sixteen write-only 7-bit '
          'registers',
    0xF9: 'read: STATUS, key rows and interrupt flags; write: line interrupt',
    0xFA: 'the page at &0000, and the two ROM switches',
    0xFB: 'the page at &8000',
    0xFC: 'the page the screen is displayed from',
    0xFD: 'MIDI in and out',
    0xFE: 'read: keyboard columns; write: border, MIC and the speaker',
    0xFF: 'read: the attribute under the raster; write: sound data, the '
          'sound address port being &1FF',
}


# The sources leave some of the best-known variables uncommented -- the
# ROM's author had no need to write down what STKEND was.  These are
# mine, not his, and the listing says so where it prints them.
# Addresses in the ROM's variable area that its own source leaves
# unlabelled and MasterDOS's source names in a comment.  &5C16 is the one
# that forced this: MasterDOS writes `LD HL,&5C16+FS ;STREAM ZERO` three
# times, so &5C16 begins the ROM's table of streams.  Without a name for
# it, every &9C16 in the DOS came out as a reference to MasterBASIC's own
# &5C16, which is unrelated code that happens to sit at the same address.
FROM_MDOS_COMMENTS = {
    0x5C16: ('STRMS', 'the table of streams; stream zero first'),
}


EXTRA_NOTES = {
    'SKIP_NEXT_2_BYTES': 'the opcode of LD HL,nn, standing here only to'
                         ' swallow the two bytes after it, see docs/idioms.md',
    'STKEND': 'end of the calculator stack',
    'WORKSP': 'address of the workspace',
    'WORKSPP': 'page holding the workspace',
    'RAMTOP': 'last address BASIC may use',
    'RAMTOPP': 'page holding RAMTOP',
    'PPC': 'line number of the statement being run',
    'SUBPPC': 'number of that statement within its line',
    'EPPC': 'line number of the cursor line',
    'FLAGX': 'flags: bit 5 set while INPUT is in progress',
    'TVDATA': 'the parameters of a control code being collected',
    'MODE': 'screen mode, 0 to 3',
    'CHARS': 'address of the character set less 256',
    'KCUR': 'address of the cursor in the edit line',
    'ELINEP': 'page holding the edit line',
    'ATTRT': 'attribute used by temporary colour statements',
    'BASSTK': "base of BASIC's GOSUB, DO and PROC stack",
    'BSTKEND': 'end of that stack',
    'LISTSP': 'stack pointer saved before an automatic listing',
    'NRREAD': 'ROM entry: read a byte of a system variable',
    'NRWRITE': 'ROM entry: write a byte of a system variable',
    'GETCHAR': 'ROM entry: the character at CHAD, control codes skipped',
    'NEXTCHAR': 'ROM entry: step CHAD and fetch the character there',
    'PRINTSTR': 'ROM entry: print BC characters from (DE)',
    'HLJPI': 'ROM entry: jump to the address in HL',
    'IXJUMP': 'ROM entry: jump to the address in IX',
    'DELBC': 'ROM entry: a delay of BC iterations',
    'PRINT_A': 'ROM entry: print the character in A',
    'STRMS': FROM_MDOS_COMMENTS[0x5C16][1],
    'RST8V': 'vector taken by RST &08 before the ROM handles it',
    'RST28V': 'vector taken by the calculator before each literal',
    'PRTOKV': 'vector for printing a keyword token',
    'MTOKV': 'vector for matching a keyword while tokenising',
    'EVALUV': 'vector for evaluating an expression',
    'CMDV': 'vector for dispatching a command',
    'EDITV': 'vector taken by the editor',
    'PALTAB': "the sixteen CLUT entries, as the ROM's copy",
    'LINICOLS': 'per-line colour data for the current screen',
}
