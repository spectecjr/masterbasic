---
name: evidence-register
description: Use when a reverse-engineering project has questions that reading the code cannot settle — what enters a vector, what a field holds at run time, whether a defect fires — and you need to keep them so that someone with the hardware can close them. Carries the entry shape (what is open, what is already known, what would settle it, what it costs), the at-a-glance table, the separation of "needs a capture" from "needs a machine and a line of BASIC" from "turned out to need no evidence at all", and the trap of a dump named in prose that does not hold the bytes. Trigger on "what evidence do we need", "open questions", "what would settle this", "what dumps do we have", "hardware test".
---

# The evidence register

One document, `docs/evidence-wanted.md`, holding everything reading
alone could not settle.  Its job is to be worked from by someone with
a machine, so every entry ends with an action.

## An entry

```
## N. <what is open, as a question>

**Open.** <what the code shows, and exactly where it stops being enough>

<what is already settled around it, with addresses -- so the reader
knows which half of the question is done>

**What would settle it.** <the capture or the test, concretely: which
page, which address, which command to type, and what each possible
answer would mean>
```

Give both branches of the answer their meaning.  "If offsets 229-231
hold the original page and address, the field is real and the writer
is worth finding; if they are zero or garbage, the load path is reading
a field nobody fills, and the expander does not depend on what it was
handed -- which is worth knowing on its own."

## The at-a-glance table

At the top of the open section:

| capture or test | closes | cost |
|---|---|---|

Group by what one capture would close.  One dump of one page settled
three questions at once in this project; say so, and put that capture
first.  Mark the cheap ones -- a single line of BASIC with the expected
output and what a different output would mean.

## Three kinds of hole

1. **Wants a capture** -- a dump of a page or a region at a particular
   moment.  Say which page, at what moment, and what to look for in it.
2. **Wants a machine and a test** -- a defect read out of the
   instructions and never seen run.  Give the test.  Mark the ones not
   worth attempting (damaged media, an unreachable stack state) so
   nobody spends an afternoon on them.
3. **Wants no evidence at all.**  Keep a section for these.  A question
   marked "not worked out" for months was answered by a table in the
   ROM source that was in the repository the whole time.  A hole that
   wants a hardware capture and a hole that wants ten minutes of reading
   look identical from inside a notes file; the register is where they
   are told apart.

## The dumps

List every dump with what it holds -- size, which page, at what moment
in the boot -- and keep it current.  **A dump named in prose may not be
the dump that holds the bytes.**  "A dump proves every byte of it"
named a file holding filler at that address; the proof was in a dump
retired months before, on the belief that later ones superseded it.
They did not: it was the only one that caught that buffer with that
routine still in it.  Before retiring a dump, grep the prose for it.

## When a correction leaves a question

Correcting a wrong sentence can leave an absence.  "The DOS owns the
NMI vector" was false -- the vector held the ROM's own handler in
every dump, including the pre-boot one -- but the menu is plainly meant
to be entered, so *what enters it* became open.  Record it as an entry
with the evidence that ruled out the old answer and the capture that
would give the new one, rather than deleting the claim and leaving
nothing where it stood.
