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
# Every tree, because prose is written about all of them: notes/clean/
# describes the reading copy, docs/ quotes whichever makes the point, and
# a name defined in any of them is a name that exists.
#
# base.asm is here because the shared equates moved into it.  Without it
# IN_PAGE_C, SYSPAGE_IN_B, PRINT_A and every hook code read as names that
# no longer exist -- they are defined once now, in the file that includes
# the two halves rather than in either of them.
LISTINGS = tuple(
    'listings/%s/%s.asm' % (tree, part)
    for tree in ('disasm', 'clean', 'speculate')
    for part in ('masterdos', 'masterbasic', 'base', 'samhw', 'samrom')
) + ('listings/disasm/postinstall-syspage.asm',)

PROSE = ('docs', 'notes', 'design')

# The manual is a transcript of someone else's document, so its wording
# is not a claim about the listing and its capitals are not label names.
# exampledocs.md is exempt for the opposite reason: it opens "If I was
# going to document part of the masterdos.asm file, I might do it like
# this", so every name in it is a hypothetical and none was ever meant to
# be the listing's.
NOT_PROSE = ('masterbasic-manual.md', 'exampledocs.md')

# prose whose point is a name the listing no longer has, file by file
HISTORICAL = {
    # design/cleanstyle.md argues from names on purpose.  Its opening
    # table has a "before" column of what the working copy calls things;
    # its M2-M4 sections are the original proposals, in a syntax that did
    # not ship and using constants invented to illustrate it; and its
    # section 5 names four things the hand-written sketch got wrong, in
    # order to make the point that only a generator can hold a style
    # together.  None of these is a claim about the listing.
    ('design/cleanstyle.md', 'MAX_RAMDRIVE_PAGE_TYPE'),
    ('design/cleanstyle.md', 'DISK_STATUS_BUSY'),
    ('design/cleanstyle.md', 'DISK_SECTOR_READ_ERROR_FLAGS'),
    ('design/cleanstyle.md', 'V511F'),
    ('design/cleanstyle.md', 'DISK_READ_SECTOR_CMD'),
    ('design/cleanstyle.md', 'MAX_RETRY_COUNT'),
    ('design/cleanstyle.md', 'MAX_SECTOR_RETRY_COUNT'),
    ('design/cleanstyle.md', 'BOOT_FOUND_PAGE'),
    ('docs/disassembly.md', 'L1234'),     # an invented name, in an example
    ('docs/disassembly.md', 'L4461'),     # what CALL_NEXTCHAR was called
    ('docs/disassembly.md', 'L45D9'),     # what the address column reads
    ('docs/disassembly.md', 'L6016'),     # what CHECK_BREAK_LOOP2 was called
    ('docs/disassembly.md', 'V4110'),     # the name DSC would have had
    ('docs/disassembly.md', 'V4111'),     # the name DCT would have had
    ('notes/mb-vectors.txt', 'V589C'),    # a window address read as this page's
    ('notes/mb-filetypes.txt', 'L440A'),  # a label the false decode invented
    ('notes/mb-filetypes.txt', 'L4391'),  # the other one
    # Prose that says what something used to be called, and would say
    # nothing without the old name in it.
    ('notes/mb-helpers.txt', 'CALL_ROM_0010'),
    ('notes/mb-screencopy.txt', 'SCREEN_ADDRESS_FOR_MODE'),
    ('notes/mb-screencopy.txt', 'DOS_ITRCK'),
    ('notes/mb-lineentry.txt', 'CTAB_USING_S'),
    ('notes/mb-nrfamily.txt', 'NRWR_DONE'),
    ('notes/refparse.txt', 'STEP_BY_TABLE_ENTRY'),
    ('notes/slots.txt', 'CHECK_BREAK_2'),
    ('notes/mb-blanker.txt', 'DOS_L4073'),
    ('notes/mb-printerready.txt', 'DOS_FSTR1'),
    ('notes/mb-format.txt', 'WRITE_ENTRY_HEADER'),
    ('notes/joinsplit.txt', 'CMD_JOIN_FAIL'),
    ('notes/clean/dos-boot.txt', 'BOOT_17'),
    ('notes/clean/dos-boot.txt', 'BOOT_18'),
    ('notes/clean/dos-boot.txt', 'BOOT_20'),
    ('notes/clean/dos-boot.txt', 'BOOT_21'),
    # The nine names the boot's by-number renames used to carry, listed
    # in that note to say what is no longer there and where each had got
    # to.  Five were on addresses that were never entry points, three on
    # real code they did not describe, two on nothing at all.
    ('notes/clean/dos-boot.txt', 'BOOT_STEP_HEAD'),
    ('notes/clean/dos-boot.txt', 'BOOT_STEP_SETTLE'),
    ('notes/clean/dos-boot.txt', 'BOOT_FOUND_TRACK'),
    ('notes/clean/dos-boot.txt', 'BOOT_SETTLE_AFTER_READ_CMD'),
    ('notes/clean/dos-boot.txt', 'BOOT_READ_CMD_SETTLE'),
    ('notes/clean/dos-boot.txt', 'BOOT_RESTORE_SETTLE'),
    ('notes/clean/dos-boot.txt', 'BOOT_TRACK_TEST'),
    ('notes/clean/dos-boot.txt', 'BOOT_DATA_PORT_FROM_C'),
    ('notes/clean/dos-boot.txt', 'BOOT_DATA_PORT_PLUS_1'),
    ('notes/clean/dos-boot.txt', 'BOOT_DATA_PORT_PLUS_2'),
}

INSN = re.compile(r'^\s{10,}(\S.*?)\s+;\s([0-9A-F]{4})\s')
QUOTED = re.compile(r'^\s{4,}(\S.*?)\s{2,};\s([0-9A-F]{4})\b')
NAME = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):(?:$|\s+EQU)')
SYNTHETIC = re.compile(r'\b[LV][0-9A-F]{4}\b')

# An invented name is words joined by underscores -- COMPRESS_BLOCK,
# HKC_XVARNVAL, DIR_MODE_NAME_ONLY.  The ROM's and MasterDOS's own names
# are single words (STKEND, MCHWR, PAGCOUNT), so this picks out exactly
# the names this project made up and can therefore rename out from under
# its own prose.  Checking only SYNTHETIC missed every one of them: a
# rename of L6594 to V6594 was caught and a rename of SET_UP_WORK_AREA to
# COMPRESS_BLOCK was not.
INVENTED = re.compile(r'\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b')

# Two kinds of line declare a name rather than referring to one, so a
# name that is not in the listing is not a fault in them:
#
#   RENAME OLD NEW   exists to say what a thing used to be called
#   CONST NAME = ..  is emitted only where the value is used, and a
#                    complete register map is worth writing down whole
#                    even when the code happens to test four bits of it
#
# A label declaration is NOT exempt: `MB &610E SOME_NAME` that does not
# reach the listing has silently done nothing, which is worth hearing.
DECLARES = re.compile(r'^\s*(?:RENAME|CONST)\s')


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
    """Every prose file under docs/ and notes/, nested ones included.

    This used to be a flat listdir, so notes/clean/ -- the whole of the
    reading copy's commentary -- was never checked, and it used to skip
    anything called master*, which took masterbasic-tokens.md and
    masterbasic-keywords.md out with the manual they were named like.
    """
    for d in PROSE:
        base = os.path.join(ROOT, d)
        for dirpath, _, files in os.walk(base):
            for fn in sorted(files):
                if not fn.endswith(('.md', '.txt')) or fn in NOT_PROSE:
                    continue
                full = os.path.join(dirpath, fn)
                yield os.path.relpath(full, ROOT).replace(os.sep, '/'), full


GRAMMAR = 'docs/sam-basic-grammar.txt'
ROM_TEXT = 'ref/samrom/text.asm'
# DW ROUTINE ;KEYWORD tok -- CMDADT's own layout, with the "** ALTERED"
# that some rows carry after the code.
CMDADT_ROW = re.compile(
    r'^(?:CMDADT:)?\s*DW\s+(\w+)\s*;\s*(?:.*?)\s*([0-9A-F]{2})\s*(?:\*\*.*)?$')
# `: ref/samrom/file.asm ROUTINE, ROUTINE (why)` -- a provenance line.
CITES = re.compile(r'ref/samrom/\w+\.asm\s+([^;]+)')
ROUTINE = re.compile(r'\b([A-Z][A-Z0-9]{2,})\b')


def command_table():
    """token -> the routine CMDADT dispatches it to, from the ROM source.

    Read rather than typed, like the grammar's generated blocks.  A
    commented-out DW is not an entry: the table stops at &F6 and the
    rows past it are `;  DW NONSENSE`.
    """
    out, started = {}, False
    for line in open(os.path.join(ROOT, ROM_TEXT), encoding='utf-8',
                     errors='replace'):
        if line.startswith('CMDADT:'):
            started = True
        if not started or re.match(r'^\s*;', line):
            continue
        m = CMDADT_ROW.match(line.rstrip())
        if m:
            out[int(m.group(2), 16)] = m.group(1).upper()
        elif out and re.match(r'^\w+:', line):
            break
    return out


def grammar_entries():
    """[STATEMENTS] as [{token, name, line, provenance}].

    Several `@` lines may stack above one shared body -- ZAP, POW, BOOM
    and ZOOM are four headings over one entry -- so a run of them all
    take the `:` lines that follow.
    """
    entries, run, section, prev_at = [], [], None, False
    for n, line in enumerate(open(os.path.join(ROOT, GRAMMAR),
                                  encoding='utf-8', errors='replace'), 1):
        line = line.rstrip('\n')
        if re.match(r'^\[\w+\]', line):
            section, run, prev_at = line.strip(), [], False
            continue
        if section != '[STATEMENTS]':
            continue
        m = re.match(r'^@ ([0-9A-F]{2,4}) (.+)$', line)
        if m:
            e = {'tok': int(m.group(1), 16), 'name': m.group(2).strip(),
                 'line': n, 'prov': []}
            entries.append(e)
            run = (run + [e]) if prev_at else [e]
            prev_at = True
            continue
        if line.startswith(': '):
            for e in run:
                e['prov'].append(line[2:])
        prev_at = False
    return entries


def token_names():
    """The [TOKENS] block's own name for each code."""
    out, section = {}, None
    for line in open(os.path.join(ROOT, GRAMMAR), encoding='utf-8',
                     errors='replace'):
        if re.match(r'^\[\w+\]', line):
            section = line.strip()
        elif section == '[TOKENS]' and '|' in line:
            f = line.rstrip('\n').split('|')
            if re.fullmatch(r'[0-9A-F]{2,4}', f[0]):
                out[int(f[0], 16)] = f[2]
    return out


def check_grammar():
    """(problems, statements checked) for docs/sam-basic-grammar.txt.

    [TOKENS] is generated and [STATEMENTS] is not, so the two can drift;
    and a `:` line naming a ROM routine can name the wrong one.  Both are
    checked against the sources rather than by eye.

    THE SECOND CHECK IS THE ONE THAT EARNED ITS PLACE.  @ CF COPY listed
    'COPY' and 'COPY' , 'CHR$' and cited ref/samrom/scrfn.asm COPY,
    GRCOPY -- but CMDADT points &BF at COPY and gives &CF NONSENSE, so
    those two were DUMP's forms, filed under the wrong keyword.  A
    provenance that names another token's routine and never its own is
    the shape of that mistake.

    A routine several tokens share is fine: SLMVC serves &94 to &97, and
    LIST serves LLIST as well as itself.  So the test is whether this
    entry's token is among those that reach a cited routine, not whether
    it is the only one.
    """
    try:
        cmdadt = command_table()
        entries = grammar_entries()
        names = token_names()
    except (IOError, OSError):
        return [], 0                    # no ref/ checkout: nothing to say
    reach = {}
    for tok, routine in cmdadt.items():
        reach.setdefault(routine, set()).add(tok)
    bad = []
    for e in entries:
        want = names.get(e['tok'])
        if want != e['name']:
            bad.append('%s:%d @ %02X %s but [TOKENS] says %s'
                       % (GRAMMAR, e['line'], e['tok'], e['name'], want))
        cited = set()
        for text in e['prov']:
            for m in CITES.finditer(text):
                cited |= {r for r in ROUTINE.findall(m.group(1)) if r in reach}
        if cited and not any(e['tok'] in reach[r] for r in cited):
            bad.append('%s:%d @ %02X %s cites %s, which CMDADT reaches from '
                       '%s -- &%02X goes to %s'
                       % (GRAMMAR, e['line'], e['tok'], e['name'],
                          ', '.join(sorted(cited)),
                          ', '.join('&%02X' % t for r in sorted(cited)
                                    for t in sorted(reach[r])),
                          e['tok'], cmdadt.get(e['tok'], 'nothing')))
    return bad, len(entries)


# ---------------------------------------------------------------------
# Keywords that list in a form which will not tokenise back
#
# A keyword is a keyword only while a letter, '_' or '$' does not follow
# it -- ALDU, ref/samrom/misc2.asm -- and one whose own last character is
# '=', '>' or '$' is exempt, GTTOK6 not calling ALDU for those at all.
# So a word that ends in a letter, that LIST prints with no trailing
# space, and that something starting with a letter can follow, lists as
# text the tokeniser reads back as one name.
#
# NVAL was exactly that until the spacing of MasterBASIC's words was read
# properly: it listed as NVALtwo$ and the two bytes of the token vanished
# into the variable.  It was found from three programs on a disk, by
# byte-counting, which is a slow way to learn it -- so the rule is
# checked here from the other end, against the productions.
#
# Nothing in the file should now meet all three, so the set below is
# empty and anything appearing is a fault: a production edited, or a
# spacing field that has moved.
#
# IT WAS NOT EMPTY WHEN IT WAS WRITTEN, and that is the point of it.  The
# seven single-byte MasterBASIC commands were named here, because HPRTOK
# looked as though it printed no trailing space -- its last CALL prints
# the word and the routine appeared to end there.  It does not end there:
# PRINT_SPACE is the next byte and there is no RET, so the space is a
# fall-through.  SORT a$() listed on a machine came back with its space
# and settled it.  A check whose expected set is empty is the one that
# cannot hide a mistake of that kind inside itself.

UNLISTABLE = set()

# A production opens with the keyword itself: its own spelling, or a
# "<one of the six>" standing for a group that shares one entry.  What
# may follow it is the rest of the line.  A production matching neither
# is not a prefix form -- the binary operators are written round their
# operands -- and says nothing about what follows a keyword.
HEAD = re.compile(r"^\s*(?:'[^']*'|<one of the [a-z]+>)\s*(?:,\s*(.*))?$")


def split_top(text, sep):
    """Split on `sep` outside brackets and quotes."""
    out, depth, quoted, cur = [], 0, False, ''
    for ch in text:
        if quoted:
            cur += ch
            quoted = ch != "'"
            continue
        if ch == "'":
            quoted = True
        elif ch in '[{(<':
            depth += 1
        elif ch in ']})>':
            depth -= 1
        elif ch == sep and depth == 0:
            out.append(cur)
            cur = ''
            continue
        cur += ch
    out.append(cur)
    return [s.strip() for s in out]


def resolve(atom, rules, seen):
    """An atom as itself, or as the atoms its rule can begin with."""
    if not atom or atom == "''":
        return []
    if atom.startswith("'"):
        return [atom]
    if atom in seen or atom not in rules:
        return [atom]           # a leaf, or prose: judged by the caller
    out = []
    for alt in rules[atom]:
        out += first_set(alt, rules, seen + (atom,))
    return out


def first_set(expr, rules, seen=()):
    """Every atom that can stand first in `expr`.

    An optional element does not end the walk, because what follows it
    can be first as well: `[ 'ABS' ] , [ 'INVERSE' ] , sort-target` can
    begin with any of the three.
    """
    out = []
    for item in split_top(expr, ','):
        if not item:
            continue
        optional = item[0] in '[{'
        inner = item
        if item[0] in '[{(' and item[-1] in ']})':
            inner = item[1:-1].strip()
        alts = split_top(inner, '|')
        if len(alts) > 1:
            for alt in alts:
                out += first_set(alt, rules, seen)
        elif inner != item or len(split_top(inner, ',')) > 1:
            out += first_set(inner, rules, seen)
        else:
            out += resolve(inner, rules, seen)
        if not optional:
            break
    return out


def begins_with_letter(atom):
    """Can this atom start with a letter or '_', the characters ALDU
    refuses to let a keyword be followed by?  Anything not a literal --
    a rule left as prose, a name defined nowhere -- is assumed to."""
    if atom.startswith("'"):
        return atom[1:2].isalpha() or atom[1:2] == '_'
    return True


def grammar_syntax():
    """({'TOK NAME': [productions]}, {rule: [alternatives]}).

    Rules come from [RULES] and from the `:=` lines an entry defines for
    itself.  An indented '|' line is another alternative of whatever the
    line above it was, and a trailing `--` comment is not part of either.
    """
    prods, rules = {}, {}
    section, run, prev_at, last = None, [], False, None
    for line in open(os.path.join(ROOT, GRAMMAR), encoding='utf-8',
                     errors='replace'):
        line = re.sub(r'\s+--(\s|$).*$', '', line.rstrip('\n'))
        if re.match(r'^\[\w+\]', line):
            section, run, prev_at, last = line.strip(), [], False, None
            continue
        m = re.match(r'^@ ([0-9A-F]{2,4}) (.+)$', line)
        if m:
            key = '%s %s' % (m.group(1), m.group(2).strip())
            run = (run + [key]) if prev_at else [key]
            prods.setdefault(key, [])
            prev_at, last = True, None
            continue
        if line.startswith('= '):
            body = line[2:].strip()
            d = re.match(r'^([A-Za-z][\w-]*)\s*:=\s*(.*)$', body)
            if d:
                rules.setdefault(d.group(1), []).append(d.group(2))
                last = ('rule', d.group(1))
            elif section in ('[STATEMENTS]', '[FUNCTIONS]'):
                for key in run:
                    prods[key].append(body)
                last = ('prod', tuple(run))
            else:
                last = None
            prev_at = False
            continue
        if re.match(r'^\s+\|', line) and last:
            alt = line.strip()[1:].strip()
            if last[0] == 'rule':
                rules[last[1]].append(alt)
            else:
                for key in last[1]:
                    prods[key].append(alt)
            continue
        prev_at = False
    return prods, rules


def check_roundtrip():
    """(problems, keywords that list unusably) for the grammar file."""
    try:
        prods, rules = grammar_syntax()
    except (IOError, OSError):
        return [], 0
    spacing, section = {}, None
    for line in open(os.path.join(ROOT, GRAMMAR), encoding='utf-8',
                     errors='replace'):
        if re.match(r'^\[\w+\]', line):
            section = line.strip()
        elif section == '[TOKENS]' and '|' in line:
            f = line.rstrip('\n').split('|')
            if re.fullmatch(r'[0-9A-F]{2,4}', f[0]):
                spacing['%s %s' % (f[0], f[2])] = f[4]
    found = set()
    for key, sp in spacing.items():
        if sp in ('both', 'trail') or not key[-1].isalpha():
            continue
        for p in prods.get(key, []):
            m = HEAD.match(p)
            if m and any(begins_with_letter(a) for a in
                         first_set((m.group(1) or '').strip(), rules)):
                found.add(key)
    bad = ['%s lists with no trailing space and a letter can follow it, so '
           'the listing will not tokenise back' % k
           for k in sorted(found - UNLISTABLE)]
    bad += ['%s is named in UNLISTABLE and no longer lists that way' % k
            for k in sorted(UNLISTABLE - found)]
    return bad, len(found)



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
            if DECLARES.match(line):
                continue
            key = rel.replace(os.sep, '/')
            for word in set(SYNTHETIC.findall(line)) | set(
                    INVENTED.findall(line)):
                if word not in names and (key, word) not in HISTORICAL:
                    bad.append('%s:%d names %s, which no longer exists'
                               % (rel, n, word))
    for line in bad:
        print('  stale: ' + line)
    print('%d prose files check out against the listings%s'
          % (sum(1 for _ in prose_files()),
             '' if not bad else ' -- except the %d above' % len(bad)))
    grammar, checked = check_grammar()
    for line in grammar:
        print('  grammar: ' + line)
    if checked:
        print('%s: %d statements agree with [TOKENS] and CMDADT%s'
              % (GRAMMAR, checked, '' if not grammar
                 else ' -- except the %d above' % len(grammar)))
    roundtrip, unlistable = check_roundtrip()
    for line in roundtrip:
        print('  roundtrip: ' + line)
    print('%s: %d keywords list in a form that will not tokenise back%s'
          % (GRAMMAR, unlistable, '' if not roundtrip
             else ' -- %d unaccounted for, above' % len(roundtrip)))
    return 1 if bad or grammar or roundtrip else 0


if __name__ == '__main__':
    sys.exit(main())
