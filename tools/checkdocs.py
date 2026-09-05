# -*- coding: utf-8 -*-
"""Check that the prose still matches the listings.

Two things go stale on their own, because renaming a label rewrites the
listings and touches nothing else:

  * assembler quoted in docs/, which claims to be what the listing says;
  * names written in docs/ and notes/ that no longer exist.

Both are checked here rather than by eye.  Prose is sometimes about a name
that has gone -- "so CHECK_BREAK_LOOP2 says more than L6016 did" is the
point of the sentence -- and those few are listed below by hand rather than
guessed at from the wording, so that writing a new one is a decision and
not an accident.

    python tools/checkdocs.py            # from tools/build.sh
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LISTINGS = ('listings/disasm/masterdos.asm', 'listings/disasm/masterbasic.asm',
            'listings/disasm/postinstall-syspage.asm')
PROSE = ('docs', 'notes')

# prose whose point is a name the listing no longer has, file by file
HISTORICAL = {
    ('docs/disassembly.md', 'L1234'),     # an invented name, in an example
    ('docs/disassembly.md', 'L4461'),     # what CALL_NEXTCHAR was called
    ('docs/disassembly.md', 'L45D9'),     # what the address column reads
    ('docs/disassembly.md', 'L6016'),     # what CHECK_BREAK_LOOP2 was called
    ('docs/disassembly.md', 'V4110'),     # the name DSC would have had
    ('docs/disassembly.md', 'V4111'),     # the name DCT would have had
    ('notes/mb-vectors.txt', 'V589C'),    # a window address read as this page's
    ('notes/mb-filetypes.txt', 'L440A'),  # a label the false decode invented
    ('notes/mb-filetypes.txt', 'L4391'),  # the other one
}

INSN = re.compile(r'^\s{10,}(\S.*?)\s+;\s([0-9A-F]{4})\s')
QUOTED = re.compile(r'^\s{4,}(\S.*?)\s{2,};\s([0-9A-F]{4})\b')
NAME = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):(?:$|\s+EQU)')
SYNTHETIC = re.compile(r'\b[LV][0-9A-F]{4}\b')


def read_listings():
    """(text at each address, every name defined).

    A listing that is not there is an error and not a skip.  This used
    to `continue`, which meant a wrong path checked nothing and still
    reported that every file checked out -- and the path did move once,
    when postinstall/syspage.asm became listings/disasm/postinstall-syspage.asm.
    Silence is the one answer a checker must not give.
    """
    at, names = {}, set()
    for rel in LISTINGS:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            raise SystemExit('checkdocs: no %s -- run tools/build.sh first,'
                             ' or fix LISTINGS if the file has moved' % rel)
        for line in open(path, encoding='utf-8'):
            m = INSN.match(line)
            if m:
                at.setdefault(m.group(2), set()).add(m.group(1).strip())
            m = NAME.match(line)
            if m:
                names.add(m.group(1))
    return at, names


def prose_files():
    for d in PROSE:
        base = os.path.join(ROOT, d)
        for fn in sorted(os.listdir(base)):
            if fn.endswith(('.md', '.txt')) and not fn.startswith('master'):
                yield os.path.join(d, fn), os.path.join(base, fn)


def main():
    at, names = read_listings()
    bad = []
    for rel, path in prose_files():
        for n, line in enumerate(open(path, encoding='utf-8'), 1):
            m = QUOTED.match(line)
            if m and '/' not in m.group(1):
                text, addr = m.group(1).strip(), m.group(2)
                if addr in at and text not in at[addr]:
                    bad.append('%s:%d quotes "%s" at &%s; the listing has %s'
                               % (rel, n, text, addr,
                                  ' or '.join('"%s"' % t for t in sorted(at[addr]))))
            for word in SYNTHETIC.findall(line):
                if word not in names and (rel.replace(os.sep, '/'),
                                          word) not in HISTORICAL:
                    bad.append('%s:%d names %s, which no longer exists'
                               % (rel, n, word))
    for line in bad:
        print('  stale: ' + line)
    print('%d prose files check out against the listings%s'
          % (sum(1 for _ in prose_files()),
             '' if not bad else ' -- except the %d above' % len(bad)))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
