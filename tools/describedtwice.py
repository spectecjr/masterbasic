"""Routines described in two places, which is where descriptions drift apart.

A routine's banner comes from a `DOC NAME` block in one notes file, and
its label is often declared by a `MB &addr NAME` or `DOS &addr NAME`
line in another -- usually a per-area file for the banner and a
catch-all helpers file for the label.  Where the second of those carries
a paragraph of its own, the routine has two descriptions and nothing
compares them.

Both faults this found the first time it was run were of that shape.
ADJUST_VARIABLE_SIZE, then still called ENTRY_TO_LONG_ADDRESS, had a
banner saying it adjusts a 24-bit length and a paragraph elsewhere
saying it converts an address and checks it against V409E -- the reading
the ROM's lookvar.asm had overturned, left behind when the banner was
rewritten.  COMPARE_FAR_STRINGS_FOLDED had a banner describing a
case-folded comparison and a paragraph describing a copy, complete with
"a write" where the instruction is LD D,(HL).

This does not decide anything: it prints the pairs so they can be read
against each other and against the code.  A pair that agrees is the
normal case, and the two saying different things about the same routine
is what to look for -- especially where one of them describes a
mechanism the other does not mention at all.

    python tools/describedtwice.py
"""
import io, os, re

NOTES = 'notes'
NAME = re.compile(r'^(?:MB|DOS)\s+&([0-9A-Fa-f]{4})\s+([A-Z][A-Z0-9_]*)\s*$')
DOC = re.compile(r'^DOC\s+([A-Za-z_][A-Za-z0-9_]*)\s*$')


def scan(root):
    """(name -> files with a DOC banner, name -> (file, paragraph))."""
    docs, described = {}, {}
    for here, _dirs, files in os.walk(root):
        for f in sorted(files):
            if not f.endswith('.txt'):
                continue
            path = os.path.join(here, f).replace(os.sep, '/')
            lines = io.open(path, encoding='utf-8').read().split('\n')
            for i, line in enumerate(lines):
                m = DOC.match(line)
                if m:
                    docs.setdefault(m.group(1), []).append(path)
                    continue
                m = NAME.match(line)
                if not m:
                    continue
                # An indented paragraph under the name is a description;
                # a bare declaration is just the label and says nothing
                # that could contradict the banner.
                body = []
                for nxt in lines[i + 1:]:
                    if not nxt.startswith('    '):
                        break
                    body.append(nxt.strip())
                if body:
                    described.setdefault(m.group(2), []).append(
                        (path, ' '.join(body)))
    return docs, described


def main():
    docs, described = scan(NOTES)
    both = sorted(set(docs) & set(described))
    print('%d routines carry a DOC banner and a described declaration.'
          % len(both))
    print('Read each pair against the other; they should say the same thing.')
    for name in both:
        print()
        print(name)
        for path in docs[name]:
            print('    banner       %s' % path)
        for path, body in described[name]:
            print('    declaration  %s' % path)
            print('                 %s' % body)


if __name__ == '__main__':
    main()
