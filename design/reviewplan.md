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

## Phase 0 -- the tools  (done 2026-09-13)

Each was a day or less.  What each found is kept here because it says
what the tools are for.

**0.1  Two notes for one address now warn.**  `notes.apply` prints
`file:line: &addr already has a line comment from other:line; this one
wins` for a `:` line, AFTER, `value`, `expr`, `step` or header given
twice in one folder (`notes/clean/` over `notes/` is by design and not
reported).  Fourteen line-comment pairs and sixteen doubled headers
surfaced; the line comments were resolved by reading each pair against
the code, the headers by deleting eleven the later file had rewritten
in full and merging the five that said different things.  One pair was
the wrong way round: `STORE_BC_AT_XVAR76`'s two-line header ("the ROM
system variable whose address is held at &4076") was winning over the
twelve-line one that knew `V4076` is the ROM's saved stack pointer and
the write lands on its return address.

  The survey found a larger fault beside it.  **A `:` comment wrapped
onto a second line was being read as a header.**  The parser treated
any indented line under an entry as its description, so the tail of
114 long comments -- nearly all of `record.txt` and `mb-vectors.txt`,
proposal-round output wrapped at the text column -- came out as a
`;; ----` banner above the instruction, and where the address had a
header of its own (ESCCHK, PREPARE_ROM1_COPY) the fragment displaced
it.  A continuation aligned to the comment's text column now joins the
comment; indented any other way it is a header, as before, which is
what the six deliberate ones do.

**0.2  `tools/cutregion.py`** cuts by routine: `MB NAME...`, `DOS --part
C11`, or `MB --range &5E00-&6400` (half-open; every routine whose label
is inside).  A routine runs from its banner to the banner of the next
label the namer did not derive, so a routine's `_1` and `_LOOP` labels
stay with it and `CMD_JOIN_TO` does not.  It prints the routines taken, so a
range cut can be repeated by name, and the two counts step 1 of the
process file asks for.

**0.3  The stale-A branch lines** now read `when the CP found A <> &44`:
`explain_branches` tracks what the flag-neutral instructions it steps
over write, and puts the reading in the past tense when the tested
register is among them.  `EX AF,AF'` also stops the walk now; it had
been treated as leaving the flags alone.

**0.4  The two skips were `sweep_gaps`' doing.**  `TRACE_DEBUG=6605,661C`
(a switch on the trace queue in `tools/disasm.py`, new) named the
instruction that queued each: `DJNZ &661C` at `&65D9` and `JR NZ,&6605`
at `&65E3` -- inside AUTNAM, the auto-load parameter block, which the
gap sweeps read as code because `01 FF FF 44 10 41 55 ...` decodes to
exactly where HAUTO begins.  A sweep now refuses a run whose decode
carries a *relative* branch into the middle of a known instruction
(absolute ones are what a relocated block legitimately has, and the
first version of the test returned RELOCATED_TO_46CC to DEFBs); the
permissive sweep applies it only up to the first point flow stops.
AUTNAM is marked data in `notes/clean/dos-loadsave.txt` besides.

**0.5  `review_audit.py` flags a stale `says:`**: the quoted text is
looked for in the listing's prose with whitespace normalised, and a
finding whose quote is not there gets a line saying so and a place in
the summary.  On a round-five report it flagged nine of twenty-eight,
all of them findings since applied.

**0.6  `reviewlog.py`** was not extended; no question needed it.

---

## Phase 1 -- the carried comments  (run 2026-09-13; round 8)

Twelve cuts -- ten PARTs and MOVE in two halves, by `cutregion.py` --
sent to twelve reviewers on Opus with one prompt
(`scratchpad/phase1/prompt-template.txt` that day; the facts block is the
process file's with the controller's port table from the Technical
Manual added).  100 findings, 97 confirmed and applied, 3 left open,
none refuted.  The three: EXDT1_DONE at &6280, a stale label the old
&A280 misreading left and nothing references (generator); two source
continuation lines rendered as banners above EVPR5 and WFODB; and the
carried FNDI2 at &7925, three instructions from where the source put
it, with no referent.  The reviewers' own verdict
on the carried comments was near-unanimous: all but a handful sit on the
instruction the author wrote them against.  What they found instead was
in three classes -- carried comments *split*, the second line of a
two-line comment swept into the next routine's banner (ENTIRE BLOCK,
IN CASE 2ND ONE WANTED, OLD ENTRY, BC=0306H); carried comments *stranded*
where this build collapsed the source's sequence into one CALL (NSBYT's
SELECT DRIVE and PREV, both on the wrong instruction); and the source
*wrong* where the bytes say otherwise (PADDING WITH SPACES over two
zero-filling paths, JR IF NO SENSIBLE TAPE SPEED inverted, HL+BC*510 a
sector over, HL=SECTOR on a displacement).  And one defect: the inlined
POIDFT at `&4D42` lost its `LD A,(HL)`, so SAVE over a subdirectory's
name erases the subdirectory (`docs/bugs.md`, 10).  Density 2.4 per
hundred own lines against round six's 11.5, on commentary that had
mostly been reviewed once already.

Two lessons for the next round.  A carried banner is corrected in
the carried-fixes table in `tools/clean.py`, not by a `DOC` -- a `DOC` displaces the carried
header, and three of the banner fixes went in as DOCs before the build's
"carried fix matches 0 places" said so.  And removing a spurious
cross-page reference renumbers the routine's derived labels (`OFSM_1`
went, `OFSM_2..4` became `_1..3`), which `checkdocs` caught in the new
bugs entry and would not catch in prose that merely names one.

Two of the twelve cuts, C12 and RAMD, were also handed to Fable from
another session with byte-identical prompts, for the model comparison
the plan's convergence section wants.  Both pairs audited:

    C12   Opus 4 (2C 2G)   Fable 6 (1C 4P 1G)   shared 1
    RAMD  Opus 5 (2C 2P 1G) Fable 5 (1C 1P 3G)  shared 2

Every finding on both sides confirmed; neither invented anything.  The
overlap is small -- three of eighteen -- and what each found alone is
of the same kind: Opus had the round's one defect (the dead POIDFT test)
and the `&77C4` page misreading; Fable had FLAG3's bit 3 credited to
the wrong record, a 48K snapshot passing CHECK_FILE_TYPE as SCREEN$, and
that both of SDCHK2's exits return carry.  Two reviewers on one region
found nearly twice what one did, and that -- not a difference between
the models -- is the measurable result.  It argues for phase 2's second
passes more than it argues for either model.

The description that follows is what was run.

`build.log` read `1323 still the MasterDOS author's own` for the DOS
reading copy before the sweep, 1312 after.  Those upper-case comments were carried across from the 1991
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

## Phase 2 -- second passes where the first pass found a lot  (run 2026-09-14; round 9)

Both regions re-cut by routine and sent to fresh reviewers with the
round-six brief.  Functions: 4 findings on 276 own lines, none `[C]`.
Load/save: 5 on 432, none `[C]`.  That is 1.3 per hundred against the
11.5 the first pass returned, and the `[C]` share is zero -- the
convergence signature the last section describes, on the two regions
that had the most to find.  One of the nine reversed a round-8 `[P]`
(FSTAT's option 5 is the manual's page rule for every file type, not a
page high for BASIC), which is the second reader catching the first
reader's second reader; the others were softenings and one name.

So a second pass on a reviewed region returns about a tenth of the
first, and what it returns is mostly wording.  Phase 3's fresh regions
are the better use of a reviewer from here.

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
| `&5E00-&6400` -- done 2026-09-14, round 10: 29 findings on 861 own lines (3.4 per hundred), 17 of them `[C]`; the slot chain is a ring, `&62A6` is now EXPAND_SCREEN_FILE, and three claims in `docs/compression-modes.md` were refuted from the bytes | | |
| `&66AE-&69E7` -- done 2026-09-14: 16 findings on 368 own lines, all confirmed; a second shipped defect, the MODE 3 start column (`docs/bugs.md` 11) | | |
| `&4700-&500C` -- three cuts, two done 2026-09-14 (26 findings on 941 own lines, all confirmed; hook 153's broken argument passing is `docs/bugs.md` 12), the middle cut `&49E0-&4C90` out for review after a stalled run | | |
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

- `described N of 2372 labelled addresses` in `build.log` (626 on
  2026-09-13; eleven of the earlier figure were wrapped-comment
  fragments, see phase 0.1).  The other 1700 have a name and, on the DOS
  side, the author's carried header; a
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
