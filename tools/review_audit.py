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

And it says when a finding's "says:" quotes text the listing no longer
holds.  Two findings in round two were stale -- the region had been cut
before a rebuild -- and the agent noticed; this notices too.  A quote
that is not found is stale or paraphrased, and either way the claim
has to be read against what is there now rather than against the
report.

    python tools/review_audit.py <report.txt> [listing.asm]

Understood in the report (anywhere in it; everything else is ignored):

    DOS &4B31 : some claim about that instruction [C]
    DOC FDHR [P]
    &4B31  [C]           a review finding, whose claim is the "says:" line
    says:  "quoted from the listing, possibly over
            several indented lines"

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


def normalise(text):
    """Text as compared: one space between words, no quote characters.

    A listing comment wraps where the emitter wrapped it and the report
    quotes it re-wrapped, and the two use straight and curly quotes
    without agreement; neither difference is a difference in the claim.
    """
    return ' '.join(re.sub(r'[\'"\u2018\u2019\u201c\u201d]', '', text).split())


def prose(path):
    """Every comment in the listing, joined, in the form normalise() gives."""
    out = []
    for l in io.open(path, encoding='utf-8'):
        l = l.rstrip()
        if l.startswith(';'):
            out.append(l.lstrip(';').strip())
            continue
        m = LINE.match(l)
        if m:
            out.append(m.group(4) or '')
            continue
        m = re.match(r'^\s+; (.*)$', l)         # a wrapped comment's tail
        if m:
            out.append(m.group(1))
    return normalise(' '.join(out))


def quoted(block):
    """The claim a finding's says: lines quote, or None.

    The block is the lines after the address line up to the next
    finding.  The quote is what sits between the first and last double
    quote of the says: lines; without quotes, the whole says: text.
    """
    says = []
    for l in block:
        s = l.strip()
        if says and re.match(r'^(but|fix):', s):
            break
        if s.startswith('says:'):
            says.append(s[5:].strip())
        elif says:
            says.append(s)
    if not says:
        return None
    text = ' '.join(says)
    i, j = text.find('"'), text.rfind('"')
    if 0 <= i < j:
        text = text[i + 1:j]
    return text


def stale(claim, text):
    """True if the claim is not in the listing's prose.

    An ellipsis in the quote splits it; each piece long enough to mean
    something must be found.  A claim too short to check is not stale.
    """
    pieces = [normalise(p) for p in re.split(r'\.\.\.|\u2026', claim)]
    pieces = [p for p in pieces if len(p) >= 12]
    if not pieces:
        return False
    return not all(p in text for p in pieces)


def main(report, path):
    code, known, text = listing(path), labels(path), prose(path)
    lines = io.open(report, encoding='utf-8').read().split('\n')
    if '=== NOTES ===' in lines:
        lines = lines[:lines.index('=== NOTES ===')]

    # Where each finding starts, so that the lines after it -- says:,
    # but:, fix: -- can be read as its block.
    starts = [i for i, l in enumerate(lines)
              if DOC.match(l.strip()) or ENTRY.match(l.strip())]
    tally = {'C': 0, 'P': 0, 'G': 0, '?': 0}
    bad_addr, bad_label, docs, stale_at = [], [], [], []

    def check_quote(i, where):
        end = starts[starts.index(i) + 1] if starts.index(i) + 1 < len(starts) else len(lines)
        claim = quoted(lines[i + 1:end])
        if claim and stale(claim, text):
            stale_at.append(where)
            print('       ** says: quotes text that is not in the listing now '
                  '-- stale, or paraphrased **')

    for i in starts:
        l = lines[i]
        m = DOC.match(l.strip())
        if m:
            docs.append(m.group(1))
            tally[(m.group(2) or '[?]')[1]] += 1
            if m.group(1) not in known:
                bad_label.append(m.group(1))
            else:
                check_quote(i, 'DOC ' + m.group(1))
            continue
        m = ENTRY.match(l.strip())
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
        check_quote(i, '&%04X' % a)
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
    if stale_at:
        print('%d findings quote text the listing does not hold now: %s'
              % (len(stale_at), ', '.join(stale_at)))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1],
         sys.argv[2] if len(sys.argv) > 2 else DEFAULT_LISTING)
