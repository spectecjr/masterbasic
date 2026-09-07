"""base.asm -- the two halves of the image in one assembly.

Each half is assembled at &4000, because that is where it runs and where
its own labels have to land, and each is DUMPed to a page of its own so
that the two do not overlap in the output.  pyz80 keeps ORG and DUMP
apart for exactly this.  The 64 bytes between them, from &7FC0 to &7FFF,
are not padding anyone writes: a half is 16320 bytes and a page is
16384, so the gap is what the second DUMP leaves behind.

Two things follow from the halves meeting in one assembly.

The equates they share can be said once.  Fifty-eight names were
declared twice, identically, because neither file could see the other.
Four families join them whichever half declares them -- see
SHARED_FAMILIES in dis_mb.py -- because a hook code, an error code, a
BASIC token and a skip idiom are facts about the machine rather than
about the half that happens to use one.

And the equates that bridge between them stop being numbers.
`DOS_BOOT: EQU &8009` is a literal that nothing checks; written as
`BOOT + IN_PAGE_C` it is a reference the assembler resolves, so a
routine that moves takes its peer equate with it instead of leaving a
stale address behind.  That is the point of the file.
"""

import re

# NAME: EQU value ; comment -- as header() in dis_mb.py emits it, before
# asmfmt has laid the columns out.
# The value is everything up to a comment, not one token: base.asm
# writes peer equates as `LABEL + IN_PAGE_C`, and a pattern that
# stopped at the first space matched none of them -- which made the
# pruner below see an empty file and drop nothing.
EQU = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):\s+EQU\s+([^;]+?)\s*(?:;\s?(.*))?$')
ORG = re.compile(r'^\s*ORG\b')
# The heading above the peer block, which base.asm replaces wholesale.
PEER_HEAD = '; Addresses in the other page'


def split_at_org(text):
    """(everything above the ORG line, the ORG line and everything after)."""
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if ORG.match(line):
            return lines[:i], lines[i:]
    raise SystemExit('basefile: no ORG in a listing')


def blocks(head):
    """The header as [(heading lines, [(name, value, comment, line)])].

    A heading is the run of `;` lines above a group of equates.  Prose
    that belongs to nothing -- the title block, the UNPLACED note -- has
    an empty equate list and is carried through untouched.
    """
    out, pending, equates = [], [], []
    for line in head:
        m = EQU.match(line)
        if m:
            equates.append((m.group(1), m.group(2), m.group(3) or '', line))
            continue
        if equates:                       # the group has ended
            out.append((pending, equates))
            pending, equates = [], []
        pending.append(line)
    out.append((pending, equates))
    return out


def number(written):
    """The value of an equate as written, or None if it is an expression."""
    w = written.strip()
    if w.startswith('&'):
        try:
            return int(w[1:], 16)
        except ValueError:
            return None
    return int(w) if w.isdigit() else None


def shared(dos_head, mb_head):
    """(names both halves declare with one value, notes about the spelling).

    Compared as numbers rather than as text, so that PRINT_A -- &0010 in
    MasterDOS's ROM-entry group and &10 in MasterBASIC's restart group,
    the same address either way -- is hoisted rather than left declared
    twice.  MasterDOS's spelling is the one base.asm keeps, and the
    difference is reported so that a real disagreement could not hide
    among them.  A name whose values genuinely differ is not shared at
    all: it is returned in `clash` and left where it is.
    """
    def table(head):
        return {n: (v, c) for blk in blocks(head) for n, v, c, _ in blk[1]}
    a, b = table(dos_head), table(mb_head)
    same, spelling, clash = set(), [], []
    for n in sorted(set(a) & set(b)):
        av, bv = a[n][0], b[n][0]
        if av == bv:
            same.add(n)
        elif number(av) is not None and number(av) == number(bv):
            same.add(n)
            spelling.append('%s: %s here, %s in the other half' % (n, av, bv))
        else:
            clash.append('%s: %s against %s' % (n, av, bv))
    return same, spelling, clash


def strip(head, names):
    """Drop those equates, and any heading left describing nothing."""
    out = []
    for heading, equates in blocks(head):
        kept = [line for n, _v, _c, line in equates if n not in names]
        if equates and not kept:
            # The whole group has gone, so its heading describes nothing.
            # Only its OWN heading, mind: blocks() hands over everything
            # since the last group, and for the first group that is the
            # file's title.  Dropping all of it took the title with it.
            own = own_heading(heading)
            heading = heading[:len(heading) - len(own)]
        out.extend(heading)
        out.extend(kept)
    return out


def peer_equates(d, peer, bias):
    """The peer block, written as references instead of numbers.

    `used_peer` holds the windowed address -- the peer's label plus the
    16K between the two views -- and the peer's own label table says what
    is at it.  One name does not match: MB_HK_SKIPNAME's address is
    labelled CMD_DELETE in MasterBASIC's listing, because the peer names
    come from the label table and not from the emitted text.  Taking the
    label back out of that same table is what keeps the two agreeing.
    """
    out, unresolved = [], []
    for name in sorted(d.used_peer):
        addr = d.used_peer[name] - 0x8000 + 0x4000
        label = peer.labels.get(addr)
        if label:
            out.append('%-14s EQU  %s + %s' % (name + ':', label, bias))
        else:
            out.append('%-14s EQU  %s' % (name + ':', '&%04X' % d.used_peer[name]))
            unresolved.append(name)
    return out, unresolved


def own_heading(heading):
    """The comment lines belonging to the group below, and no more.

    `blocks` hands over everything since the previous group, which for
    the first group is the whole title preamble.  A group's own heading
    is the unbroken run of `;` lines at the end of that -- anything above
    the last blank line belongs to the file, not to these equates.
    """
    out = []
    for line in reversed(heading):
        if not line.lstrip().startswith(';'):
            break
        out.append(line)
    return list(reversed(out))


def equ_lines(head):
    """name -> the line declaring it."""
    out = {}
    for line in head:
        m = EQU.match(line)
        if m:
            out[m.group(1)] = line
    return out


def take_homed(pairs, names):
    """Those equates, under one copy of each heading, in one order.

    `pairs` is (header lines, that half's equ_home) for each half, in
    the order the groups should come out.  header() records where it
    wrote each equate, so a family scattered over both halves -- the
    error codes are half in one and half in the other -- comes back as
    one list under one heading, sorted by the key its own group used:
    the codes by value, everything else by name.

    The first half to declare a name is the one whose spelling is kept,
    which is what shared() promises.
    """
    groups, order, placed = {}, [], set()
    for head, homes in pairs:
        found = [(homes[n][0], homes[n][1], homes[n][2], n, line)
                 for n, line in equ_lines(head).items()
                 if n in names and n in homes]
        for _seq, heading, key, name, line in sorted(found, key=lambda t: t[0]):
            # Once, under the first heading that claims it.  A name the
            # two halves group differently -- PAGE_VALUE_MASK is under
            # "Memory" in the DOS, where a notes/clean GROUP put it, and
            # ungrouped in MasterBASIC, which only uses it -- would
            # otherwise be declared twice in the one file.  pyz80 accepts
            # that while the values agree, so the build cannot see it.
            if name in placed:
                continue
            placed.add(name)
            if heading not in groups:
                groups[heading] = {}
                order.append(heading)
            groups[heading].setdefault(key, line)
    out = []
    for heading in order:
        if out:
            out.append('')
        out.extend(heading)
        out.extend(line for _k, line in sorted(groups[heading].items()))
    return out


def take(head, names):
    """The groups holding those equates, with their headings, in order.

    Only the `;` lines of a heading are carried across -- the blank runs
    that separate groups in the half are put back here, so the block
    reads the same whichever half it was lifted from.
    """
    out = []
    for heading, equates in blocks(head):
        kept = [line for n, _v, _c, line in equates if n in names]
        if not kept:
            continue
        if out:
            out.append('')
        out.extend(own_heading(heading))
        out.extend(kept)
    return out


def prune(base_lines, halves):
    """Drop base.asm equates that nothing in the three files refers to.

    prune_equates() in dis_mb.py works on one finished file, so it cannot
    see that an equate declared here is used over in a half -- and the
    peer block is built from used_peer, which holds every name the pass
    ever asked for rather than only the ones that survived.  Left alone
    base.asm declares about thirty names nothing mentions.

    A name counts as used if it appears anywhere in either half, or in
    the value of another equate here: DOS_BOOT is EQU BOOT + IN_PAGE_C,
    so keeping it keeps IN_PAGE_C.
    """
    seen = set()
    for text in halves:
        for line in text.split('\n'):
            if line.lstrip().startswith(';'):
                continue
            code = re.split(r'\s;\s', line, maxsplit=1)[0]
            m = EQU.match(code.strip())
            if m:                      # a declaration is not a use of itself
                code = code.split('EQU', 1)[1]
            seen.update(re.findall(r'[A-Za-z_][A-Za-z0-9_]*', code))
    # Two passes, because one equate here may be the only user of another.
    keep, changed = list(base_lines), True
    while changed:
        changed = False
        used = set(seen)
        for line in keep:
            m = EQU.match(line.strip())
            if m:
                used.update(re.findall(r'[A-Za-z_][A-Za-z0-9_]*', m.group(2)))
        out = []
        for line in keep:
            m = EQU.match(line.strip())
            if m and m.group(1) not in used:
                changed = True
                continue
            out.append(line)
        keep = out
    dropped = sum(1 for l in base_lines if EQU.match(l.strip())) - \
        sum(1 for l in keep if EQU.match(l.strip()))
    return keep, dropped
