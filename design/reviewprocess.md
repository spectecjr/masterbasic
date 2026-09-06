# The review process

*How a second reader is used to check annotations that nothing else can check.*

---

## Why this exists

The build gate is strong and narrow. `tools/build.sh` assembles all six listings
and compares them byte for byte against the original image; six BYTE-IDENTICAL
lines mean every instruction, operand and constant is right.

**It says nothing at all about the commentary.** A comment that describes the
opposite of what an instruction does assembles perfectly. So does a routine
header that explains a mechanism the code does not have, a label named for a job
it does not do, and a table of bit meanings copied from a version of the
software this is not. Every one of those has been found in this project, and
every one of them survived a green build.

The commentary is most of the value of the work and it has no automatic check.
The substitute is a **second reader with no memory of having written it** —
which, in practice, is a subagent given the region and nothing else.

The reason it works is not that the reviewer is cleverer. It is that the author
reads the code through the explanation they already formed, and the reviewer has
no explanation to read it through. Almost every finding so far has been of the
form "the prose says the subtraction goes this way and it goes the other" —
things obvious to anyone who had not already decided what the routine did.

---

## The two shapes

**Proposal.** The region has no commentary. The agent reads it and proposes
comments. Output is a `notes/`-format file written to scratch.

**Review (adversarial).** The region is already annotated. The agent is told
explicitly that it is *not* writing comments, and is hunting for claims the
instructions do not support. Output is a list of findings.

The review is the more valuable of the two by a wide margin. A proposal has to
be checked line by line before any of it can be used, which costs about as much
as writing it; a review arrives pre-filtered to a dozen places worth looking at.
Run the proposal shape only on regions that are genuinely bare.

---

## The rules that do not bend

1. **The agent writes to scratch and nowhere else.** Never into `notes/`,
   `listings/clean/`, `listings/disasm/`, `listings/speculate/`, `tools/` or `docs/`. The prompt says this
   twice. An agent that can edit the repository turns a wrong finding into a
   wrong file, and the wrongness is then indistinguishable from the work.
2. **The agent does not run `tools/build.sh`.** It takes minutes and proves
   nothing about what the agent was asked to do.
3. **Nothing is applied unaudited.** Every finding is checked against the actual
   instructions before a character of it reaches the repository. This is not a
   formality — see the calibration note below for why it is still worth doing
   at a hit rate this high.
4. **Every entry carries a confidence marker**, `[C]` / `[P]` / `[G]`, as the
   last thing on the line. `[C]` means "I can point at the instructions that
   prove it". The prompt must say plainly that a `[G]` costs nothing and a wrong
   `[C]` is the worst possible outcome, or the markers all come back `[C]`.
5. **The first line of every report is the model ID the environment gives it.**
   Not what the model believes it is — what its environment states. This exists
   because a run was once reported under the wrong model's name, and the
   conclusions drawn from it about model choice were therefore worthless.
   Treat that string as a label, not as proof: in the second round every report
   said `claude-fable-5` while the user believed the runs were still on Opus,
   because the enablement had not taken effect. The line is there so a run can
   be *questioned*, not so it can be trusted. Don't credit a model in a commit
   message on the strength of it.

   **The transport is a better witness than the report.** When four of these
   agents died at once, the 429 named the model the API had actually been
   sent — `claude-fable-5-1`. That settled in one line what the `MODEL:`
   self-reports had left ambiguous for two rounds, because it came from the
   plumbing rather than from the thing being asked about itself. Read the
   error text when a run fails; it is the only place the answer is not
   self-reported.
6. **"I found nothing wrong" is a success.** Say so in the prompt, in those
   words. Otherwise the agent pads, and a padded report costs more to audit than
   a short one is worth.

---

## Step by step

### 1. Cut the region out

The agent gets the region as its own file, not a line range in a 20,000-line
listing. Regions here are `PART` blocks, delimited by `;;  PART <name>` banners:

```python
import io, re
L = io.open('listings/clean/masterdos.asm', encoding='utf-8').read().split('\n')
out, inpart = [], False
for l in L:
    m = re.match(r';;\s+PART (\S+)', l)
    if m:
        inpart = (m.group(1) == 'C11')
    if inpart:
        out.append(l)
io.open(SCRATCH + 'c11-region.asm', 'w', encoding='utf-8',
        newline='\n').write('\n'.join(out))
```

Count the lines of *your own* prose in it while you are there (a listing comment
containing a lower-case letter is yours; the 1991 author's are upper case). That
is the denominator for the hit rate afterwards.

**It is not the number that chooses the shape, and using it that way has already
gone wrong.** PART SUBD came out at 16% by this count and was billed as the
thinnest region in either half, fit only for a proposal. It is nothing of the
kind: 150 lines of this project's prose, 145 of the 1991 author's, and 165
banner lines. The measure ignores upper-case comments *by design* — that is what
makes it a fair denominator — so on the MasterDOS side, where every routine
carries the source's own header, it understates total annotation by about half.
The MasterBASIC side has no carried comments and is unaffected.

To choose the shape, count every commented line regardless of case. To score the
round afterwards, count only your own.

Aim for 500–1500 lines. Larger and the agent skims the far end.

### 2. Dispatch

One `Agent` call per region, `run_in_background: true`, several at once — they
are independent. Templates below.

### 3. Audit

```
python tools/review_audit.py <report.txt> [listings/clean/masterdos.asm]
```

This prints, for each finding, the instruction at that address, its bytes, the
comment already there, and the confidence marker — so judging a claim is reading
two adjacent lines rather than three lookups. It also flags:

- **addresses that are not an instruction** — the cheapest kind of wrong, and a
  sign the agent invented rather than read;
- **`DOC` headers naming a label that does not exist** — same;
- **the confidence distribution**, which is the thing to look at first. All-`[C]`
  means the marker instruction did not land and the markers carry no
  information.

Then read every finding against the code yourself. Three outcomes:

- **confirmed** — the fix goes in, usually reworded, because the agent is
  writing to be understood by you and the repository is written to be understood
  by a reader;
- **refuted** — write down why, in the commit message or the audit notes, so the
  same claim is not re-litigated when the next review raises it;
- **partly right** — the commonest interesting case. The agent has found a real
  problem and misdiagnosed it. Take the problem, not the diagnosis.

A finding that touches `docs/` rather than a listing comment is worth more than
one that touches a listing comment, because prose in `docs/` is read by people
who cannot check it against the instructions in front of them.

### 4. Apply, build, commit

Edits go into `notes/clean/*.txt`, never directly into the generated listings.
Then `bash tools/build.sh > build.log 2>&1` in the background — it takes 4–7
minutes — and grep the log rather than watching it. Six BYTE-IDENTICAL lines,
and only then commit.

The commit message names what was found and what was refuted. The refutations
are the part that stops the work going round in circles.

---

## Prompt template — adversarial review

Used close to verbatim for PART C11 and PART C12. Substitute the region, the
address range, the one-line description of what the region does, and the domain
facts specific to it.

```
You are checking someone else's annotations on a reverse-engineered Z80
disassembly of MasterDOS 2.3 for the SAM Coupe. The repository is
c:\repo\masterbasic.

# First line of your report -- before anything else

Write the model ID your environment reports you are running as, exactly as it
gives it:

    MODEL: <id as reported by your environment>

If your environment does not state one, write "MODEL: not stated". Do not infer
it from your own knowledge; report what the environment says.

# The job

You are NOT writing comments. You are looking for things that are WRONG.

Read PART <NAME> (<range>) -- <one line saying what the region is> -- and find
every place where the commentary does not match what the instructions actually
do.

Your input:
- The region, already extracted: <scratch>/<name>-region.asm
- The full listing for context: c:\repo\masterbasic\clean\masterdos.asm
- References, which may themselves be wrong: <the docs/ files that make claims
  about this region>

DO NOT modify any file in the repository. Do not run tools/build.sh.

# Output

Write to exactly this path and nothing else:
<scratch>/<name>-review.txt

# Which comments are whose

- Lower-case prose comments and the `;;` banners were written by the person you
  are checking. PRIMARY target.
- UPPER-CASE comments are the original 1991 author's, occasionally wrong
  themselves. Secondary, still worth reporting.
- <name any docs/ file that makes strong claims about this region>. Check those
  claims against the instructions too -- confirming OR refuting them is equally
  valuable.

# What counts as a finding

1. A claim the instructions do not support.
2. Wrong arithmetic or flag reasoning: a stated value that does not follow, a
   carry or zero flag claimed to go the wrong way, an off-by-one, a mask tested
   in the wrong space.
3. A label whose NAME does not fit what the code does.
4. An internal contradiction between two pieces of commentary.
5. A claim stated as fact but not derivable from the code or the references.

# Format

For each finding:

    &45B2  [C]
    says:  "<the claim, quoted>"
    but:   <what the instructions actually do, with the addresses that show it>
    fix:   <what it should say, if you can tell>

Confidence: [C] provable from the instructions -- [P] probable -- [G] a
suspicion worth a look.

# IMPORTANT -- do not manufacture findings

Most of this commentary is probably correct. A short list of real errors is
worth far more than a long list of quibbles, and a wrong accusation costs more
to check than a missing one costs to leave. If a section is sound, say so and
move on: ending with "I checked X, Y, Z and found nothing wrong" is a GOOD
outcome. Do not pad. Do not report style, wording, or things merely incomplete.

Where you quote a number as evidence -- an offset, a length, a count, a bound --
derive it rather than repeating it from the commentary. A finding that is right
in substance and carries a wrong subsidiary number is the failure mode this
review process has actually suffered from.

# Facts about this machine

<the half-dozen facts without which an operand cannot be read: the paging
model, what an &8xxx address means here, sector geometry, what IX points at,
the controller's status bits if the region touches it>
```

The "facts about this machine" block is the part that decides whether the run is
useful. Without it the agent reads `&8000` as a second part of the DOS, and
every finding about the window is noise. Keep it to the facts an operand cannot
be read without.

**Check the block against a reference before sending it, because it is stated
as fact and will be believed.** One round went out with "bit 5 puts ROM 0 over
&0000-&3FFF" in all four prompts. The Technical Manual's LMPR table calls bit 5
RAM0 — "when bit set high, RAM replaces the first half of the ROM" — so it takes
ROM 0 *out*, and ROM 0 is normally in. `base.asm`'s own preamble carried the
same inversion, while `notes/clock.txt` and `notes/slots.txt` had it right, so
the repository had been contradicting itself in the paragraph a reader meets
first.

One of the four agents caught it, checked the manual itself, and said so rather
than filing a finding against the correct comment it had been primed to
disbelieve. That is the behaviour the "instructions win" rule asks for, applied
to the brief instead of to the listing — and it is worth saying in the prompt
that the facts block is fallible too.

**On the MasterDOS side, hand the agent `ref/masterdos/src/masterdos23.asm` —
and not the annotated tree beside it.** The `src/` file is the 1991 author's own
source, and the upper-case comments in the listing are carried from it, so a
claim about one of those can be checked against what he actually wrote. That is
a reference the MasterBASIC half does not have at all.

**`annotated-src/` is not that, and pointing an agent at it wastes the run.** It
is a parallel copy of `src/` documented as a modern codebase — by this same
effort, with AI assistance, and its own README says in as many words: "Treat the
commentary as a well-evidenced reading of the code, not as the author's own
documentation." Its `PART SUBD` header is word for word the header in this
project's listing. Checking our prose against it is checking a claim against
itself.

This guidance was in this file for exactly one round, saying the opposite, and
the reviewer it was written for caught it and switched to `src/` unprompted.

**Nor does either source settle a byte.** `annotated-src` assembles to
`ref/masterdos/res/MDOS23.bin`, 15750 bytes; this project's listings assemble to
the halves of `dumps/MasterBasicMasterDos.bin`, of which the DOS half is 16320.
Two proofs, two artifacts, and the image is a substantially different build —
`tools/carrydoc.py` exists to track where the two disagree, and reports the
count. So the source is evidence about what a routine *does*, never about what
byte is at an address here.

Two warnings go with `src/`, and both belong in the prompt:

- Where the source and the instructions disagree, **the instructions win** — the
  author is occasionally wrong, and the agent should say when that happens
  rather than deferring.
- **An upper-case comment carried onto the wrong instruction is a finding**, and
  a likely one, because the carry-across is automated rather than read.

---

## Prompt template — proposal

The differences from the review prompt:

- the job is to propose comments, in `notes/` format — `DOS &xxxx : text` for a
  line comment, `DOC LABEL` with four-space-indented prose for a header;
- the house style has to be stated: say **why** not **what**; explain the trick
  when there is one; lead the important paragraph with a short capitalised
  phrase; British spelling; `--` for a dash and never a unicode one; do not
  comment every line, only the lines carrying a decision or a non-obvious
  quantity;
- it ends with a `=== NOTES ===` section listing what the agent could not work
  out at all, anything in the existing commentary it believes is wrong, and any
  label whose name looks wrong for what the code does. That section has been
  worth as much as the proposal above it.

---

## Calibration, and what the score means

| Region | Shape | Entries | Confirmed on audit |
|---|---|---|---|
| PART RAMD (&74C1–&7861) | proposal | 87 comments, 6 headers | — (used as raw material) |
| PART C12 (&4A78–&5010) | review | 12 findings | 12 |
| PART C11 (&4549–&4A76) | review | 12 findings | 12 |
| PART F11 (&595B–&5E75) | review | 13 findings | 13 |
| PART D1 (&4FF0–&549B) | review | 17 findings | 17 |
| PART E1 (&549E–&595A) | review | 17 findings | 17 |
| PART MOVE A/B, HOOKS, RAMD | review | 55 findings | 55 |
| PART F12 + two sweeps | review | — | — |
| PART G1 (&5E78–&61FF) | review | 8 findings | 6 |
| MB &500C–&51D6 (tokens) | review | 8 findings | 8 |
| MB &69E7–&6AD4 (grey DUMP) | review | 7 findings | 6 |
| MB &6C01–&6DF6 (COPY SCREEN) | review | 11 findings | 11 |
| MB &6594–&66AE (CSIZE, compressor) | proposal | 61 comments, 4 headers | — |
| MB &41C5–&42B1 (NVAL) | proposal | 53 comments, 7 headers | — |
| MB &4500–&4700 (classifiers, NR, SORT) | review | 15 findings | 14 |
| MB &6400–&6594 (SAVE BOOT, CSIZE head) | review | 9 findings | 9 |
| MB &5C00–&5E00 (RECORD, ROM-1 builders) | review | 10 findings | 10 |
| MB &7700–&7900 (installer, external memory) | review | 14 findings | 14 |

The first five ran on one model; the rest on another, after the first hit a
session limit mid-run. The prompts were byte-identical across the change,
which is the only reason the two groups can be compared at all — if the brief
had been retuned at the same time, nothing could be concluded from a
difference in yield.

G1 is the first row that is not a clean sweep, and it is the useful kind of
miss: two of its eight findings were stale because the region had been cut
before a rebuild, and *the agent said so* rather than reporting them as
current. The lesson is a process one — re-cut the extract after a rebuild —
and it recurred on the MasterBASIC batch, where five regions cut before the
`base.asm` work still said `CALL CMR` where the listing had come to say
`MBCMR`. Re-cutting also showed which of the five had been annotated in the
meantime, and so which shape to run.

The three MasterBASIC reviews cost one refutation and one deferral between
them. Both are worth more than the tally suggests. The refutation (that
`&BF - B` is a coordinate conversion) is refuted by a sibling case that would
need the same conversion and does not do it — an argument the next reviewer
would otherwise have to reconstruct. The deferral is a generator fault, not a
prose one: two auto-generated "from" lines describe flags for a value a later
`LD A,H` has replaced. Fixing it properly touches every listing, so it is
written down rather than done.

That is 204 of 208 across the review rows, and the first two rounds were a
clean 71 of 71.

The four MasterBASIC regions in the last batch cost one row: region H's
account of `MULTIPLY_BY_100` was right that the routine multiplies by a
hundred and wrong about the range it is exact over. It put the bound at
`HL <= 2621`, reasoning from the `ADD HL,BC` that makes 25x; the carries
that are actually dropped are the four before it, so the bound is
`12*HL` under `&10000`, or `HL <= 5461`. Both callers are inside either
figure, so the finding stood — but the number was going into a banner,
and a banner is where a wrong number stops being checkable.

**That is the case the audit exists for, and it is not the one the rules
describe.** The finding was true, the confidence marker was honest, the
evidence was quoted correctly, and a subsidiary number in it was wrong.
Auditing for fabrication would have passed it. What caught it was
re-deriving the claim rather than reading it, which is a different and
more expensive habit — and the only one that would have caught this.

**The obvious thing it shows:** the annotations had a real error rate, and
forward reading by the author was not finding them. One of the C11 findings
landed on `docs/bugs.md` itself and changed a documented bug from "cannot be
reached" to "is never chosen by the bit it tests" — an error that had been read
past repeatedly. A later round found that every "call the ROM with ROM 1 paged
in" in the repository was wrong about which ROM, while the correct account sat
three files away in an equate comment, a `docs/` page, and the 1991 author's own
remark on the very instruction.

**The less obvious thing:** a rate this high is *not* a reason to stop auditing.
It is the rate at which findings survive an audit, and the reason it is so high
is that the prompt spends a third of its length telling the agent not to guess.
Relax the audit and the incentive that produces the rate goes with it. The audit
is also where the finding gets reworded into the repository's voice, and where
the *partly right* case gets separated from the right one — neither of which the
score measures.

**And the three that did not survive are the ones worth reading.** Two were
stale rather than wrong, from a region cut before a rebuild. The third proposed
a better explanation for a subtraction and was refuted by a sibling case that
would need the same explanation and does not do it. None of them was a
fabrication, which is the failure the brief is actually written against — so the
number to watch is not the rate but whether a miss is ever an invention. So far
it has not been.

A third thing showed up in the second round: a few findings are best applied
as *softenings* rather than reversals. The reviewer shows a claim is not
supported; the honest fix is often "this is not established, and here is what
would settle it" rather than asserting the opposite. Count those as confirmed —
the finding was right — but do not let the tally tempt you into writing a new
claim you cannot support either.

Track the score anyway, per region. A region that comes back with nothing is
evidence the commentary there is sound; a region that comes back with twelve is
a region to re-read by hand afterwards, because a review finds a sample of the
errors and not all of them.

---

## Choosing what to review next

In rough order of return:

1. **Regions where the prose makes strong claims** — a table of bit meanings, a
   documented bug, an explanation of a trick. Strong claims are checkable, and
   they are the ones worth being wrong about.
2. **Regions annotated early**, before the paging model and the idioms were
   understood.
3. **Regions whose commentary was carried from the 1991 annotated source** and
   rewritten rather than derived from the instructions. Rewriting someone else's
   explanation propagates their errors in your voice, which is worse than
   quoting them.
4. Bare regions — proposal shape, and only if genuinely bare.

---

## Things learned the hard way

- **Do not let the agent near the repository.** Scratch only. Twice stated.
- **Report the model from the environment, not from self-knowledge.** A model
  asked what it is will answer confidently and may be wrong; conclusions about
  which model to use are then built on sand.
- **Ask for the confidence marker and explain the asymmetry**, or every entry
  comes back `[C]`.
- **Give the machine facts.** Half a page of paging model turns noise into
  findings.
- **Tell it that finding nothing is a win.** Reviewers pad by default.
- **Give it the region as a file.** "Read lines 4000-5500" produces a review of
  lines 4000-4200.
- **Run several in the background at once.** They are independent and each takes
  a while.
- **Refutations are worth writing down**, or the next review raises the same
  claim and it gets audited twice.

---

## Beyond this project

Nothing above is specific to Z80. The shape generalises to any work where a
machine check proves one property and the valuable property is unchecked:
documentation against code, comments against behaviour, a migration guide
against a schema, a spec against an implementation. The ingredients are

- a **narrow automatic gate** that everyone trusts and that does not check the
  thing you actually care about,
- a **fresh reader** with no access to the reasoning that produced the artefact,
- an **adversarial brief** with an explicit anti-padding clause,
- **confidence markers** with the asymmetry spelled out,
- a **mechanical audit harness** that puts each claim next to its evidence,
- and **an author who applies nothing unchecked**.

Drop any one of them and it degrades into a plausible-sounding second opinion,
which is worse than no second opinion, because it reads like corroboration.
