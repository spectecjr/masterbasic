"""The ROM system page, as MasterBASIC leaves it.

The code the ROM actually calls through CMDV, EDITV, RST8V and the rest
is not at the addresses the listings show it at.  It is copied into the
ROM's own system page at boot, and runs there with MasterBASIC paged out.
This builds that page and disassembles it where it really runs.

Unlike disasm/, nothing here can be proved by assembling it: there is no
original to compare against.  Every byte is either copied from the image
by a rule read out of the installer, or left blank.  The blanks are as
much a part of the result as the code.
"""

import io
import os
import sys
import textwrap
import asmfmt
import clean

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from disasm import Disassembler, UNKNOWN, CODE, CONT, DATA
from z80 import hexn

BASE, TOP = 0x4000, 0x8000
HALF = 16320
BLANK = 0xFF
# How far to follow an entry point that no copy rule accounts for -- the
# ROM's code buffer and MNIP, whose contents are built at run time.
LOOSE_VECTOR = 128

# Where the installers put things.  Each is (source half, from, to, at).
# The first three are INSTALL_ROM_PATCHES at &7B03 in
# disasm/masterbasic.asm, which sets HMPR to zero and so writes &8xxx
# meaning the system page's &4xxx.
COPIES = (
    ('MB', 0x7460, 0x75E1, 0x46CC, 'first stub, from &7460'),
    ('MB', 0x7BA4, 0x7E43, 0x484D, 'second stub, from &7BA4'),
    ('MB', 0x7B80, 0x7BA4, 0x4BA0, 'the 36 bytes from &7B80'),
    # INSTALL_SYSPAGE_CODE at &7A9F, which zeroes HMPR the same way and
    # so writes &9xxx meaning &5xxx.
    ('MB', 0x7E43, 0x7E6B, 0x5896, 'the 40 bytes from &7E43, in the gap '
     'the ROM leaves between the DEF KEY buffer and the keyboard table'),
    ('MB', 0x7AF2, 0x7B00, 0x5BE0, "MasterBASIC's own paging routine, in "
     'the fourteen bytes the ROM reserves at PAGER'),
    # INSTALL_TAIL_INTO_SYSPAGE at the DOS's &7D60, called once from the
    # boot sector at &40CD.  It runs from section C so that section B can
    # hold the system page, and copies the DOS page's tail there in two
    # runs.  The first carries the alternate character set, 116 bytes in.
    ('DOS', 0x7D60, 0x7F1E, 0x4F00, "the DOS page's tail, 446 bytes, which "
     'carries the alternate character set at &4F74'),
    ('DOS', 0x7F1E, 0x7FBF, 0x4C14, 'and 161 bytes more, the rest of the '
     'DOS half, following straight on'),
)

# INSTALL_EXTENDED_PUT at &7829 fills &45A2-&46CB and is deliberately not
# in COPIES: two of its five runs are lifted out of the ROM's own PUT,
# wherever the signature search found it, so the block cannot be
# assembled from this image alone.  A dump has it; the model does not.

# The vectors INSTALL_ROM_VECTORS points into this page, and so the
# entry points worth tracing from.
VECTORS = (
    # Named for what the ROM uses each vector for, read out of the ROM
    # source rather than guessed: the ROM's own variable table leaves most
    # of them without a comment.
    (0x46CC, 'INSLV_STRING_MOVE'),    # STRMOV1: LD HL,(INSLV) / JP NZ,HLJUMP
    (0x4866, 'EDITV_EDITOR'),         # EDITOR: the line editor entry
    (0x488E, 'CMDV_COMMAND'),         # STMTLP3, after LD (CSA),HL
    (0x4986, 'FRAMIV_FRAME_INT'),     # FRAMINT, the 50Hz frame interrupt
    (0x49A9, 'PATOUT_CHAR_OUT'),      # LD IX,(PATOUT) -- "usually=ENDOUTP"
    (0x4AB8, 'RST8V_ERROR'),          # ERROR2, where RST &08 ends up
    (0x4BB0, 'PRTOKV_PRINT_TOKEN'),   # PRGR802, printing a keyword
    (0x4BBA, 'EVALUV_EVAL_FN'),       # ABOVLETS, evaluating a function
    # Not a vector: DISPATCH_ON_COMMAND_TOKEN jumps here for PUT, and the
    # dump shows ten bytes of MasterBASIC's &7986 -- RST NEXT_CHAR, SUB
    # &AB, LD (&4AF0),A -- turning a token into a function index.  It is
    # the first of the five runs INSTALL_EXTENDED_PUT lays down, so this
    # is where MasterBASIC's rebuilt PUT begins.
    (0x45A2, 'TOKEN_TO_FN_INDEX'),
    # The ROM's code buffer.  Whatever is here was put here at run time,
    # by the ROM copying one of its own ROM 1 routines in or by
    # MasterBASIC building one; the two share the space.
    (0x4C14, 'MNIP_MAIN_INPUT'),   # INSTALL_SYSPAGE_CODE points MNIP here
    (0x4D11, 'CDBUFF_11'),
    (0x4D50, 'CDBUFF_50'),
)


class SysPage(Disassembler):
    def __init__(self, mem):
        Disassembler.__init__(self, mem, BASE)
        self.title = ''

    def ext_target(self, v):
        return None


def build(image, dump=None):
    """The system page: from a dump of a running machine if there is one,
    otherwise assembled from the copy rules and marked as a model."""
    raw = open(image, 'rb').read()
    halves = {'DOS': raw[:HALF], 'MB': raw[HALF:]}
    mem = bytearray([BLANK]) * (TOP - BASE)
    placed = []
    agree = None
    for tag, lo, hi, at, why in COPIES:
        chunk = halves[tag][lo - BASE:hi - BASE]
        mem[at - BASE:at - BASE + len(chunk)] = chunk
        placed.append((at, at + len(chunk), why))

    real = None
    if dump and os.path.exists(dump):
        real = bytes(open(dump, 'rb').read())
        diffs = []
        checked = 0
        for at, end, _ in placed:
            for a in range(at, min(end, BASE + len(real))):
                checked += 1
                if real[a - BASE] != mem[a - BASE]:
                    diffs.append(a)
        # Every difference so far has been a hole the image carries as
        # zero and the machine carries filled in.  Worth checking rather
        # than asserting, because a difference that is not one would mean
        # the copy rules are wrong somewhere.
        holes = sum(1 for a in diffs if mem[a - BASE] == 0)
        agree = (len(diffs), checked, holes)
        # The dump wins: it is the machine, and the model is only a way of
        # explaining it.  Every byte it covers is taken from it.
        for i, b in enumerate(real):
            if i < len(mem):
                mem[i] = b
        placed.append((BASE, BASE + len(real), 'from the dump'))
        print('dump covers &%04X-&%04X; the copy rules predicted it to '
              'within %d bytes' % (BASE, BASE + len(real) - 1, len(diffs)))
        # With a dump of the page before the boot as well, every byte the
        # rules claim can be asked a harder question than "is it right":
        # did the boot actually write it, or was it already that value?
        here = os.path.dirname(dump)
        pre = os.path.join(here, 'SYSPAGE_before_boot.bin')
        only = os.path.join(here, 'SYSPAGE_after_MasterDOS_loaded.bin')
        if os.path.exists(pre):
            was = open(pre, 'rb').read()
            claimed = [a for at, end, why in placed if why != 'from the dump'
                       for a in range(at, min(end, BASE + len(real)))]
            moved = sum(1 for a in claimed
                        if a - BASE < len(was) and was[a - BASE] != real[a - BASE])
            changed = sum(1 for i in range(min(len(was), len(real)))
                          if was[i] != real[i])
            print('the boot changed %d bytes of the page; the rules claim %d '
                  'of them, and %d bytes they claim were already right'
                  % (changed, moved, len(claimed) - moved))
            # A third dump, of MasterDOS booted on its own, separates what
            # the DOS does from what MasterBASIC adds.  A byte the rules
            # claim which is already right with the DOS alone is one the
            # dumps cannot attribute either way.
            if os.path.exists(only):
                dosonly = open(only, 'rb').read()
                bydos = sum(1 for i in range(min(len(was), len(dosonly)))
                            if was[i] != dosonly[i])
                inert = sum(1 for a in claimed
                            if a - BASE < len(dosonly)
                            and dosonly[a - BASE] == real[a - BASE])
                print('  of which MasterDOS alone accounts for %d; %d of the '
                      'claimed bytes the DOS already leaves as they are'
                      % (bydos, inert))
    return mem, placed, real, agree


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    image = os.path.join(root, 'file', 'MasterBasicMasterDos.bin')
    dump = os.path.join(root, 'file', 'SYSPAGE_after_MBMD_boot.bin')
    mem, placed, real, agree = build(image, dump)
    d = SysPage(mem)
    # Everything the installer does not write is not code, and the trace
    # must not wander into it: &FF decodes as RST &38 and would swallow
    # the whole page.
    # Only what an installer actually wrote, plus a bounded run at each
    # of the extra entry points.  With a dump present `placed` covers the
    # whole page, and letting the trace loose on that walks it straight
    # out of the installed blocks and into the ROM's own data: &4BF2 is
    # the text "19456," and was decoding as code, one line of which read
    # CALL NC,&8E05 -- an entry into MasterBASIC that does not exist.
    inside = set()
    for tag, lo, hi, at, why in COPIES:
        inside.update(range(at, at + (hi - lo)))
    for at, name in VECTORS:
        if at not in inside:
            inside.update(range(at, min(at + LOOSE_VECTOR, TOP)))
    for a in range(BASE, TOP):
        if a not in inside:
            d.setm(a, DATA)
    for at, name in VECTORS:
        if at in inside:
            d.seed(at, name)
    d.run()
    d.relabel()
    # Name every target something reaches, so the internal jumps can be
    # checked: in a correctly placed block they all land inside it.
    for a in sorted(d.xrefs):
        if d.m(a) == CODE and a not in d.labels:
            d.labels[a] = 'S%04X' % a
    d.relabel()

    for at, end, why in placed:
        d.headers[at] = ('; ' + '-' * 68 + '\n; %s\n; ' % why) + '-' * 68

    out = os.path.join(root, 'disasm')
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, 'postinstall-syspage.asm')
    covered = sum(1 for a in range(BASE, TOP)
                  if d.m(a) in (CODE, CONT))
    # With a dump, that one range is the page and the copy ranges lie
    # inside it; emitting both would print the stubs twice.
    if real is not None:
        segs = [(BASE, len(real))]
    else:
        segs = []
        for at, end, _ in sorted(placed):
            if segs and at == segs[-1][0] + segs[-1][1]:
                segs[-1] = (segs[-1][0], segs[-1][1] + end - at)
            else:
                segs.append((at, end - at))
    with open(path, 'w') as f:
        f.write(HEAD % (agreement(agree), covered,
                        sum(e - s for s, e, _ in placed)))
        d.emit(f, segs=segs)
    print('wrote', path)

    # The same page, written to be read: see tools/clean.py.  The two sit
    # beside their listings under the same names -- disasm/ carries the
    # working notes and clean/ the conclusions -- rather than in a
    # directory of their own.
    cpath = os.path.join(root, 'clean', 'postinstall-syspage.asm')
    os.makedirs(os.path.dirname(cpath), exist_ok=True)
    clean.clean_pages((d,))
    buf = io.StringIO()
    buf.write(CLEAN_HEAD % (covered, sum(e - s for s, e, _ in placed)))
    d.emit(buf, segs=segs)
    with open(cpath, 'w') as f:
        f.write(asmfmt.format_listing(buf.getvalue()))
    print('wrote', cpath)

    print('%d bytes placed, %d reached as code from the vectors'
          % (sum(e - s for s, e, _ in placed), covered))


def agreement(agree):
    """How well the model matched the dump, counted rather than
    remembered: the figures move whenever a copy rule is added, and a
    stale number in a header is worse than no number at all."""
    if agree is None:
        return ('; There is no dump here, so what follows is the model and'
                ' nothing\n; has checked it.\n')
    diffs, checked, holes = agree
    lead = ('; The two agree to within %d bytes across the %d the copy rules '
            'cover, ' % (diffs, checked))
    if holes == diffs:
        body = ('and every one of those %d is a byte the image carries as '
                'zero and the machine carries filled in -- the boot-time '
                'patches: ROM addresses RESOLVE_ROM_ENTRIES finds by '
                'signature, and single bytes holding MasterBASIC own page '
                'number, two of which land exactly on L7CF5+1 and L7D46+1, '
                'the operands the installer is seen to patch.' % diffs)
    else:
        body = ('but only %d of those %d are zeroes the machine fills in, so '
                '%d are something else and the copy rules are wrong '
                'somewhere.' % (holes, diffs, diffs - holes))
    return textwrap.fill(lead + body, 71,
                         initial_indent='', subsequent_indent='; ') + '\n'


HEAD = """\
; The ROM's system page after MasterBASIC has installed itself.
;
; The code the ROM calls through CMDV, EDITV, RST8V, PRTOKV, EVALUV,
; FRAMIV, PATOUT and INSLV runs here, at these addresses, with
; MasterBASIC paged out.  In disasm/masterbasic.asm the same code sits at
; &7460 and &7BA4 and has to be read with a bias in your head.
;
; WHERE THESE BYTES COME FROM.  If file/SYSPAGE_after_MBMD_boot.bin is
; present -- all 16K of the page from a machine that has booted -- it is
; used, and it is the authority: it is what the hardware holds.  Without
; it the page is assembled from the copy rules read out of the installer,
; which is a model and can be wrong.  The build says which happened, and
; how far the two agree.
;
%s;
; %d bytes are reached as code from the entry points below; %d bytes were
; placed in total.
"""


CLEAN_HEAD = """; The ROM's system page, after MasterBASIC has installed itself.
;
; This is the third listing, and the one that explains the other two.
; MasterBASIC does not patch the ROM -- it cannot, the ROM is read-only
; -- so it copies code into the ROM's own workspace page, page 0, and
; points the ROM's vectors at the copies.  CMDV, EDITV, RST8V, PRTOKV,
; EVALUV, FRAMIV, PATOUT and INSLV all end up here.
;
; That is why this page matters to a reader: the code below is what
; actually runs when you type a command.  The same bytes appear in
; clean/masterbasic.asm at &7460 and &7BA4, where they are only the
; master copy waiting to be installed, and where every address in them
; is 16K out.  Here they are at the addresses they run at.
;
; This page is at &4000-&7FFF with the ROM paged in, which is the same
; &4000 each half of the extension occupies -- so the extension and the
; system page can never both be low at once.  Whichever is not low is
; reached through the window at &8000, and code here that touches
; MasterBASIC does exactly that.
;
; It does not assemble to anything in the image, because it is not in
; the image: it is assembled out of the copy rules, checked against a
; dump of a booted machine where one is available.
;
; %d bytes are reached as code from the ROM's entry points; %d bytes
; were placed in total.
"""

if __name__ == '__main__':
    main()
