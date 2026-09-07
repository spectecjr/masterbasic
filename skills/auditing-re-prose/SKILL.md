---
name: auditing-re-prose
description: Use when auditing or correcting the DOCUMENTATION of a reverse-engineering project — how-it-works write-ups, bug reports, design notes, evidence lists — as opposed to the code commentary itself. Prose about disassembled code fails in a different way from the commentary: it is mostly claims that WERE true, beside a tree that has since moved. Carries the seven recurring faults, the stale-value sweep that must follow every correction, and the two signals that a change did not take. Trigger on "audit the docs", "are the notes still accurate", "check the write-up", "sweep for stale figures", "is this document current".
---

# Auditing prose about reverse-engineered code

A code review asks whether a claim about the machine is true.  A
document audit mostly finds claims that *were* true.  Read for these.

## The seven faults

**1. A number with no stated counting rule cannot be audited.**  When
five figures in one section reproduce under no reading of the listings,
it is usually because the rule was never written down -- so a stale
number and a wrong one look exactly alike, and both are present.  Fix:
state the rule in the sentence, or make the build print the number.
Where the generator is the only thing that knows (it assigned the
labels, it classified the bytes), it is the only honest source.

**2. Check the sentences that name their own evidence first.**  "A
dump proves every byte of it" -- naming a dump that held filler at that
address; the evidence was real and lived in a file retired months
earlier.  "The build prints this table so it can be checked rather than
remembered" -- directly above five rows that disagreed with the run
beside them.  These are the most confident sentences and therefore the
least examined.

**3. Mechanisms get scrutiny; consequences do not.**  Every defect in a
bug list survived audit; four of their *what it costs* paragraphs did
not.  The interesting half of a finding is the half that gets checked.
Read the boring half.

**4. A sentence that asserts a thing and then gives a reason can
contradict itself.**  "The low bits cannot carry into the flag bits --
every structure ends in a terminator first" claims a hardware property
in its first clause and gives the real, contingent reason in its
second.  Watch for `because` and a dash joining an absolute to an
argument.

**5. An entry can be overtaken by its own fix.**  A write-up that spends
its second half on faults the entry above it records as fixed, quoting
labels that no longer exist.  When a fix lands, grep the prose for the
*symptom*, not just the label.

**6. Some of what an audit reports as a fault was never one.**  Of the
phantom cross-references collected under one heading, two were genuine.
A phantom and a coincidence look alike from a distance -- which is the
argument for counting rather than estimating, and for checking the
audit as hard as the prose.

**7. The same wrong number is usually in more than one place, and the
way to find the copies is to search for the value you just removed.**
"27 sites" was in two notes files, two generators and both listings,
which contradicted each other.  This is a *step to run after every
correction*, not a thing to be alert to: the person who wrote that
sentence fixed "five runs" in the two places an audit had quoted and
left it in four others, including forty lines below the table just
edited.  Checking the places you changed proves nothing; a corrected
figure tells you nothing about its copies.  Grep the old value across
every prose folder, the tools and the listings, until it is gone.

## Two signals that a change did not take

- **A total that comes back exactly unchanged** after a change that
  should have moved it.  Not close -- identical.  The patch failed, its
  assertion scrolled past, and the build ran on the old code.
- **A total that moves a long way in the direction you argued for.**
  Sample what was excluded before believing it.  A rule that "excluded
  327 sites" had excluded 232 with no symbol in them, because hex
  digits A-F are letters.

## How to apply a finding

Verify it against the instructions or the reference before applying,
including the auditor's subsidiary numbers.  Write the edit as an
exact-match patch built from the file's text, run it in the foreground,
then re-run the prose check.  Then sweep for the old value.

Where a corrected claim leaves a *genuinely* open question behind --
"the vector holds the ROM's own handler in every dump, so what enters
this routine?" -- record it in the evidence register rather than leaving
an absence where a wrong sentence used to be.
