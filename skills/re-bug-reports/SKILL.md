---
name: re-bug-reports
description: Use when writing up a defect found by reading disassembled code rather than by running it — a wrong mask, a swapped restore, a sentinel applied to the wrong field, a dead branch. Carries the entry shape that keeps the claim honest (Where / What / Why that is not an opinion / How it happened / What it costs / Scope / Not observed / Written up at), the discipline of the "not observed" label, and the one part of such a report that audits consistently found wrong. Trigger on "write this bug up", "is this a real bug", "document the defect", "not observed", "what does this cost".
---

# Bug reports from a disassembly

A defect proved from the instructions and never executed is still a
reading.  The report's job is to make the reading checkable and to say
plainly what has not been checked.

## The shape

```
## N. <one sentence naming the fault>

**Where**  address(es) and routine(s)
**What**   the instructions, quoted, and what they do
**Why that is not an opinion**  the evidence that rules out a misreading:
           the only other site that does the same thing does it the
           other way; the reference source has the same bytes with a
           different comment; the value can be shown to be impossible
**How it happened**  where the code came from, if it can be told -- an
           inherited routine, a representation changed and one test left
           behind, a sentinel written for the first field of a loop
**What it costs**  the observable consequence, and its bound
**Scope**  what is and is not affected
**Not observed.**  read out of the instructions, not seen on a machine.
           The test that would show it: what to set up, what to type,
           what to expect.
**Written up at**  the address in the listing where the comment lives
```

## "Not observed" is a label, not a hedge

It says which column of the evidence register this belongs in.  Give
the test concretely enough that someone with the machine can run it
without re-deriving the defect: the array size, the clock setting, the
file name pair.  And mark the ones that are not worth attempting --
inducing a controller error mid-transfer, reaching a stack alignment
that needs fifty pending operands -- so the label is honest about cost
as well as status.

## The part that is usually wrong

All nine defects in one list survived an adversarial audit.  Four of
their *what it costs* paragraphs did not.  The mechanism is the
interesting half and gets the scrutiny; the consequence is written
last, from memory of the mechanism, and gets none.

What failed, specifically:

- A reassurance ("if X was never done the value is zero, which is
  harmless") contradicted by the image, where the value ships non-zero
  and is still non-zero in a post-boot dump.
- A register named the wrong way round, with a conclusion that follows
  only from the right reading -- so the sentence contradicted itself.
- "The previous file's stamp survives in the slot" when the entry
  image is rebuilt from an uninitialised header area before the stamp
  runs, so what survives is garbage, not the previous file's.
- "Five alignments in 256" where there is one, and it needs a stack
  state ordinary use never reaches -- so "the kind of fault that
  survives testing" was backwards: it is the kind that never fires.

Derive the consequence with the same care as the mechanism, and say
which claims in it rest on an assumption.

## Established beyond the code

Where a second binary of the same program exists -- a stock release,
an earlier version -- it can settle whether a fault is inherited or
introduced, and whether a value is a build artefact or a bug.  "The
stock DOS's hook table is genuinely at `&43F3`, so this image's `DVAR
22` pointing there is a relocation left unfixed" is a stronger claim
than the same sentence without the second binary.  Say which binary
each claim rests on; they are not interchangeable.
