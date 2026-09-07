---
name: adversarial-review
description: Use when reviewing the commentary on a disassembly or any annotated listing by dispatching agents to find what is WRONG in it — not to write more. Carries the rules that do not bend (scratch only, never the build, nothing applied unaudited, confidence markers, "nothing wrong" is a success), the step-by-step (cut the region, dispatch several in the background, audit every finding against the instructions, apply through notes), the prompt template with its machine-facts slot, and what the score means. Trigger on "review this region", "audit the commentary", "adversarial review", "dispatch reviewers", "check the annotations".
---

# Adversarial review of listing commentary

The agent is not asked to write.  It is asked to find every place the
commentary does not match what the instructions do, and to say so with
a confidence marker.  A short list of real errors is worth more than a
long list of quibbles.

## The rules that do not bend

1. **The agent writes to scratch and nowhere else.**  Never into the
   notes, the listings, the tools or the docs.  Say it twice in the
   prompt.  An agent that can edit the repository turns a wrong finding
   into a wrong file, and the wrongness is then indistinguishable from
   the work.
2. **The agent does not run the build.**  It takes minutes and proves
   nothing about what the agent was asked to do.
3. **Nothing is applied unaudited.**  Every finding is checked against
   the actual instructions before a character of it reaches the
   repository -- at any hit rate.  Auditors have been wrong in ways that
   only reading the code exposes: a region placed in the wrong tree,
   phantoms that were never phantoms, a right conclusion carried on a
   wrong subsidiary number.
4. **Every finding carries `[C]` / `[P]` / `[G]`** as the last thing on
   its line.  `[C]` means "I can point at the instructions that prove
   it".  The prompt must say plainly that a `[G]` costs nothing and a
   wrong `[C]` is the worst outcome, or every marker comes back `[C]`.
5. **The first line of the report is the model ID the environment
   reports.**  Not what the model believes it is.  Treat it as a label
   that lets a run be questioned, not as proof; the transport (a 429,
   an error body) is a better witness than the self-report.
6. **"I found nothing wrong" is a success.**  Say so, in those words.
   Otherwise the agent pads, and a padded report costs more to audit
   than it is worth.

## Step by step

**1. Cut the region out.**  The agent gets it as its own file, not a
line range in a 20,000-line listing -- "read lines 4000-5500" produces
a review of lines 4000-4200.  Aim for 500-1500 lines; larger and the
far end is skimmed.  Cut it *immediately before dispatch*: a region
cut before a rebuild produces findings that are stale rather than
wrong, and they cost the same to audit.

**2. Dispatch.**  One agent per region, in the background, several at
once -- they are independent.  Template below.

**3. Audit.**  A small script that prints, for each finding, the
instruction at that address, its bytes, the comment already there, and
the marker, so judging a claim is reading two lines rather than three
lookups.  It should also flag: addresses that are not an instruction
(the cheapest kind of wrong, and a sign of invention); headers naming a
label that does not exist; and the confidence distribution -- all-`[C]`
means the marker instruction did not land.

Then read every finding against the code.  Three outcomes:

- **confirmed** -- the fix goes in, usually reworded, because the agent
  writes to be understood by you and the repository is written for a
  reader;
- **refuted** -- write down why, so the next review does not re-raise
  it and it gets audited twice;
- **partly right** -- the commonest interesting case.  A real problem,
  misdiagnosed.  Take the problem, not the diagnosis.

A finding that touches prose is worth more than one that touches a
listing comment: prose is read by people who cannot check it against
the instructions in front of them.

**4. Apply through the notes, build, commit.**  Never edit a generated
listing.

## What the score means

Keep a table: region, shape, findings, confirmed on audit.  Over a
whole project the confirmation rate ran above 95%.  Two things that
number does *not* mean:

- It does not mean auditing can stop.  The 5% included a region that
  did not exist in the tree the auditor named, and a paragraph whose
  conclusion stood on a wrong number.
- A finding right in substance and wrong in a subsidiary figure is
  **not confirmed**.  That is the failure mode this process actually
  suffers from, and scoring it as a hit hides it.

## Prompt template

Substitute the region, the range, one line on what it does, and the
machine facts.  The facts block is what decides whether the run is
useful: without it, every finding about paging or windows is noise.

```
You are checking someone else's annotations on a reverse-engineered
<CPU> disassembly of <program>.  The repository is <path>.

# First line of your report -- before anything else
    MODEL: <id as reported by your environment>
Do not infer it; report what the environment says, or "not stated".

# The job
You are NOT writing comments.  You are looking for things that are WRONG.
Read <region file> (<range>) -- <one line on what it is> -- and find every
place where the commentary does not match what the instructions do.

Input: the region at <scratch>/<name>-region.asm; the full listing for
context at <path>; references, which may themselves be wrong: <list>.
DO NOT modify any file in the repository.  Do not run the build.

# Output
Write to exactly <scratch>/<name>-review.txt and nothing else.

# Which comments are whose
<lower-case prose is the reviewee's: PRIMARY.  Original-author comments,
if carried: secondary.  Name any docs making strong claims here.>

# What counts as a finding
1. A claim the instructions do not support.
2. Wrong arithmetic or flag reasoning: a value that does not follow, a
   carry or zero flag the wrong way, an off-by-one, a mask tested in the
   wrong space.
3. A label whose NAME does not fit what the code does.
4. An internal contradiction between two pieces of commentary.
5. A claim stated as fact but not derivable from the code or references.

# Format
    &45B2  [C]
    says:  "<the claim, quoted>"
    but:   <what the instructions do, with the addresses that show it>
    fix:   <what it should say, if you can tell>
[C] provable from the instructions -- [P] probable -- [G] worth a look.

# IMPORTANT -- do not manufacture findings
Most of this is probably correct.  A wrong accusation costs more to check
than a missing one costs to leave.  If a section is sound, say so; ending
with "I checked X, Y, Z and found nothing wrong" is a GOOD outcome.  Do
not report style or things merely incomplete.  Where you quote a number
as evidence, DERIVE it rather than repeating it from the commentary.

# Facts about this machine
<the half-dozen facts without which an operand cannot be read: the
memory map and paging model, what an address in some range means here,
what each index register points at, the status bits of any controller
the region touches, which dump is which>
```

## Things learned the hard way

- Give the machine facts; half a page turns noise into findings.
- Give the region as a file.
- Ask for the marker *and explain the asymmetry*.
- Refutations are worth writing down.
- A corrected fact in the facts block invites over-application: an
  agent told "bit 5 set takes ROM 0 out" will start reading every `&1F`
  as a paging value.  State the fact, and state where it does not apply.
