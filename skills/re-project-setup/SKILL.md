---
name: re-project-setup
description: Use at the START of a disassembly or reverse-engineering project, before any code is read, to tell the user what to gather and why — the binary and its provenance, an assembler that round-trips, the reference sources, the dumps that turn readings into proof, a second build of the same program, and a machine. Also what to decide up front: who the reading copy is for, and whether "no magic numbers" means zero. Trigger on "starting a disassembly", "new reverse-engineering project", "what do you need from me", "what should I collect", "before we begin".
---

# Before the first byte is read

Most of what made the reference project work was in hand before any
code was read, and most of what stayed open was open for want of one
capture.  Ask for these, in this order.

## 1. The binary, and where it came from

The exact file, its size, and how it was obtained -- a disc image, a
memory dump, a download.  Say whether it is *the file* or *a dump of a
booted machine*: those differ in every run-time-patched operand, and a
claim checked against the wrong one will be wrong in ways that look
right.  If it is a load image with a header, say so; the first nine
bytes were part of the image in the reference project and a
documented "header plus two halves" did not add up.

## 2. An assembler that can round-trip

One that assembles a listing and emits a raw binary, so the output can
be compared with the original byte for byte.  Check before anything
else that it can express what the listing will need: `ORG` and output
placement separately, if the code runs at an address other than where
it is stored; expressions in operands (`LABEL + 1`, `A | B`, `>> 1`),
which are how named constants are held to the bytes; and `INCLUDE`, if
two banks are to be assembled as one unit so cross-bank references
become checked symbols instead of numbers.

## 3. The reference sources

In descending order of how much each is worth:

- **The original source**, if any survives, even of a different
  version.  It gives names, and its comments, and it lets "inherited"
  be told from "introduced".
- **The ROM source** for the machine, or a labelled disassembly of it.
  An extension calls the ROM constantly; without names for what it
  calls, half the listing is numbers.
- **The hardware manual**: port bits, the memory map, the paging model,
  the interrupt and NMI paths.  This is the "facts about this machine"
  block every reviewer will be given.
- **The user manual** for the program, for what each command is meant
  to do.  Its errata are findings.
- Token tables, character sets, file-format documents.

Say which of these is *someone else's text* and which was generated:
an AI-annotated copy of a source is not the author's words and must not
be quoted as such.

Where a reference lives in git, add it as a submodule under `ref/`
rather than copying files in.  Then its provenance is a URL and a
commit, a later reader can see exactly which revision a claim was
checked against, and a fix upstream is a `git submodule update` rather
than a hunt.  Record the branch if it is not the default one: a
reference checked out on a fix branch is a fact about the project that
a fresh clone will silently lose.  The machine-specific skills carry
these URLs for the machines they cover.

## 4. Dumps

Readings become proof only against memory.  The set that closed
questions in the reference project:

- **The system/variable page before any boot**, after the base OS
  alone, and after the program has loaded.  Three dumps of one page
  settled 16K to within 33 bytes and showed which installer wrote what.
- **The program's own page(s) after boot**, to compare with the file:
  every difference is a run-time patch, and the list of them is a list
  of what the code resolves for itself.
- **A page captured mid-boot**, if a block is copied and run
  elsewhere: it is the only way to see the block where it runs.
- **A full memory dump** once, for the questions nobody predicted.
- Whatever the open questions turn out to need: a page with a
  particular mode active, a directory entry after a particular save.

Name each dump for the page and the moment, keep a table of them, and
never retire one without grepping the prose for it.  The one capture
most wanted at the end of the reference project was the one nobody
took: the page holding an emulator that the ROM hands the NMI to.

## 5. A second build of the same program

The stock release, an earlier version, a different licensee's build.
It settles whether a value is a bug or a relocation artefact, whether
a defect was inherited, and whether a table is where its author said.
It is a different binary and must be cited as one.

## 6. A machine, or an emulator that is honest about timing

For the defects that are read out of the instructions and never run.
Each will come with a test -- a line of BASIC, a file-name pair, a
clock setting -- and someone with the machine closes them in an
afternoon.  Without one, every such finding stays labelled *not
observed*, which is honest but is not the same as known.

## Two decisions to make before starting

**Who the reading copy is for.**  "A working professional who knows
the CPU but not the machine" is a good answer; it decides what gets a
banner, what gets explained, and what is assumed.

**What "no magic numbers" means.**  Not zero -- `&00` appeared at 791
sites meaning something different at nearly every one.  The workable
target is *no unexplained number in a routine that has been worked*,
with a report saying how many are left per routine, and with the
numbers that can never be named (operands in a block written to run
elsewhere; placeholders a later step fills) carrying a comment
instead.  Agree it early; it changes what "done" looks like.

## What to tell the assistant

Put it in a `CLAUDE.md`: the gate and how long it takes; the six
machine facts; the notes grammar; the reference-source trap; the patch
discipline; and that another session may share the clone.  One page.
Everything not on that page will be re-derived from scratch each
session, and re-derived slightly differently each time.
