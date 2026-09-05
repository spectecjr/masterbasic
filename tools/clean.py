# -*- coding: utf-8 -*-
"""Write the reading copy of the two halves, in listings/clean/.

listings/disasm/ is a record: it says what the bytes are and where every claim in
it came from, including the claims that turned out to be wrong, because
the working copy is where an argument is kept.  That makes it a poor
thing to read straight through.

listings/clean/ is the same three listings with a different job.  It is written
for somebody who knows Z80 and does not know this machine, so it drops
the arguing, keeps the conclusions, and says what a routine is for
before saying what it does.  Nothing in it is a new claim: every byte
still assembles to the original image, and build.sh proves it for these
files exactly as it does for the working copies.

Three things happen here:

  * the working notes come out -- a paragraph whose subject is how the
    reading was arrived at, or what an earlier reading got wrong, is
    for listings/disasm/ and not for a reader who only wants the code;

  * prose from notes/clean/ goes in, and wins over everything.  This is
    where the MasterDOS source's own commentary is rewritten rather
    than carried: the original's line comments are the author talking
    to himself in capitals -- "T/S", "JR IF ERROR", "NO RECURSE NOW" --
    and they are worth reading once and saying properly, which is a
    thing a person does and not a transform;

  * each file gets a preamble that explains the machine, since none of
    the paging makes sense without it.

What has not been rewritten yet keeps the commentary it has, so the
listing is complete at every stage rather than sparse.  coverage()
counts what is left, and build.sh prints it, so the gap is visible
instead of implied.
"""

import re

NL = chr(10)

#  A banner paragraph whose subject is the investigation rather than the
#  code.  Each of these is a phrase that only makes sense to someone
#  following the work; the reading copy has no use for any of them.
WORKING = re.compile(
    r'WITHDRAWN'
    r'|\bused to (?:say|show|call|read|come out|be)\b'
    r'|\bthe name it had before\b'
    r'|\bwas a guess\b'
    r'|\bis now called\b'
    r'|\bthis note\b'
    r'|\bthis project\b'
    r'|\bwhich is why it had no name\b'
    r'|\bnot established here\b'
    r'|\bstill not found\b'
    r'|\bhad had to leave\b'
    r'|\bthe doubt recorded here\b',
    re.I)

#  Not a paragraph so much as a line drawn under one.  notes/ records the
#  header a DOC displaced, so that the working copy can see what changed;
#  everything from that line to the end of the banner is the old text,
#  however it reads, so the whole tail of it goes.
SUPERSEDED = re.compile(r'what was here before', re.I)

BAR = ';; ' + '-' * 68

#  Prose carried from the annotated MasterDOS source that this image's
#  code does not bear out.  The source describes stock MasterDOS 2.3;
#  where MasterBASIC changed something underneath a comment, the comment
#  came across with it and is now wrong.
#
#  Each entry is a run of consecutive banner lines exactly as they are
#  emitted, and its replacement.  Every one must fire exactly once: a
#  correction that no longer matches is a correction that has gone
#  stale, and a silent miss is the failure this file exists to prevent.
CARRIED_FIXES = [
    ([';;  Normalise a page and address pair so the address lies within one page and the surplus is in the page number.'],
     [';;  Flatten a page and address pair into one number.  Not the other way about: the window base is discarded and',
      ";;  the page's low bits are shifted down into the address, so what comes back is a flat byte address rather than",
      ";;  a tidied pair.  PAGEFORM is the inverse, and &602A does one then the other -- two pairs flattened so that",
      ';;  SBC HL,DE and SBC A,C can subtract them, then PAGEFORM to put the difference back into page-and-address',
      ';;  form.']),
    ([';;  Errors: REP22 for a drive above RDLIM, "out of memory" if there are not enough free pages'],
     [';;  Errors: REP22 for a drive of RDLIM or above -- the test is CP RDLIM / JP NC, so RDLIM itself is refused --',
      ';;  and "out of memory" if there are not enough free pages']),
    ([';;    DFMT / DMT1 / WFM     format a disk, and build the track image the controller writes'],
     [';;    DFMT / FMTSR          format a disk; the track image it writes is built by MasterBASIC']),
    ([";;    PNTYP / DRTAB         print a file's type, and for some types its address and length"],
     [";;    PNTYP                 print a file's type, and for some types its address and length (the"
      ";;                          table of names is DRTAB, in MasterBASIC)"]),
    ([';;  MCPT, whose codes are 1 to 12 and are listed with the table. Code 0 is not a substring at all: it clears the lower',
      ';;  screen, so a message can begin by wiping what was there.'],
     [';;  MCPT, whose codes are 1 to 11. Code 0 is not a substring at all: it clears the lower screen, so a message can',
      ';;  begin by wiping what was there, and a code of 12 or more runs off the end of the table.']),
    ([';;  Writes every track, then either copies another disk onto it, verifies it, or does neither, depending on whether a',
      ';;  second drive was named.'],
     [';;  Writes every track, then copies another disk onto it if a second drive was named. Without one it verifies what it',
      ';;  wrote, unless the byte at &42B9 has been poked -- nothing in either half ever writes it, so as shipped a plain',
      ';;  FORMAT always verifies.']),
    ([';;  the gaps, sync fields and address marks. The controller stops at the index hole, so the trailing gap is',
      ';;  deliberately longer than a track and the surplus is never written.'],
     [';;  the gaps, sync fields and address marks. The controller stops at the index hole, so the image is deliberately',
      ';;  longer than a revolution -- 6306 bytes against about 6250 -- and the surplus, the tail of the 256-byte gap at',
      ';;  the end, is never written.']),
    ([';;  The text ends at the character with bit 7 set, and the routine returns past it rather than to it. Bytes below 13',
      ';;  are not characters: 1 to 12 are indices into MCPT and are expanded by recursion, and 0 clears the lower screen, so',
      ';;  a message can begin by wiping whatever was there.'],
     [';;  The text ends at the character with bit 7 set. PTM pops the address of the text, so nothing returns to the byte',
      ';;  after it: the RET at the end goes to whoever called the routine that called PTM. Bytes below 13 are not',
      ';;  characters: 1 to 11 are indices into MCPT and are expanded by recursion, and 0 clears the lower screen, so a',
      ';;  message can begin by wiping whatever was there.']),
    ([';;  A disk formatted by SAMDOS has no name field, and reads as 00 or &FF there; those print "SAM DOS". A name of "*"'],
     [';;  A disk formatted by SAMDOS has no name field. Formatting fills it with zeros, and &FF is accepted too; either',
      ';;  prints "SAM DOS". A name of "*"']),
    ([";;  planned. This inserts the address of the next statement below the ROM's error stack pointer, with a null address",
      ';;  below that, and adjusts the saved stack pointer to match.'],
     [";;  planned. This inserts the address of the next statement below the ROM's error stack pointer, and the ROM's own",
      ';;  &0004 -- POP HL : JP (HL) -- below that, and takes two off the saved stack pointer to match. The &0004 is not',
      ";;  padding: it is what the ROM's dispatcher finally RETs to, and it forwards through to the next statement."]),
    ([';;  that follows -- so the chain falls through to the single tail below. REP27 is the odd one out: it reports the',
      ";;  ROM's own \"End of file\" (22) rather than a DOS code."],
     [';;  that follows -- so the chain falls through to the single tail below, and one CALL DERR serves the twenty codes',
      ";;  the chain carries. REP27 is the odd one out: it reports the ROM's own \"End of file\" (22) rather than a DOS",
      ';;  code.']),
    ([';;  report names the sector that failed. A hook that failed unwinds to the stack pointer in HKSP so the ROM can report',
      ';;  it; a command unwinds to a fixed stack and leaves the error marker at the position in the line.'],
     [";;  report names the sector that failed. HKSP is not a hook's stack pointer, whatever its name suggests: ZFSP",
      ';;  zeroes it on the way in to every hook and every command, and the one instruction in the image that stores anything',
      ";;  else is the NMI's, at &5370. So both hooks and commands take the DERR1 path to a fixed stack, and the HKSP",
      ';;  path belongs to the snapshot menu -- where an error resumes the frozen program instead of reporting anything.']),
    ([';;  The colour comes from the low bits of RBCC and is ANDed with E -- the sector number -- so the border changes as the',
      ';;  head moves. Setting RBCC to zero turns the effect off.'],
     [';;  The colour comes from the low bits of RBCC and is ANDed with E -- the sector number -- so the border changes from',
      ';;  sector to sector as the disc turns. Setting RBCC to zero turns the effect off.']),
    ([';;    ORDER                 the sort behind a sorted listing, and hook code 153'],
     [';;    HK_PCAT               the sorted catalogue -- the sort itself is in the MasterBASIC page, through hook 153']),
    ([';;    OHASR / FNMAE         the per-file confirmation the "?" option asks for'],
     [';;    OHASR                 the per-file confirmation the "?" option asks for (FNMAE, which prints it, is in E1)']),
    ([';;  REFBUF / PTSVT -- re-read the directory sector and point back at the entry the search stopped on. Needed because',
      ';;  the caller writes the entry back between finds, so the buffer cannot be trusted to still hold it.'],
     [';;  REFBUF / PTSVT -- re-read the directory sector and point back at the entry the search stopped on. Writing the',
      ";;  entry back is not what makes this necessary: WSAD writes from this very buffer and leaves it holding what it",
      ";;  wrote. What spoils it is other traffic through DRAM between one find and the next -- COPY passes the file's own",
      ';;  data sectors through it, and RENAME runs a second directory scan in FINDC to see whether the new name is taken.']),
    ([';;  Both file specifiers are parsed, and if they name the same drive flag bit 5 is set so the user will be asked to',
      ';;  swap disks between reading and writing.'],
     [';;  Both file specifiers are parsed, and if they name the same drive -- and it is a real one, drive 1 or 2 -- flag',
      ';;  bit 5 is set so the user will be asked to swap disks between reading and writing. A copy within one RAM disc',
      ';;  needs no swap, and the CP &03 in front of SETF5 is what leaves it out.']),
    ([';;  quadratic. The position is kept in FFHL and FFDE -- which are the four bytes of the "BOOT" file name at &4100,',
      ';;  reused as variables once the DOS is in memory and the name is no longer needed.'],
     [';;  quadratic. The position is kept in FFHL and FFDE. Stock MasterDOS 2.3 keeps those in the four bytes of',
      ';;  the "BOOT" file name at &4100, reused once the DOS is in memory and the name is no longer needed. This',
      ';;  image does not: it leaves the name alone and uses four spare bytes at &42E6 instead.']),
    ([';;  Step to the next page and wait for the key to be released, so the user can pick which page is captured. The border',
      ';;  changes as they go, which is the only feedback available with the machine frozen.'],
     [';;  Nothing of the five was pressed, so step the border colour and go round again -- the only sign of life a stopped',
      ';;  machine can give.  The port written is &FE, which is the border as well as the keyboard, so BC needs no',
      ';;  reloading.  X is tested here rather than with the digits because it is on another row, and holding it leaves',
      ';;  the menu for good.']),
    ([';;    GTFLE                 open a file for reading'],
     [';;    GTFL3 / CHECK_FILE_TYPE  open a file for reading']),
    ([';;  Errors: REP24, "not enough space", when the map runs past the last track'],
     [';;  Errors: REP24, "Disk full", when the map runs past the last track']),
    ([';;  Writes the directory entry built up in the entry image into the slot FSLSR noted earlier, or finds one if that has',
      ';;  become stale.'],
     [';;  Writes the directory entry built up in the entry image into the slot FSLOT and FSLTE noted earlier, or finds one',
      ';;  if they noted none.']),
    ([';;  The first entry of the directory -- track 0, sector 1, entry 1 -- is special: it also holds the disk name, the',
      ";;  disk's random identifying word, the directory tag and the count of extra directory tracks. Those are read from the",
      ';;  disk and written back unchanged, so only the parts of the entry that belong to the file are replaced.'],
     [';;  The first entry of the directory -- track 0, sector 1, entry 1 -- is special: it also holds the disk name, the',
      ";;  disk's random identifying word and the count of extra directory tracks. Those are read from the disk and written",
      ';;  back unchanged, so only the parts of the entry that belong to the file are replaced.']),
]


def fix_carried(pages):
    """Apply CARRIED_FIXES to the banners.  Returns the count.

    Raises if any of them fails to match, or matches more than once.
    """
    done = 0
    for old, new in CARRIED_FIXES:
        hits = []
        for d in pages:
            for a, text in d.headers.items():
                lines = text.split(NL)
                for i in range(len(lines) - len(old) + 1):
                    if lines[i:i + len(old)] == old:
                        hits.append((d, a, i))
        if len(hits) != 1:
            raise AssertionError(
                'carried fix matches %d places, not 1: %s'
                % (len(hits), old[0].strip()))
        d, a, i = hits[0]
        lines = d.headers[a].split(NL)
        d.headers[a] = NL.join(lines[:i] + list(new) + lines[i + len(old):])
        done += 1
    return done



def split_banner(text):
    """Separate the ;; banner from anything emitted after it.

    A header is not always only prose.  DRTAB's, for one, ends its
    banner and then declares the equates the table is written in, and
    those lines are code: losing them costs the listing its assembly.
    So only the run of ;; lines is prose, and everything from the first
    line that is not one of them is passed through untouched.
    """
    lines = text.split(NL)
    n = len(lines)
    while n and not lines[n - 1].startswith(';;'):
        n -= 1
    return lines[:n], lines[n:]


def paragraphs(banner):
    """Split the ;; lines into paragraphs, dropping the rules."""
    out, cur = [], []
    for line in banner:
        stripped = line.strip()
        if stripped == ';;':                  # the break between two
            if cur:
                out.append(cur)
            cur = []
        elif not stripped.strip('; -'):
            continue                          # a rule, or a blank
        else:
            cur.append(line)
    if cur:
        out.append(cur)
    return out


def strip_working(text):
    """Drop the paragraphs that are about the reading, not the code.

    Returns the header and how many paragraphs went.  A banner left with
    nothing is dropped entirely -- an empty pair of rules says less than
    no banner at all -- but only if nothing was emitted after it.
    """
    banner, tail = split_banner(text)
    paras = paragraphs(banner)
    total = len(paras)
    for i, para in enumerate(paras):
        if SUPERSEDED.search(NL.join(para)):
            paras = paras[:i]              # and everything under the line
            break
    kept = [para for para in paras if not WORKING.search(NL.join(para))]
    if len(kept) == total:
        return text, 0
    gone = total - len(kept)
    if not kept:
        return (NL.join(tail).strip(NL) or None) if tail else None, gone
    out = [BAR]
    for i, para in enumerate(kept):
        if i:
            out.append(';;')
        out.extend(para)
    out.append(BAR)
    return NL.join(out + tail), gone


#  The annotated MasterDOS source carries a few of its author's own
#  working marks on instruction lines -- an address in the shipped code,
#  the addresses the source's own labels have, and "=" or "?" for
#  whether they agreed -- each ending in ";*".  They are notes about
#  reading the code, not about the code, and carrydoc brings them across
#  with everything else.  A few lines carry the bare "*" alone, which is
#  the same mark with the rest of it left off.
ALIGNMENT_MARK = re.compile(r';\*\s*$|^\*+\s*$')


def strip_alignment_marks(pages):
    """Take those marks off the lines they sit on.  Returns the count."""
    gone = 0
    for d in pages:
        for a in list(d.comments):
            if ALIGNMENT_MARK.search(d.comments[a]):
                del d.comments[a]
                gone += 1
    return gone


def clean_pages(pages):
    """Take the working notes out of every banner.  Returns the count."""
    gone = 0
    for d in pages:
        for a in list(d.headers):
            banner, n = strip_working(d.headers[a])
            if not n:
                continue
            gone += n
            if banner is None:
                del d.headers[a]
            else:
                d.headers[a] = banner
    return gone


def coverage(pages):
    """How much of each half still reads as the original author left it.

    The MasterDOS source's own line comments are in capitals; anything
    rewritten here is not.  That makes the count a one-liner and, more
    to the point, makes it honest -- it cannot drift, because it is
    measured from the listing rather than tracked by hand.
    """
    out = {}
    for d in pages:
        shouty = mine = 0
        for a, notes in d.comments.items():
            for text in (notes if isinstance(notes, list) else [notes]):
                letters = [c for c in text if c.isalpha()]
                if not letters:
                    continue
                if sum(c.isupper() for c in letters) / len(letters) > 0.8:
                    shouty += 1
                else:
                    mine += 1
        out[d.tag] = (mine, shouty)
    return out


def bare_numbers(pages):
    """How many instructions still carry a number nobody has named.

    A count, not a judgement: plenty of them should stay numbers, and a
    loop counter of 8 is just 8.  It is here because it is the one thing
    the byte check cannot see.  Taking a name away leaves the listing
    assembling perfectly and reading worse -- which is what happened when
    the boot's constants were regrouped and two were dropped on the way.
    """
    out = {}
    for d in pages:
        n = 0
        for a, ins in d.insns.items():
            if not d.inside(a) or not ins.asm:
                continue
            text = d.overrides.get(a, ins.text)
            if re.search(r'&[0-9A-F]{2}([0-9A-F]{2})?\b', text):
                n += 1
        out[d.tag] = n
    return out


PREAMBLE = """\
; %(what)s -- a reading copy.
;
; Generated by tools/dis_mb.py into listings/clean/.  Assembling this file with
; pyz80 reproduces its half of dumps/MasterBasicMasterDos.bin byte for
; byte, and tools/build.sh checks that on every run: nothing here is a
; transcription, and no comment in it can drift away from the code it
; sits on without the build saying so.
;
; This is the reading copy.  listings/disasm/ has the same code with the working
; notes left in -- where a name came from, what an earlier reading got
; wrong, which claims are still open.  If you want the argument, read
; that one.  This one keeps the conclusions.
;
; ---------------------------------------------------------------------
; The machine, in as much as the code needs
; ---------------------------------------------------------------------
;
; The SAM Coupe is a Z80B at 6MHz with 256K or 512K of RAM, addressed
; 16K at a time through four pages.  Two ports do the paging:
;
;   LMPR  &FA   the page at &0000, plus two switches: bit 5 puts the
;               32K ROM 0 over &0000-&3FFF, bit 6 puts ROM 1 over
;               &C000-&FFFF
;   HMPR  &FB   the page at &8000
;
; So an address says nothing on its own -- &8000 is whatever page HMPR
; last named.  Almost every awkward thing in this listing follows from
; that one fact.
;
; %(where)s
;
; The other half is at &8000-&BFBF while this one runs, so an operand in
; that range is an address in the other page, and the listings write it
; with a %(prefix)s prefix.  &4000 is the difference between the two
; views: a routine that hands out a pointer to itself for the other
; half to call adds &4000 to its own address, and a table entry with
; bit 15 set means "not in this page".
;
; The ROM's own variables live at &5A00-&5CFF in page 0, the system
; page, which is at &4000 when the ROM is running -- the same &4000
; this half occupies.  Neither half can simply read them.  It either
; calls the ROM's NRRD and NRWR, which page the system page in and out
; around a single access, or it does the same thing inline.  A name
; written NAME+&4000 in an operand is that second case: the system
; page seen through the window.
;
; ---------------------------------------------------------------------
; How to read a line
; ---------------------------------------------------------------------
;
;     LD A,(DSC)              ; 451B 3A 10 41  the drive's port base
;     \\_______/                 \\__/ \\______/  \\__________________/
;      the code                 addr  the bytes  what it is for
;
; The address is where the byte sits when this half is paged at &4000.
; The bytes are the assembled instruction, so any line can be checked
; against the image by hand.
;
; A routine is introduced by a banner and, where anything calls it, by
; a line saying from where:
;
;     ; ---- TRCKP ---- from &46FE, &4751
;
; A routine with no such line is not dead code.  Several are reached
; from the ROM's system page, or from the other half, or from a copy of
; themselves somewhere else entirely; each one says so in its banner.
"""

WHERE = {
    'DOS': """; This file is the MasterDOS 2.3 half: 16320 bytes that run at
; &4000-&7FBF in page 29.  MasterBASIC is the other half, in page 28.""",
    'MB': """; This file is the MasterBASIC 1.7 half: 16320 bytes that run at
; &4000-&7FBF in page 28.  MasterDOS is the other half, in page 29.""",
}

WHAT = {'DOS': 'MasterDOS 2.3', 'MB': 'MasterBASIC 1.7'}
PREFIX = {'DOS': 'MB_', 'MB': 'DOS_'}


def preamble(d):
    return PREAMBLE % {'what': WHAT[d.tag], 'where': WHERE[d.tag],
                       'prefix': PREFIX[d.tag]}


def drop_self_loop_labels(pages):
    """Drop the label on an instruction whose only caller is itself.

    DJNZ $ is a delay.  Naming its target puts a label in the margin and
    a caller list above it -- "from &4077 when B is not 0 yet" -- for a
    destination nothing else ever reaches and no reader needs to find.
    A label is only dropped when the instruction it sits on is the one
    reference to it, and when nothing has been written about it.
    """
    n = 0
    for d in pages:
        peer = getattr(d, 'peer_xrefs', {})
        for a in list(d.labels):
            if set(d.xrefs.get(a, ())) != {a} or peer.get(a):
                continue
            if a in d.headers or a in d.steps or a in d.notes:
                continue
            del d.labels[a]
            n += 1
    return n
