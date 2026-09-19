# Finishing the reading copy  (written 2026-09-18)

The review process is closed (`reviewplan.md`, phase 7): every region
of both halves has had its carried comments swept, its banners read,
two lower-case readers and a claims pass, and a third reader on the
worst cuts returns 0.4 findings per hundred lines.  Everything that
can be run under the emulator has been run.  What is left is not
accuracy but *shape*: `listings/clean/` still reads in places like the
working copy with the arguments cut out, rather than as a document
written for someone arriving cold.  This is the plan to fix that and
then stop.

Nothing here touches a byte.  Every step is notes, a generator rule,
or prose; the gate is `bash tools/build.sh > build.log 2>&1` printing
**6 BYTE-IDENTICAL** and `N prose files check out`, and every step
commits on its own green build by pathspec, as `CLAUDE.md` says.
Where a step adds a rule, the rule goes into a check (`checkdocs`,
`notes.py`, or a new line in `build.log`) so that it stays true after
this plan is done.

Read this file, `CLAUDE.md` and the top of `reviewprocess.md` before
starting.  Read the top 60 lines of both reading copies as a stranger
would; that is the audience.

---

## 1. Give the MasterBASIC half a shape

**Problem.**  `listings/clean/masterdos.asm` has eleven `PART` banners,
carried from the 1991 source, so a reader can find "the disc
controller" or "the RAM discs".  `listings/clean/masterbasic.asm` has
935 routine dividers and no sectioning at all: 22,000 lines with
nothing between the file header and the first routine to say where
the commands are, where the functions are, where the installer is.

**Do.**

- Add a notes kind for a section banner that is this project's own,
  not carried.  Proposed syntax, in `notes/clean/mb-parts.txt`:

      MB &4000 PART The variables and the boot
          Text of the banner, indented as a DOC is.

  `notes.py` reads it like a bare-address banner but the emitter
  renders it in the `;;  PART` style the DOS listing already has, so
  `cutregion.py --part` works on both halves unchanged.  Check first
  whether `carrydoc.py`'s `sections()` output and the emitter's banner
  code can be reused rather than duplicated.
- Choose the parts from `docs/how-it-works.md`'s map of routines by
  area (the table near line 379) and from the order the code is
  already in.  Ten to fourteen parts; each banner three to eight
  lines saying what the part holds and where it is entered from.
  Name them the way the DOS parts are named (a short code and a
  title), so `reviews.csv` and `cutregion.py` can refer to them.
- Put a **table of contents** at the top of each half, generated from
  the part banners: code, title, address range, first routine.  For
  the DOS this is new too.  Generated, not typed, so it cannot drift;
  `build.log` prints the count of parts per half.
- After the parts exist, run `python tools/claims.py MB --top 20`
  once more: a section banner is new prose and carries the
  first-pass rate.  Audit as always.

**Done when** both reading copies open with a contents table, every
routine in the MasterBASIC copy sits under a part banner, and
`cutregion.py MB --part X` cuts by it.

**Done, 2026-09-18.**  Three departures from the proposal, each a
judgement call.  The notes are `notes/mb-parts.txt` and
`notes/dos-parts.txt`, shared rather than clean-only, so all three
trees carry the same shape and `cutregion.py --tree` works on any of
them.  Seventeen parts, not ten to fourteen: the code's own order
makes the divisions, and merging neighbours to hit a number would
have put SORT under the clock or the compile pass under JOIN.  And
one DOS part added, `B1`, with the annotated source's title: the boot
and the two entries sat outside every part, and the check that no
label precedes the first PART (`checkdocs.py check_parts`) would have
failed the DOS half without it.  The section banner is its own table
(`d.parts`), emitted above the routine's header rather than folded
into it, so a routine that opens a part keeps its banner and nothing
written at the same address can displace the heading.
`carrydoc.py`'s `sections()` was not reusable: it reads the source's
rule lines, which MasterBASIC has none of.  `build.log` prints
`DOS -- 12 parts` and `MB -- 17 parts`.  The banners had their
second reader (round 18 in `reviews.csv`): fifteen findings in 542
lines, all confirmed -- 2.8 per hundred, the first-pass rate this
plan predicted, and the reason step 4's claims cut on changed prose
is not optional.

## 2. One voice in the reading copy

**Problem.**  The working copy's diary leaks into the reading copy:
"an earlier reading of this had both branches the wrong way round"
(three in MB, eight in DOS), references to `notes/*.txt` files
(nineteen in MB, three in DOS), `carrydoc`, "the listing" talking
about itself.  The reading copy is for conclusions; the working copy
(`listings/disasm/`) is where the argument lives and where those
sentences belong.

**Do.**

- Grep the clean tree for the diary words and decide each case:
  most move to the working copy (a `notes/` entry can carry both, the
  clean-tree override dropping the diary sentence), a few become a
  plain statement of the conclusion.  Start with these patterns and
  add what turns up:
  `earlier reading`, `used to`, `notes/`, `carrydoc`, `this note`,
  `the listing`, `round `, `reviewer`, `docs/` (a reference to a doc
  is fine when the doc is the place the reader should go; a reference
  to a *note file* is not).
- Add the rule to `checkdocs.py`: the clean listings may not contain
  `notes/`, `carrydoc`, `earlier reading`, or `round N`.  It runs in
  the build already; a fault fails the prose check.
- Keep the "read, not run" caveats -- they are honest -- but say them
  one way.  Pick the phrase (`Read from the bytes, not run.` is in
  use) and make the others match.

**Done when** the check passes and a reader of the clean tree is never
sent to a file that is not in `docs/`.

## 3. The author's comments, declared once

**Problem.**  1,304 upper-case lines in the DOS reading copy are the
1991 author's, verified in place beside our lower-case prose; the
MasterBASIC copy has three.  The convention -- upper case is his,
lower case is ours, `;;` blocks are ours -- is stated in the review
briefs and in `CLAUDE.md`, not in the listing a reader holds.

**Do.**  One paragraph in each reading copy's header, and one in
`docs/disassembly.md`: whose the two voices are, that his shorthand
is kept as written and is right about this build unless a lower-case
comment on the same line says otherwise, and that "PROB NOT NEEDED"
is him.  Also fix the header itself: the doubled `; ;` at line 15 of
the MasterBASIC copy, and the runs of blank lines (up to twelve) after
it -- the emitter should collapse a run to one.

## 4. An editor's pass

**Problem.**  Every pass so far read for truth.  Nobody has read for
consistency of terms -- "this half", "this page", "the DOS page", "the
other half", "MasterBASIC's page" are all in use for the same two
things -- or for register (some banners are essays, some are
shorthand), or for length.

**Do.**  One reader per half, Opus, with a brief that is *not* the
review brief: it asks for terms used inconsistently, sentences a
stranger cannot parse, banners that restate what the line comments
under them already say, and banners longer than the routine they
head.  It does not ask for errors.  Findings are applied through the
notes as always, and the terms chosen go into `design/cleanstyle.md`
as the house style.  Then `tools/claims.py` on the prose the pass
changed, because a rewrite is new prose.

Two readers, two audits, one round.  Record it in `reviews.csv` as
round 19 with shape `edit`, and teach `reviewlog.py` the shape as it
was taught `claims`.

## 5. The residue, stated once

Scattered today: 19 synthetic labels (`grep -c '^[LV][0-9A-F]\{4\}:$'`
on each clean listing), `CKESV_1`'s open reading (`CLAUDE.md`), the
deferred findings (the rows of `reviews.csv` with a non-zero last
count), bugs 1, 2, 4 and 9 and evidence-wanted 10d and 10h-j.

**Do.**  A section "What is not known" at the end of
`docs/disassembly.md` listing every one of them with where it is
written up, and why it stops there.  Short.  README points at it.

## 6. Freeze

- Final figures into README and `docs/disassembly.md`, quoted from
  `build.log` and `reviewlog.py`, not computed by hand (`CLAUDE.md`
  says why).
- `docs/evidence-wanted.md`'s recipes (emulator, printer, debugger)
  are the reproduction procedure; check they still run from a clean
  checkout once, with the emulator, before tagging.
- Tag the release.  A tag name that says what it is:
  `mdmb17-annotated-1.0`.

## Optional, and the largest readability win of all

An HTML rendering of both reading copies with every label reference
linked to its definition, every `DOS_`/`MB_` cross-page name linked
into the other half, and every ROM name linked to the line of
`ref/samrom/` that defines it.  The listing is 40,000 lines and a
reader navigates it today by search.  This is a new tool
(`tools/render.py`), read-only over the clean tree, and can be done
after the tag without disturbing it.  Not part of "done".

---

## Order and cost

1, 2 and 3 first: mechanical, and the build can enforce them.  Then
4 as one reviewer round with a different brief.  Then 5 and 6.  About
two sessions.  Every step is a commit; if the plan stops in the
middle, what is committed is still better than what preceded it.

## What not to do

- No new region reviews for accuracy.  `reviewplan.md` phase 7 says
  why; the claims cut on *changed* prose is the only review this plan
  asks for.
- No renaming for taste.  A generated name needs the grep and the
  label diff that `CLAUDE.md` describes, and every rename is new prose
  in every place the old name was.
- No editing of `ref/masterdos/` (a submodule; a wrong carried
  comment goes through `clean.py`'s carried-fix table) and no editing
  under `listings/` (the hook denies it; everything is notes and
  generators).
