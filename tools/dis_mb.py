"""Disassemble file/MasterBasicMasterDos.bin -- MasterDOS 2.3 + MasterBASIC 1.7.

Layout
------
The file is a SAM Coupe CODE file of 32640 bytes, which is exactly 64
sectors of 510 payload bytes.  The nine-byte header at the front is part
of the loaded image, not something to skip.

The boot sector -- the first 512 bytes, which the ROM reads to &8000 and
calls -- loads 32 sectors into the page the ROM gave it, then switches
LMPR to a free page and loads the remaining 32 there.  So the file is two
16320-byte halves that end up in two different RAM pages:

    file 0     - 16319   MasterDOS 2.3, with MasterBASIC's patches
    file 16320 - 32639   MasterBASIC 1.7

**Both are assembled to run at &4000-&7FBF**, and each is written to see
the other at &8000-&BFBF.  Which is which depends on the paging at the
time: with the DOS paged in at &4000 the extension sits at &8000, and
when the extension takes over the two swap.  That is why the DOS's
message pointer at &4210 holds &9200 while the extension calls &BD79 --
each is reaching into the other page.

So this is two address spaces, not one, and the two halves are written
out as two files.  A reference to &8000-&BFBF is resolved against the
other half and named for it.

The boot sector is the exception: it runs before either page is in place,
with its own half at &8000, so inside &4000-&41FF an address of &8000 and
up means this page, &4000 higher.

    python tools/dis_mb.py <workdir> [-o outdir]

<workdir> must hold the map, listing, symbol and binary files from
assembling ref/masterdos/annotated-src and ref/samrom with pyz80.
"""

import argparse
import glob
import re
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from disasm import Disassembler, UNKNOWN, CODE, CONT, DATA, WORD, TEXT, RST8, PARAM
from z80 import hexn, CALL, CCALL
import annotate
import romsyms
import sambasic
import xfer
import carrydoc
import fpcalc
import notes
import nrfam
import specrender
import speculate
import infer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE = os.path.join(ROOT, 'file', 'MasterBasicMasterDos.bin')
MDOS = os.path.join(ROOT, 'ref', 'masterdos', 'res', 'MDOS23.bin')

BASE = 0x4000
HALF = 16320                    # 32 sectors x 510 payload bytes
TOP = BASE + HALF               # &7FC0: one past the end of a page
PEER = 0x8000                   # where each page sees the other one
BOOT_END = 0x4200               # the boot sector runs with its own page at &8000

HOOK_TABLE = 0x44A6             # SAMHK: RST &08 code 128+i is entry i
MBTEXT = (0x7E6B, 0x7FC0)       # tokenised BASIC at the end of the extension
MBKEYS = (0x50D8, 0x5169)       # the extension's keyword names
MBVARS = (0x4000, 0x405A)       # the XVARs the manual documents
MBVARS2 = (0x405A, 0x41BA)      # the rest of the variable block, undocumented
INSTALLER = 0x75E1              # copied to &BC00 by the boot sector and run there
DOSVARS = ((0x40F9, 0x4200),   # the DOS's variables, after the boot code
           (0x4220, 0x42BD))   # DVAR: the block DVAR n indexes, up to CALLMB
DOSBUF = (0x7C00, 0x7FC0)       # the DOS's buffers: the installer lands here first
REPORTERS = {'DOS': set(), 'MB': {0x43BE}}   # take the error number in A

# What a table entry adds to a peer label to become the stored word.  It
# is not bit 15 itself -- that is &8000 -- but the net of two steps: take
# &4000 off to undo the &8000 window this page sees the other one
# through, then put &8000 on to set the flag.
PAGE_FLAG = 'NOT_IN_THIS_PAGE'


# A label nothing named: Lxxxx or Vxxxx, made up from the address.
SYNTHETIC = re.compile(r'^[LV][0-9A-Fa-f]{4}$')


class Page(Disassembler):
    """One of the two halves, at &4000, with the other half at &8000."""

    def __init__(self, mem, tag, title):
        Disassembler.__init__(self, mem, BASE)
        self.tag = tag                    # DOS or MB: prefixes the peer's names
        self.title = title
        self.peer = None
        self.peer_seeds = []
        self.no_peer = []             # ranges where &8000+ is not the peer
        self.self_window = []         # ranges where &8000+ is this page
        self.sys_low = []             # ranges where &4000+ is the system page
        self.carried_by_value = {}    # address -> the MasterDOS source's name
        self.rendered = []            # ranges written by a renderer
        self._inline = {}
        self.msg_calls = set()
        self.dead_calls = set()
        self.conflicts = []
        self.syms = None
        self.ports = {}
        self.rst8 = {}                    # RST &08 code -> EQU name
        self.errors = {}                  # error code -> its message
        self.used_codes = set()
        self.used_peer = {}               # peer name -> address in this space
        self.peer_xrefs = {}              # addr -> where the other page uses it
        self.basic_equs = {}
        self.peer_params = set()
        self.fetchers = set()
        self.inferred = {}
        self.rst_equs = {}
        self.romdesc = {}
        self.fpc = []
        self.declared_data = set()
        self.user_equs = {}
        self.used_page_flag = False

    # -- the two address spaces --------------------------------------------
    def inside(self, a):
        return BASE <= a < TOP

    def peer_addr(self, a, frm=None):
        """The peer address `a` refers to, or None.

        Inside the boot sector the same range means this page instead, so
        nothing there is resolved against the peer.
        """
        if frm is not None and frm < BOOT_END:
            return None
        if frm is not None and any(lo <= frm < hi for lo, hi in self.no_peer):
            return None
        if PEER <= a < PEER + HALF:
            return a - PEER + BASE
        return None

    def peer_name(self, a, frm=None):
        p = self.peer_addr(a, frm)
        if p is None or self.peer is None:
            return None
        name = self.peer.labels.get(p)
        if not name:
            return None
        full = self.peer.tag + '_' + name
        self.used_peer[full] = a
        if self._cur is not None:
            self.peer.peer_xrefs.setdefault(p, set()).add((self.tag, self._cur))
        return full

    def windowed_var(self, a):
        """A ROM system variable reached through the &8000 window.

        The NR primitives get at the ROM's variables by setting HMPR to 0
        and turning the address into the &8000-&BFFF window -- `SET 7,H`
        then `RES 6,H`, which for the &4000-&7FFF the variables live in
        comes to adding &4000.  Code that does it inline rather than
        calling NRRD leaves the windowed address in the operand, so
        &9C65 is STKEND.  A peer label wins if it is a real name; a
        synthetic one is no evidence of anything.
        """
        if not self.syms or not 0x9000 <= a < 0xA000:
            return None
        name = self.syms.var(a - 0x4000)
        if not name:
            return None
        peer = self.peer.labels.get(a - PEER + BASE) if self.peer else None
        if peer and not re.match(r'^[LV][0-9A-F]{4}$', peer):
            return None
        return name

    def boot_self(self, a, frm=None):
        """Where &8000 and up is this page seen &4000 higher, not the peer.

        True throughout the boot sector, and true again in code that runs
        with this half in the window rather than at &4000 -- the interrupt
        path does, which is how it can read the ROM's own variables at
        their proper addresses and its own at &8xxx in the same routine.
        """
        if frm is None:
            return None
        if frm >= BOOT_END and not any(lo <= frm < hi
                                       for lo, hi in self.self_window):
            return None
        if PEER <= a < PEER + HALF:
            # Whether this page has a label there or not, the address is
            # this page's: nothing else is in the window.  Falling
            # through on a missing label let the peer claim it, which is
            # how &806D at &5FDA came out as DOS_L406D while &806F two
            # instructions later came out as V406F+&4000.
            return self.labels.get(a - PEER + BASE) or hexn(a - PEER + BASE, 4)
        return None

    # -- operand naming ----------------------------------------------------
    def a16(self, v, rel=False):
        # A JR or DJNZ target is not an address the routine names: it is
        # this code, wherever this code happens to be paged.  Everything
        # else -- JP, CALL, LD -- names a location, and in an inverted
        # stretch that location is in the ROM's system page.
        return self._name(v, self.ext_target, absolute=not rel)

    def mem16(self, v, at=None):
        """A memory address.  If nothing in this page claims it and the
        ROM names a system variable there, that is what it is."""
        return self._name(v, self.ext_var, absolute=True)

    def carried_name(self, a):
        """The MasterDOS source's own name for an address outside this page.

        &A280 is the case that found this.  Six of the seven LD HL,&A280
        in the DOS come out as FTADD, the author's name for the screen
        borrowed as a buffer -- '(SCR in section C)' is his comment on
        it -- and the seventh, where the instruction streams had diverged
        and the name could not be carried, came out as MB_L6280: a call
        into the extension that does not exist.  A synthetic peer label
        is no evidence against a name the author wrote down, which is the
        same rule windowed_var already applies.
        """
        # Only in the window.  Outside it a small number is as likely to
        # be a count as an address, and the MasterDOS source has equates
        # for lengths too: without this, LD BC,&000F comes out as BUFL
        # and LD BC,&0008 -- the author's own comment on which is
        # "STR LEN" -- comes out as RDLIM.
        if not PEER <= a < PEER + (TOP - BASE):
            return None
        name = self.carried_by_value.get(a)
        if not name:
            return None
        peer = self.peer.labels.get(self.peer_addr(a, self._cur))             if self.peer else None
        if peer and not SYNTHETIC.match(peer):
            return None
        return name

    def imm16(self, v, at=None):
        return self.mem16(v)

    def word_operand(self, v, at=None):
        """An inline DEFW parameter.

        The NR and CMR conventions both take a ROM address, and the ROM's
        variables sit at &4000-&5FFF -- the same addresses this page
        occupies -- so the ROM name has to win over any label of ours.

        The exception is the parameter of a cross-page call, which is
        read after the paging has already changed.  &4000 and up is then
        the other page, so &4FAC there is DOS_POINT and not one of the
        ROM variables that share those addresses; below &4000 the switch
        leaves ROM0 in place, so those really are ROM entry points.
        """
        if v is None:
            return '?'
        if at is not None and at in self.peer_params:
            if self.peer and self.peer.inside(v):
                name = self.peer_name(v - BASE + PEER)
                if name:
                    # The peer's names are defined for &8000-&BFBF, where
                    # this page sees it.  Under the paging this call sets
                    # up it is at &4000 instead, which is how the other
                    # listing numbers it, so the stored word is that much
                    # lower -- the mirror of the +&4000 written elsewhere.
                    return name + '-&4000'
            elif v < BASE:
                n = self.ext_target(v)
                if n:
                    self.used_ext.add(n)
                    return n
            return hexn(v, 4)
        n = self.ext_datum(v)
        if n:
            self.used_ext.add(n)
            return n
        # A stored pointer with bit 15 set is the other page's, the
        # convention INDJP and CTAB both use.
        if v & 0x8000 and self.peer and self.peer.inside(v & 0x7FFF):
            name = self.peer_name((v & 0x7FFF) - BASE + PEER)
            if name:
                self.used_page_flag = True
                return name + '+' + PAGE_FLAG
        return self._name(v, lambda _: None)

    def _name(self, v, outside, absolute=False):
        if v is None:
            return '?'
        if self.inside(v):
            # In code that runs with the ROM's system page at &4000, an
            # address in this range is a ROM variable, not this page's own
            # label.  INSTALL_ROM_VECTORS is the clear case: the values it
            # writes to &5AFA, &5AF6, &5AE2, &5BC4 and &5BBA are found in
            # the system page afterwards and not in this one.
            # Absolute operands only.  A JR or DJNZ inside one of these
            # routines lands in this code wherever the code is paged, so
            # its label is right: it was JR NZ,L433B that made the point
            # by turning into JR NZ,&433B.
            if absolute and self._cur is not None and any(
                    lo <= self._cur < hi for lo, hi in self.sys_low):
                n = self.ext_var(v)
                if n:
                    self.used_ext.add(n)
                    return n
                # No ROM name for it, but it is still not this page's
                # &45A2: INSTALL_EXTENDED_PUT writes there and the bytes
                # turn up in the system page.  Raw hex says less and is
                # not wrong.
                return hexn(v, 4)
            if self._cur is not None:
                self.xrefs.setdefault(v, set()).add(self._cur)
            n = self.labels.get(v)
            if n:
                return n
            n = outside(v)
            if n:
                self.used_ext.add(n)
                return n
            return hexn(v, 4)
        if absolute:
            n = self.carried_name(v)
            if n:
                self.used_ext.add(n)
                return n
        n = self.boot_self(v, self._cur)
        if n:
            return n + '+&4000'
        n = self.windowed_var(v)
        if n:
            self.used_ext.add(n)
            return n + '+&4000'
        n = self.peer_name(v, self._cur)
        if n:
            return n
        n = outside(v)
        if n:
            self.used_ext.add(n)
            return n
        return hexn(v, 4)

    def port8(self, v):
        return self.ports.get(v) or hexn(v, 2)

    def ext_target(self, v):
        return self.syms.target(v) if self.syms else None

    def ext_datum(self, v):
        return self.syms.datum(v) if self.syms else None

    def ext_var(self, v):
        return self.syms.var(v) if self.syms else None

    def code8(self, v):
        n = self.rst8.get(v)
        if n:
            self.used_codes.add(v)
            return n
        return hexn(v, 2)

    def code_note(self, v):
        if v >= 0x80:
            return 'hook code'
        text = self.errors.get(v)
        return 'error %d, "%s"' % (v, text) if text else 'error %d' % v

    # -- "CALL x / DEFW y" and friends -------------------------------------
    def inline_len(self, t):
        if t not in self._inline:
            self._inline[t] = self._sniff(t)
        return self._inline[t]

    def _sniff(self, t):
        seq, a = [], t
        for _ in range(9):
            i = self.decode(a)
            if i is None:
                break
            seq.append(i.text)
            a = i.end
        if not seq:
            return 0
        # NRRD / NRRDD / NRWR / NRWRD swap the return address into HL.
        # NRWRHL is two bytes in front of NRWRD and moves HL into BC before
        # falling into it, so the swap is not always the first instruction.
        for skip in range(3):
            if seq[skip:skip + 1] == ['EX (SP),HL']:
                return 2
        # CMR, and the copies of it in both pages: pop the return address,
        # read a word through it, push it back past the word.
        want = ['POP HL', 'LD E,(HL)', 'INC HL', 'LD D,(HL)', 'INC HL', 'PUSH HL']
        for skip in range(3):
            if seq[skip:skip + len(want)] == want:
                return 2
        return 0

    def _walk(self, addr):
        while True:
            if not self.inside(addr):
                return
            if self.m(addr) == CONT:
                # Something jumps here, but an earlier path decoded straight
                # over it.  That is the "LD HL,nn as a two-byte skip" trick,
                # where a chain of entry points each load a different value
                # and fall into common code.  Record it for repair.
                b = addr
                while b > self.base and not self._starts_insn(b):
                    b -= 1
                if self._starts_insn(b):
                    self.conflicts.append((addr, b))
                return
            if addr in self.seen:
                return
            if self.m(addr) not in (UNKNOWN, CODE):
                return
            insn = self.decode(addr)
            if insn is None or not self.inside(insn.end - 1):
                return
            # Never let one instruction overlap another: an overlap means one
            # of the two paths that reached here decoded at the wrong
            # alignment, and silently overwriting would lose bytes.
            clash = [i for i in range(addr + 1, insn.end)
                     if self.m(i) in (CODE, CONT)]
            if clash:
                self.conflicts.append((addr, clash[0]))
                return
            self.seen.add(addr)
            self.insns[addr] = insn
            self.setm(addr, CODE)
            for i in range(addr + 1, insn.end):
                self.setm(i, CONT)
                self.seen.add(i)

            tgt = insn.target
            if insn.text.startswith(('JP ', 'JR ', 'DJNZ', 'CALL')) and tgt is not None:
                if self.inside(tgt):
                    self.queue.append(tgt)
                elif addr < BOOT_END and PEER <= tgt < PEER + HALF:
                    self.queue.append(tgt - PEER + BASE)
                else:
                    p = self.peer_addr(tgt, addr)
                    if p is not None:
                        self.peer_seeds.append(p)

            nxt = insn.end
            if insn.text.startswith('RST') and tgt == 0x28:
                # The calculator's literals, not instructions.  How many
                # bytes they run to is only knowable by walking them.
                got = fpcalc.scan(self, nxt)
                if got is not None:
                    end, resumes, items = got
                    self._run(nxt, end - nxt, PARAM)
                    self.fpc.append((nxt, end, items))
                    if not resumes:
                        return
                    nxt = end
            elif insn.text.startswith('RST'):
                nxt = self._run(nxt, self.rst_inline.get(tgt, 0), DATA)
                if tgt == 0x08 and self.inside(insn.end):
                    self.setm(insn.end, RST8)
            elif insn.text.startswith('CALL') and tgt is not None:
                if tgt in self.msg_calls:
                    self._message(nxt)
                    return
                # A routine copied into the other page is called through
                # the window, so its inline parameters cannot be sniffed
                # from here -- the length has to be registered by address.
                n = (self.inline_len(tgt) if self.inside(tgt)
                     else self._inline.get(tgt, 0))
                if n:
                    nxt = self._run(nxt, n, PARAM)
                if tgt in self.dead_calls:
                    return
            if not insn.falls_through():
                return
            addr = nxt

    def _run(self, a, n, kind):
        for i in range(a, a + n):
            if self.inside(i) and self.m(i) == UNKNOWN:
                self.setm(i, kind)
            self.seen.add(i)
        return a + n

    def _message(self, a):
        s = a
        while self.inside(a) and not (self.byte(a) & 0x80):
            a += 1
        a += 1
        for i in range(s, a):
            if self.inside(i) and self.m(i) == UNKNOWN:
                self.setm(i, TEXT)
            self.seen.add(i)
        return a


# EXX / POP HL / LD E,(HL) / INC HL / LD D,(HL) / INC HL / PUSH HL /
# LD C,&FA / IN B,(C) -- take the inline word, then read LMPR.
XPAGE_CALL = bytes((0xD9, 0xE1, 0x5E, 0x23, 0x56, 0x23, 0xE5, 0x0E, 0xFA, 0xED, 0x40))


def find_xpage_call(d):
    """The helper that calls a routine in the other page.

    It reads the word after the call, switches LMPR to the page whose
    number the boot sector patched into its `LD H,n`, and calls through.
    Because the paging changes first, its parameter is an address in the
    *other* page -- or in ROM0, which the switch leaves at &0000.
    """
    i = bytes(d.mem).find(XPAGE_CALL)
    if i < 0:
        return None
    a = BASE + i
    return a if d._starts_insn(a) else None


def xpage_params(d, at):
    """Mark the parameters of every cross-page call, and seed the peer."""
    n = 0
    for a, ins in sorted(d.insns.items()):
        if not ins.text.startswith('CALL') or ins.target != at:
            continue
        v = d.word(ins.end)
        if v is None:
            continue
        d.peer_params.add(ins.end)
        if d.peer and d.peer.inside(v):
            d.peer_seeds.append(v)
        n += 1
    return n


def run_both(pages):
    """Trace both pages, letting each seed the other."""
    for _ in range(40):
        moved = False
        for p in pages:
            p.run()
            if p.peer_seeds:
                for a in p.peer_seeds:
                    p.peer.seed(a)
                p.peer_seeds = []
                moved = True
        if not moved:
            return


# ---------------------------------------------------------------------------
NOTES = {}

NOTES['boot'] = '\n'.join((
    ';; ---------------------------------------------------------------------',
    ';; The boot sector.  The ROM reads the first 512 bytes of the file to',
    ';; &8000 and calls it there, so everything up to &41FF runs with this',
    ';; page at &8000-&BFBF rather than at &4000.  Its absolute addresses are',
    ';; therefore &4000 above the labels used here, which is why they are',
    ';; written as LABEL+&4000.',
    ';;',
    ';; It finds a free RAM page, loads 32 sectors into the page it was given,',
    ';; switches LMPR to the free page and loads the remaining 32 there, then',
    ';; copies the installer out of the other page and runs it.',
    ';; ---------------------------------------------------------------------',
))

NOTES['entry'] = '\n'.join((
    ';; The three entry points the ROM knows about, at page offset &0200: the',
    ';; RST &08 hook handler, the unrecognised-command handler and the NMI',
    ';; (snapshot button) handler.',
))

NOTES['installer'] = '\n'.join((
    ';; ------------------------------------------------------------------',
    ';; The installer.  The boot sector copies these 943 bytes to &BC00 --',
    ';; the DOS page, as the boot sector has it mapped -- and runs them',
    ';; there.  The paging at that point is the one this listing assumes,',
    ';; so the addresses read normally: &4xxx-&7xxx here, &8xxx-&Bxxx in',
    ';; the DOS page.',
    ';; ------------------------------------------------------------------',
))

NOTES['keywords'] = '\n'.join((
    ';; The names of the commands and functions MasterBASIC adds to SAM',
    ';; BASIC, each terminated by bit 7 of its last character.',
))

NOTES['tail'] = '\n'.join((
    ';; ------------------------------------------------------------------',
    ';; Tokenised SAM BASIC.  The end of the page holds fragments of BASIC',
    ';; source that MasterBASIC pastes into a program -- the profiler report',
    ';; ("TOTAL FRAMES", "MEMORY USED") and its key prompts among them.',
    ';;',
    ';; Each fragment is a run of program lines: two bytes of line number,',
    ';; high byte first -- the one word in either listing that is not',
    ';; little-endian, so it stays two DEFBs where a DEFW would reverse',
    ';; it -- then two bytes of length low first, which is a DEFW, then',
    ';; the statement, then &0D.  The',
    ';; run starts and ends part way through a line.  Keywords are named',
    ";; from the SAM ROM's own token tables (see tools/sambasic.py); a",
    ';; number is its digits followed by &0E and five bytes of value; and',
    ';; inside a string &80-&A8 are graphics characters, not keywords.',
    ';; ------------------------------------------------------------------',
))

NOTES['dosbuf'] = '\n'.join((
    ';; ------------------------------------------------------------------',
    ";; The DOS's variables and buffers.  Routines all over the DOS reach",
    ';; in here with LD HL,&7Cxx and LD (&7Cxx),A, and nothing calls or',
    ';; jumps into it, so despite what the bytes look like it is not code.',
    ';;',
    ';; It is also where the boot sector puts the installer: the LDIR at',
    ';; the end of BOOT copies 943 bytes from &75E1 in the MasterBASIC',
    ';; page to &BC00, which is this address as the boot sector has the',
    ';; pages mapped, and jumps to it.  So what the file holds here is',
    ';; whatever was in the buffers when the image was saved, and none of',
    ';; it is ever executed.',
    ';; ------------------------------------------------------------------',
))

NOTES['mbvars'] = ";; MasterBASIC's own variables, and a nibble table."

TITLES = {
    'DOS': '\n'.join((
        '; MasterDOS 2.3, from MD+MBAS17 -- file bytes 0-16319.',
        '; Generated by tools/dis_mb.py.  Assembling this file with pyz80',
        '; reproduces that half of the image byte for byte.',
        ';',
        '; This page runs at &4000-&7FBF.  &8000-&BFBF is the MasterBASIC',
        '; page, whose labels appear here with an MB_ prefix; it is',
        '; disassembled in masterbasic.asm.',
        ';',
        '; The routine headers and most of the line comments come from the',
        '; annotated MasterDOS 2.3 source in ref/masterdos/annotated-src,',
        '; carried across by matching the two instruction streams against',
        '; each other.  Nothing is carried where they diverge, so a routine',
        '; MasterBASIC rewrote is left undescribed rather than described',
        '; wrongly, and the routines it changed are marked as changed.',
    )),
    'MB': '\n'.join((
        '; MasterBASIC 1.7, from MD+MBAS17 -- file bytes 16320-32639.',
        '; Generated by tools/dis_mb.py.  Assembling this file with pyz80',
        '; reproduces that half of the image byte for byte.',
        ';',
        '; This page runs at &4000-&7FBF.  &8000-&BFBF is the MasterDOS',
        '; page, whose labels appear here with a DOS_ prefix; it is',
        '; disassembled in masterdos.asm.',
        ';',
        '; The routines the DOS dispatch tables name carry the MasterBASIC',
        "; manual's description of what they do; see docs/masterbasic-manual.md.",
    )),
}


def load(work):
    raw = open(IMAGE, 'rb').read()
    assert raw[0] == 0x13, 'not a SAM CODE file'
    assert len(raw) == 9 + (raw[7] << 14) + (raw[1] | raw[2] << 8), 'header length mismatch'
    assert len(raw) == 2 * HALF

    dos = Page(bytearray(raw[:HALF]), 'DOS', TITLES['DOS'])
    mb = Page(bytearray(raw[HALF:]), 'MB', TITLES['MB'])
    dos.peer, mb.peer = mb, dos

    mdos = open(MDOS, 'rb').read()
    mapfile = os.path.join(work, 'mdos.map')
    lstfile = os.path.join(work, 'mdos.lst')
    found, ambiguous, _ = xfer.carry(raw[:HALF], BASE, mdos, 0x4009, mapfile, lstfile)
    found, dropped = xfer.monotone_filter(found)
    extra = xfer.resolve(found, ambiguous, raw[:HALF], BASE, mdos, 0x4009,
                         mapfile, lstfile)
    used = set()
    for a in sorted(found):
        t, name, _, _ = found[a]
        if t not in dos.labels and name not in used:
            dos.labels[t] = name
            used.add(name)
    print('carried %d MasterDOS labels (%d dropped as out of order, '
          '%d placed by interpolation)' % (len(found), dropped, extra))
    return dos, mb, raw


def seeds(dos, mb):
    for d in (dos, mb):
        d.rst_inline = {0x08: 1}
    rev = {v: k for k, v in dos.labels.items()}
    if 'PTM' in rev:
        dos.msg_calls.add(rev['PTM'])
    if 'DERR' in rev:
        dos._inline[rev['DERR']] = 1
        dos.dead_calls.add(rev['DERR'])

    # The search helper this half keeps at &775A is copied into the DOS
    # page and called there, at &BD79 through the window, by 27 sites.  It
    # pops its return address and reads three bytes, an address and a
    # signed offset -- six in all -- so six bytes after every one of those
    # calls are parameters, not code.  Every site is followed by an
    # LD (nn),HL storing the pointer it hands back.
    mb._inline[0xBD79] = 6

    # DOS &5ADD is LD DE,&B800 setting up a buffer address, not a
    # reference to anything in the other page: the 2.3 source comments it
    # "ALLOWS 1580H BYTES FOR SECTOR LIST" and the routine returns HL, DE
    # and BC for a caller to copy with.  Naming it after whatever this
    # half happens to hold at &7800 is worse than leaving it a number.
    dos.no_peer.append((0x5ADD, 0x5AE0))

    dos.headers[0x4000] = NOTES['boot']
    dos.headers[0x4200] = NOTES['entry']
    dos.labels[DOSBUF[0]] = 'DOSBUF'
    dos.headers[DOSBUF[0]] = annotate.banner(annotate.DOSBUF_DOC)
    dos.region(*DOSBUF, DATA)
    dos.labels[0x4000] = 'HEADER'
    dos.headers[0x4000] = annotate.HEADER_DOC_BANNER
    dos.region(0x4000, 0x4009, DATA)
    dos.seed(0x4009, 'BOOT')
    for a, nm in ((0x4200, 'HOOK'), (0x4203, 'SYNTAX'), (0x4206, 'NMI')):
        dos.seed(a)
        t = dos.word(a + 1)
        if t is not None and dos.inside(t):
            dos.seed(t, nm)

    mb.headers[MBVARS[0]] = annotate.XVAR_DOC_BANNER
    mb.region(MBVARS[0], MBVARS[1], DATA)
    mb.headers[MBVARS2[0]] = annotate.MBVARS2_BANNER
    mb.labels[MBKEYS[0]] = 'MBKEYS'
    mb.headers[MBKEYS[0]] = NOTES['keywords']
    mb.region(MBKEYS[0], MBKEYS[1], TEXT)
    # &5A55 calls &8137, which under the inversion there is this page's
    # own &4137.  Nothing reaches it at &4137, so the trace left it
    # sitting in the variable block as data -- and while the call was
    # being credited to the DOS page there was no reason to look.  It is
    # thirty-four bytes of code.
    mb.seed(0x4137, 'SEND_BYTE_TO_PRINTER')
    # Reached the same way, from &5FE8 as &A114.
    mb.seed(0x6114)
    mb.labels[MBTEXT[0]] = 'MBTEXT'
    mb.headers[MBTEXT[0]] = NOTES['tail']
    mb.region(MBTEXT[0], MBTEXT[1], DATA)
    # HGTTK sets HMPR to 0 before this LDIR, so its &8F00 is the ROM's own
    # workspace rather than the other page.
    mb.no_peer.append((0x4FBF, 0x4FCA))
    # The installer does the same across a much longer stretch: HMPR is
    # zeroed at &7B03 and not put back until &7B73, so every &8000 in
    # between is the ROM's system page.  The named ROM variables in there
    # come out right either way, but the unnamed addresses were being
    # given the other page's labels.
    mb.no_peer.append((0x7B03, 0x7B75))
    # HK_PROGPREP zeroes HMPR at &732E and does not put it back until
    # &735A, and the routine it calls builds code in the ROM's own code
    # buffer, so every &8Dxx through here is CDBUFF and not the DOS page.
    mb.no_peer.append((0x732A, 0x7385))
    # The screen-blanker tick and its neighbours run from the interrupt,
    # with the ROM's system page at &4000 and this half in the window: they
    # read SOFFCT at &5AC4 straight, and their own SOFV as &8002.
    mb.self_window.append((0x59A3, 0x5A00))
    # The printer-ready test is the same: LPTPRT1 read straight at &5A10,
    # and its own SORP and SPORT as &8006 and &800B.
    mb.self_window.append((0x432B, 0x4349))
    # &6485 calls &A4E7 and &A4AC, which are this half's own &64E7 and
    # &64AC -- neither address is an instruction in the DOS page -- and
    # &64E7 reads DEVICE at &5A73 straight, so the same inversion holds.
    # It runs on to &6533: PRINT_MAGNIFIED_CHAR builds each cell in
    # SCRNBUF at &5188 and steps DHADJ at &5B82, both of which read as
    # this page's own code and data without this.
    mb.self_window.append((0x6485, 0x6534))
    # The general rule behind all of these: a routine the DOS calls runs
    # through the window, so its own addresses are &8xxx while the ROM's
    # variables are at their proper &5Axx.  No routine in this half is
    # reached from both pages, so the two conventions never meet.  These
    # are the stretches that call themselves at &8xxx.
    # INSTALL_ROM_VECTORS runs with the ROM's system page at &4000: the
    # vector values it writes turn up there, not in this half.
    mb.sys_low.append((0x76DA, 0x775A))
    # INSTALL_EXTENDED_PUT is called from inside that stretch, so it runs
    # in the same arrangement: its &5BDA is the ROM's CMDADDRT and its
    # &45A2 is in the system page, not an address in this half.
    mb.sys_low.append((0x7829, 0x7879))
    # &5FB9 rather than &5FD8: the system page calls it there, with
    # LD A,&1C : LD HL,&9FB9 : CALL PAGER at &48DA.
    # &63F6 used to be in this list and should not have been.  Its only
    # reference was DOS &54FE, which is LD HL,FTADD+&0176 -- the screen
    # borrowed as a buffer, the same false address that made L6280 look
    # like a routine the DOS called.  Nothing in it addresses itself
    # through a window, and JP NC,&43A7 is REP_INTEGER_OUT_OF_RANGE in
    # this page, which is what CP &03 : JP NC wants.
    for lo, hi in ((0x4510, 0x4520), (0x5A3E, 0x5A64), (0x5C16, 0x5C34),
                   (0x5FB9, 0x6030), (0x7900, 0x7940)):
        mb.self_window.append((lo, hi))
    # HK_SETUPREGS does the same at &7210: its &8D50 is CDBUFF+&50 in the
    # ROM's system page, not the DOS page's &4D50.
    mb.no_peer.append((0x7203, 0x7220))
    # FORMAT: SELRDP at &76BC pages the newly reserved RAM disc page in at
    # &8000, and the code after it builds the mover and blanks 62 directory
    # entries there -- &8002, &8020, &8125, &8200, &82FF.  The 2.3 source
    # writes all of those as raw hex for the same reason.
    dos.no_peer.append((0x76BC, 0x771A))
    # self_window and sys_low are two halves of one arrangement: if this
    # page is in the window then something else is at &4000, and in every
    # case found so far that something is the ROM's system page.  The
    # &64xx run is what made the point -- it reads DEVICE at &5A73 and
    # DMPFG at &5AB7 straight, and calls itself at &A4E7 -- so a range
    # registered as one is registered as both.  sys_low alone stays
    # possible, and means the DOS is in the window instead.
    for d in (dos, mb):
        for lo, hi in d.self_window:
            if (lo, hi) not in d.sys_low:
                d.sys_low.append((lo, hi))
    seed_from_tables(dos, mb)
    mb.headers[INSTALLER] = NOTES['installer']
    mb.seed(INSTALLER, 'INSTALLER')
    run_both((dos, mb))


def seed_from_tables(dos, mb, ctab=0x42EA, samhk=0x44A6, samhk_len=58,
                     fnvec=0x78EB, fnvec_len=16):
    """Seed the trace with everything the three dispatch tables point at.

    A table entry is proof that its target is an entry point, and several
    of them -- SVAL$ among them -- are reached no other way.
    """
    def go(word):
        page, a = (mb, word & 0x7FFF) if word & 0x8000 else (dos, word)
        if page.inside(a):
            page.seed(a)

    for i in range(dos.byte(ctab)):
        go(dos.word(ctab + 1 + 3 * i + 1))
    for i in range(samhk_len):
        go(dos.word(samhk + 2 * i))
    for i in range(fnvec_len):
        go(dos.word(fnvec + 2 * i))


def table_seeds(d, minlen=6):
    """Follow runs of in-page pointers found in unclaimed space.

    The hook table and the BASIC command tables are reached only through
    an indexed jump, so nothing in the trace points at their entries.
    """
    added = 0
    for s, e in list(d.gaps()):
        a = s
        while a + 1 < e:
            run, b = [], a
            while b + 1 < e:
                v = d.word(b)
                if d.m(b) != UNKNOWN:
                    break
                if v is None or not d.inside(v) or v < 0x4200 or d.m(v) == DATA:
                    break
                run.append((b, v))
                b += 2
            if len(run) >= minlen:
                for off, v in run:
                    d.setm(off, WORD)
                    d.setm(off + 1, WORD)
                    d.seed(v)
                    added += 1
                d.labels.setdefault(run[0][0], 'TBL_%04X' % run[0][0])
                a = b
            else:
                a += 2
    d.run()
    return added


def looks_like_text(d, s, e):
    """True if a run reads as one of the bit-7-terminated message tables.

    The test is on unmasked ASCII: masking bit 7 first would pass most Z80
    code too, since &CD, &45 and friends all land in the printable range.
    """
    n = e - s
    if n < 6:
        return False
    plain = sum(1 for a in range(s, e) if 32 <= d.byte(a) < 127)
    return plain * 10 >= n * 7


def sweep_gaps(d, minlen=6, maxskew=3, permissive=False):
    """Disassemble unclaimed runs that read as code.

    Routines reached only through a dispatch the tracer cannot follow leave
    holes between traced regions.  Where such a hole decodes cleanly and
    ends exactly where the next known instruction begins, it is code, and
    seeding the tracer there lets flow analysis take over again.
    """
    seeded = 0
    for s, e in list(d.gaps()):
        if e - s < minlen or d.m(s) != UNKNOWN or looks_like_text(d, s, e):
            continue
        best = None
        for off in range(min(maxskew, e - s) + 1):
            a, bad = s + off, 0
            while a < e:
                i = d.decode(a)
                if i is None:
                    break
                if not i.asm or i.text == 'NOP':
                    bad += 1
                a = i.end
            if a == e:                       # meets the next instruction exactly
                score = (bad, off)
                if best is None or score < best[0]:
                    best = (score, s + off)
        if best is None and permissive:
            best = ((0, 0), s)
        if best:
            d.seed(best[1])
            seeded += 1
    d.run()
    return seeded


def classify_text(d):
    """Mark unclaimed runs that read as message tables, so that later
    passes do not read them as pointers or as code."""
    for s, e in list(d.gaps()):
        if looks_like_text(d, s, e):
            d.region(s, e, TEXT)
            for a in list(d.labels):
                if s < a < e and d.labels[a].startswith('TBL_'):
                    del d.labels[a]


def repair(d, rounds=4):
    """Re-decode where two paths disagreed about instruction alignment.

    A conflict means one path started mid-instruction.  The path that
    reached a call or jump target is the trustworthy one, so its decode is
    replayed and the bytes the other path claimed, up to the point where
    the two streams line up again, are handed back.
    """
    for _ in range(rounds):
        fixed = 0
        for a, b in list(d.conflicts):
            if d.m(a) not in (UNKNOWN, CONT) or not d._starts_insn(b):
                continue
            p = a                                   # find the resync point
            for _ in range(64):
                i = d.decode(p)
                if i is None or not d.inside(i.end - 1):
                    p = None
                    break
                p = i.end
                if p > b and d._starts_insn(p):
                    break
            else:
                p = None
            if p is None or not d._starts_insn(p):
                continue
            q, chain = b, []                        # the run being displaced
            while q < p and d._starts_insn(q):
                chain.append(q)
                q = d.insns[q].end
            if q != p:
                continue
            for q in chain:
                ins = d.insns.pop(q)
                for x in range(q, ins.end):
                    d.setm(x, UNKNOWN)
                    d.seen.discard(x)
            d.conflicts.remove((a, b))
            d.seed(a)
            fixed += 1
        d.run()
        if not fixed:
            return


def autolabel(d, skip=()):
    """Give a name to every address the listing refers to.

    Only the routines MasterDOS itself names come through xfer, so most
    call and jump targets would otherwise be bare hex.  L for something
    that starts an instruction, V for data.  Addresses that land inside an
    instruction are left alone: those are the misalignments the listing
    reports separately.
    """
    d.relabel()                                   # fills in the cross-references
    added = 0
    for a in sorted(d.xrefs):
        if a in d.labels or not d.inside(a):
            continue
        if any(lo < a < hi for lo, hi in list(skip) + d.rendered):
            continue
        # Don't shadow a ROM system variable with a synthetic name.
        if not d._starts_insn(a) and d.syms and d.syms.var(a):
            continue
        if d._starts_insn(a):
            d.labels[a] = 'L%04X' % a
        elif d.m(a) != CONT:
            d.labels[a] = 'V%04X' % a
        else:
            continue
        added += 1
    # The boot sector runs &4000 higher than it is assembled, so its own
    # references need a name at the address they really mean.
    for a, insn in d.insns.items():
        v = insn.target
        # The same holds wherever this page runs in the window, not only
        # in the boot sector: &5FE2 calls &A02A, and without this the
        # target had no name and the cross-reference was invisible.
        here = a < BOOT_END or any(lo <= a < hi for lo, hi in d.self_window)
        if not here or v is None or not (PEER <= v < PEER + HALF):
            continue
        t = v - PEER + BASE
        if t in d.labels or not d.inside(t):
            continue
        # Not into the middle of an instruction: &5C33 writes to &9022,
        # which is the operand of the CALL at &5020, and a label there
        # would be a misalignment report rather than a name.  The patch
        # detector names the instruction that owns it instead, the way
        # label_peer_targets has always done for the other page.
        if d.m(t) == CONT:
            continue
        d.labels[t] = ('L%04X' if d._starts_insn(t) else 'V%04X') % t
        added += 1
    return added


def label_peer_targets(d):
    """Label the addresses this page reaches into the other one.

    A cross-page call is only readable if the far end has a name, and the
    far end often has nothing pointing at it from inside its own page.
    """
    added = 0
    for a, insn in d.insns.items():
        v = insn.target
        if v is None or a < BOOT_END:
            continue
        p = d.peer_addr(v, a)
        if p is None or p in d.peer.labels:
            continue
        if any(lo < p < hi for lo, hi in d.peer.rendered):
            continue
        if d.peer._starts_insn(p):
            d.peer.labels[p] = 'L%04X' % p
        elif d.peer.m(p) != CONT:
            d.peer.labels[p] = 'V%04X' % p
        else:
            continue
        added += 1
    return added


def until_stable(d, step, limit=60):
    """Run a seeding pass until it stops finding new code."""
    for _ in range(limit):
        before = d.coverage()[0]
        step(d)
        if d.coverage()[0] == before:
            return


def load_symbols(d, work):
    """Names for everything outside both pages: ROM routines and variables,
    the hardware ports, and the RST &08 codes."""
    syms = romsyms.Symbols()
    lst = os.path.join(work, 'mdos.lst')
    if os.path.exists(lst):
        syms.from_mdos_listing(lst)
    rom_map = os.path.join(work, 'samrom.map')
    rom_sym = os.path.join(work, 'samrom.sym')
    rom_bin = os.path.join(work, 'samrom.bin')
    if os.path.exists(rom_map):
        syms.from_rom_map(rom_map)
        if os.path.exists(rom_bin):
            syms.from_jump_table(open(rom_bin, 'rb').read(), rom_map)
    if os.path.exists(rom_sym):
        syms.from_rom_equates(rom_sym)

    sources = [os.path.join(ROOT, 'ref', 'masterdos', 'annotated-src', 'masterdos23.asm')]
    sources += sorted(glob.glob(os.path.join(ROOT, 'ref', 'samrom', '*.asm')))
    tables = [p for p in (os.path.join(work, 'samrom.sym'), os.path.join(work, 'mdos.sym'))
              if os.path.exists(p)]
    if tables:
        d.ports = {v: n for v, n in romsyms.ports(sources, tables).items()
                   if n not in set(d.labels.values())}
    d.romdesc = romsyms.descriptions(
        sorted(glob.glob(os.path.join(ROOT, 'ref', 'samrom', '*.asm')))
        + [os.path.join(ROOT, 'ref', 'masterdos', 'annotated-src',
                        'masterdos23.asm')])
    syms.finalise(set(d.labels.values()) | set(d.ports.values()))
    d.syms = syms

    taken = {}
    rom_errs = os.path.join(ROOT, 'ref', 'samrom', 'text.asm')
    if os.path.exists(rom_errs):
        d.errors.update(romsyms.rom_error_names(rom_errs))
    errs = os.path.join(ROOT, 'ref', 'masterdos', 'docs', 'errors.md')
    if os.path.exists(errs):
        for code, name in romsyms.error_names(errs).items():
            d.errors.setdefault(code, name[4:].replace('_', ' ').capitalize())
    for code, text in d.errors.items():
        d.rst8.setdefault(code, romsyms.error_symbol(code, text, taken))


def render_basic(d, work):
    """Decode the tokenised BASIC at the end of the MasterBASIC page."""
    rom = os.path.join(work, 'samrom.bin')
    mapfile = os.path.join(work, 'samrom.map')
    if not (os.path.exists(rom) and os.path.exists(mapfile)):
        print('no SAM ROM build in %s; leaving MBTEXT as raw bytes' % work)
        return
    toks = sambasic.Tokens(open(rom, 'rb').read(), sambasic.read_map(mapfile))
    text, equs = sambasic.BasicText(d, MBTEXT[0], MBTEXT[1], toks).render()
    _table(d, MBTEXT[0], MBTEXT[1], text)
    d.basic_equs = equs


def name_tables(dos, mb, work):
    """Name what the hook, command and function tables point at."""
    mapfile = os.path.join(work, 'samrom.map')
    rom = os.path.join(work, 'samrom.bin')
    if not (os.path.exists(rom) and os.path.exists(mapfile)):
        return None
    toks = sambasic.Tokens(open(rom, 'rb').read(), sambasic.read_map(mapfile))
    src = os.path.join(ROOT, 'ref', 'masterdos', 'annotated-src', 'masterdos23.asm')
    hooks = annotate.hooks_from_source(src)
    print('named %d routines from the dispatch tables'
          % annotate.name_tables(dos, mb, toks, hooks))
    return toks


def split_skips(d, start, end):
    """Re-decode a run in which &21 is a two-byte skip, not an instruction.

    `LD HL,nn` is the usual way to jump over the next two bytes without a
    branch, and MasterBASIC strings its error entry points together with
    it: each loads its own number into A and falls through, the following
    LD A,n being swallowed as the operand.  A plain linear decode reads
    the whole chain as a row of LD HL,nn and hides every entry point but
    the first.  The trace splits the ones something jumps to; this splits
    the rest, in a run that has been shown to be a chain.
    """
    for a in range(start, end):
        d.insns.pop(a, None)
        d.setm(a, UNKNOWN)
        d.seen.discard(a)
    p = start
    while p < end:
        if d.byte(p) == 0x21 and d.byte(p + 1) == 0x3E:
            d.setm(p, DATA)
            p += 1
            continue
        i = d.decode(p)
        if i is None or i.end > end:
            break
        d.insns[p] = i
        d.setm(p, CODE)
        for x in range(p + 1, i.end):
            d.setm(x, CONT)
        p = i.end


def annotate_errors(d, reporters):
    """Comment the LD A,n that feeds an error report with the message.

    The reporter takes the number in A, so the value has to be traced
    forward rather than read off the instruction.  The decode is a fresh
    one, not the emitted stream, because these chains are strung together
    with LD HL,nn used as a two-byte skip: from one entry point the next
    entry's LD A,n is swallowed as an operand and never runs.
    """
    n = 0
    for a, insn in list(d.insns.items()):
        m = re.match(r'^LD A,&([0-9A-F]{2})$', insn.text)
        if not m:
            continue
        code = int(m.group(1), 16)
        text = d.errors.get(code)
        if not text:
            continue
        p = insn.end
        for _ in range(16):
            if p in reporters:
                d.comments[a] = 'error %d, "%s"' % (code, text)
                # These entry points are called from all over; name them
                # for the error they raise rather than for their address.
                slug = re.sub(r'[^A-Za-z0-9]+', '_', text).strip('_').upper()[:20]
                name = 'REP_' + slug
                if a not in d.labels and name not in set(d.labels.values()):
                    d.labels[a] = name
                n += 1
                break
            i = d.decode(p)
            if i is None or not d.inside(i.end - 1) or not i.falls_through():
                break
            p = i.end
    return n


def render_tables(d, work):
    """Write the two dispatch tables out as tables rather than as code."""
    mapfile = os.path.join(work, 'samrom.map')
    rom = os.path.join(work, 'samrom.bin')
    if not (os.path.exists(rom) and os.path.exists(mapfile)):
        return
    toks = sambasic.Tokens(open(rom, 'rb').read(), sambasic.read_map(mapfile))
    for start, (end, text) in ((0x42EA, annotate.render_ctab(d, toks)),
                               (0x44A6, annotate.render_samhk(d)),
                               (0x78EB, annotate.render_fnvec(d))):
        _table(d, start, end, text)


def _table(d, start, end, text):
    for a in range(start, end):
        d.setm(a, DATA)
        d.insns.pop(a, None)
    d.renderers[start] = (end, text)
    d.rendered.append((start, end))


def report(d, note=''):
    n, tot = d.coverage()
    print('%-4s %-8s code %d/%d bytes (%.1f%%)' % (d.tag, note, n, tot, 100.0 * n / tot))


CENSUS = (('Code', (CODE, CONT)), ('Variables and other data', (DATA,)),
          ('Inline call parameters', (PARAM,)), ('Message and keyword text', (TEXT,)),
          ('RST &08 codes', (RST8,)), ('Pointer tables', (WORD,)),
          ('Unclassified', (UNKNOWN,)))


def census(pages):
    """Every byte of the image by what the listing makes of it.

    The counts in README.md and docs/disassembly.md are this table, so
    that they can be checked rather than remembered."""
    tot = sum(len(d.mark) for d in pages)
    print('byte census, %d bytes:' % tot)
    for name, kinds in CENSUS:
        n = sum(sum(1 for v in d.mark if v in kinds) for d in pages)
        pct = '  (%.1f%%)' % (100.0 * n / tot) if name == 'Code' else ''
        print('    %-26s %6d%s' % (name, n, pct))
    labels = sum(len(d.labels) for d in pages)
    described = sum(sum(1 for a in d.headers if a in d.labels) for d in pages)
    print('    %-26s %6d of %d labelled addresses'
          % ('described', described, labels))


def analyse(d):
    report(d, 'trace')
    repair(d)
    classify_text(d)
    until_stable(d, table_seeds)
    until_stable(d, sweep_gaps)
    until_stable(d, lambda x: sweep_gaps(x, minlen=12, permissive=True))
    repair(d)
    classify_text(d)
    report(d, 'final')


def header(d):
    head = [d.title, '']
    if d.ports:
        head.append('; Hardware ports, under the names the two source trees use.')
        head.append('; What each one does is from the SAM Coupe Technical Manual.')
        for v in sorted(d.ports):
            # The Coupe's own ports come from the technical manual; the
            # disk and printer ports are the DOS's, and its source says
            # what they are.
            note = romsyms.PORT_NOTES.get(v) or d.romdesc.get(d.ports[v], '')
            head.append(('%-14s EQU  %-6s %s'
                         % (d.ports[v] + ':', hexn(v, 2),
                            '; ' + note if note else '')).rstrip())
    eq = d.syms.equates(d.used_ext) if d.syms else {}
    if eq:
        head.append('')
        head.append('; SAM ROM entry points and system variables.  A page cannot')
        head.append('; address the variables directly -- it occupies the same')
        head.append('; &4000-&7FFF they live in -- so it either calls NRRD/NRWR, which')
        head.append('; page them in, or does the same windowing inline, which is what a')
        head.append('; name written here as NAME+&4000 means.')
        head.append("; The notes are mostly the ROM source's own words.")
        # Several addresses have two names -- CHAD and CHADD are the same
        # byte -- and only one of them is described.  Share it.
        shared = {}
        def described(name):
            # J_FARLDIR is the jump table's FARLDIR, and ROM_BORDCR is
            # the ROM's own BORDCR under a name that does not clash with
            # ours; the sources describe them without the prefix.
            for key in (name, re.sub(r'^(J_|ROM_)', '', name)):
                got = d.romdesc.get(key) or romsyms.EXTRA_NOTES.get(key)
                if got:
                    return got
            return ''

        for name in eq:
            got = described(name)
            if got:
                shared.setdefault(eq[name], got)
        for name in sorted(eq):
            note = described(name) or shared.get(eq[name], '')
            head.append(('%-14s EQU  %-6s %s'
                         % (name + ':', hexn(eq[name], 4),
                            '; ' + note if note else '')).rstrip())
    if d.used_page_flag:
        head.append('')
        head.append('; What a dispatch table adds to one of the names below to')
        head.append('; make the word it stores.  Not bit 15 itself, which is')
        head.append('; &8000: it is &4000 off to undo the window this page sees')
        head.append('; the other one through, then &8000 on to set the flag.')
        head.append('%-14s EQU  %s' % (PAGE_FLAG + ':', hexn(0x4000, 4)))
    if d.used_peer:
        head.append('')
        head.append('; Addresses in the other page, which sits at &8000-&BFBF while')
        head.append('; this one is at &4000.  The names are its own labels.  A stored')
        head.append('; pointer written as NAME+&4000 has bit 15 set, the flag INDJP')
        head.append('; and CTAB use to mean "not in this page".')
        for name in sorted(d.used_peer):
            head.append('%-14s EQU  %s' % (name + ':', hexn(d.used_peer[name], 4)))
    if d.rst_equs:
        head.append('')
        head.append("; The ROM's restarts, under the names its own source gives")
        head.append('; them.  A restart is a one-byte call to a fixed address, so')
        head.append('; these are those addresses.')
        for name in sorted(d.rst_equs, key=lambda n: d.rst_equs[n][0]):
            v, why = d.rst_equs[name]
            lines = why.split(chr(10))
            head.append('%-14s EQU  %-6s ; %s' % (name + ':', hexn(v, 2), lines[0]))
            for extra in lines[1:]:
                head.append('%-14s %-11s ; %s' % ('', '', extra))
    if d.inferred:
        head.append('')
        head.append('; Read from the code, not carried from a source.  MasterBASIC')
        head.append('; has no published source, so unlike the names above these are')
        head.append('; an interpretation of what the surrounding instructions do,')
        head.append('; given here so it can be judged.  Each is written only where')
        head.append('; the byte already had that value, so the file still assembles')
        head.append('; to the original either way.')
        for name in sorted(d.inferred):
            v, why = d.inferred[name]
            head.append('%-14s EQU  %-6s ; %s' % (name + ':', hexn(v, 2), why))
    if d.user_equs:
        head.append('')
        head.append('; Numbers named in notes/, each for one instruction where')
        head.append('; the same value means something else elsewhere.')
        for name in sorted(d.user_equs):
            v = d.user_equs[name]
            head.append('%-14s EQU  %s' % (name + ':', hexn(v, 2 if v < 256 else 4)))
    if d.mdos_equs:
        head.append('')
        head.append("; Constants under MasterDOS's own names, from the annotated")
        head.append('; source.  Each one is written where the listing would have')
        head.append('; printed the same number, and means the same thing here.')
        for name in sorted(d.mdos_equs):
            v = d.mdos_equs[name]
            note = described(name)
            head.append(('%-14s EQU  %-6s %s'
                         % (name + ':', hexn(v, 2 if v < 256 else 4),
                            '; ' + note if note else '')).rstrip())
    codes = {d.rst8[v]: v for v in sorted(d.used_codes)}
    if codes:
        head.append('')
        head.append('; The byte after RST &08: a DOS error, or a hook code, which is')
        head.append('; 128 plus the index of an entry in the DOS hook table at &44A6.')
        for name in sorted(codes, key=lambda n: codes[n]):
            head.append('%-14s EQU  %s' % (name + ':', hexn(codes[name], 2)))
    if d.tag == 'MB':
        head.append('')
        head.extend('; ' + line if line else ';'
                    for line in annotate.UNPLACED.rstrip().split('\n'))
    if d.basic_equs:
        head.append('')
        head.append('; SAM BASIC tokens, from the ROM tables -- see MBTEXT.')
        for name in sorted(d.basic_equs):
            head.append('%-14s EQU  %s' % (name + ':', hexn(d.basic_equs[name], 2)))
    bad = d.unplaced()
    if bad:
        head.append('')
        head.append('; These labels fall inside an instruction, so the trace has')
        head.append('; mis-aligned somewhere near each of them.')
        for a in sorted(bad):
            head.append('%-14s EQU  %s' % (bad[a] + ':', hexn(a, 4)))
    print('%-4s %d labels land inside an instruction' % (d.tag, len(bad)))
    return '\n'.join(head)


SPEC_TITLE = """; %s -- a reading, not a record.
;
; This is disasm/%s with a guess attached to every routine.  The
; listing in disasm/ holds what can be shown; this holds what the code
; looks like it is doing, which is a different thing and lives in a
; different folder for that reason.
;
; Each routine carries a banner with:
;
;   Takes / Leaves / Preserves   worked out by dataflow over the
;       instructions, with calls propagated until they settle.  Derived,
;       so wrong only where the routine boundaries are wrong -- and they
;       will be, wherever a routine has several entry points, which this
;       code does constantly.
;   ?   a reading.  Composed from what the routine touches: the ROM
;       variables it names, the routines it calls, how it ends.  Every
;       line that starts with ? is a guess.
;
; Lines carry notes where an idiom has one meaning in this codebase --
; the HMPR window, an inline parameter, a self-modified operand.
;
; It still assembles to the original bytes: everything added here is a
; comment.
"""


def write_speculation(dos, mb, outdir):
    """Write speculate/*.asm beside the listings."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(root, 'speculate')
    if not os.path.isdir(out):
        os.makedirs(out)
    total = 0
    for d, name in ((dos, 'masterdos.asm'), (mb, 'masterbasic.asm')):
        bodies, known = speculate.analyse(d)
        for a, text in specrender.notes_for(d, bodies).items():
            d.notes.setdefault(a, []).append(text)
        for s, e, nm in bodies:
            was = d.headers.get(s)
            d.headers[s] = annotate.banner(
                specrender.banner(d, s, e, nm, known[s], was))
            total += 1
        d.relabel()
        # header() emits the equates the body needs -- ROM names, peer
        # labels, RST codes -- so the preamble replaces the title inside
        # it rather than standing in for the whole thing.
        was_title, d.title = d.title, SPEC_TITLE % (name, name)
        d.emit(io.StringIO(), segs=[(BASE, HALF)])
        with open(os.path.join(out, name), 'w') as f:
            d.emit(f, title=header(d), segs=[(BASE, HALF)])
        d.title = was_title
        print('wrote', os.path.join(out, name))
    print('read %d routines' % total)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('work')
    ap.add_argument('-o', '--outdir')
    args = ap.parse_args()

    fpcalc.load(ROOT)
    dos, mb, _ = load(args.work)
    seeds(dos, mb)
    for _ in range(3):
        for d in (dos, mb):
            analyse(d)
        for d in (dos, mb):
            at = find_xpage_call(d)
            if at is not None and xpage_params(d, at):
                # Only where it is actually used.  Both pages carry the
                # code -- they were assembled from one source -- but the
                # DOS reaches the extension through its dispatch tables
                # instead, and already has MasterDOS's name on the entry
                # four bytes above this one.
                name = 'CALL' + d.peer.tag
                if name not in set(d.labels.values()):
                    d.labels.setdefault(at, name)
        run_both((dos, mb))

    # Now that every instruction is decoded, find the stretches where HMPR
    # is zero for real, rather than listing them by hand.
    nz = 0
    for d in (dos, mb):
        found = hmpr_zero_ranges(d)
        print('  %s: %d stretches with HMPR zero' % (d.tag, len(found)))
        # Overlaps are harmless -- the test is any() over the list -- so
        # every stretch goes in, including the few already there by hand.
        d.no_peer.extend(found)
        nz += len(found)
    print('%d more stretches where &8000 is the system page, not the peer' % nz)
    for d in (dos, mb):
        d.relabel()

    # Name the routines that have been worked out before anything else, so
    # that the hook codes and the tables below pick the names up.
    annotate.apply(dos, annotate.DOS)
    annotate.apply(mb, annotate.MB)
    toks = name_tables(dos, mb, args.work)
    for d in (dos, mb):
        load_symbols(d, args.work)
        d.rst8.update(romsyms.hook_names(dos, HOOK_TABLE))
    render_basic(mb, args.work)
    mb.region(MBVARS2[0], MBVARS2[1], DATA)
    render_tables(dos, args.work)
    for tag, page in (('DOS', dos), ('MB', mb)):
        for lo, hi in annotate.SKIP_CHAINS.get(tag, ()):
            split_skips(page, lo, hi)
    print('commented %d error numbers'
          % sum(annotate_errors(d, REPORTERS[d.tag]) for d in (dos, mb)))
    _table(dos, 0x4000, *annotate.render_header(dos))
    _table(mb, MBKEYS[0], *annotate.render_mbkeys(mb))
    print('named %d XVARs from the manual' % annotate.name_xvars(mb))
    _table(mb, MBVARS[0], *annotate.render_xvars(mb))

    # Each page's operands need the other page's labels, so name both first.
    print('named %d routines in the copied block'
          % annotate.name_copied_block(dos, mb))
    print('documented %d routines from the manual'
          % annotate.document_features((dos, mb)))
    ncom, nhdr, nsec, ndata, nops, nequ, nprom, changed = carrydoc.apply(
        dos, args.work, os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        annotate.banner, data_mark=DATA, data_region=DOSVARS)
    print('carried from the annotated MasterDOS source: %d line comments, '
          '%d routine headers, %d section banners' % (ncom, nhdr, nsec))
    print('%d routines MasterBASIC changed too much to describe from it, '
          '%d bytes of declared storage taken back from the trace'
          % (len(changed), ndata))
    print('named the operands of %d instructions, needing %d equates; '
          '%d variables took their MasterDOS name' % (nops, nequ, nprom))
    dos.changed_routines = changed
    # The author's own names for addresses outside this page, so that a
    # synthetic peer label cannot displace one.  See Page.carried_name.
    for name, value in dos.mdos_equs.items():
        if not dos.inside(value):
            dos.carried_by_value.setdefault(value, name)
    # The NR family sits in both pages at different addresses, so it is
    # documented by name.  L4575 is NRWRD's other entry point: it copies
    # HL into BC and falls in, which nothing else in the listing says.
    nnr = 0
    for d in (dos, mb):
        rev = {}
        for at, name in d.labels.items():
            rev.setdefault(name, at)
        head = rev.get('NRWRD')
        if head is not None and d._starts_insn(head - 2)                 and d.insns[head - 2].text == 'LD B,H':
            d.labels[head - 2] = 'NRWRHL'
            rev['NRWRHL'] = head - 2
        for name, doc in nrfam.DOC.items():
            at = rev.get(name)
            if at is not None and at not in d.headers:
                d.headers[at] = annotate.banner(doc)
                nnr += 1
    print('documented %d routines of the NR family' % nnr)

    print('described %d carried labels from their own source line'
          % carrydoc.describe_labels(dos, args.work, ROOT))
    ntw, ntc, nth = carrydoc.twins(
        mb, args.work, os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        annotate.banner)
    print('%d routines the extension shares with MasterDOS: %d line comments, '
          '%d headers' % (ntw, ntc, nth))

    # The extension has no source to carry from, so its immediates are
    # named from what the code around them does -- and said to be.
    rev = {v: k for k, v in mb.labels.items()}
    mb.fetchers = set()
    wrap = infer.wrappers(mb, rev.get('CMR'), mb.syms)
    for a, name in wrap.items():
        if name not in set(mb.labels.values()):
            mb.labels[a] = name
    mb.fetchers = set(a for a, name in wrap.items()
                      if name in ('CALL_NEXTCHAR', 'CALL_GETCHAR', 'CALL_GETSTR'))
    nimm, mb.inferred = infer.name_immediates(mb, toks)
    print('named %d wrapper routines and read %d immediates from context'
          % (len(wrap), nimm))

    syms = fpcalc.names(ROOT)
    consts = fpcalc.constants(ROOT)
    n = ok = 0
    for d in (dos, mb):
        for at, end, items in d.fpc:
            d.renderers[at] = (end, fpcalc.render(d, items, syms))
            d.rendered.append((at, end))
            n += 1
            # What the list computes, said once above the RST that starts
            # it.  None means the list cannot be one, so nothing is said.
            said = fpcalc.summarise(items, syms, consts, d)
            if said:
                d.notes[at - 1] = ['calculator: ' + said]
                ok += 1
    print('decoded %d calculator literal lists, summarised %d' % (n, ok))
    print('swept %d unclaimed runs that decode exactly'
          % sum(sweep_unknown_all(d) for d in (dos, mb)))
    # The trace has finished, so the source's data declarations can be
    # applied a second time: split_entries and the sweeps re-decode,
    # and a few of these bytes get claimed as code again on the way.
    again = sum(carrydoc.undo_code(d, d.declared_data, DATA,
                                   zero_only=False)
                for d in (dos, mb) if d.declared_data)
    if again:
        print('%d bytes the source calls storage, reclaimed after the '
              'trace ran again' % again)
    print('showed %d entry points a longer instruction was hiding'
          % sum(split_entries(d) for d in (dos, mb)))
    print('%d RST &38s that were really &FF bytes'
          % sum(drop_fake_rst38(d) for d in (dos, mb)))
    print('dropped %d stray labels'
          % sum(drop_stray_labels(d) for d in (dos, mb)))

    z = o = t = 0
    for d in (dos, mb):
        a, b, c = classify_leftovers(d)
        z, o, t = z + a, o + b, t + c
    print('accounted for the leftovers: %d bytes of zero fill, %d read '
          'twice, %d of text' % (z, o, t))
    print('named %d restarts' % sum(infer.name_restarts(d) for d in (dos, mb)))
    print('named the port in %d register loads'
          % sum(infer.name_port_loads(d) for d in (dos, mb)))
    # Hand-written notes come last of the naming passes, so that a
    # person's name beats anything worked out, and before autolabel,
    # so nothing synthetic is invented for an address they named.
    nn, nc, nm, problems = notes.apply((dos, mb), ROOT, annotate.banner)
    if nn or nc or nm:
        print('notes/: %d names, %d line comments, %d bytes marked'
              % (nn, nc, nm))
    for p in problems:
        print('notes/: ' + p)
    # CTAB's text names the routines it points at, and some of those names
    # arrive from notes/, so it has to be composed again now they exist.
    render_tables(dos, args.work)

    n = sum(autolabel(d, skip=(MBTEXT,)) for d in (dos, mb))
    n += sum(label_peer_targets(d) for d in (dos, mb))
    print('named %d further addresses' % n)

    # After autolabel, so the label a patch refers to is the final one.
    print('%d operands in relocated blocks told what they mean'
          % sum(note_relocated(d) for d in (dos, mb)))
    print('%d instructions told which operand they patch'
          % sum(note_patched_ports(d) for d in (dos, mb)))


    nr, rp = notes.rename((dos, mb), ROOT)
    if nr:
        print('notes/: %d names changed' % nr)
    for p in rp:
        print('notes/: ' + p)

    print('%d signature searches given their parameters'
          % sum(note_signature_calls(d, args.work) for d in (dos, mb)))

    if args.outdir:
        for d, name in ((dos, 'masterdos.asm'), (mb, 'masterbasic.asm')):
            d.relabel()
            # A dry run: the header must declare every outside name, peer
            # label and RST &08 code the body turns out to use.
            d.emit(io.StringIO(), segs=[(BASE, HALF)])
            path = os.path.join(args.outdir, name)
            with open(path, 'w') as f:
                d.emit(f, title=header(d), segs=[(BASE, HALF)])
            print('wrote', path)
        for p in notes.check_equates(ROOT, [
                os.path.join(args.outdir, n)
                for n in ('masterdos.asm', 'masterbasic.asm')]):
            print('notes/: ' + p)
        # Only now: the speculation is written by adding to these same
        # headers and notes, so it has to come after the clean listings.
        # Before the speculation pass, which puts a header on every
        # routine in its own listings and would count as description.
        census((dos, mb))
        write_speculation(dos, mb, args.outdir)
    return dos, mb



def hmpr_zero_ranges(d, back=16, limit=192):
    """Ranges where HMPR is zero, so &8000+ is the ROM's system page.

    Three of these were found by hand, each after a label in the listing
    turned out to name the wrong page, so it is worth deriving the rest
    rather than waiting for them to be noticed.  A range runs from the
    label the zeroing sits under -- the windowed address is usually built
    a few instructions before the OUT that makes it mean anything -- to
    the next write to HMPR, which is the restore.
    """
    addrs = sorted(d.insns)
    out = []
    for i, a in enumerate(addrs):
        # By opcode, not by text: the ports are not named until later.
        if not (d.byte(a) == 0xD3 and d.byte(a + 1) == 0xFB):
            continue
        prev = addrs[i - 1] if i else None
        if prev is None:
            continue
        zeroed = (d.byte(prev) == 0xAF                       # XOR A
                  or (d.byte(prev) == 0x3E and d.byte(prev + 1) == 0))
        if not zeroed:
            continue
        # Walk back over the instructions that build the address, but no
        # further than the start of the run: an instruction that does not
        # fall through belongs to whatever came before, and its operands
        # are read with the caller's paging, not this one's.
        lo = prev
        for b in reversed([x for x in addrs if prev - back <= x < prev]):
            if not d.insns[b].falls_through():
                break
            lo = b
        hi = d.insns[a].end
        for b in addrs[i + 1:]:
            ins = d.insns[b]
            # Stop at the restore, at a jump or return that ends the run --
            # HMPR is often put back by the caller, and without this the
            # range would swallow whatever routine follows -- or at a cap.
            if b - hi > limit or (d.byte(b) == 0xD3 and d.byte(b + 1) == 0xFB):
                break
            # A call can page something else in and return with it still
            # there -- SELRDP in FORMAT does exactly that -- and this pass
            # cannot see into it, so the run ends at the call.  Where the
            # paging is known to survive one, notes/ or a hand-written
            # range says so.
            if ins.flow in (CALL, CCALL):
                break
            hi = ins.end
            if not ins.falls_through():
                break
        out.append((lo, hi))
    return out



MBCOPY_FIND = 0xBD79          # the signature search, in the DOS page


def note_signature_calls(d, work=None):
    """Render the six bytes after the ROM signature search as what they are.

    Three bytes of signature -- a byte and then a word, both big-endian as
    the search compares them -- the address to start looking from, and a
    signed offset applied to whatever it finds.
    """
    if d.tag != 'MB':
        return 0
    # Resolve each signature against the ROM this build assembled, so the
    # listing can say which entry point the search actually finds.  That
    # answer belongs to ROM 3.0: finding it by signature is the whole
    # point of the mechanism, and another ROM would land elsewhere.
    rom, sym = b'', {}
    if work:
        try:
            rom = open(os.path.join(work, 'samrom.bin'), 'rb').read()
            for line in open(os.path.join(work, 'samrom.map'),
                             encoding='utf-8', errors='replace'):
                m = re.match(r'^([0-9A-F]{4})=(\S+)', line.strip())
                if m:
                    sym.setdefault(int(m.group(1), 16), m.group(2))
        except OSError:
            rom = b''

    def resolve(sig, start, step):
        if not rom:
            return ''
        if start < 0x4000:
            base, lo, hi = 0, start, 0x4000
        elif 0xC000 <= start <= 0xFFFF:
            base, lo, hi = 0xC000, start - 0xC000 + 0x4000, 0x8000
        else:
            return ''
        i = rom.find(sig, lo, hi)
        if i < 0:
            return '  -- not in this ROM'
        at = i if not base else i - 0x4000 + 0xC000
        got = (at + step) & 0xFFFF
        name = sym.get(got)
        return '  -> %s%s' % (hexn(got, 4), ' ' + name if name else '')

    n = 0
    for a, ins in sorted(d.insns.items()):
        if not (ins.text.startswith('CALL') and ins.target == MBCOPY_FIND):
            continue
        p = ins.end
        if p + 6 > d.limit:
            continue
        b = [d.byte(p + i) for i in range(6)]
        off = b[5] - 256 if b[5] > 127 else b[5]
        d.renderers[p] = (p + 6, ('%-14s DEFB %-25s ; %04X %s' + chr(10)) % (
            '', ','.join(hexn(x, 2) for x in b), p,
            'signature %02X %02X %02X from %s%s%s'
            % (b[0], b[1], b[2], hexn(b[3] << 8 | b[4], 4),
               ', %+d' % off if off else '',
               resolve(bytes(b[0:3]), b[3] << 8 | b[4], off))))
        n += 1
    return n


def unknown_runs(d):
    """Maximal runs of bytes nothing has claimed."""
    runs, a = [], d.base
    while a < d.limit:
        if d.m(a) != UNKNOWN:
            a += 1
            continue
        s = a
        while a < d.limit and d.m(a) == UNKNOWN:
            a += 1
        runs.append((s, a))
    return runs


def classify_leftovers(d):
    """Account for the bytes left over after everything else has run.

    Almost none of them are a third thing.  They are either zero fill,
    or the *other* reading of bytes an overlapping instruction has
    already claimed -- the skipped &21 of an entry chain, the opcode a
    caller steps over by entering a byte later.  Both readings are real;
    only one can be written down, and the byte left behind is the one
    that was not.  Saying so is better than leaving it unclassified as
    though nobody had looked.
    """
    zeros = other = text = 0
    for s, e in unknown_runs(d):
        if all(d.byte(x) == 0 for x in range(s, e)):
            d.region(s, e, DATA)
            d.comments.setdefault(s, 'zero fill')
            zeros += e - s
            continue
        if e - s >= 6 and looks_like_text(d, s, e):
            d.region(s, e, TEXT)
            text += e - s
            continue
        # The hidden reading usually runs past the gap and finishes
        # inside the instruction that covers it -- that overlap is the
        # whole point of the trick -- so the decode has only to reach the
        # end of the run, not to stop on it.
        p, bad = s, 0
        while p < e:
            i = d.decode(p)
            if i is None or not i.asm:
                bad += 1
                break
            p = i.end
        if p >= e and not bad:
            first = d.decode(s)
            d.region(s, e, DATA)
            d.comments.setdefault(
                s, 'skipped: reads as %s from here, and as part of the '
                   'instruction above it' % first.text)
            other += e - s
    return zeros, other, text


def sweep_unknown(d, minlen=6):
    """Disassemble runs of unclaimed bytes that decode exactly.

    sweep_gaps works on the runs d.gaps() yields, which merge unclaimed
    bytes with data; where such a run begins with data it is skipped,
    and a block of real code sitting behind a few bytes of padding is
    never looked at.  This walks the runs that are unclaimed and nothing
    else, and takes one only when decoding from its first byte lands
    exactly on the next instruction with nothing invalid in between --
    the same test, applied where the other pass could not reach.
    """
    runs, a = [], d.base
    while a < d.limit:
        if d.m(a) != UNKNOWN:
            a += 1
            continue
        s = a
        while a < d.limit and d.m(a) == UNKNOWN:
            a += 1
        runs.append((s, a))
    seeded = 0
    for s, e in runs:
        if e - s < minlen or looks_like_text(d, s, e):
            continue
        p, bad, n = s, 0, 0
        while p < e:
            i = d.decode(p)
            if i is None:
                break
            if not i.asm:
                bad += 1
            n += 1
            p = i.end
        if p == e and not bad and n >= 3:
            d.seed(s)
            seeded += 1
    d.run()
    return seeded


def sweep_unknown_all(d, rounds=8):
    """Sweep until it stops finding anything.

    One pass claims only as far as the first RET: a block reached by
    several hooks has entry points behind that, and each becomes a fresh
    unclaimed run once the one before it is taken.
    """
    total = 0
    for _ in range(rounds):
        got = sweep_unknown(d)
        total += got
        if not got:
            break
    return total


def split_entries(d, rounds=8):
    """Show alternate entry points that a longer instruction hides.

    `LD HL,nn` is the cheapest way to skip two bytes without branching,
    and this code strings entry points together with it: each loads its
    own error number and falls through, the &21 of the next `LD HL`
    swallowing the two bytes after it.  A linear decode reads the whole
    chain as a row of LD HL,nn and shows only the first entry.  `CP n`
    does the same job for one byte, and an FD prefix turns `LD HL,nn`
    into `LD IY,nn` for a caller who enters one byte earlier.

    Both readings are real -- that is the trick -- but only one can be
    written down, and the entry points are the useful one.  A label
    inside an instruction is the evidence: something reaches that
    address, so it is where an instruction begins.  The bytes before it
    become DEFB, and the decode is redone from the label.
    """
    fixed = 0
    for _ in range(rounds):
        moved = 0
        # A label inside an instruction is one kind of evidence; a jump
        # or call that lands inside one is the same evidence, and it is
        # available before any label has been given out.
        inside = dict((a, 'target') for a in sorted(set(
            ins.target for ins in d.insns.values()
            if ins.target is not None and d.inside(ins.target)
            and ins.text.startswith(('CALL', 'JP ', 'JR ', 'DJNZ'))
            and d.m(ins.target) == CONT)))
        inside.update(d.unplaced())
        for a, name in sorted(inside.items()):
            p = a - 1
            while p > d.base and not d._starts_insn(p):
                p -= 1
            ins = d.insns.get(p)
            if ins is None or ins.end <= a:
                continue
            probe = d.decode(a)
            if probe is None or probe.end > d.limit or not probe.asm:
                continue
            d.insns.pop(p, None)
            for x in range(p, ins.end):
                d.setm(x, UNKNOWN)
                d.seen.discard(x)
            for x in range(p, a):               # the skipped opcode byte
                d.setm(x, DATA)
                d.seen.add(x)
            d.seed(a)
            d.run()
            moved += 1
            fixed += 1
        if not moved:
            break
    return fixed


# Blocks the installer copies into the ROM's system page.  Each is
# assembled for where it lands, so its absolute operands mean addresses
# there and the labels this listing puts on them are of the wrong page.
RELOCATED = ((0x7460, 0x75E1, 0x46CC), (0x7BA4, 0x7E43, 0x484D))


def note_relocated(d):
    """Say what an operand in a relocated block means once it is moved."""
    if d.tag != 'MB':
        return 0
    n = 0
    for lo, hi, dest in RELOCATED:
        bias = dest - lo
        d.comments.setdefault(
            lo, 'from here to &%04X this code is written for &%04X: '
                'subtract &%04X from any address in it' % (hi - 1, dest, -bias))
        for a in range(lo, hi):
            ins = d.insns.get(a)
            if ins is None or ins.target is None:
                continue
            if not ins.text.startswith(('CALL', 'JP ')):
                continue
            t = ins.target
            if not (dest <= t < dest + (hi - lo)):
                continue
            d.comments.setdefault(
                a, '&%04X once this block is moved, not the label shown' % t)
            n += 1
    return n


def note_patched_ports(d, NEAR_PATCH=1024):
    """Say where an IN or OUT gets its port, when it is written at run time.

    The DOS does not bracket a transfer with INC C and DEC C to move
    between the controller's registers, as SAMDOS did; it pokes the port
    numbers straight into the IN and OUT instructions before the loop
    starts, so the loop itself is two instructions.  What is left in the
    listing is `IN A,(&00)`, which says nothing at all -- the &00 is a
    placeholder that is never executed.
    """
    n = 0
    for a, ins in sorted(d.insns.items()):
        text = d.overrides.get(a, ins.text)
        # The +&4000 form too: by the time this runs, a write through the
        # window has already been named, so LD (&9022),HL reads as
        # LD (V5022+&4000),HL and the older pattern missed it.
        m = re.match(r'^LD \((?:&[0-9A-F]{4}|[A-Za-z_]\w*)'
                     r'(?:\+&?[0-9A-F]+)?\),'
                     r'(A|HL|DE|BC|IX|IY|SP)$', text)
        if not m or ins.target is None:
            continue
        tgt = ins.target
        # Where this page runs in the window, a write to &9022 is a write
        # to its own &5022, and that is a patch like any other -- &5C33
        # does exactly that.  Without following it the address gets a
        # label in the middle of the instruction it patches, which the
        # misalignment report then reports as a fault.
        windowed = PEER <= tgt < PEER + HALF             and any(lo <= a < hi for lo, hi in d.self_window)
        if windowed:
            tgt -= PEER - BASE
        if not d.inside(tgt):
            continue
        # A low address written from a stretch that runs with the ROM's
        # system page at &4000 is not in this page at all, so whatever it
        # appears to land inside is a coincidence.  &793F is the one that
        # showed it: LD (&5C65),HL read as patching the port of the OUT
        # at &5C63, which is two bytes long and does not reach &5C65, and
        # is really LD (STKEND),HL.
        if not windowed and any(lo <= a < hi for lo, hi in d.sys_low):
            continue
        # A write that lands on the start of an instruction is replacing
        # code, not patching an operand, and the instruction before it is
        # not its owner.  &5C2D writes to &5007, which is a POP DE, and
        # the walk back was blaming the ADD IY,BC at &5005 -- a two-byte
        # instruction with no operand at all.
        if d._starts_insn(tgt):
            continue
        owner = tgt - 1
        while owner > d.base and not d._starts_insn(owner):
            owner -= 1
        if not d._starts_insn(owner):
            continue
        victim = d.overrides.get(owner, d.insns[owner].text)
        port = victim.startswith(('IN ', 'OUT '))
        if not port and not windowed:
            # Beyond the ports, a write into another instruction is only
            # taken as self-modifying code when it is close by.  Most of
            # the addresses that land inside an instruction are ROM
            # system variables -- the ROM's variables and a page occupy
            # the same &4000-&7FFF -- and those coincidences outnumber
            # the real thing by better than two to one.
            #
            # A write through the window needs none of that care: an
            # address reached as &9022 from a routine running at &8000 is
            # this page's &5022 and nothing else, so distance says
            # nothing.  &5C33 patches &5020 from three thousand bytes
            # away and is still a patch.
            if abs(a - owner) >= NEAR_PATCH:
                continue
            if not re.match(r'^LD \(&[0-9A-F]{4}\),', text):
                continue
            if d.insns[owner].length < 2:
                continue
        what = 'port' if port else 'operand'
        d.comments.setdefault(
            owner, 'the %s is written here at run time, from &%04X'
                   % (what, a))
        d.comments.setdefault(
            a, 'patches the %s of the %s at &%04X'
               % (what, victim.split()[0], owner))
        # Write it as the instruction it patches, not as a number.  The
        # source does this itself where the author bothered -- LD
        # (LDB6+1),A -- and it is the difference between a reader seeing
        # a store to nowhere and seeing self-modifying code.
        d.labels.setdefault(owner, 'L%04X' % owner)
        text = d.overrides.get(a, ins.text)
        raw = re.search(r'&[0-9A-F]{4}', text)
        if raw and int(raw.group(0)[1:], 16) == ins.target:
            d.overrides[a] = text.replace(
                raw.group(0), '%s+%d' % (d.labels[owner], ins.target - owner))
        n += 1
    return n


def drop_fake_rst38(d):
    """&FF bytes decoded as RST &38.

    &0038 is the maskable interrupt vector, which a DOS or an extension
    never calls -- the ROM gets there from the hardware.  A RST &38 that
    nothing jumps to is an &FF byte in a table, and every one of them
    here is inside a run of &FF.
    """
    reached = set(ins.target for ins in d.insns.values()
                  if ins.target is not None
                  and ins.text.startswith(('CALL', 'JP ', 'JR ', 'DJNZ')))
    n = 0
    for a, ins in list(d.insns.items()):
        if ins.text == 'RST &38' and a not in reached:
            d.insns.pop(a)
            d.setm(a, DATA)
            n += 1
    return n


def drop_stray_labels(d):
    """Remove synthetic labels that still land inside an instruction.

    A TBL_ name comes from a run of bytes that read as pointers; where
    one lands mid-instruction and nothing refers to it, the run was a
    coincidence and the name is noise.
    """
    n = 0
    for a, name in list(d.unplaced().items()):
        if re.match(r'^(TBL|[LV])[0-9A-F_]', name) and not d.xrefs.get(a):
            del d.labels[a]
            n += 1
    return n


if __name__ == '__main__':
    main()
