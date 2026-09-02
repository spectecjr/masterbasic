# -*- coding: utf-8 -*-
"""Lay a finished listing out to the rules in design/listingformats.md.

Whitespace only.  Nothing here may change a mnemonic, an operand or the
text of a comment -- only where on the line they sit, and where a comment
is broken -- and the build proves it: a reformatted listing that no longer
reassembles byte for byte would mean this got something wrong.

The rules:

  * lines are at most WIDTH characters, comments wrapping onto lines of
    their own rather than running past it;
  * within a block -- a run of lines with nothing blank between them --
    inline comments start at one column, far enough right to clear the
    longest instruction in the block and never left of HOME, so the
    listing keeps the column it has almost everywhere;
  * a wrapped comment continues at its own column where that leaves room
    to say anything, and otherwise slips left to the opcode column, which
    is as far left as it may go;
  * every EQU in the file shares a column, clearing the longest label
    there is -- the equate section reads as one thing even though comment
    headings divide it into groups, so aligning each group on its own
    would leave several columns in view;
  * a `;;` banner has a blank line above and below it.
"""

import re

WIDTH = 120          # the longest line to emit
HOME = 47            # where inline comments sit unless something is too long
OPCODE = 15          # the column instructions start at
LIMIT = 96           # past this an instruction gets its comment on its own line
ROOM = 24            # a comment narrower than this is not worth starting

BODY = re.compile(r'^\s{10,}\S')
# The value runs to the comment, not to the first space: an equate may be
# an expression of other equates, and DISK_STATUS_BUSY | LOST_DATA | CRC
# says more than the &0D it comes to.
EQU = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*:)\s+(EQU\s+[^;]*?)\s*((?:\s;.*)?)$')
BANNER = re.compile(r'^;;')


def split_comment(line):
    """(body, comment) with the comment's leading ';', quotes respected."""
    quoted = False
    for i, c in enumerate(line):
        if c == '"':
            quoted = not quoted
        elif c == ';' and not quoted:
            return line[:i].rstrip(), line[i:].rstrip()
    return line.rstrip(), ''


# `; 7DF0 CD 84 4A  the installer saves...` -- the address and the bytes,
# then two spaces, then a note.  The gap is how the eye tells them apart,
# so the head travels as one word and keeps its double space.
HEAD = re.compile(r'^;\s*([0-9A-F]{4}(?:\s\S+)*?)\s\s+(\S.*)$')


def wrap(text, first, rest, width=WIDTH):
    """`text` as ';' comment lines, indented `first` then `rest`."""
    m = HEAD.match(text)
    if m:
        words = [m.group(1) + ' '] + m.group(2).split()
    else:
        words = text.lstrip(';').split()
    if not words:
        return [' ' * first + ';']
    out, cur, indent = [], [], first
    for wd in words:
        if cur and indent + 2 + len(' '.join(cur + [wd])) > width:
            out.append(' ' * indent + '; ' + ' '.join(cur))
            cur, indent = [wd], rest
        else:
            cur.append(wd)
    out.append(' ' * indent + '; ' + ' '.join(cur))
    return out


def wrap_banner(line):
    """A `;;` banner line, kept as one: its marker and its indent survive."""
    m = re.match(r'^(;;\s*)(\S.*)$', line)
    if not m or len(line) <= WIDTH:
        return [line]
    lead, text = m.group(1), m.group(2)
    out, cur = [], []
    for wd in text.split():
        if cur and len(lead) + len(' '.join(cur + [wd])) > WIDTH:
            out.append(lead + ' '.join(cur))
            cur = [wd]
        else:
            cur.append(wd)
    out.append(lead + ' '.join(cur))
    return out


def lay_out(body, comment, col, cont):
    """One line: body, then its comment at `col`, wrapping at `cont`."""
    if not comment:
        return [body]
    if len(body) < col:
        head = body.ljust(col) + comment
        if len(head) <= WIDTH:
            return [head]
        rest = wrap(comment, col, cont)
        return [body.ljust(col) + rest[0].lstrip()] + rest[1:]
    return [body] + wrap(comment, col, cont)


def column(widest):
    """Where comments go, and where a wrapped one continues."""
    col = max(HOME, min(LIMIT, widest + 1))
    return col, (col if WIDTH - col >= ROOM else OPCODE)


def format_block(lines):
    """One run of instruction lines, sharing a comment column."""
    parts = [split_comment(l) for l in lines]
    col, cont = column(max((len(b) for b, c in parts if c), default=0))
    out = []
    for body, comment in parts:
        out.extend(lay_out(body, comment, col, cont))
    return out


def equate_columns(src):
    """The one EQU column and comment column for the whole file."""
    m = [EQU.match(l.rstrip()) for l in src]
    real = [x for x in m if x]
    if not real:
        return None, None, None
    at = max(max(len(x.group(1)) for x in real) + 1, OPCODE)
    wide = [at + len(x.group(2)) for x in real]
    # One long value -- an equate written as an expression of the others,
    # which is the point of writing it that way -- must not drag every
    # description in the file across the page after it.  The column is
    # set by the equates that fit, and a longer one takes its comment on
    # the next line, which is the rule instructions already follow.
    col, cont = column(max([w for w in wide if w <= LIMIT] or wide))
    return at, col, cont


def format_listing(text):
    src = text.split('\n')
    at, ecol, econt = equate_columns(src)
    out, i = [], 0
    while i < len(src):
        line = src[i].rstrip()
        if not line:
            out.append('')
            i += 1
            continue
        if BANNER.match(line):                      # a section banner
            j = i
            while j < len(src) and BANNER.match(src[j].rstrip()):
                j += 1
            if out and out[-1]:
                out.append('')
            for b in src[i:j]:
                out.extend(wrap_banner(b.rstrip()))
            if j < len(src) and src[j].strip():
                out.append('')
            i = j
            continue
        m = EQU.match(line)
        if m and at is not None:                    # an equate, anywhere
            body = m.group(1).ljust(at) + m.group(2)
            out.extend(lay_out(body, split_comment(m.group(3))[1], ecol, econt))
            i += 1
            continue
        if line.startswith(';'):                    # a cross-reference head
            out.extend([line] if len(line) <= WIDTH else wrap(line, 0, 0))
            i += 1
            continue
        if BODY.match(line):                        # a block of instructions
            j = i
            while j < len(src) and BODY.match(src[j].rstrip()):
                j += 1
            out.extend(format_block([s.rstrip() for s in src[i:j]]))
            i = j
            continue
        out.append(line)                            # a label, ORG, anything else
        i += 1
    return '\n'.join(out)
