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
twelve-line one that knew `HOOK_ROM_SP` is the ROM's saved stack pointer and
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
none refuted.  The three, closed 2026-09-15: EXDT1_DONE at &6280, a
stale label the old &A280 misreading left and nothing references --
held by two things, the window forms of FORMAT's own LD HL,FTADD at
&45FC, which was not in the pinned list, and a cross-page reference
recorded before the `expr` note on MB &5352 withdrew it, and
drop_unused_labels now discounts both (the MB's own NEXT_SOURCE_NIBBLE_1
at &6280, the same coincidence from the other side, went with it); two
source continuation lines rendered as banners above EVPR5 and WFODB,
put back on the JP NC,IOOR and JR NC,WIOOR they belong to with DOCs
for the two labels; and the carried FNDI2 at &7925, three instructions
from where the source put it, moved to the EVNAMX at &791A by the
misplaced-labels table in dis_mb.py's load().  With them, three observations left by
later rounds: the CSIZE fix-up's UWBOT comment now says heights 97 to
176 fall through it; the directory-entry numbering says once, at
DFMTA and FESET, that the source counts from one and the prose from
zero; and FN_EQU's &4D52, an orphan DEFB &CD because the trace had
followed the JP &4D53 at &5D2F -- a system-page address -- into the
byte after it, is a CALL again (no_follow on that one JP, and
split_entries told the same).  The reviewers' own verdict
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

**Phase 3 record (2026-09-14, round 10).**  Sixteen cuts, 6,743 own
lines, 182 findings, 178 confirmed -- 2.7 per hundred lines, 57% of
them `[C]`.  Every cut returned something the bytes disproved, and the
reach went past the region several times: two operands that were
another page's addresses wearing this page's labels, a banner shared
by both halves wrong for both, a DOS equate misnamed from this side, a
"table" that was the ROM's channel hook byte for byte, a generator rule
for branches leaving relocated blocks, and the 97 bytes hook 185
copies at run time turning out to be the DOS file's, not this page's.
Three items stand open in phase 4.  The stopping signal in
"Convergence" has not shown: the `[C]` share is 57% over the sixteen
cuts with the confirmed rate at 98%, and the two lowest-`[C]` cuts (the
compiler and the proposal-only regions, a third each) still returned
provable errors.

Reviewed so far, by address: `&41C5-&42B1` and `&6594-&66AE` (proposals
only, never reviewed), `&4500-&4700`, `&500C-&51D6`, `&5C00-&5E00`,
`&6400-&6594`, `&69E7-&6AD4`, `&6C01-&6DF6`, `&7700-&7900`.  Never read
by a second reader, in the order they are worth doing:

| Range | What is there | Why this order |
|---|---|---|
| `&5E00-&6400` -- done 2026-09-14, round 10: 29 findings on 861 own lines (3.4 per hundred), 17 of them `[C]`; the slot chain is a ring, `&62A6` is now EXPAND_SCREEN_FILE, and three claims in `docs/compression-modes.md` were refuted from the bytes | | |
| `&66AE-&69E7` -- done 2026-09-14: 16 findings on 368 own lines, all confirmed; a second shipped defect, the MODE 3 start column (`docs/bugs.md` 11) | | |
| `&4700-&500C` -- three cuts, done 2026-09-14: 36 findings on 1411 own lines, all confirmed; hook 153's broken argument passing is `docs/bugs.md` 12, and the LOCN entry there lost its "reports a match" consequence to the carry it had not followed | | |
| `&51D6-&5C00` -- three cuts, done 2026-09-14: 37 findings on 1481 own lines, all confirmed, 21 of them `[C]`; two operands had been read as this page's labels when they were the DOS's DRPT-1 and the system page's HKC_LPRINT_BYTE stub, the routine labelled as a far-memory scan hook was BLITZ SOUND's body, and the ALTER argument comments had the calculator stack's order backwards.  All three reviewers stalled at the 600-second watchdog and were resumed; the template now tells them to read a routine at a time | | |
| `&42B1-&4500` -- done 2026-09-14: 7 findings on 248 own lines, all confirmed; the shared CMR banner had both halves "paging the ROM back in" when they put the system page in section B, and CHAR_MUST_BE_C's "not stepped past" was the opposite of the fall-through | | |
| `&6DF6-&7700` -- three cuts, done 2026-09-14: 26 findings on 1144 own lines, 25 confirmed and one judgement call (hook 185's name, settled in phase 4) left; DELETE's paging comment was inverted, hook 183 is EDIT handing the line to INPUT, the two borrows in the string mover were described as one, and the DOS's equate calling `&30` a screen page was MasterBASIC's own page mark, `MB_PAGE_MARK` now | | |
| `&7900-&7FC0` -- two cuts, done 2026-09-14: 22 findings on 826 own lines, all confirmed.  `&7D57` was a "table" that is the ROM's AT/TAB channel hook byte for byte; a JR leaving a relocated block had manufactured a caller (the generator now writes those as `$+n`, which also undid three fictional labels in CMD_PAUSE's interleaved blocks); and the 97 bytes hook 185 copies from `&7E03` at run time are the DOS file's `&7D73-&7DD3`, EDIT's body, which the DOS listing shows as DEFBs -- read in phase 4 | | |
| `&41C5-&42B1`, `&6594-&66AE` -- done 2026-09-14 as one cut: 9 findings on 404 own lines, 8 confirmed and one code observation left (CSIZE's UWBOT fix-up and heights over 96); the SAVE block copiers were said to call SVBLK and call an unlabelled DOS entry that leaves the last sector in the buffer for the next block, now `HSVBK_DWAIT` | | |

Aim for 800-1200 lines a cut, and cut by routine (phase 0.2).  A reviewer
that reads the whole cut before writing anything can sit past the harness's
600-second no-output watchdog and be killed; a resume with "continue from
the last routine you wrote" recovers it with its context intact, and the
template now asks for one routine per read and an append after each.  The facts
block in the prompt needs the MasterBASIC additions: the installed blocks
and their addresses in the system page (`notes/mb-postboot.txt` has the
map), what `CALLDOS` leaves in the alternate registers, and that the
manual (`docs/masterbasic-manual.md`) is a transcript to check claims
against rather than a claim itself.

---

## Phase 4 -- the countable backlog

Bounded jobs, good between rounds or when a round is out for review:

- **EDIT's body -- done 2026-09-14.**  The DOS file's `&7D73-&7DD3` is
  `EDIT_INSERT_VALUE_BODY`, with the 97 bytes decoded and read in its
  banner: clear `EDIT_PENDING`, return if it was clear or FLAGX says the
  variable is new, else STR$ a number, open room at KCUR and FARLDIR the
  value into the edit line with the cursor after it -- the manual's EDIT.
  `postinstall-syspage.asm` decodes it at `&4F13`, where the DOS's tail
  puts it; the DOS listing keeps the DEFBs because FIND_ROM_CODE's
  boot-time label lands mid-instruction.  Hook 185 is `HOOK_EDIT_INSERT`,
  and the five spare ROM bytes MasterBASIC uses between LSOFF and SPOSNU
  have names (`EDIT_PENDING`, `REF_MATCH_END`, `REF_CURSOR`,
  `EDITOR_RETURN`, `SAVED_CHANNEL_OUTPUT`).  Not traced: where the planted
  routine's final RET lands.

- `described N of M labelled addresses` in `build.log` -- two lines
  since 2026-09-14, because the one line was counting the working copy's
  headers while README quoted it as the reading copy's, and twenty-three
  new DOCs did not move it: 666 of 2345 in the working copy, 772 of 2341
  in the reading copy.  Most labelled addresses are derived internal
  labels and variables that want no banner; the routine heads without
  one, reached from afar, come to about 200 in the DOS (REP stubs, the
  PMO family, hook entries, micro-entries that fall into the routine
  below) and a few dozen in MasterBASIC, thunks mostly.  Do it by PART,
  and send each PART for review once it is written -- that is what
  round six was.  **Round 11, 2026-09-14**: every DOS PART's routine
  heads bannered -- C11 (23), C12 (11), D1 (10), E1 (11), F12 (19),
  G1 (24), MOVE (23), F11 (12), SUBD (9), RAMD (11), HOOKS (10) -- and
  the 25 REP stubs and 16 PTM message stubs, being one shape each,
  take generated headers (the error code and message; the decoded
  text).  All eleven PARTs reviewed, 2026-09-14/15: 52 findings on
  4969 own lines, 48 applied; nineteen were on the new banners, which
  is the point of sending them -- TGT1 was the once-per-entry poll,
  AHLNX's rotate ran backwards, WIORH's limit was 159 not 158, STPDX's
  A = 0 is 256 rounds, a generated message header decoded a run-time
  buffer, the error texts had come through a twenty-character equate
  cut, DSCHD had the header coming from the disc entry when the hook's
  registers supply it, SCASD was called a save, HDUMMY at &66CE is not
  this build's placeholder, EVMOV is either operand, CLOSE here is
  CLOSE *n, SF1S is ERASE's and PROTECT's not DIR's, RDCE is fallen
  into, CFMI counts into DE, NSTKAH's JR Z is dead in this build, and
  HOC0 never sees a floppy.  The other thirty-three were on prose
  reviewed once before, and every carried comment in every PART sits
  on the instruction the author wrote it against.  Four [G]s left as
  observations (design/reviews.csv).  **MasterBASIC, 2026-09-15**: 55
  heads without a banner, of which 17 are one shape each and take
  generated headers -- the twelve CALL_x ROM thunks (CALL MBCMR, a
  word, RET: the ROM's own description of the routine and the caller
  count) and the five hook stubs that are RST &08 and a code (the hook
  and its handler) -- 29 are written by hand in `notes/clean/
  mb-heads.txt`, one (SORT_TAIL, a patched operand) is a `site` now,
  and 8 are branch targets inside their own routine
  (VARIABLE_BODY_BY_KIND_ADD, STAMP_DATE_FIELDS, DUMP_INVERT and the
  like) that want no banner.  Reviewed as one cut: 12 findings, all
  applied -- the PUT pieces had GRAB and PUT swapped twice, the
  generated caller counts were from d.xrefs (which drops an operand an
  `expr` rewrote, and a CALL the listing shows as DEFB) and are from
  the instructions now, and three thunks nothing calls had said "One
  caller".  **The banner item is done**: every routine head reached
  from outside its routine, in both halves, has a banner, and every
  one of them has been reviewed once.  Reading copy: 997 of 2339.
- **The synthetic labels -- 138 to 19, done 2026-09-14** (`grep -c
  '^[LV][0-9A-F]\{4\}:$'` on each clean listing).  Three commits.
  MasterBASIC's 31 patched sites are named for what their operands
  become, from the resolver's own signature results, and a `site` kind
  in the notes syntax keeps such a name from parenting the derived
  labels after it -- the first attempt re-parented the string mover's
  internals wholesale.  The DOS's 55 fell to 9 by two generator rules:
  a page declares its data blocks (NSTR1, UIFA, the channel record)
  sized from the source, so a reference inside reads `NSTR1+2`; and
  after emit a synthetic label that no operand in either half names is
  dropped, since the cross-reference alone was keeping a synthetic name on
  a byte every reference calls `FSA+210`.  MasterBASIC's variables at
  `&4061-&40AD` are named where one mechanism owns the byte (the two
  interrupt-fed buffers' four pointers each, SORT's best-element
  pointer and page, REF's kind and case pair, the clock's text).  What
  is left is deliberate: ten words at `&4098-&40AD` that SORT, LOCN,
  INARRAY, JOIN TO, DUMP and the compressor share as scratch, where any
  one command's name would lie for the others; the source's own
  `L41FF`; and `V7CFF`, the one byte of the sector area a MasterBASIC
  routine reaches by number from outside the installer.  The eight
  labels in the DOS's tail that were the installer addressing its own
  copy are gone: a call or jump from inside the installer into the copy,
  and seven listed data operands, now read as the source address plus
  `INSTALLER_COPY` (&461F); the installer's other &BCxx operands --
  DRIVE, PTH1, PTH2 -- are the DOS's variables under the copy and stay
  so, which the first version of the rule got wrong.
- **The two lists -- done 2026-09-14.**  `describedtwice.py`'s 39 pairs
  were read against each other and the code: four disagreed
  (CHECK_FILE_TYPE's declaration had the SUB/ADC arithmetic separating
  "the three SAM types" when it folds `&11` and `&12`, the two array
  types, into one refusal; WAIT_DC_READY_BEFORE_CMD's two texts each
  described half the routine; PARSE_STRING_AND_OPTIONAL_ABS's had a
  subscript and a left bracket where the code wants a comma then ABS's
  two bytes; READ_KEY_LINE's did not say which row `&FFFE` is) and are
  reconciled.  `deadnotes.py`'s three lost notes were `:` lines on
  rendered data -- two calculator literals and a keyword-list
  terminator -- that the renderers never consulted; the emitters now
  do, and the fpcalc renderer runs at emit time so the note is there
  to read.  Its one "duplicate" was a clean-tree note over a shared
  one, which is the override design, so it now counts only two notes
  in the same tree.  `deadnotes` prints nothing now and `describedtwice`'s
  pairs agree; run both after each round.
- **The DOS's inline words -- done 2026-09-14.**  The five that read
  as numbers with nothing on the line (`&C000` in SNLEN, `&4A9D`,
  `SLDEV+1`, `&4A97`, MTBLS's two stub addresses) each have a `:` line;
  the thirty-one `DEFW &0000` are run-time-filled operands and say so
  already.  The same pass on the other side found five DOS entries
  MasterBASIC reaches by number through CALLDOS that had no label --
  `READ_NEXTST_BC`, `READ_HKDE_DE`, `HLDBK_NO_EXX`,
  `PLANT_TYPE_THEN_GOFSM`, `FN_LENGTH_CHANNEL` -- so those `DEFW`s now
  read as the DOS label less &4000 like the rest.  MasterBASIC's own remaining
  numeric `DEFW`s are NR parameters whose CALL line explains them, and
  the four-line tables at `&610E`.

---

## Phase 5 -- second passes on MasterBASIC  (begun 2026-09-15; round 12)

Phase 2's rule applied to phase 3: a cut that returned twelve or more
findings is read again by someone fresh, with the same brief and a
paragraph saying it is a second pass and not to look for the first
reader's findings.  Six of the sixteen qualify -- MB-A (15), MB-B (14),
MB-C (16), MB-D (15), MB-G (18), MB-O (12) -- re-cut from the current
listing over the same ranges (`scratchpad/phase5/`).  What the pair
measures is in "Convergence": phase 2's second passes came in at 1.3
per hundred against 11.5, with no `[C]`, on DOS prose that had a
source to check against; these have none, and the first pass was 2.7
per hundred with 57% `[C]`, so the second-pass figure here is the one
that says whether the MasterBASIC prose is converging or merely
sampled.

**Phase 5 record (2026-09-15, round 12).**  Six cuts, 2807 own lines,
46 findings, all confirmed and applied -- 1.6 per hundred against the
first pass's 2.7 on the same regions, with 41% `[C]` against 57%.
That is not phase 2's collapse to 1.3 and zero `[C]`: the second
readers found provable errors in every cut, and three of them change
a reading rather than a number -- the thirteen bytes after
LOAD_RETURN_STUB are DEF KEYCODE's syntax-time hook and not dead
copy; WRITE_SCREEN_NIBBLE is the decoder's only write to the bitmap;
a double-strike DUMP 3 prints its second strike a dot or two out
(`docs/bugs.md` 13).  Two generator faults surfaced through them: a
jump out of a relocated block to a system-page address outside the
block's copy was still followed (the `no_follow` set; it had split
CALL WAIT_FOR_CLOCK at &4A83 into a DEFB and two phantoms, the split
the clock notes had been apologising for), and the synthetic namer's
error-exit rule had never fired for `RST &08`.  So the MasterBASIC
prose is converging -- the density fell by two fifths and the `[C]`
share with it -- but it is not there, and the ten cuts that returned
under twelve the first time have not had a second reader at all.

**The other ten, 2026-09-15/16.**  Six back so far -- E, F, H, I, J,
K: 42 findings on 2473 own lines, all confirmed and applied, 1.7 per
hundred with 45% `[C]` -- on cuts that had returned 7 to 11 the first
time.  So a low first count was not a clean region: the second
reader's rate on these is the same as on the six that returned the
most.  Among them a fourth suspected defect (`docs/bugs.md` 14,
ADJUST_VARIABLE_SIZE's subtract path drops its borrow), bugs.md 6
confirmed from the bytes, CMD_DELETE entered on the token rather than
the name, and four derived labels parented on the wrong routine.  Two
of the findings were this round's own: a wrapped `:` line half
replaced, and HPRTOK's paragraphs attached to the wrong label by an
indented block after a `:` line -- the notes syntax lets that happen
silently.  L, M, N and P, 2026-09-16: 19 findings on 1348 own lines,
17 applied, 3 `[C]`; the weekly limit killed the first two readers
mid-read and they were sent again.  The installer's "&4A bytes zeroed
from &4068" is seventy-four stores to one byte; the drive probe
overwrites TRAKS2 with zero when the controller does not answer, which
`docs/evidence-wanted.md` had as "left alone"; and the worked example
in `docs/compression-modes.md` chose an escape the scan cannot choose.

**Phase 5 is done.**  Sixteen cuts, 6628 own lines, 107 findings, 105
applied: 1.6 per hundred against the first pass's 2.7, with 38% `[C]`
against 57%.  Every cut returned something, the low-count cuts as
much as the high; nine findings changed a reading and two added
suspected defects.  What the second pass found most was not
arithmetic but *attribution* -- the right fact credited to the wrong
routine, register, page or path: "the ROM's CMR" for this half's
MBCMR, "the caller kept BC" for a routine that returned it, "this
page" for the DOS's, a stepper for the decoder's only write.  The
first readers checked numbers; the second checked who does what.

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

**Round 12 (2026-09-16), the MasterBASIC second passes, is the first
reading of that signal on this half**: 1.6 per hundred against 2.7 on
the same regions, `[C]` at 38% against 57%, confirmed at 98%.  The
`[C]` share is falling with the confirmed rate holding, which is the
shape the paragraph above asks for -- but on one round, not two, and
the density is still above phase 2's 1.3 on the DOS.  A third pass on
the two or three MasterBASIC cuts that returned most this time (G, O,
E) would say whether the curve continues; the DOS's other PARTs have
had one carried-comment pass and one banner pass each, and no second
reader of the lower-case prose since round 8 except the two in phase
2.  Either is a round's work.  What neither can find is what a
machine would: the four suspected defects in `docs/bugs.md` and the
open items in `docs/evidence-wanted.md`.
