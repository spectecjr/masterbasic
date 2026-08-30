"""SAM BASIC token tables, and a renderer for tokenised program text.

The token names come out of the SAM ROM itself rather than being typed in
here: `KEYWTAB` in ref/samrom/text.asm holds four command sub-lists and
three function lists, each a run of words ended by bit 7 of the last
character.  tprint.asm's `PRGR802` and `PSTFF2` give the mapping from a
token byte to a list and an index, and that is what `Tokens` reproduces.

    command   &85-&FE   one byte
    function  &FF nn    nn is &3B-&84

Inside a string literal bytes &80 and up are graphics characters, not
tokens -- "QUOTES FORCES UDGS", as text.asm puts it -- so the renderer
tracks quote state.
"""

import re

# tprint.asm: SUB PITOK / CP SINTOK-PITOK / SUB MODTOK-PITOK
PITOK, SINTOK, MODTOK = 0x3B, 0x53, 0x7A
CMD_LISTS = (('KWDS85', 0x85, 0x1B), ('KWDSA0', 0xA0, 0x20),
             ('KWDSC0', 0xC0, 0x20), ('KWDSE0', 0xE0, 0x1F))
FN_LISTS = (('IMFNTL', PITOK, SINTOK - PITOK),
            ('FPCFNTL', SINTOK, MODTOK - SINTOK),
            ('BINFNTL', MODTOK, 0x0B))

NUM = 0x0E              # marks the five-byte binary form of a number
CR = 0x0D
CTRL = {0x10: 'PEN', 0x11: 'PAPER', 0x12: 'FLASH', 0x13: 'BRIGHT',
        0x14: 'INVERSE', 0x15: 'OVER', 0x16: 'AT', 0x17: 'TAB'}
CTRL_ARGS = {0x16: 2}   # AT takes two, the rest take one

MANGLE = {'<>': 'NE', '<=': 'LE', '>=': 'GE'}


def read_map(path):
    out = {}
    for line in open(path):
        line = line.strip()
        if '=' in line:
            a, n = line.split('=', 1)
            try:
                out[n] = int(a, 16)
            except ValueError:
                pass
    return out


class Tokens:
    """The ROM's token tables, indexed by token byte."""

    def __init__(self, rom, sym, rom1_base=0xC000, rom1_off=0x4000):
        self.cmd, self.fn = {}, {}

        def words(addr, n):
            o = rom1_off + (addr - rom1_base)
            out = []
            for _ in range(n):
                s = ''
                while True:
                    b = rom[o]
                    o += 1
                    s += chr(b & 0x7F)
                    if b & 0x80:
                        break
                out.append(s)
            return out

        for name, base, n in CMD_LISTS:
            for i, word in enumerate(words(sym[name], n)):
                self.cmd[base + i] = word
        for name, base, n in FN_LISTS:
            for i, word in enumerate(words(sym[name], n)):
                self.fn[base + i] = word

    @staticmethod
    def _sym(prefix, word):
        """A symbol name for a keyword: T_GO_TO, F_VAL_S, F_NE."""
        if word == '-':
            return None
        w = MANGLE.get(word)
        if w is None:
            w = word.replace('$', '_S').replace(' ', '_')
        if not re.fullmatch(r'\w+', w):
            return None
        return prefix + w

    def command(self, code):
        return self.cmd.get(code), self._sym('T_', self.cmd.get(code, '-'))

    def function(self, code):
        return self.fn.get(code), self._sym('F_', self.fn.get(code, '-'))


def number(b):
    """The value of the five bytes after &0E, small-integer form only."""
    if b[0] == 0 and b[4] == 0:
        v = b[2] | (b[3] << 8)
        return -((0x10000 - v) & 0xFFFF) if b[1] else v
    return None


class BasicText:
    """Renders a run of tokenised BASIC as commented, named assembler.

    The text is a series of program lines -- two bytes of line number
    high first, two of length low first, the statement, then &0D -- and
    may begin or end part way through one, since these are fragments
    MasterBASIC pastes together rather than a whole program.
    """

    def __init__(self, dis, start, end, toks):
        self.d = dis
        self.start = start
        self.end = end
        self.t = toks
        self.equs = {}

    def byte(self, a):
        return self.d.byte(a)

    # -- listing text, for the comment above each line ---------------------
    def listing(self, s, e):
        """As LIST would show it, spacing included.

        tprint.asm gives commands a space on both sides, the FPC functions
        and FN and BIN a trailing one only, and the rest none; a trailing
        space is dropped unless the keyword ends in a letter.
        """
        out, a, quoted = [], s, False

        def keyword(word, lead, trail):
            if lead and out and out[-1] != ' ':
                out.append(' ')
            out.append(word)
            if trail and word[-1].isalpha():
                out.append(' ')

        while a < e:
            c = self.byte(a)
            if c == 0x22:
                quoted = not quoted
                out.append('"')
                a += 1
            elif c in CTRL and a + CTRL_ARGS.get(c, 1) < e:
                n = CTRL_ARGS.get(c, 1)
                out.append('{%s %s}' % (CTRL[c],
                                        ','.join(str(self.byte(a + 1 + i)) for i in range(n))))
                a += 1 + n
            elif quoted:
                # In a string &80-&A8 are the block graphics and extended
                # characters, not keywords.
                out.append(chr(c) if 32 <= c < 127 else
                           '{gr &%02X}' % c if 0x80 <= c <= 0xA8 else '{&%02X}' % c)
                a += 1
            elif c == 0xFF and a + 1 < e:
                t = self.byte(a + 1)
                word = self.t.fn.get(t)
                if not word or word == '-':
                    out.append('{FN &%02X}' % t)
                else:
                    both = MODTOK <= t <= 0x80          # MOD .. AND
                    trail = both or SINTOK <= t < MODTOK or t in (0x42, 0x43)
                    keyword(word, both, trail)
                a += 2
            elif 0x85 <= c <= 0xFE:
                word = self.t.cmd.get(c)
                if not word or word == '-':
                    out.append('{&%02X}' % c)
                else:
                    keyword(word, True, True)
                a += 1
            elif c == NUM:
                a += 6                       # the digits were printed already
            elif c == CR:
                a += 1
            elif 32 <= c < 127:
                out.append(chr(c))
                a += 1
            else:
                out.append('{&%02X}' % c)
                a += 1
        return ''.join(out)

    # -- assembler ---------------------------------------------------------
    def render(self):
        lines = []
        a = self.start
        first = True
        while a < self.end:
            head, num = [], None
            if not first and a + 4 <= self.end:
                num = (self.byte(a) << 8) | self.byte(a + 1)
                ln = self.byte(a + 2) | (self.byte(a + 3) << 8)
                # The line number is stored high byte first, so it stays
                # two DEFBs: a DEFW would assemble it the other way round.
                # The length that follows is low first, so that is a DEFW.
                head.append('%-14s DEFB %-25s ; %04X line %d, high byte first'
                            % ('', '&%02X,&%02X' % (self.byte(a), self.byte(a + 1)), a, num))
                head.append('%-14s DEFW %-25s ; length, low byte first' % ('', ln))
                a += 4
            b = a
            while b < self.end and self.byte(b) != CR:
                b += 1
            b = min(b + 1, self.end)
            text = self.listing(a, b)
            # The comment heads the whole line, the four bytes of line
            # number and length included: they belong to the line below
            # it, not to the one that has just ended.
            lines.append(';')
            lines.append(('; %s' % text if first else '; %d %s' % (num, text)).rstrip())
            lines.extend(head)
            lines.extend(self._body(a, b))
            a = b
            first = False
        return '\n'.join(lines) + '\n', self.equs

    def _body(self, s, e):
        out, run, a, quoted = [], [], s, False

        def flush():
            if run:
                out.append('%-14s DEFM "%s"' % ('', ''.join(run).replace('"', '""')))
                del run[:]

        while a < e:
            c = self.byte(a)
            if c == 0x22:
                quoted = not quoted
                run.append('"')
                a += 1
                continue
            if 32 <= c < 127 and (quoted or c != 0x0E):
                run.append(chr(c))
                a += 1
                continue
            if c in CTRL and a + CTRL_ARGS.get(c, 1) < e:
                flush()
                n = CTRL_ARGS.get(c, 1)
                args = [self.byte(a + 1 + i) for i in range(n)]
                sym = 'C_' + CTRL[c]
                out.append('%-14s DEFB %-25s ; %04X %s %s'
                           % ('', sym + ',' + ','.join('&%02X' % x for x in args),
                              a, CTRL[c], ','.join(str(x) for x in args)))
                self.equs[sym] = c
                a += 1 + n
                continue
            if quoted:
                flush()
                b = a
                while b < e and not (32 <= self.byte(b) < 127)                         and self.byte(b) not in CTRL:
                    b += 1
                raw = [self.byte(i) for i in range(a, b)]
                out.append('%-14s DEFB %-25s ; %04X %s'
                           % ('', ','.join('&%02X' % x for x in raw), a,
                              'graphics' if all(0x80 <= x <= 0xA8 for x in raw) else ''))
                a = b
                continue
            flush()
            if c == 0xFF and a + 1 < e:
                word, sym = self.t.function(self.byte(a + 1))
                out.append('%-14s DEFB %-25s ; %04X %s'
                           % ('', 'FN_PFX,' + (sym or '&%02X' % self.byte(a + 1)),
                              a, word or ''))
                if sym:
                    self.equs[sym] = self.byte(a + 1)
                self.equs['FN_PFX'] = 0xFF
                a += 2
            elif 0x85 <= c <= 0xFE:
                word, sym = self.t.command(c)
                out.append('%-14s DEFB %-25s ; %04X %s'
                           % ('', sym or '&%02X' % c, a, word or ''))
                if sym:
                    self.equs[sym] = c
                a += 1
            elif c == NUM and a + 6 <= e:
                raw = [self.byte(a + 1 + i) for i in range(5)]
                v = number(raw)
                out.append('%-14s DEFB %-25s ; %04X %s'
                           % ('', 'TK_NUM,' + ','.join('&%02X' % x for x in raw),
                              a, '= %d' % v if v is not None else 'number'))
                self.equs['TK_NUM'] = NUM
                a += 6
            elif c == CR:
                out.append('%-14s DEFB %-25s ; %04X end of line' % ('', 'TK_CR', a))
                self.equs['TK_CR'] = CR
                a += 1
            else:
                out.append('%-14s DEFB %-25s ; %04X' % ('', '&%02X' % c, a))
                a += 1
        flush()
        return out
