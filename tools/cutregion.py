"""Cut a region out of a clean listing for a reviewer, by routine.

    python tools/cutregion.py MB NAME [NAME ...] [-o FILE]
    python tools/cutregion.py DOS --part C11 [-o FILE]
    python tools/cutregion.py MB --range &5E00-&6400 [-o FILE]

The first word is the half.  Then either routine names, a PART name (the
DOS listing's ";;  PART x" banners), or an address range, half-open, of
which every routine whose label falls inside is taken.  The region runs
from each routine's banner -- its header block, any step lines, the
"; ---- NAME ---- from" line -- to the banner of the next routine that
is not in the set, so a label lands over the code it names and not over
its neighbour.  Round six cut by address range and three of seven
reviewers lost time to labels sitting over the wrong routine; this is
the replacement for that recipe on both halves.

A routine, for this purpose, is a label the namer did not derive: NAME_1,
NAME_LOOP, NAME_DONE2, NAME_FAIL are inside NAME and do not end its
region; CMD_JOIN_TO is a routine of its own.

What is printed alongside (to stderr when the region goes to stdout):
the routines taken, in order, so a --range cut can be repeated by name;
the line count; the count of commented lines; and the count of lines of
this project's own prose -- a comment holding a lower-case letter, the
1991 author's being upper case -- which is the own_lines column of
design/reviews.csv.  The commented count chooses the shape (proposal or
review); the own count scores the round.  Both are described in
design/reviewprocess.md, step 1.
"""
import argparse
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LISTING = {'MB': 'masterbasic.asm', 'DOS': 'masterdos.asm'}

LABEL = re.compile(r'^([A-Za-z_][A-Za-z_0-9]*):\s*$')
DERIVED = re.compile(r'^(.+)_(?:(?:LOOP|DONE|FAIL)\d*|\d+)$')
ADDR = re.compile(r'^\s+\S.*?; ([0-9A-F]{4})(?: |$)')
PART = re.compile(r'^;;\s+PART (\S+)')
# The comment text of a line, for the two counts.  The generated
# "; ---- NAME ---- from" line and the header's rules are not prose.
INLINE = re.compile(r'^\s+\S.*?; [0-9A-F]{4}(?: [0-9A-F]{2})*(.*)$')
CONT = re.compile(r'^\s+; (.*)$')


def comment_text(line):
    """The prose on a line, or None if it carries none."""
    if line.startswith(';'):
        if re.match(r'^; ---- .* ----', line):
            return None
        text = line.lstrip(';').strip()
        if not text or set(text) <= set('-'):
            return None
        return text
    m = INLINE.match(line) or CONT.match(line)
    if m:
        text = m.group(1).strip()
        return text or None
    return None


def load(half, tree='clean'):
    path = os.path.join(ROOT, 'listings', tree, LISTING[half])
    return io.open(path, encoding='utf-8').read().split('\n')


def heads(lines):
    """Every label line: (line index, name, address or None, derived?)."""
    out = []
    names = set()
    for i, l in enumerate(lines):
        m = LABEL.match(l)
        if m:
            names.add(m.group(1))
    for i, l in enumerate(lines):
        m = LABEL.match(l)
        if not m:
            continue
        name = m.group(1)
        addr = None
        for j in range(i + 1, min(i + 12, len(lines))):
            a = ADDR.match(lines[j])
            if a:
                addr = int(a.group(1), 16)
                break
            if LABEL.match(lines[j]):
                continue
        d = DERIVED.match(name)
        derived = bool(d and d.group(1) in names)
        out.append((i, name, addr, derived))
    return out


def banner_start(lines, i):
    """Where the banner above label line i begins.

    Back over the "; ---- NAME ----" line, blank lines, and the run of
    left-margin comment lines that is the header and any steps -- to
    the blank line above them, which is where the emitter starts a
    routine.
    """
    j = i - 1
    while j >= 0 and (not lines[j].strip() or lines[j].startswith(';')):
        j -= 1
    return j + 1


def cut_by_names(lines, wanted, hs):
    """Regions for the named routines, as (start, end) line ranges."""
    by_name = {h[1]: h for h in hs}
    missing = [n for n in wanted if n not in by_name]
    if missing:
        sys.exit('not a label in this listing: ' + ', '.join(missing))
    wanted = set(wanted)
    regions, taken = [], []
    for k, (i, name, addr, derived) in enumerate(hs):
        if name not in wanted:
            continue
        # from this banner to the banner of the next underived label
        # that is not itself wanted
        end = len(lines)
        for i2, n2, a2, d2 in hs[k + 1:]:
            if d2 or n2 in wanted:
                continue
            end = banner_start(lines, i2)
            break
        if regions and regions[-1][1] >= banner_start(lines, i):
            regions[-1] = (regions[-1][0], end)     # runs on from the last
        else:
            regions.append((banner_start(lines, i), end))
        taken.append((name, addr))
    return regions, taken


def cut_by_range(lines, lo, hi, hs):
    names = [n for i, n, a, d in hs
             if a is not None and lo <= a < hi and not d]
    if not names:
        sys.exit('no routine starts in &%04X-&%04X' % (lo, hi))
    return cut_by_names(lines, names, hs)


def cut_by_part(lines, part, hs):
    starts = [i for i, l in enumerate(lines) if PART.match(l)]
    for k, i in enumerate(starts):
        if PART.match(lines[i]).group(1) == part:
            # the banner's rule line sits one above the PART line
            s = i - 1 if i and lines[i - 1].startswith(';; ---') else i
            e = starts[k + 1] if k + 1 < len(starts) else len(lines)
            if e < len(lines) and lines[e - 1].startswith(';; ---'):
                e -= 1
            names = [(n, a) for i2, n, a, d in hs if s <= i2 < e and not d]
            return [(s, e)], names
    sys.exit('no PART %s; the DOS listing has: %s'
             % (part, ', '.join(PART.match(lines[i]).group(1) for i in starts)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('half', choices=('MB', 'DOS'))
    ap.add_argument('names', nargs='*', help='routine labels')
    ap.add_argument('--part', help='a PART name (DOS listing)')
    ap.add_argument('--range', dest='range_',
                    help='&LO-&HI, half-open: routines whose label is inside')
    ap.add_argument('--tree', default='clean',
                    help='which listings/ tree (default clean)')
    ap.add_argument('-o', '--out', help='write the region here')
    args = ap.parse_args()

    lines = load(args.half, args.tree)
    hs = heads(lines)
    if args.part:
        regions, taken = cut_by_part(lines, args.part, hs)
    elif args.range_:
        m = re.fullmatch(r'&?([0-9A-Fa-f]{4})\s*-\s*&?([0-9A-Fa-f]{4})',
                         args.range_)
        if not m:
            sys.exit('--range wants &LO-&HI')
        regions, taken = cut_by_range(lines, int(m.group(1), 16),
                                      int(m.group(2), 16), hs)
    elif args.names:
        regions, taken = cut_by_names(lines, args.names, hs)
    else:
        ap.error('give routine names, --part or --range')

    out = []
    for k, (s, e) in enumerate(regions):
        if k:
            gap = s - regions[k - 1][1]
            out.append('')
            out.append(';; [cutregion: %d lines of the listing skipped here]'
                       % gap)
        out.extend(lines[s:e])
    text = '\n'.join(out).rstrip('\n') + '\n'

    commented = own = 0
    for l in out:
        t = comment_text(l)
        if t is None:
            continue
        commented += 1
        if re.search(r'[a-z]', t):
            own += 1

    if args.out:
        io.open(args.out, 'w', encoding='utf-8', newline='\n').write(text)
        say = print
    else:
        sys.stdout.write(text)
        say = lambda *a: print(*a, file=sys.stderr)

    lo = min((a for n, a in taken if a is not None), default=None)
    hi = max((a for n, a in taken if a is not None), default=None)
    say('%s %s: %d routines%s' % (
        args.half, args.tree, len(taken),
        '' if lo is None else ', labels from &%04X to &%04X' % (lo, hi)))
    say('  ' + ' '.join(n for n, a in taken))
    say('%d lines, %d commented, %d of this project\'s own prose '
        '(own_lines)' % (len(out), commented, own))
    if args.out:
        say('written to %s' % args.out)


if __name__ == '__main__':
    main()
