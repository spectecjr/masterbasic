# The review plan

*What to do next, in order, and how to know when to stop.  Written for a
session that has not read the rest of this directory; it says where the
prompts and the scoring live and does not repeat them.*

---

## What this is for

The byte gate proves the listings; nothing proves the commentary except a
second reader.  `design/reviewprocess.md` is the method -- the prompt
templates, the rules that do not bend, the audit step -- and it has been
run six rounds.  `design/reviews.csv` is the score of every region ever
reviewed, and `python tools/reviewlog.py` prints the figures that say
whether the rounds are converging.  Read the process file first, then this.

The plan is in phases because the order matters: the tooling in phase 0
makes every later round cheaper and catches a class of fault the reviewers
have been finding by hand.  Nothing after phase 0 depends on anything but
the previous phase having been *started*; a session can take one phase and
stop.

Working rules that apply throughout:

- A review agent writes to scratch and nowhere in the repository, and
  never runs `tools/build.sh`.  Twice stated in the prompt.
- Every finding is audited against the instructions before a character of
  it is applied.  `python tools/review_audit.py <report>` shows each
  finding beside the instruction it names.
- Every region reviewed gets a row in `design/reviews.csv` with the counts
  from the audit.  Fill the `own_lines` column -- the density figure needs
  it, and it is what the earlier rounds lack.
- Commit per green build, by pathspec.  The commit message names what was
  refuted, so it is not re-litigated.

---

## Phase 0 -- the tools

Each of these is a day or less.  Together they remove the faults that cost
the sixth round time or lost it a finding.

**0.1  Warn on two notes for one address.**  In `tools/notes.py`, a `:`
line, `value` or `expr` for an address that another file has already
given one is applied silently, last file wins.  `&644D` had a line in
`dos-nmi.txt` and `dos-loadsave.txt`; the correction in the second was
never seen because the first is later in the alphabet.  Print a problem
line naming both files.  Expect a handful of existing collisions to
surface; resolve each by deleting the one that is wrong.

**0.2  Cut regions by label, not by address range.**  The cutter used for
round six kept the label line before a range's first address only when
the previous range's flag was still on, and three of seven reviewers lost
time to labels sitting over the wrong routine.  Write `tools/cutregion.py`
that takes a list of routine names (or a PART name on the DOS side) and
emits the listing from each label's banner to the next label outside the
set, and prints the count of this project's own comment lines for the
`own_lines` column.  MasterBASIC has no PART banners, so the DOS recipe in
reviewprocess.md does not transfer; this replaces it for both halves.

**0.3  The stale-A branch lines.**  The generated `; ---- NAME ---- from
&xxxx when A <> &44` lines key on the CP and do not notice an intervening
`LD A`; `RCLM4`, `SDCM2` and `OPND45_1` are three of them.  Deferred in
rounds five and six.  The condition named is right; only the register is
stale, so the fix is to say "when the compare found A <> &44" or to drop
the register when a load sits between the CP and the jump.

**0.4  The two instructions decoded as skips.**  `&6604` is a live `LD
HL,AUTNAM` in AUINSR and `&661A` is INIT's `CALL AUINSR`; both listings
render each as a one-byte `DEFB` skip plus a phantom instruction, because
the trace claimed their second bytes as instruction starts.  What claims
`&6605` and `&661C` was not found in round six -- no CALL, JP, DEFW or
peer reference names either -- so the first job is to find it
(tracing what seeds the queue, the way the build's sites debug switch traces a routine), the second to stop
it.  A rendering fault, not a byte fault: the build stays green either way.

**0.5  `review_audit.py` flags a stale `says:`.**  When the quoted claim
is not in the current listing, say so beside the finding.  Two findings in
round two were stale because the region had been cut before a rebuild,
and the agent said so; the tool should, too.

**0.6  Extend `reviewlog.py` only if a question needs it.**  It prints
findings per hundred own lines, the confirmed rate and the `[C]` share per
round.  That is the convergence view; do not add columns for their own
sake.

---

## Phase 1 -- the carried comments

`build.log` reads `1323 still the MasterDOS author's own` for the DOS
reading copy.  Those upper-case comments were carried across from the 1991
source by `tools/carrydoc.py`, which matches instructions, and every
round so far has found some sitting on the wrong instruction as a side
effect of looking for something else: `ORIG SP` on a PUSH that holds the
other value, `JR IF PARAM WAS 4` on the fifth DEC rather than the third,
`READ - SET TO 7FF0H` on the byte after the DEFW it described.  Six of
those in round six, none of them looked for.

Run the review shape with the target reversed: the upper-case comments are
PRIMARY, the question is "does this build still do what the comment says
here", and `ref/masterdos/src/masterdos23.asm` is the reference -- the
author's text, not `annotated-src/`.  Two ways a carried comment is wrong,
and the prompt should name both: the instruction it sits on is not the one
it described (MasterBASIC inserted or moved code), and the source itself
was wrong.  Where a comment is right but the routine beneath it has changed
enough that the header no longer describes it, that is a finding too.

Cut the DOS in PART-sized pieces; there are about eleven.  A comment found
wrong is fixed with a `:` line, which replaces it.

---

## Phase 2 -- second passes where the first pass found a lot

The process file's own rule: a region that returns twelve findings is one
to re-read, because a review samples the errors and does not exhaust them.
Round six returned twenty on the load/save region and nineteen on the
functions region.  Re-cut both after phase 0.2 and send them to a fresh
reviewer with the same prompt.  The score of the second pass against the
first is the most direct measure this project has of what one pass leaves
behind; write the pair up in the process file when it is in.

---

## Phase 3 -- the MasterBASIC half

`0 of them unexplained` measures operands, not prose, and MasterBASIC has
no 1991 source: every explanation there was inferred from the bytes and
the manual, which is the kind of claim the reviewers have been overturning.
It is the larger risk.

Reviewed so far, by address: `&41C5-&42B1` and `&6594-&66AE` (proposals
only, never reviewed), `&4500-&4700`, `&500C-&51D6`, `&5C00-&5E00`,
`&6400-&6594`, `&69E7-&6AD4`, `&6C01-&6DF6`, `&7700-&7900`.  Never read
by a second reader, in the order they are worth doing:

| Range | What is there | Why this order |
|---|---|---|
| `&5E00-&6400` | the utility slots, CHECK_BREAK and TRACE, COMPRESS_SCREEN_FILE and the nibble encoder, EXPAND_COMPRESSED_FILE, LOAD_NEXT_INPUT_BLOCK, CMD_SAVE | strong claims about mechanisms, and round six leaned on `&62A6` and `LOAD_NEXT_INPUT_BLOCK`: check what it leaned on |
| `&66AE-&69E7` | EXPAND_FILE and the work page, CMD_DUMP and its line, strike and pixel routines | the DUMP claims the emulator settled were about &69E7 on; this is the half before |
| `&4700-&500C` | the far-string compares, SORT_NAMES, CMD_DATE and CMD_TIME and the clock, STAMP_WITH_DATE, FN_TICS, FN_LOCN, FN_INARRAY, SEARCH_MEMORY, FN_EQU | the clock and date-stamp claims cross into the DOS, which round six read from the other side |
| `&51D6-&5C00` | HOOK_RCPTCH and the program walk, BUILD_TRACK_IMAGE, CMD_ALTER, the serial channel and CMD_LPRINT, CMD_PRINT, CMD_REF and the reference parser | large and bare of review; `notes/mb-cmdbuf.txt` and the serial notes make the boldest claims in the repository |
| `&42B1-&4500` | CALLDOS, the serial hooks, DRTAB, the REP_ stubs, FIND_VARIABLE, the EXPECT_ and CALL_ helpers | paging claims; the kind reviewers have overturned before |
| `&6DF6-&7700` | CMD_JOIN and CMD_DELETE, CMD_SPLIT_LINE, FN_USING_S, the compiler, the PROC index, RELOCATED_TO_46CC and INSTALLER | RELOCATED_TO_46CC was the mechanism a note had called unexplainable until it was read |
| `&7900-&7FC0` | RESOLVE_ROM_ENTRIES, INSTALL_SYSPAGE_CODE, MB_PAGER, the stubs and callbacks, the installed blocks | the copy rules are checked against the dump; the callbacks are not |
| `&41C5-&42B1`, `&6594-&66AE` | the two proposal-only regions | proposals were applied without a review pass |

Aim for 800-1200 lines a cut, and cut by routine (phase 0.2).  The facts
block in the prompt needs the MasterBASIC additions: the installed blocks
and their addresses in the system page (`notes/mb-postboot.txt` has the
map), what `CALLDOS` leaves in the alternate registers, and that the
manual (`docs/masterbasic-manual.md`) is a transcript to check claims
against rather than a claim itself.

---

## Phase 4 -- the countable backlog

Bounded jobs, good between rounds or when a round is out for review:

- `described 638 of 2372 labelled addresses` in `build.log`.  The other
  1700 have a name and, on the DOS side, the author's carried header; a
  banner of this project's own is the difference.  Do it by PART, and
  send each PART for review once it is written -- that is what round six
  was.
- 141 synthetic `Lxxxx`/`Vxxxx` labels between the halves (`grep -c
  '^[LV][0-9A-F]\{4\}:$'` on each clean listing).  Each is a routine or
  variable nobody has named; name by address, never by RENAME, and read
  the label diff afterwards.
- `python tools/describedtwice.py` prints the banner/declaration pairs that
  could have drifted apart; `python tools/deadnotes.py` the notes that
  match nothing.  Both are short lists; clear them.
- `DEFW` operands and data are outside the magic-number count by design.
  A pass over the DOS's inline parameters that still read as numbers --
  `DEFW &5BB8`, `DEFW &4A97` -- explaining each with a `:` line.

---

## Evidence that needs a machine

`docs/evidence-wanted.md` lists what is left: items 7, 9, 10a-j and 12.
**Item 9 and everything under it is parked**: the Spectrum-mode capture
needs the emulator to load files, and as of 2026-09-13 it will not.  Do
not spend a session on it; the listing says where the reading stops
(`SNAP7`'s stub in page 3) and that is enough.  Items 7 and 12 and the
seven short BASIC tests in 10 need only a booted machine and are cheap if
one is to hand.

---

## Convergence, and when to stop

Run `python tools/reviewlog.py` after every round.  Three figures, and what
each is for, are in that file's docstring.  The one to watch is findings
per hundred lines of this project's prose: round six was 11.5, on
commentary written the same day.  Expect the carried-comment sweep and the
MasterBASIC regions to come in near that; expect second passes (phase 2)
to come in well under it, and that gap is the number that says how much
one pass leaves behind.

The stopping signal is not a low count on its own -- a reviewer who has
stopped finding things and one who has stopped looking print the same
number.  It is the `[C]` share falling while the confirmed rate holds:
the reviewer is still careful and is reaching for suspicions, which is what
a region with little left in it looks like from outside.  When two
consecutive rounds on fresh regions show that, the method has done what it
can and the remaining errors want a different one -- running the code.

None of the six rounds so far shows it.  That is the honest state: the
error density is still above what one pass exhausts, each round is buying
something, and the plan above is on the order of ten to fifteen more.
