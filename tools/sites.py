# -*- coding: utf-8 -*-
"""The unexplained numbers in one routine of the reading copy, in context.

    python tools/sites.py BUILD_PUT_BLOCK
    python tools/sites.py FSTAT masterdos
    python tools/sites.py --list masterbasic       the queue, worst first

Prints the whole routine with the outstanding sites marked `>>`, because
naming a number without reading around it is how a wrong name gets
written.  The rule is the build's own -- imported from clean.py rather
than copied, so this cannot drift from the figure build.sh prints:

  * the operand carries a hex number,
  * the line has no trailing comment, and
  * no symbol stands beside the number to explain it.

A routine runs from its label to the next label that is neither one of
its own internal labels (NAME_LOOP, NAME_3) nor a synthetic one (L7467,
V5DBF, TBL_4A20); that is bare_by_routine's grouping, read off the text.

The count at the foot should equal the build's figure for the routine.
If it does not, the listing on disk is from a different build than
build.log, or one of the two rules has changed without the other.
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clean import BARE, SYNTHETIC, _has_name  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LABEL = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):')

# The listing's instruction line: mnemonic, operand, then `; ADDR` and the
# byte column.  The bytes are separated from any comment by TWO spaces,
# and an uncommented line simply ends after them.  Matching the byte run
# with a trailing single space swallows all but the last byte and leaves
# that byte looking like a comment, so nothing is ever flagged -- which
# is how the first version of this reported 0 against the build's 27.
INSN = re.compile(r'^\s{10,}(\S+)(?:\s+([^;]*?))?\s*;\s+([0-9A-F]{4})'
                  r'\s+((?:[0-9A-F]{2} )*[0-9A-F]{2})(?:\s\s+(.*))?$')


def listing(half):
    path = os.path.join(ROOT, 'listings', 'clean', half + '.asm')
    return io.open(path, encoding='utf-8').read().split('\n')


# Directives are not instructions.  bare_numbers walks d.insns, so a
# DEFW &C000 in a table is outside its count, and this has to agree with
# it or the two figures cannot be reconciled.  (A word table's numbers
# are a different job anyway: naming a table entry is naming the table.)
DIRECTIVE = re.compile(r'^DEF[BWMS]$')


def outstanding(arg, comment, mnemonic=''):
    if DIRECTIVE.match(mnemonic):
        return False
    return bool(BARE.search(arg)) and not comment and not _has_name(arg)


def routine(lines, name):
    """(start, end) line indices of the routine called `name`."""
    start = next((i for i, l in enumerate(lines) if l.startswith(name + ':')), None)
    if start is None:
        raise SystemExit('no label %s in this listing' % name)
    for i in range(start + 1, len(lines)):
        m = LABEL.match(lines[i])
        if m and not m.group(1).startswith(name + '_') and not SYNTHETIC.match(m.group(1)):
            return start, i
    return start, len(lines)


def show(half, name):
    lines = listing(half)
    start, end = routine(lines, name)
    count = 0
    for l in lines[start:end]:
        m = INSN.match(l)
        if not m:
            print('      ' + l[:110])
            continue
        arg, comment = m.group(2) or '', (m.group(5) or '').strip()
        flag = '  '
        if outstanding(arg, comment, m.group(1)):
            flag = '>>'
            count += 1
        print('%s    %s' % (flag, l[:110]))
    print('\n%s %s: %d outstanding, %d lines' % (half, name, count, end - start))


def queue(half):
    """Every routine with something outstanding, worst first."""
    lines = listing(half)
    heads = [(i, m.group(1)) for i, l in enumerate(lines)
             for m in [LABEL.match(l)] if m]
    names = {n for _, n in heads}

    def internal(n):
        if SYNTHETIC.match(n):
            return True
        return any(n[i] == '_' and n[:i] in names
                   for i in range(len(n) - 1, 0, -1))

    owner, counts, totals = None, {}, {}
    for i, l in enumerate(lines):
        m = LABEL.match(l)
        if m and not internal(m.group(1)):
            owner = m.group(1)
            continue
        m = INSN.match(l)
        if not m or owner is None:
            continue
        totals[owner] = totals.get(owner, 0) + 1
        if outstanding(m.group(2) or '', (m.group(5) or '').strip(), m.group(1)):
            counts[owner] = counts.get(owner, 0) + 1
    rows = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    for n, c in rows:
        print('%4d/%-4d %s' % (c, totals[n], n))
    print('\n%s: %d outstanding over %d routines'
          % (half, sum(counts.values()), len(rows)))


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if '--list' in sys.argv:
        queue(args[0] if args else 'masterbasic')
    elif args:
        show(args[1] if len(args) > 1 else 'masterbasic', args[0])
    else:
        print(__doc__.strip())
