# -*- coding: utf-8 -*-
"""Write the reading copy of the two halves, in clean/.

disasm/ is a record: it says what the bytes are and where every claim in
it came from, including the claims that turned out to be wrong, because
the working copy is where an argument is kept.  That makes it a poor
thing to read straight through.

clean/ is the same three listings with a different job.  It is written
for somebody who knows Z80 and does not know this machine, so it drops
the arguing, keeps the conclusions, and says what a routine is for
before saying what it does.  Nothing in it is a new claim: every byte
still assembles to the original image, and build.sh proves it for these
files exactly as it does for the working copies.

Three things happen here:

  * the working notes come out -- a paragraph whose subject is how the
    reading was arrived at, or what an earlier reading got wrong, is
    for disasm/ and not for a reader who only wants the code;

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

import io
import os
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


PREAMBLE = """\
; %(what)s -- a reading copy.
;
; Generated by tools/dis_mb.py into clean/.  Assembling this file with
; pyz80 reproduces its half of file/MasterBasicMasterDos.bin byte for
; byte, and tools/build.sh checks that on every run: nothing here is a
; transcription, and no comment in it can drift away from the code it
; sits on without the build saying so.
;
; This is the reading copy.  disasm/ has the same code with the working
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
