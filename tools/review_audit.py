"""Lay a review agent's findings beside the instructions they claim to explain.

A fresh-context agent reading part of the listing produces entries that
each name an address.  Checking one by hand means finding that address
in the listing, reading the instruction, and reading whatever comment is
already there -- three lookups per finding, and there are dozens.  This
does the lookups, so that judging a claim is reading two adjacent lines.

It also reports the entries whose address is not an instruction at all,
and the DOC headers that name a label which does not exist.  Those are
the cheapest class of wrong and they want catching before any of the
prose is read.

    python tools/review_audit.py <report.txt> [listing.asm]

Understood in the report (anywhere in it; everything else is ignored):

    DOS &4B31 : some claim about that instruction [C]
    DOC FDHR [P]
    &4B31  [C]           a review finding, whose claim is the "says:" line

The listing is listings/clean/masterdos.asm unless a second argument says
otherwise; it is read in the form the assembler listing produces, where
each line carries its address and bytes after the semicolon.
"""
import io
import re
import sys

DEFAULT_LISTING = 'listings/clean/masterdos.asm'

LINE = re.compile(r'^\s{10,}(\S.*?)\s*;\s([0-9A-F]{4}) '
                  r'((?:[0-9A-F]{2} ?)+?)(?:\s\s(.*))?$')
LABEL = re.compile(r'^([A-Za-z_]\w*):\s*$')
ENTRY = re.compile(r'^(?:DOS |MB )?&([0-9A-F]{4})\s*[: ]\s*(.*?)\s*(\[[CPG]\])?\s*$')
DOC = re.compile(r'^DOC (\w+)\s*(\[[CPG]\])?\s*$')


def listing(path):
    """address -> (instruction, bytes, existing comment)."""
    out = {}
    for l in io.open(path, encoding='utf-8'):
        m = LINE.match(l.rstrip())
        if m:
            out[int(m.group(2), 16)] = (m.group(1), m.group(3).strip(),
                                        (m.group(4) or '').strip())
    return out


def labels(path):
    return {m.group(1) for m in
            (LABEL.match(l) for l in io.open(path, encoding='utf-8')) if m}


def main(report, path):
    code, known = listing(path), labels(path)
    lines = io.open(report, encoding='utf-8').read().split('\n')
    if '=== NOTES ===' in lines:
        lines = lines[:lines.index('=== NOTES ===')]

    tally = {'C': 0, 'P': 0, 'G': 0, '?': 0}
    bad_addr, bad_label, docs = [], [], []
    for l in lines:
        m = DOC.match(l.strip())
        if m:
            docs.append(m.group(1))
            tally[(m.group(2) or '[?]')[1]] += 1
            if m.group(1) not in known:
                bad_label.append(m.group(1))
            continue
        m = ENTRY.match(l.strip())
        if not m:
            continue
        a = int(m.group(1), 16)
        tally[(m.group(3) or '[?]')[1]] += 1
        if a not in code:
            bad_addr.append(m.group(1))
            print('&%04X  ** NO SUCH INSTRUCTION **  %s' % (a, m.group(2)))
            continue
        ins, by, was = code[a]
        print('&%04X  %-34s %-14s %s' % (a, ins, by, m.group(3) or '[?]'))
        if m.group(2):
            print('       claim: %s' % m.group(2))
        if was:
            print('       there: %s' % was)
        print()

    n = sum(tally.values())
    print('=' * 66)
    print('%d entries: %d certain, %d probable, %d guess, %d unmarked'
          % (n, tally['C'], tally['P'], tally['G'], tally['?']))
    if docs:
        print('%d DOC headers: %s' % (len(docs), ', '.join(docs)))
    if bad_addr:
        print('%d addresses that are not an instruction: %s'
              % (len(bad_addr), ', '.join(bad_addr)))
    if bad_label:
        print('%d labels that do not exist: %s'
              % (len(bad_label), ', '.join(bad_label)))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1],
         sys.argv[2] if len(sys.argv) > 2 else DEFAULT_LISTING)
