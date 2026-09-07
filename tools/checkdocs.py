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
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
