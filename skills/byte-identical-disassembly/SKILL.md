---
name: byte-identical-disassembly
description: Use when starting or working on a disassembly / reverse-engineering project where the output is an annotated assembly listing of an existing binary. Sets up the one gate that makes everything else safe — assemble the listing and compare it to the original byte for byte, so nothing you write can change a byte — and the working shape around it: three listing trees, hand-written notes as the only input, figures printed by the build rather than kept in prose, and an exact-match patch tool for editing. Trigger on "disassemble", "reverse engineer this ROM/binary", "annotate this listing", "byte-identical", "assemble and compare".
---

# Byte-identical disassembly

## The gate

One command assembles every listing and compares the result with the
original binary.  It must say, for each listing, that the bytes are
identical, and only then run the checks on prose.

    bash tools/build.sh > build.log 2>&1

Everything else follows from having this.  A comment can be wrong; an
operand written as an expression cannot, because the assembler evaluates
it and the compare catches the byte.  A label can be misplaced; a label
on a byte that is not an instruction start assembles differently and
fails.  **Nothing anyone writes can change a byte, and the build says so
if it does.**

Rules that come with it:

- The build takes minutes.  Run it in the background and read the log.
- Print the byte-identical lines *before* the prose checks, and make
  the last line an unambiguous `BUILD OK` / `BUILD FAILED`.  Counting
  identical lines is not enough; a run can be byte-identical and still
  fail its prose check.
- `build.log` is gitignored.  So every figure that can be checked -- a
  byte census, a label tally, an outstanding-work count -- is *printed
  there* and quoted from there, never kept in a document where it will
  go stale without anything noticing.

## Three trees

Generate three listings from the same bytes, and keep them apart:

| tree | job |
|---|---|
| `listings/disasm/` | the working copy: where every name came from, what an earlier reading got wrong, what is still open.  Arguments kept. |
| `listings/clean/` | the reading copy, for someone who knows the CPU and not the machine.  Conclusions only. |
| `listings/speculate/` | readings not yet proved, kept out of both. |

All three are gated.  The reading copy is not a hand-edited derivative;
it is generated from the same disassembler with a different rendering
and a different notes directory, so it cannot drift from the bytes any
more than the working copy can.

## Notes are the only input

Nothing is edited in a generated listing.  Knowledge from a person goes
into plain-text notes files that the generator reads, with a grammar
small enough to learn in a minute:

    MB &7465 NAME                   label this address
    MB &7465 : text                 comment on that instruction
    MB &7465-&7470 data|word|text|code
    MB &7465 value NAME             name this operand (an equate is made)
    MB &74A6 expr BASE + 1          rewrite the operand as an expression --
                                    evaluated and checked against the bytes
    MB &7465 step text              a line above the instruction
    CONST NAME = &15 : description  a named number belonging to no one site
    GROUP Heading                   the CONSTs after it, until the next
    RENAME OLD NEW
    DOC NAME                        banner; indented lines below are its text

`expr` is the important one: it is the mechanism by which a named
constant *cannot* quietly stop matching the byte it names.

Keep `notes/clean/` separate from `notes/`, applied to the reading copy
only, so that a pedagogical rewrite never leaks into the working copy's
record of where a claim came from.

## Hold the prose to the listings

A check that walks every document and notes file, finds every quoted
instruction and every capitalised label name, and confirms the listing
still has them.  Two exemptions it needs: files that are transcripts of
someone else's document, and files that are explicitly hypothetical
sketches.  Everything else -- including the design documents -- is in.
A design folder left outside the check is where stale names survive
for months.

What it cannot catch: prose that merely *names* a routine without
quoting an instruction.  Say so in the project's instructions.

## Editing: `patch.py`

Ships beside this file.  Exact-match edits, each required to match
exactly once, nothing written until all of them do, and on a miss it
prints where the two texts diverge.  Three rules that come with it,
each learned by losing a cycle:

1. Write the edits into a `.py` file and run it; never pipe them through
   a shell heredoc, which mangles `\b`, `\d` and the like.
2. Build the `old` string from the file, not from memory.
3. Never run it in the same command as the build.  The assertion
   scrolls past unread, the build runs green on unmodified code, and
   the totals come back unchanged -- which reads as a result.

**A total that comes back exactly unchanged after a change that should
have moved it is a failure signal, not a result.**

## Git

If more than one session shares the clone, stage by explicit path and
never `git add -A`.  Look at `git status` first; leave what you did not
touch.
