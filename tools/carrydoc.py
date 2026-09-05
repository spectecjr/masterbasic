"""Carry the annotated MasterDOS 2.3 source's commentary into the listing.

ref/masterdos/annotated-src/masterdos23.asm is a documented copy of the
DOS that assembles byte for byte to res/MDOS23.bin.  The DOS half of the
combined image is that same DOS with MasterBASIC's material spliced in,
so most of it is the same code at shifted addresses -- and the annotated
source's routine headers and line comments apply to it unchanged.

The problem is knowing where they still apply.  A comment carried onto a
routine MasterBASIC rewrote would be worse than no comment at all, so
nothing is carried on faith: every line is placed by matching the two
instruction streams against each other, and where they diverge the
commentary stops.  The divergences are themselves the interesting part --
they are exactly the places the two products were welded together -- so
they are reported rather than hidden.

Three passes build the map:

  1. xfer's label anchors give a coarse correspondence, one every
     eighteen bytes or so.
  2. Between two anchors the two instruction sequences are aligned:
     first by walking them in lockstep from the anchor, then by diffing
     them, so that a routine which matches at both ends but not in the
     middle still contributes both ends.
  3. Where a span did not shift at all, the remaining addresses are
     paired by their offset, which picks up tables and message text that
     do not decode as instructions.

An instruction matches only up to its operands: an absolute address in
the combined image is nearly always different, and a relative jump's
displacement changes whenever anything was inserted between.
"""

import bisect
import difflib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xfer
from disasm import CONT
from z80 import Decoder

LOW, HIGH = 0x4000, 0xC000

# A routine whose body barely matches is not the same routine any more.
MIN_MATCH = 0.8
MIN_BODY = 4                    # below this a ratio means nothing


def shape(dec, mem, base, a):
    """An instruction's bytes with the operands that had to change blanked."""
    i = dec.decode(a)
    if i is None:
        return None
    r = bytearray(mem[a - base:a - base + i.length])
    if i.text.startswith(('JR', 'DJNZ')) and i.length >= 2:
        r[-1] = 0
    elif i.target is not None and i.length >= 3 and LOW <= i.target < HIGH:
        r[-1] = r[-2] = 0
    return bytes(r)


def align(dos, tgt, mdos, mapfile, lstfile):
    """Map MasterDOS addresses to the addresses they occupy here."""
    found, ambiguous, _ = xfer.carry(tgt, 0x4000, mdos, 0x4009, mapfile, lstfile)
    found, _ = xfer.monotone_filter(found)
    xfer.resolve(found, ambiguous, tgt, 0x4000, mdos, 0x4009, mapfile, lstfile)
    found, _ = xfer.monotone_filter(found)

    dec = Decoder(mdos, 0x4009)
    src_starts = sorted(set(xfer.line_addresses(lstfile)))
    tgt_starts = sorted(dos.insns)
    anchors = sorted((a, v[0]) for a, v in found.items())

    pairs = {}

    def put(a, t):
        # A source address that two passes place differently is placed by
        # neither: the disagreement is the whole reason to distrust it.
        pairs[a] = t if pairs.get(a, t) == t else None

    for k, (a, t) in enumerate(anchors):
        astop = anchors[k + 1][0] if k + 1 < len(anchors) else 0x4009 + len(mdos)
        tstop = anchors[k + 1][1] if k + 1 < len(anchors) else 0x4000 + len(tgt)

        x, y = a, t
        while x < astop and y < tstop:
            ia, ib = dec.decode(x), dos.insns.get(y)
            if ia is None or ib is None:
                break
            if shape(dec, mdos, 0x4009, x) != shape(dos, tgt, 0x4000, y):
                break
            put(x, y)
            x, y = ia.end, ib.end

        srcs = [q for q in src_starts if a <= q < astop]
        tgts = tgt_starts[bisect.bisect_left(tgt_starts, t):
                          bisect.bisect_left(tgt_starts, tstop)]
        sa = [shape(dec, mdos, 0x4009, q) for q in srcs]
        sb = [shape(dos, tgt, 0x4000, q) for q in tgts]
        matcher = difflib.SequenceMatcher(None, sa, sb, autojunk=False)
        for i, j, n in matcher.get_matching_blocks():
            for q in range(n):
                put(srcs[i + q], tgts[j + q])

        if astop - a == tstop - t:
            d = a - t
            for q in srcs:
                if q - d < tstop and mdos[q - 0x4009] == tgt[q - d - 0x4000]:
                    put(q, q - d)

    return dict((a, t) for a, t in pairs.items() if t is not None), found


# -- reading the annotated source -----------------------------------------

LABEL = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):')
ADDR = re.compile(r'^([0-9A-Fa-f]{4}) ')
RULE = re.compile(r'^;\s*[-=]{10,}\s*$')


def split_comment(line):
    """Split a source line into code and comment, respecting quotes."""
    quoted = False
    for i, c in enumerate(line):
        if c == '"':
            quoted = not quoted
        elif c == ';' and not quoted:
            return line[:i], line[i + 1:]
    return line, None


def listing_offset(asm, lst, window=400, limit=4):
    """How many lines pyz80's listing runs ahead of the source.

    It is one -- the listing opens with a blank line the source does not
    have -- but taking it on trust would put every comment on the
    instruction before the one it belongs to, which is exactly the kind
    of error that reads as plausible.  So it is measured.
    """
    best, score = 0, -1
    for off in range(limit):
        n = 0
        for i, line in enumerate(asm[:window]):
            text = line.strip()
            if not text or i + off >= len(lst):
                continue
            if lst[i + off].split('\t', 1)[-1].strip() == text:
                n += 1
        if n > score:
            best, score = off, n
    return best


def read_source(asmfile, lstfile):
    """Line comments, header blocks and section banners, keyed by address.

    The listing pyz80 writes has one line per source line, so the address
    a line assembled to is simply the listing line with the same number.
    """
    asm = open(asmfile, encoding='latin-1').read().split('\n')
    lst = open(lstfile, encoding='latin-1').read().split('\n')
    off = listing_offset(asm, lst)
    addr_of = {}
    for i, line in enumerate(lst):
        m = ADDR.match(line)
        if m:
            addr_of[i - off] = int(m.group(1), 16)

    trailing, headers, rules = {}, {}, []
    for i, line in enumerate(asm):
        code, comment = split_comment(line)
        if comment is None:
            continue
        if code.strip():
            a = addr_of.get(i)
            if a is not None and comment.strip():
                trailing.setdefault(a, comment.strip())
        elif RULE.match(line.strip()) and '=' in line:
            rules.append(i)

    label_line = {}
    for i, line in enumerate(asm):
        m = LABEL.match(line)
        if not m:
            continue
        label_line.setdefault(m.group(1), i)
        block = block_above(asm, i)
        if block:
            headers.setdefault(m.group(1), block)
    return trailing, headers, sections(asm, rules, addr_of), label_line


DIRECTIVE = re.compile(r'^\s*(?:[A-Za-z_][A-Za-z0-9_]*:)?\s*'
                       r'(DEF[BWMS]|DS|DB|DW)\b', re.I)


def data_lines(asmfile, lstfile):
    """The addresses the annotated source reserves rather than assembles.

    The DOS's variables sit inside the boot sector, and zero bytes decode
    as NOP, so the trace runs straight through them and the listing shows
    a variable block as a run of instructions.  The source says plainly
    which addresses those are.
    """
    asm = open(asmfile, encoding='latin-1').read().split('\n')
    lst = open(lstfile, encoding='latin-1').read().split('\n')
    off = listing_offset(asm, lst)
    out = set()
    for i, line in enumerate(asm):
        code, _ = split_comment(line)
        if not DIRECTIVE.match(code):
            continue
        j = i + off
        if j >= len(lst):
            continue
        m = ADDR.match(lst[j])
        if not m:
            continue
        start = int(m.group(1), 16)
        for k in range(j + 1, len(lst)):        # to the next address shown
            m2 = ADDR.match(lst[k])
            if m2:
                out.update(range(start, int(m2.group(1), 16)))
                break
    return out


def undo_code(dos, addrs, data_mark, zero_only=True):
    """Turn addresses the source calls data back into data.

    Only where nothing jumps or calls there: a byte that is both reached
    by the flow and declared as storage is a disagreement worth leaving
    visible rather than resolving silently.
    """
    reached = set()
    for ins in dos.insns.values():
        if ins.target is not None and ins.text.startswith(('CALL', 'JP ', 'JR ', 'DJNZ')):
            reached.add(ins.target)
    n = 0
    for a in sorted(addrs):
        ins = dos.insns.get(a)
        if ins is None or not dos.inside(a):
            continue
        if any(x in reached for x in range(a, ins.end)):
            continue
        if zero_only and not all(dos.byte(x) == 0 for x in range(a, ins.end)):
            continue                            # only the zero fill, to be safe
        dos.insns.pop(a)
        for x in range(a, ins.end):
            dos.setm(x, data_mark)
        n += ins.length
    return n


def clean(lines):
    """Drop the source's own rules and its commented-out code.

    banner() draws its own rules.  A leading star is the author's mark
    for a line of version 2.2 that 2.3 replaced -- code, not prose, and
    carrying it as a routine's description says the opposite of what it
    means.
    """
    out = [x.rstrip() for x in lines
           if not RULE.match(';' + x.strip()) and not x.strip().startswith('*')]
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    return out


def block_above(asm, i):
    """The run of whole-line comments above a label, blank lines included.

    The annotated source puts a ruled header above a routine and then, if
    the author had one there, his own comment, with a blank line between.
    Both belong to the routine, so both come across.
    """
    groups, j = [], i - 1
    while j >= 0:
        s = asm[j].strip()
        if not s:
            j -= 1
            continue
        if not s.startswith(';'):
            break
        run = []
        while j >= 0 and asm[j].strip().startswith(';'):
            run.append(asm[j].strip()[1:])
            j -= 1
        groups.append(list(reversed(run)))
    out = []
    for run in reversed(groups):          # the groups were collected upwards
        if out:
            out.append('')
        out.extend(run)
    text = clean(out)
    return text if len(text) >= 2 else None


def sections(asm, rules, addr_of):
    """The section banners, with the address each one heads."""
    out = []
    for i in rules:
        body, j = [], i + 1
        while j < len(asm) and asm[j].strip().startswith(';'):
            if RULE.match(asm[j].strip()):
                break
            body.append(asm[j].strip()[1:].rstrip())
            j += 1
        body = clean(body)
        if not body:
            continue
        heads = [addr_of[k] for k in range(i, min(i + 600, len(asm)))
                 if k in addr_of]
        if heads:
            out.append((heads, body))
    return out


# -- operands --------------------------------------------------------------

HEXLIT = re.compile(r'&[0-9A-Fa-f]+')
TOKEN = re.compile(r'[A-Za-z_][A-Za-z0-9_]*|&[0-9A-Fa-f]+|%[01]+|\d+|[-+]|.')
IDENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
SYNTHETIC = re.compile(r'^[LV][0-9A-Fa-f]{4}$')
REGISTER = set('A B C D E H L I R AF BC DE HL IX IY SP AF\' NZ Z NC C PO PE P M '
               'IXH IXL IYH IYL'.split())


def literal(tok):
    """The value of one numeric token, in any base the sources use."""
    if tok.startswith('&'):
        return int(tok[1:], 16)
    if tok.startswith('%'):
        return int(tok[1:], 2)
    if tok.isdigit():
        return int(tok)
    return None


def evaluate(expr, resolve):
    """Add and subtract, left to right, the way the Comet assembler does.

    Returns (value, names) or None if any token cannot be resolved.  Only
    the operand forms these sources actually use are handled: a name, a
    number, and a name with a small offset.
    """
    toks = TOKEN.findall(expr.replace(' ', ''))
    if not toks:
        return None
    value, sign, used, names, want = 0, 1, 0, [], True
    for tok in toks:
        if tok in '+-':
            if want:
                return None
            sign, want = (1 if tok == '+' else -1), True
            continue
        if not want:
            return None
        n = literal(tok)
        if n is None:
            if not IDENT.match(tok):
                return None
            got = resolve(tok)
            if got is None:
                return None
            n, name = got
            used += 1
            if name:                       # not one of our own labels
                names.append(name)
        value += sign * n
        want = False
    if want or not used:
        return None
    return value, names


def fields(operands):
    """An operand list split on the commas that separate its arguments."""
    out, depth, cur = [], 0, ''
    for c in operands:
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
        if c == ',' and depth == 0:
            out.append(cur)
            cur = ''
        else:
            cur += c
    out.append(cur)
    return out


def source_operands(line):
    """The operand text of a source line, or None if it has none."""
    code, _ = split_comment(line)
    code = re.sub(r'^\s*[A-Za-z_]\w*:', '', code).strip()
    parts = code.split(None, 1)
    if len(parts) < 2 or not IDENT.match(parts[0]):
        return None
    return parts[1].strip()


def carry_operands(dos, asmfile, lstfile, symfile, pairs, reserved):
    """Write the source's names where the listing prints bare hex.

    The disassembly can only name an address something in the image
    refers to; a constant like DRSEC, or a self-modified byte written as
    LDB6+1, comes out as a number.  The source has a name for both, and
    for an instruction that matched, that name is this instruction's.

    A name is used only when it evaluates to the number already there.
    That is the whole safety argument: the bytes cannot change, and a
    symbol whose value moved with the splice simply fails the test.
    """
    import romsyms
    values = {}
    for name, v in romsyms.load_pickle(symfile).items():
        if isinstance(v, int):
            values[name] = v

    asm = open(asmfile, encoding='latin-1').read().split('\n')
    lst = open(lstfile, encoding='latin-1').read().split('\n')
    off = listing_offset(asm, lst)
    addr_of = {}
    for i, line in enumerate(lst):
        m = ADDR.match(line)
        if m:
            addr_of[i - off] = int(m.group(1), 16)

    # Only labels the listing actually prints.  A label inside a rendered
    # table -- CTAB, one byte past the count byte the renderer starts at --
    # is in the label table but never reaches the output, so writing
    # CTAB-1 for &42EA would leave the symbol undefined.
    mine = {}
    for a, name in dos.labels.items():
        if any(lo < a < hi for lo, hi in dos.rendered):
            continue
        mine.setdefault(name, a)

    needed = {}

    def resolve(name):
        if name in REGISTER:
            return None
        if name in mine:                    # a label of ours: use our address
            return mine[name], None
        v = values.get(name)
        if v is None or name in reserved:
            return None
        # Both trees name a recovered address Lxxxx, and the two mean
        # different addresses.  Such a name says nothing anyway.
        if SYNTHETIC.match(name):
            return None
        return v, name

    named = 0
    for i, line in enumerate(asm):
        a = addr_of.get(i)
        if a is None or a not in pairs:
            continue
        ins = dos.insns.get(pairs[a])
        if ins is None or not ins.asm:
            continue
        theirs = source_operands(line)
        if theirs is None:
            continue
        ours = source_operands(ins.text)
        if ours is None:
            continue
        lhs, rhs = fields(ours), fields(theirs)
        if len(lhs) != len(rhs):
            continue
        out, hit = [], False
        for mine_f, their_f in zip(lhs, rhs):
            lits = HEXLIT.findall(mine_f)
            new = replace_field(mine_f, their_f, lits, resolve, needed)
            if new is not None:
                out.append(new)
                hit = True
            else:
                out.append(mine_f)
        if hit:
            dos.overrides[pairs[a]] = '%s %s' % (ins.text.split(None, 1)[0],
                                                 ','.join(out))
            named += 1
    # A name whose value is an address in this page is a label, not a
    # constant.  xfer could not place these -- they are the variables
    # MasterBASIC rearranged, matched by byte pattern and so unplaceable
    # -- but an instruction that agrees on the address is better evidence
    # than a byte pattern ever was, so the synthetic V4110 becomes DSC.
    taken = set(dos.labels.values())
    promoted = 0
    for name, value in sorted(needed.items()):
        if not dos.inside(value) or name in taken:
            continue
        if any(lo < value < hi for lo, hi in dos.rendered):
            continue
        if dos.m(value) == CONT:
            # Mid-instruction, so it would join the misalignment report
            # without being a misalignment.  An equate says the same thing.
            continue
        old = dos.labels.get(value)
        if old is not None and not SYNTHETIC.match(old):
            continue
        dos.labels[value] = name
        taken.add(name)
        taken.discard(old)
        del needed[name]
        promoted += 1
    dos.mdos_equs.update(needed)
    return named, len(needed), promoted


def replace_field(mine_f, their_f, lits, resolve, needed):
    """One operand, with its number swapped for the source's name."""
    if len(lits) != 1:
        return None
    inner_mine, inner_their = mine_f.strip(), their_f.strip()
    paren = inner_mine.startswith('(') and inner_their.startswith('(')
    if paren:
        inner_mine, inner_their = inner_mine[1:-1], inner_their[1:-1]
    elif inner_mine.startswith('(') or inner_their.startswith('('):
        return None
    got = evaluate(inner_their, resolve)
    if got is None:
        return None
    value, names = got
    want = literal(lits[0])
    width = 0xFF if len(lits[0]) <= 3 else 0xFFFF
    if value < 0 or value & width != want or value > width:
        return None
    text = inner_their.replace(' ', '')
    for name in names:
        needed[name] = resolve(name)[0]
    return '(%s)' % text if paren else mine_f.replace(lits[0], text)


# -- attaching it ----------------------------------------------------------

def routine_match(pairs, src_starts, start, stop):
    """How much of one routine's body survived into the combined image."""
    body = [a for a in src_starts if start <= a < stop]
    if not body:
        return 0, 0
    return sum(1 for a in body if a in pairs), len(body)


def apply(dos, work, root, banner, data_mark=None, data_region=None):
    """Put the annotated source's commentary on the DOS listing.

    Returns the counts of line comments, routine headers, section
    banners and reclaimed data bytes, and the routines that were skipped
    because MasterBASIC had changed them.
    """
    asmfile = os.path.join(root, 'ref', 'masterdos', 'annotated-src',
                           'masterdos23.asm')
    lstfile = os.path.join(work, 'mdos.lst')
    mapfile = os.path.join(work, 'mdos.map')
    mdos = open(os.path.join(root, 'ref', 'masterdos', 'res',
                             'MDOS23.bin'), 'rb').read()
    tgt = bytes(dos.mem)

    pairs, found = align(dos, tgt, mdos, mapfile, lstfile)
    trailing, headers, banners, label_line = read_source(asmfile, lstfile)
    src_starts = sorted(set(xfer.line_addresses(lstfile)))

    ndata = 0
    declared = data_lines(asmfile, lstfile)
    if data_mark is not None:
        # The source declaring an address as storage is evidence enough:
        # undo_code already refuses anything a CALL or JP reaches, so the
        # extra "only if the bytes are zero" guard was keeping tables
        # like MTBLS -- two words, a letter and three more words -- being
        # read as instructions.
        here = set(pairs[a] for a in declared if a in pairs)
        ndata = undo_code(dos, here, data_mark, zero_only=False)
        # Later passes re-run the trace, which claims some of these back
        # again, so the set is kept for a second application once the
        # tracing has finished.
        dos.declared_data = here
    for region in (data_region or ()):
        # The DOS's own variables and the DVAR block, which the trace ran
        # into because a run of zeroes decodes as NOPs and the rest looks
        # like plausible instructions.  Both are blocks MasterBASIC
        # rearranged, so the source cannot name them line by line -- but
        # it can still say that none of it is code.
        ndata += undo_code(dos, range(*region), data_mark, zero_only=False)
        # xfer matches labels by byte pattern, and a routine's opening
        # bytes can turn up by chance in a table of variables -- FFHL and
        # FFDE landed on the letters of "BOOT".  In a block that is all
        # storage, keep only the names that were storage in the source.
        for a, (t, name, _, _) in list(found.items()):
            if region[0] <= t < region[1] \
                    and a not in declared and dos.labels.get(t) == name:
                del dos.labels[t]

    ncom = 0
    for a, text in trailing.items():
        t = pairs.get(a)
        # A comment goes on an instruction or on the first byte of a
        # variable, but never in the middle of either.
        if t is None or t in dos.comments:
            continue
        if not dos._starts_insn(t) and dos.m(t) == CONT:
            continue
        dos.comments[t] = text
        ncom += 1

    # Where a label was carried, its routine header can come too -- but
    # only if the routine it heads is still the routine it describes.
    at = {}
    for a, v in found.items():
        at.setdefault(v[1], (a, v[0]))
    # How far does this routine reach?  Two answers, and the right one
    # is whichever comes first.  The matched labels say where the next
    # piece of recognisable code starts, but they are sparse -- GTVAL
    # was measured across forty-five instructions when GTVAL is eleven.
    # The source's own documented routines say where the next thing with
    # a description of its own starts, but between two of those there may
    # be undocumented helpers this header never claimed to cover.
    # Taking the nearer of the two can only narrow the window, so it
    # removes false positives without inventing any.
    src_labels = xfer.read_map(mapfile)
    documented = sorted(a for a, nm in src_labels.items() if nm in headers)
    # And a third bound: the next label of any kind in the source.  The
    # 1991 author put a label where a routine starts, so this is the
    # tightest honest end -- GETSCR is byte-identical to stock and was
    # still reported as changed, because PUTSCR carries no header and
    # the span ran on into it.  An internal loop label can cut a routine
    # short, which loses a verdict rather than inventing one; that is
    # the safe direction for a check whose job is to SUPPRESS a header.
    every = sorted(src_labels)
    starts = sorted(a for a, _ in at.values())
    nhdr, changed = 0, []
    for name, (a, t) in sorted(at.items(), key=lambda kv: kv[1][0]):
        block = headers.get(name)
        if not block:
            continue
        i = bisect.bisect_right(starts, a)
        stop = starts[i] if i < len(starts) else 0x4009 + len(mdos)
        j = bisect.bisect_right(documented, a)
        if j < len(documented):
            stop = min(stop, documented[j])
        k = bisect.bisect_right(every, a)
        if k < len(every):
            stop = min(stop, every[k])
        # Data is not instructions.  MRTAB is DEFS &20 in the source, and
        # comparing zero bytes decoded as instructions gave it 8 of 48 --
        # a number about nothing.  Count only what the source assembles.
        hit, tot = routine_match(pairs, [x for x in src_starts
                                         if x not in declared], a, stop)
        if tot >= MIN_BODY and hit < tot * MIN_MATCH:
            changed.append((name, t, hit, tot))
            # Say so in the listing: a description that may belong to
            # different code is worse than none, and the reader can
            # follow the citation and judge.
            if t in dos.labels and t not in dos.headers:
                dos.headers[t] = banner(
                    'Of the %d instructions between this label and the next'
                    ' routine the source documents, %d survive into this'
                    " image, so that source's description of %s has been left"
                    ' out rather than carried across.  Compare'
                    ' ref/masterdos/annotated-src/masterdos23.asm.'
                    % (tot, hit, name))
            continue
        if t in dos.headers or t not in dos.labels:
            continue
        dos.headers[t] = banner('\n'.join(block))
        nhdr += 1

    # A section banner heads whatever follows it; if the first thing there
    # did not survive the splice, the next thing that did will do.
    nsec = 0
    for heads, body in banners:
        for a in heads:
            t = pairs.get(a)
            if t is None or not dos._starts_insn(t):
                continue
            if t not in dos.headers:
                dos.headers[t] = banner('\n'.join(body))
                nsec += 1
            break

    reserved = set(dos.ports.values()) | set(dos.used_ext)         | set(dos.rst8.values()) | set(dos.basic_equs)
    nops, nequ, nprom = carry_operands(dos, asmfile, lstfile,
                                       os.path.join(work, 'mdos.sym'),
                                       pairs, reserved)
    return ncom, nhdr, nsec, ndata, nops, nequ, nprom, changed


def twins(page, work, root, banner):
    """Document the routines both halves carry a copy of.

    A handful of MasterDOS routines appear in the extension page too --
    the NR family that reaches the ROM's variables, and the byte and
    word primitives under it -- because both were assembled from the
    same source.  The global alignment cannot find them: the extension
    is not MasterDOS, so matching it wholesale produces more
    out-of-order matches than good ones.

    Anchoring on the name instead settles it.  Where a label here has
    the name of a MasterDOS routine *and* the two bodies agree
    instruction for instruction to the first return, it is that
    routine, and the annotated source's commentary applies to it.
    """
    asmfile = os.path.join(root, 'ref', 'masterdos', 'annotated-src',
                           'masterdos23.asm')
    lstfile = os.path.join(work, 'mdos.lst')
    mdos = open(os.path.join(root, 'ref', 'masterdos', 'res',
                             'MDOS23.bin'), 'rb').read()
    dec = Decoder(mdos, 0x4009)
    byname = dict((n, a) for a, n in
                  xfer.read_map(os.path.join(work, 'mdos.map')).items())
    trailing, headers, _, _ = read_source(asmfile, lstfile)
    here = bytes(page.mem)

    def walk(start, step, shape_of, limit=60):
        """The routine's instruction shapes, down to its first return."""
        out, p = [], start
        for _ in range(limit):
            s = shape_of(p)
            ins = step(p)
            if s is None or ins is None:
                return out, []
            out.append(s)
            if not ins.falls_through():
                return out, _addrs(start, step, len(out))
            p = ins.end
        return out, _addrs(start, step, len(out))

    def _addrs(start, step, n):
        out, p = [], start
        for _ in range(n):
            out.append(p)
            ins = step(p)
            if ins is None:
                break
            p = ins.end
        return out

    mine_shape = lambda p: (shape(page, here, 0x4000, p)
                            if page._starts_insn(p) else None)
    mine_step = lambda p: page.insns.get(p)
    theirs_shape = lambda p: (shape(dec, mdos, 0x4009, p)
                              if 0x4009 <= p < 0x4009 + len(mdos) else None)
    theirs_step = lambda p: dec.decode(p)

    ncom = nhdr = n = 0
    for a, name in sorted(page.labels.items()):
        src = byname.get(name)
        if src is None or not page._starts_insn(a):
            continue
        b1, a1 = walk(a, mine_step, mine_shape)
        b2, a2 = walk(src, theirs_step, theirs_shape)
        if len(b1) < 4 or b1 != b2:
            continue
        n += 1
        for at, sat in zip(a1, a2):
            text = trailing.get(sat)
            if text and at not in page.comments:
                page.comments[at] = text
                ncom += 1
        if a in page.headers:
            continue
        block = headers.get(name)
        if not block:
            # No description in the source either, but saying which
            # routine this is a copy of still tells a reader where to
            # go: the DOS listing has it with its own cross-references.
            block = ['%s -- the same routine as in the MasterDOS page.' % name,
                     '',
                     'Both halves were assembled from one source, so this is a',
                     'copy of MasterDOS &%04X instruction for instruction.'
                     % src,
                     'See masterdos.asm.']
        page.headers[a] = banner('\n'.join(block))
        nhdr += 1
    return n, ncom, nhdr


def describe_labels(page, work, root):
    """Give a carried label the description its own source line carries.

    The variable blocks are where the address alignment fails -- they are
    what MasterBASIC rearranged most -- so a comment like

        DCT:           DEFB 0    ; retry count for the sector in progress

    never reaches the listing by address, even though the *name* did.
    Anchoring on the name instead settles it: the label is only here
    because xfer matched it, so attaching what the source says about that
    same name adds no claim that was not already being made.
    """
    asmfile = os.path.join(root, 'ref', 'masterdos', 'annotated-src',
                           'masterdos23.asm')
    lstfile = os.path.join(work, 'mdos.lst')
    asm = open(asmfile, encoding='latin-1').read().split('\n')
    trailing, _headers, _sections, label_line = read_source(asmfile, lstfile)

    said = {}
    for name, i in label_line.items():
        code, comment = split_comment(asm[i])
        if comment and code.strip() and comment.strip():
            said[name] = comment.strip()

    n = 0
    for a, name in sorted(page.labels.items()):
        text = said.get(name)
        if not text or a in page.comments:
            continue
        # Only where the listing will print it: a comment on a byte in
        # the middle of an instruction goes nowhere.
        if page._starts_insn(a) or page.m(a) != CONT:
            page.comments[a] = text
            n += 1
    return n
