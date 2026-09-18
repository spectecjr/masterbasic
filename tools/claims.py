"""The claims one routine's prose makes about another, grouped by target.

    python tools/claims.py MB [--top N] [--min N] [-o FILE]
    python tools/claims.py MB --target NAME [NAME ...] [-o FILE]
    python tools/claims.py MB --bundle NAME [NAME ...] [-o FILE]

A region review reads one routine's prose against that routine's
bytes, and the largest class of what it misses is the sentence that is
about some other routine -- "X leaves it in HL", "falls into Y", "the
ROM's W does V" -- because checking it means leaving the region.  This
is the other cut: every sentence in the reading copy that names a
routine other than the one it sits in, collected under the routine it
names, so a reader with that routine's bytes in front of them checks a
list of claims instead of a region.

A claim is a sentence of the clean listing's prose (a banner line or a
line comment, continuations joined) that names an underived label of
this half other than the one whose region it is in, or gives an address
inside such a routine.  Sentences about the ROM's routines are not
collected; they have no bytes here to check against.

--top lists the targets with the most claims; --target prints the
claims about the named routines; --bundle prints each named routine's
region (as cutregion.py cuts it) followed by the claims made about it
from elsewhere, which is the reviewer's brief.
"""
import argparse
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cutregion                                    # noqa: E402

ROOT = cutregion.ROOT
NAME = re.compile(r'\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+|[A-Z][A-Z0-9]{3,})\b')
# An address, but not one end of a range: "&4000-&7FFF" is a page, not
# a claim about whatever is labelled at &4000.
HEX = re.compile(r'(?<!-)&([0-9A-F]{4})\b(?!-)')
SENTENCE = re.compile(r'(?<=[.!?])\s+(?=[A-Z&("\d])')


def paragraphs(lines, s, e):
    """(line index, text) for each run of prose in lines[s:e].

    Banner lines run together until a blank comment line; a line
    comment and the continuation lines under it are one paragraph.
    """
    out, cur, at = [], [], None
    def flush():
        if cur:
            out.append((at, ' '.join(cur)))
        cur.clear()
    for i in range(s, e):
        l = lines[i]
        if l.startswith(';'):
            t = cutregion.comment_text(l)
            if t is None:
                flush()
                continue
            if not cur:
                at = i
            cur.append(t)
            continue
        m = cutregion.INLINE.match(l)
        if m:
            flush()
            t = m.group(1).strip()
            if t:
                at = i
                cur.append(t)
            continue
        m = cutregion.CONT.match(l)
        if m and cur:
            cur.append(m.group(1).strip())
            continue
        flush()
    flush()
    return out


def routines(lines, hs):
    """(name, start line, end line, lo addr, hi addr) per underived label."""
    under = [(i, n, a) for i, n, a, d in hs if not d and a is not None]
    out = []
    for k, (i, n, a) in enumerate(under):
        s = cutregion.banner_start(lines, i)
        if k + 1 < len(under):
            e = cutregion.banner_start(lines, under[k + 1][0])
            hi = under[k + 1][2]
        else:
            e, hi = len(lines), 0x10000
        out.append((n, s, e, a, hi))
    return out


def collect(half, tree='clean'):
    lines = cutregion.load(half, tree)
    hs = cutregion.heads(lines)
    rs = routines(lines, hs)
    labels = {n for i, n, a, d in hs}
    owner = {}                          # underived name -> routine name
    for i, n, a, d in hs:
        m = cutregion.DERIVED.match(n)
        owner[n] = m.group(1) if d and m else n
    by_addr = sorted((lo, hi, n) for n, s, e, lo, hi in rs)
    def routine_at(a):
        # This half's own addresses only: an &8xxx is the other page
        # or the system page through the window, and lands on nothing
        # here.
        if not 0x4000 < a < 0x7FC0:
            return None
        for lo, hi, n in by_addr:
            if lo <= a < hi:
                return n
        return None
    claims = {}                         # target -> [(owner, line, text)]
    for name, s, e, lo, hi in rs:
        for at, text in paragraphs(lines, s, e):
            for sent in SENTENCE.split(text):
                # This project's prose has lower case in it; the 1991
                # author's "CHECK DRIVE NUMBER" is upper case throughout
                # and names its routine in every line.
                if len(sent) < 25 or not re.search(r'[a-z]', sent):
                    continue
                targets = set()
                for m in NAME.finditer(sent):
                    n = m.group(1)
                    if n in labels and owner[n] != name:
                        targets.add(owner[n])
                for m in HEX.finditer(sent):
                    r = routine_at(int(m.group(1), 16))
                    if r and r != name:
                        targets.add(r)
                for t in targets:
                    claims.setdefault(t, []).append((name, at + 1, sent.strip()))
    return lines, hs, claims


def render(claims, targets, lines=None, hs=None, bundle=False):
    out = []
    for t in targets:
        if bundle:
            regions, _ = cutregion.cut_by_names(lines, [t], hs)
            for s, e in regions:
                out.extend(lines[s:e])
            out.append('')
            out.append(';; ==== claims made about %s from elsewhere ====' % t)
        else:
            out.append('== %s' % t)
        for owner, n, text in claims.get(t, ()):
            out.append('%s  [line %d, in %s]  %s'
                       % (';;' if bundle else ' ', n, owner, text))
        out.append('')
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('half', choices=('MB', 'DOS'))
    ap.add_argument('--tree', default='clean')
    ap.add_argument('--top', type=int, help='the N most-claimed-about routines')
    ap.add_argument('--min', type=int, default=1,
                    help='with --top: only routines with at least N claims')
    ap.add_argument('--target', nargs='+', help='claims about these routines')
    ap.add_argument('--bundle', nargs='+',
                    help='region plus claims, per routine, for a reviewer')
    ap.add_argument('-o', '--out')
    args = ap.parse_args()

    lines, hs, claims = collect(args.half, args.tree)
    total = sum(len(v) for v in claims.values())
    if args.bundle:
        text = render(claims, args.bundle, lines, hs, bundle=True)
    elif args.target:
        text = render(claims, args.target)
    else:
        ranked = sorted(claims, key=lambda t: -len(claims[t]))
        if args.top:
            ranked = ranked[:args.top]
        ranked = [t for t in ranked if len(claims[t]) >= args.min]
        text = '\n'.join('%4d  %s' % (len(claims[t]), t) for t in ranked)
    if args.out:
        io.open(args.out, 'w', encoding='utf-8', newline='\n').write(text + '\n')
    else:
        sys.stdout.write(text + '\n')
    sys.stderr.write('%d claims about %d routines\n' % (total, len(claims)))


if __name__ == '__main__':
    main()
