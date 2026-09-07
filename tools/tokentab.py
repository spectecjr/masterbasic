# -*- coding: utf-8 -*-
"""Read the token tables out of the SAM ROM source and print them.

The names are not typed in here.  `KEYWTAB` in ref/samrom/text.asm holds
the ROM's three function lists and four command sub-lists as runs of
characters with bit 7 set on the last one of each word, and tprint.asm's
`PRGR802` and `PSTFF2` give the token each list entry carries.  This
reproduces that mapping, adds the words MasterDOS and MasterBASIC graft on
through `MTOKV`, and prints one line per token:

    &FF3B  function  PI          ROM
    &BB    command   PRINT       ROM
    &FF2E  function  SVAL$       MasterBASIC

    python tools/tokentab.py            # the flat list
    python tools/tokentab.py --md       # the same as markdown tables

docs/tokens.md is written from this, and docs/sam-basic-grammar.txt
carries the same list in its TOKENS section.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT = os.path.join(ROOT, 'ref', 'samrom', 'text.asm')

# tprint.asm: SUB PITOK / CP SINTOK-PITOK / SUB MODTOK-PITOK, and PRGR802's
# four command sub-lists.  Each entry is (label, first token, how many words).
FN_LISTS = (('IMFNTL', 0x3B, 0x53 - 0x3B),
            ('FPCFNTL', 0x53, 0x7A - 0x53),
            ('BINFNTL', 0x7A, 0x0B))
CMD_LISTS = (('KWDS85', 0x85, 0x1B), ('KWDSA0', 0xA0, 0x20),
             ('KWDSC0', 0xC0, 0x20), ('KWDSE0', 0xE0, 0x1F))

# MBKEYS, the 28 names MasterBASIC's HGTTK matches, in the order that gives
# them their tokens -- index 1-19 become &26-&38, indices 20 and 21 land on
# the ROM's two spare FPC slots, and 22-28 become the single-byte 247-253.
# Seven of the names are MasterDOS's own and keep the tokens it gave them.
MBKEYS = ('EXIT PROC', 'EXIT DO', 'EXIT FOR', 'LOCN', 'RESERVED', 'EQU',
          'TICS', 'SHIFT$', 'SVAL$', 'USING$', 'TIME$', 'DATE$', 'INP$',
          'DIR$', 'FSTAT', 'DSTAT', 'FPAGES', 'SCRAD', 'INARRAY', 'XVAR',
          'NVAL', 'BACKUP', 'TIME', 'DATE', 'ALTER', 'SORT', 'JOIN', 'EDIT')
# The seven MasterDOS supplies on its own, with no MasterBASIC present,
# plus the three commands it already had.
FROM_DOS = {'TIME$', 'DATE$', 'INP$', 'DIR$', 'FSTAT', 'DSTAT', 'FPAGES',
            'BACKUP', 'TIME', 'DATE'}

# What a token does, which is not always what its shape suggests.  &85-&8F
# are the qualifiers -- words that only ever appear inside another
# statement -- except that WRITE is a MasterDOS statement and LINE a
# MasterBASIC one.  MasterBASIC's three EXIT words are statements wearing
# two-byte function tokens, because that is where HGTTK's arithmetic put
# them.  &FF76 and &FF7A-&FF83 are operators, and eval.asm's OPPRIORT and
# FNPRIORT give them priorities the other functions do not have.
STATEMENT_QUALIFIERS = {0x86, 0x8C}
OPERATORS = {0xFF76} | set(range(0xFF7A, 0xFF84))
EXIT_WORDS = {0xFF26, 0xFF27, 0xFF28}


def role(tok):
    if tok in OPERATORS:
        return 'operator'
    if tok in EXIT_WORDS:
        return 'statement'
    if tok < 0x100:
        if 0x85 <= tok <= 0x8F and tok not in STATEMENT_QUALIFIERS:
            return 'qualifier'
        return 'statement'
    return 'function'


def mb_token(index):
    """HGTTK's arithmetic, from MasterBASIC &4FE5 onwards.  One-based."""
    if index >= 22:
        return index + 0xA6 + 0x3B, 'command'   # its + &A6, the ROM's + &3B
    if index <= 19:
        return 0xFF00 | (index + 0x25), 'function'
    return (0xFF68, 0xFF6A)[index - 20], 'function'


def read_lists():
    """Every word of KEYWTAB, keyed by the label that starts its list."""
    src = open(TEXT, errors='replace').read().split('\n')
    out, label, word = {}, None, ''
    for line in src:
        m = re.match(r'^([A-Z0-9_]+):', line)
        if m and m.group(1) in ('KEYWTAB', 'IMFNTL', 'FPCFNTL', 'BINFNTL',
                                'KWDS85', 'KWDSA0', 'KWDSC0', 'KWDSE0'):
            label = m.group(1)
            out.setdefault(label, [])
        if label is None:
            continue
        # DM "PRIN" builds the word up;  DB "T"+&80 ends it.
        for op, text in re.findall(r'\b(DM|DB)\s+"((?:[^"]|"")*)"', line):
            if '+&80' in line.split('"')[-1] or op == 'DB' and '&80' in line:
                out[label].append(word + text)
                word = ''
            else:
                word += text
    return out


def tokens():
    """(token, kind, name, origin) for every token, in token order."""
    words = read_lists()
    # KEYWTAB's own DB &A0 is a count byte, not a word; IMFNTL follows it.
    rows = []
    for label, base, n in FN_LISTS:
        for i, w in enumerate(words[label][:n]):
            rows.append((0xFF00 | (base + i), 'function', w, 'ROM'))
    for label, base, n in CMD_LISTS:
        for i, w in enumerate(words[label][:n]):
            rows.append((base + i, 'command', w, 'ROM'))
    taken = {t for t, _, _, _ in rows if t != 0xFFFF}
    for i, name in enumerate(MBKEYS, 1):
        tok, kind = mb_token(i)
        origin = 'MasterDOS' if name in FROM_DOS else 'MasterBASIC'
        rows.append((tok, kind, name, origin))
    # A MasterBASIC word that lands on a ROM slot replaces the ROM's "-".
    seen, out = {}, []
    for row in sorted(rows):
        if row[0] in seen and seen[row[0]][3] == 'ROM':
            out[out.index(seen[row[0]])] = row
        elif row[0] not in seen:
            out.append(row)
        seen[row[0]] = row
    return [r for r in out if r[2] != '-'], taken


def spacing(tok, origin):
    """The spaces LIST puts round the word.  POGEN2, tprint.asm.

    'both' is a leading and a trailing space, 'lead' only the leading one,
    'trail' only the trailing, 'none' neither.  A leading space is further
    suppressed when the last character printed was already one (FLAGS bit
    0), and a trailing one when the word does not end in a letter or `$`
    -- which only ever excludes `<>`, `<=` and `>=`, and those are 'none'
    anyway.
    """
    if origin != 'ROM':
        return 'both' if tok < 0x100 else 'lead'   # HPRTOK, MasterBASIC &500E
    if tok < 0x100:
        return 'both'
    low = tok & 0xFF
    if low <= 0x52:
        return 'trail' if low in (0x42, 0x43) else 'none'   # FN and BIN
    if low <= 0x79:
        return 'trail'
    return 'both' if low <= 0x80 else 'none'


def spell(tok):
    return '&%02X' % tok if tok < 0x100 else '&FF %02X' % (tok & 0xFF)


def main():
    rows, _ = tokens()
    if '--md' in sys.argv:
        for kind in ('command', 'function'):
            print('| Token | Dec | Keyword | Role | From |')
            print('|---|--:|---|---|---|')
            for tok, k, name, origin in rows:
                if k == kind:
                    print('| `%s` | %d | `%s` | %s | %s |'
                          % (spell(tok), tok & 0xFF, name, role(tok), origin))
            print()
    elif '--grammar' in sys.argv:
        print('# token | role | name | origin | list-spacing')
        for tok, kind, name, origin in rows:
            print('%s|%s|%s|%s|%s'
                  % ('%02X' % tok if tok < 0x100 else '%04X' % tok,
                     role(tok), name, origin, spacing(tok, origin)))
    else:
        for tok, kind, name, origin in rows:
            print('%-8s %-10s %-11s %s'
                  % (spell(tok), role(tok), name, origin))


if __name__ == '__main__':
    main()
