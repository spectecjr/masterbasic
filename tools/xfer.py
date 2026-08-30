"""Carry MasterDOS 2.3's label names over to the combined image.

The combined build is the same source with material inserted, so routines
sit at different addresses and every absolute operand differs.  Matching
raw bytes therefore fails on almost any routine that mentions an address.

Instead each MasterDOS label is turned into a byte pattern in which the
operand bytes of in-image 16-bit references are wildcards, and that
pattern is searched for in the target.  A label is carried only when the
pattern matches in exactly one place.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from z80 import Decoder

MDOS_BASE = 0x4009
LOW, HIGH = 0x4009, 0xC000          # values treated as in-image addresses


def read_map(path):
    out = {}
    for line in open(path):
        line = line.strip()
        if '=' in line:
            a, n = line.split('=', 1)
            try:
                out[int(a, 16)] = n
            except ValueError:
                pass
    return out


def line_addresses(path):
    """Addresses of the lines pyz80 emitted code for, in order."""
    addrs = []
    pat = re.compile(r'^([0-9A-Fa-f]{4}) ')
    for line in open(path, encoding='latin-1'):
        m = pat.match(line)
        if m:
            addrs.append(int(m.group(1), 16))
    return addrs


def instruction_bounds(mem, base, addrs):
    """The set of addresses at which an instruction starts.

    Line addresses include DEFB/DEFW lines and repeat where a line emitted
    nothing, so they are used only as a starting grid; the real boundaries
    come from decoding forward from each distinct address.
    """
    starts = sorted(set(a for a in addrs if base <= a < base + len(mem)))
    return starts


def mask_pattern(mem, base, start, length, dec):
    """Regex source for `length` bytes from `start`, wildcarding operands."""
    end = start + length
    out = []
    solid = 0
    a = start
    while a < end:
        ins = dec.decode(a)
        if ins is None:
            break
        n = min(ins.length, end - a)
        raw = mem[a - base:a - base + n]
        wild = set()
        if ins.target is not None and LOW <= ins.target < HIGH and ins.length >= 3:
            # the last two bytes of the encoding are the address
            if ins.flow in (0, 1, 2, 3, 4):          # NORMAL/JUMP/CJUMP/CALL/CCALL
                if not ins.text.startswith(('JR', 'DJNZ')):
                    wild.add(ins.length - 2)
                    wild.add(ins.length - 1)
        for i in range(n):
            if i in wild:
                out.append(b'.')
            else:
                out.append(re.escape(bytes([raw[i]])))
                solid += 1
        a += ins.length
    return b''.join(out), solid, a - start


def carry(target, tbase, mdos, mbase, mapfile, lstfile,
          windows=(64, 48, 32, 24, 18, 14, 10)):
    labels = read_map(mapfile)
    addrs = line_addresses(lstfile)
    dec = Decoder(mdos, mbase)
    starts = set(instruction_bounds(mdos, mbase, addrs))

    found, ambiguous, missing = {}, [], []
    for a in sorted(labels):
        if not (mbase <= a < mbase + len(mdos)):
            continue
        if a not in starts:
            missing.append((a, labels[a]))
            continue
        for w in windows:
            w = min(w, mbase + len(mdos) - a)
            pat, solid, used = mask_pattern(mdos, mbase, a, w, dec)
            if solid < 6:
                continue
            hits = [m.start() for m in re.finditer(pat, target, re.DOTALL)]
            if len(hits) == 1:
                found[a] = (tbase + hits[0], labels[a], used, solid)
                break
            if len(hits) == 0:
                continue
        else:
            ambiguous.append((a, labels[a]))
    return found, ambiguous, missing


def resolve(found, ambiguous, target, tbase, mdos, mbase, mapfile, lstfile,
            windows=(64, 48, 32, 24, 18, 14, 10)):
    """Place labels whose pattern matched in more than one spot.

    The labels that did match uniquely give a map from MasterDOS's
    addresses to this build's, and both run in the same order.  So an
    ambiguous label has to land between the neighbours that did match,
    and a hit is accepted only if exactly one of them does.
    """
    anchors = sorted((a, v[0]) for a, v in found.items())
    if not anchors:
        return 0
    import bisect
    keys = [a for a, _ in anchors]

    def bracket(a):
        """The window the label must fall in, from its two neighbours."""
        i = bisect.bisect_left(keys, a)
        lo = anchors[i - 1][1] if i > 0 else tbase
        hi = anchors[i][1] if i < len(anchors) else tbase + len(target)
        return lo, hi

    dec = Decoder(mdos, mbase)
    taken = set(v[0] for v in found.values())
    added = 0
    for a, name in ambiguous:
        lo, hi = bracket(a)
        for w in windows:
            w = min(w, mbase + len(mdos) - a)
            pat, solid, used = mask_pattern(mdos, mbase, a, w, dec)
            if solid < 6:
                continue
            near = [tbase + m.start() for m in re.finditer(pat, target, re.DOTALL)
                    if lo <= tbase + m.start() <= hi]
            if len(near) == 1 and near[0] not in taken:
                found[a] = (near[0], name, used, solid)
                taken.add(near[0])
                added += 1
                break
    return added


def monotone_filter(found):
    """Drop matches that break the overall ordering (a coincidence guard)."""
    items = sorted(found.items())
    import bisect
    tails, back, idxs = [], [], []
    for k, (a, v) in enumerate(items):
        j = v[0]
        pos = bisect.bisect_left(tails, j)
        if pos == len(tails):
            tails.append(j)
            idxs.append(k)
        else:
            tails[pos] = j
            idxs[pos] = k
        back.append(idxs[pos - 1] if pos else -1)
    keep, k = set(), (idxs[-1] if idxs else -1)
    while k >= 0:
        keep.add(items[k][0])
        k = back[k]
    return {a: v for a, v in found.items() if a in keep}, len(found) - len(keep)


if __name__ == '__main__':
    work = sys.argv[1]
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target = open(os.path.join(root, 'file', 'MasterBasicMasterDos.bin'), 'rb').read()[9:]
    mdos = open(os.path.join(root, 'ref', 'masterdos', 'res', 'MDOS23.bin'), 'rb').read()
    found, amb, miss = carry(target, MDOS_BASE, mdos, MDOS_BASE,
                             os.path.join(work, 'mdos.map'),
                             os.path.join(work, 'mdos.lst'))
    found, dropped = monotone_filter(found)
    print('located %d labels (%d dropped as out of order), %d ambiguous, %d not at an instruction start'
          % (len(found), dropped, len(amb), len(miss)))
    for a in sorted(found)[:20]:
        t, n, used, solid = found[a]
        print('  %-12s %04X -> %04X  (%+5d, %d bytes / %d solid)' % (n, a, t, t - a, used, solid))
