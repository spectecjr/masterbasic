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

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from disasm import Disassembler, UNKNOWN, CODE, CONT, DATA
from z80 import hexn

BASE, TOP = 0x4000, 0x8000
HALF = 16320
BLANK = 0xFF

# Where the installer puts things.  Each is (source half, from, to, at):
# see INSTALL_ROM_PATCHES at &7B03 in disasm/masterbasic.asm, which sets
# HMPR to zero and so writes &8xxx meaning the system page's &4xxx.
COPIES = (
    ('MB', 0x7460, 0x75E1, 0x46CC, 'first stub, from &7460'),
    ('MB', 0x7BA4, 0x7E43, 0x484D, 'second stub, from &7BA4'),
    ('MB', 0x7B80, 0x7BA4, 0x4BA0, 'the 36 bytes from &7B80'),
)

# The vectors INSTALL_ROM_VECTORS points into this page, and so the
# entry points worth tracing from.
VECTORS = (
    (0x46CC, 'INSLV_TARGET'),
    (0x4866, 'EDITV_TARGET'),
    (0x488E, 'CMDV_TARGET'),
    (0x4986, 'FRAMIV_TARGET'),
    (0x49A9, 'PATOUT_TARGET'),
    (0x4AB8, 'RST8V_TARGET'),
    (0x4BB0, 'PRTOKV_TARGET'),
    (0x4BBA, 'EVALUV_TARGET'),
)


class SysPage(Disassembler):
    def __init__(self, mem):
        Disassembler.__init__(self, mem, BASE)
        self.title = ''

    def ext_target(self, v):
        return None


def build(image):
    raw = open(image, 'rb').read()
    halves = {'DOS': raw[:HALF], 'MB': raw[HALF:]}
    mem = bytearray([BLANK]) * (TOP - BASE)
    placed = []
    for tag, lo, hi, at, why in COPIES:
        src = halves[tag]
        chunk = src[lo - BASE:hi - BASE]
        mem[at - BASE:at - BASE + len(chunk)] = chunk
        placed.append((at, at + len(chunk), why))
    return mem, placed


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    image = os.path.join(root, 'file', 'MasterBasicMasterDos.bin')
    mem, placed = build(image)
    d = SysPage(mem)
    # Everything the installer does not write is not code, and the trace
    # must not wander into it: &FF decodes as RST &38 and would swallow
    # the whole page.
    inside = set()
    for at, end, _ in placed:
        inside.update(range(at, end))
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

    out = os.path.join(root, 'postinstall')
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, 'syspage.asm')
    covered = sum(1 for a in range(BASE, TOP)
                  if d.m(a) in (CODE, CONT))
    segs = []
    for at, end, _ in sorted(placed):
        if segs and at == segs[-1][0] + segs[-1][1]:
            segs[-1] = (segs[-1][0], segs[-1][1] + end - at)
        else:
            segs.append((at, end - at))
    with open(path, 'w') as f:
        f.write(HEAD % (covered, sum(e - s for s, e, _ in placed)))
        d.emit(f, segs=segs)
    print('wrote', path)
    print('%d bytes placed, %d reached as code from the vectors'
          % (sum(e - s for s, e, _ in placed), covered))


HEAD = """\
; The ROM's system page after MasterBASIC has installed itself.
;
; THIS IS NOT A VERIFIED LISTING.  disasm/ can be proved right by
; assembling it and comparing with the original file.  Nothing here can:
; there is no original to compare against.  Every byte below was either
; copied out of the image by a rule read from the installer, or is &FF
; standing for a byte this page holds that the file does not.
;
; What it is for: the code the ROM calls through CMDV, EDITV, RST8V,
; PRTOKV, EVALUV, FRAMIV, PATOUT and INSLV runs here, at these addresses,
; with MasterBASIC paged out.  In disasm/masterbasic.asm the same code
; sits at &7460 and &7BA4 and has to be read with a bias in your head.
;
; Operands that are zero are not necessarily zero in the running system.
; RESOLVE_ROM_ENTRIES fills several of them with ROM addresses it finds
; by signature before the installer copies the blocks out here.
;
; %d bytes are reached as code from the eight vectors; %d bytes were
; placed in total.
;
; What is deliberately missing:
;
;   &45A2   PATCH_45A2 at &7800 copies a space skipper here out of the
;           DOS page tail, and the block below does JP Z,&45A2.  It is
;           not placed here because which page that copy lands in is not
;           settled -- nothing in that routine touches LMPR, which says
;           its own, but the code it installs reads &5A9A and &5C3C as
;           ROM system variables, which says this one.  See
;           notes/mb-selfpatch.txt.  A dump of the running machine would
;           decide it.
;
;   &4000-&46CB and &4AEC-&4B9F are the ROM's own heap and stack, with
;           BASIC's stack moved down to &45A1 by INSTALL_ROM_VECTORS.
;           Nothing of MasterBASIC's is placed there.
;
; The jumps that go to &0000 are the ones RESOLVE_ROM_ENTRIES fills in
; before the copy; the listing shows the zeros the file holds.
"""


if __name__ == '__main__':
    main()
