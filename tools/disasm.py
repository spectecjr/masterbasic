"""Trace-driven Z80 disassembler.

Walks the flow graph from a set of entry points, marks every byte it
reaches as code, and writes the rest out as data.  The output is pyz80
source, so a disassembly can be proved correct by assembling it and
comparing the result with the input image.

Usage as a library: build a Disassembler, add seeds and symbols, call
run(), then emit().
"""

from z80 import Decoder, hexn
from z80 import NORMAL, JUMP, CJUMP, CALL, CCALL, RET, CRET, RST, JPHL, HALT_

UNKNOWN, CODE, CONT, DATA, WORD, TEXT, RST8, PARAM = range(8)

NOP_RUN = 3         # runs of at least this many NOPs are written as DEFS


class Disassembler(Decoder):
    def __init__(self, mem, base):
        Decoder.__init__(self, mem, base)
        self.mark = bytearray(len(mem))       # one of the constants above
        self.insns = {}                       # addr -> Insn
        self.labels = {}                      # addr -> name  (inside the image)
        self.xrefs = {}                       # addr -> set of referring addrs
        self.comments = {}                    # addr -> comment text
        self.headers = {}                     # addr -> banner text
        self.renderers = {}                   # addr -> (end, text) for a whole run
        self.overrides = {}                   # addr -> instruction text to print instead
        self.notes = {}                       # addr -> lines to print above it
        self.mdos_equs = {}                   # names those overrides need defining
        self.used_ext = set()                 # outside names the listing mentions
        self.queue = []
        self.seen = set()
        self.rst_inline = {0x08: 1}           # RST &08 is followed by a code byte
        self._cur = None

    # -- classification helpers -------------------------------------------
    def inside(self, a):
        return self.base <= a < self.limit

    def m(self, a):
        return self.mark[a - self.base]

    def setm(self, a, v):
        self.mark[a - self.base] = v

    # -- symbols -----------------------------------------------------------
    def a16(self, v, rel=False):
        """A jump or call target: an in-image label, or an outside name.

        `rel` marks a JR or DJNZ, whose target is a displacement into
        this same code rather than an address.  Nothing here needs the
        distinction; dis_mb does.
        """
        if v is None:
            return '?'
        if self._cur is not None and self.inside(v):
            self.xrefs.setdefault(v, set()).add(self._cur)
        n = self.labels.get(v)
        if n:
            return n
        n = self.ext_target(v)
        if n:
            self.used_ext.add(n)
            return n
        return hexn(v, 4)

    def mem16(self, v, at=None):
        """A memory address.  Only in-image labels: what lies outside the
        image at a given address depends on the paging at the time, so a
        ROM name would be a guess."""
        if v is None:
            return '?'
        if self._cur is not None and self.inside(v):
            self.xrefs.setdefault(v, set()).add(self._cur)
        n = self.labels.get(v)
        return n if n else hexn(v, 4)

    def imm16(self, v):
        """A 16-bit immediate.  Named only when it points into the image,
        where a label exists only because something reached that address;
        an outside value is as likely to be a count as an address."""
        return self.mem16(v)

    def word_operand(self, v, at=None):
        """An inline DEFW parameter: always an address, so outside names
        apply, and here the ROM's variable area is in scope too."""
        if v is None:
            return '?'
        if self._cur is not None and self.inside(v):
            self.xrefs.setdefault(v, set()).add(self._cur)
        n = self.labels.get(v)
        if n:
            return n
        n = self.ext_datum(v)
        if n:
            self.used_ext.add(n)
            return n
        return hexn(v, 4)

    def ext_target(self, v):
        return None

    def ext_datum(self, v):
        return None

    def n8(self, v):
        return '?' if v is None else hexn(v, 2)

    def code8(self, v):
        """The byte after RST &08: an error number or a hook code."""
        return hexn(v, 2)

    def code_note(self, v):
        return ''

    # -- tracing -----------------------------------------------------------
    def seed(self, addr, label=None):
        if label and self.inside(addr):
            self.labels.setdefault(addr, label)
        if self.inside(addr) and addr not in self.seen:
            self.queue.append(addr)

    def run(self):
        while self.queue:
            self._walk(self.queue.pop())

    def _walk(self, addr):
        while True:
            if not self.inside(addr) or addr in self.seen:
                return
            if self.m(addr) not in (UNKNOWN, CODE):
                return
            insn = self.decode(addr)
            if insn is None or insn.end > self.limit:
                return
            self.seen.add(addr)
            self.insns[addr] = insn
            self.setm(addr, CODE)
            for i in range(addr + 1, insn.end):
                self.setm(i, CONT)
                self.seen.add(i)

            if insn.flow in (JUMP, CJUMP, CALL, CCALL) and insn.target is not None:
                if self.inside(insn.target):
                    self.queue.append(insn.target)

            nxt = insn.end
            if insn.flow == RST:
                skip = self.rst_inline.get(insn.target, 0)
                for i in range(nxt, min(nxt + skip, self.limit)):
                    self.setm(i, DATA)
                    self.seen.add(i)
                nxt += skip
            elif not insn.falls_through():
                return
            addr = nxt

    # -- second pass: resolve operand text now that labels exist -----------
    def relabel(self):
        self.xrefs = {}
        for a in sorted(self.insns):
            self._cur = a
            self.insns[a] = self.decode(a)
        self._cur = None

    # -- data regions -------------------------------------------------------
    def region(self, start, end, kind):
        for a in range(start, end):
            if self.m(a) == UNKNOWN:
                self.setm(a, kind)

    def gaps(self):
        """Yield (start, end) runs of bytes not claimed as code."""
        a = self.base
        while a < self.limit:
            if self.m(a) in (CODE, CONT):
                a += 1
                continue
            s = a
            while a < self.limit and self.m(a) not in (CODE, CONT):
                a += 1
            yield s, a

    def coverage(self):
        n = sum(1 for v in self.mark if v in (CODE, CONT))
        return n, len(self.mark)

    def unplaced(self):
        """Labels that fall inside an instruction, so cannot be written out.

        Each one is a place where the trace decoded bytes at the wrong
        alignment, so this doubles as the disassembly's own error report.
        """
        bad = {}
        for a, n in self.labels.items():
            if self.m(a) == CONT:
                bad[a] = n
        return bad

    def _starts_insn(self, a):
        return self.m(a) == CODE and a in self.insns

    # -- emit ---------------------------------------------------------------
    def emit(self, out, title='', segs=None, width=15):
        """Write pyz80 source.  `segs` is a list of (address, length)."""
        w = out.write
        if title:
            w(title.rstrip() + '\n\n')
        if segs is None:
            segs = [(self.base, len(self.mem))]
        for si, (org, ln) in enumerate(segs):
            if si == 0:
                w('%-14s ORG  %s\n' % ('', hexn(org, 4)))
            else:
                w('\n%-14s DEFS %s-$   ; the gap is not part of the file\n'
                  % ('', hexn(org, 4)))
            a, end = org, org + ln
            while a < end:
                if a in self.headers:
                    w('\n' + self.headers[a].rstrip() + '\n')
                insn = self.insns.get(a) if self.m(a) == CODE else None
                if insn is not None and insn.text == 'NOP' and a not in self.labels:
                    b = a
                    while b < end and self._starts_insn(b) \
                            and self.insns[b].text == 'NOP' \
                            and (b == a or b not in self.labels) \
                            and b not in self.headers:
                        b += 1
                    if b - a >= NOP_RUN:
                        w('%-14s DEFS %-25s ; %04X %d NOPs\n' % ('', b - a, a, b - a))
                        a = b
                        continue
                if insn is not None:
                    self._label(w, a)
                    for line in self.notes.get(a, ()):
                        w('%-14s ; %s\n' % ('', line))
                    raw = bytes(self.mem[a - self.base:insn.end - self.base])
                    if insn.asm:
                        body = '%-14s %-31s ; %04X %s' % (
                            '', self.overrides.get(a, insn.text), a,
                            ' '.join(hexn(b, 2)[1:] for b in raw))
                    else:
                        body = '%-14s DEFB %-26s ; %04X %s' % (
                            '', ','.join(hexn(b, 2) for b in raw), a, insn.text)
                    c = self.comments.get(a)
                    if c:
                        body += '  ' + c
                    w(body.rstrip() + '\n')
                    a = insn.end
                elif a in self.renderers:
                    stop, text = self.renderers[a]
                    if a in self.labels:
                        w('\n%s:\n' % self.labels[a])
                    w(text)
                    a = stop
                else:
                    s0 = a
                    a += 1
                    while a < end and not self._starts_insn(a):
                        # A commented address starts its own run, so that
                        # what the comment describes is the line it is on.
                        if a in self.labels or a in self.headers \
                                or a in self.comments:
                            break
                        a += 1
                    self._data(w, s0, a, width)
        w('\n')

    def _label(self, w, a):
        if a in self.labels:
            refs = [hexn(r, 4) for r in sorted(self.xrefs.get(a, ()))]
            # References from the other page count too: a few variables are
            # only ever touched from there.
            refs += ['%s &%04X' % (tag, r)
                     for tag, r in sorted(getattr(self, 'peer_xrefs', {}).get(a, ()))]
            if refs:
                w('\n; ---- %s ---- from %s\n'
                  % (self.labels[a],
                     ', '.join(refs[:8]) + (' ...' if len(refs) > 8 else '')))
            else:
                w('\n')
            w('%s:\n' % self.labels[a])

    def _text(self, w, s, e):
        """A run of words, each ended by bit 7 of its last character."""
        a = s
        while a < e:
            b = a
            while b < e and not (self.byte(b) & 0x80):
                b += 1
            body = ''.join(chr(self.byte(i)) for i in range(a, b))
            if b < e:
                last = chr(self.byte(b) & 0x7F)
                if body and '"' not in body and body.isprintable() \
                        and last.isprintable() and last != '"':
                    w(('%-14s DEFM %-25s ; %04X %s' + chr(10))
                      % ('', '"%s"' % body, a,
                         ' '.join(hexn(self.byte(i), 2)[1:]
                                  for i in range(a, min(b, a + 8)))))
                    w(('%-14s DEFB %-25s ; %04X %s' + chr(10))
                      % ('', '"%s"+&80' % last, b,
                         hexn(self.byte(b), 2)[1:]))
                    a = b + 1
                    continue
            n = min(b + 1, e) - a
            chunk = bytes(self.mem[a - self.base:a - self.base + n])
            w('%-14s DEFB %-25s ; %04X\n'
              % ('', ','.join(hexn(c, 2) for c in chunk), a))
            a += n

    def _data(self, w, s, e, width):
        if s in self.labels:
            # Through _label, so a variable lists the routines that use it.
            self._label(w, s)
        kind = self.m(s)
        a = s
        if kind == RST8:
            for i in range(s, e):
                w(('%-14s DEFB %-25s ; %04X %s %s' + chr(10))
                  % ('', self.code8(self.byte(i)), i,
                     hexn(self.byte(i), 2)[1:],
                     self.code_note(self.byte(i))))
            return
        if kind == TEXT:
            self._text(w, s, e)
            return
        while a < e:
            if kind in (WORD, PARAM) and e - a >= 2:
                n = min(8, (e - a) // 2)
                vals = [self.word(a + 2 * i) for i in range(n)]
                show = self.word_operand if kind == PARAM else self.mem16
                raw = bytes(self.mem[a - self.base:a - self.base + 2 * n])
                w('%-14s DEFW %-25s ; %04X %s\n'
                  % ('', ','.join(show(v, a + 2 * i)
                                  for i, v in enumerate(vals)), a,
                     ' '.join(hexn(b, 2)[1:] for b in raw)))
                a += 2 * n
                continue
            n = min(width, e - a)
            chunk = bytes(self.mem[a - self.base:a - self.base + n])
            txt = ''.join(chr(c & 0x7F) if 32 <= (c & 0x7F) < 127 else '.' for c in chunk)
            note = self.comments.get(a)
            w('%-14s DEFB %-*s ; %04X %s\n'
              % ('', width * 4 - 1, ','.join(hexn(c, 2) for c in chunk), a,
                 (txt + '  ' + note).strip() if note else txt))
            a += n
