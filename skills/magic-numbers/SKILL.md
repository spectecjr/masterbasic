---
name: magic-numbers
description: Use when the brief for a disassembly's reading copy says "no magic numbers" and you need to make that measurable and then work it down. Carries the target that actually works (no UNEXPLAINED number in a routine that has been worked — not zero numbers), the classes of number that can never be named and must be explained instead, the per-routine counter that turns the remainder into a queue, and the four faults such a counter fell into, three of which flattered the figure. Trigger on "magic numbers", "name the constants", "bare immediates", "unnamed numbers", "how many are left", "which routine next".
---

# Magic numbers in a reading copy

## The target

Not zero.  `&00` alone appeared at 791 sites meaning something different
at nearly every one, so there is no global table to write; naming is
per site.  And a loop counter of 8 is just 8.

The workable target: **no unexplained number in a routine that has been
worked.**  A number is explained when it is named, or when a symbol
stands beside it (`BASE + &1D` says what `&1D` is), or when the line
carries a comment saying what it is and why it is not named.

## Numbers that can never be named

Recognise these before starting a routine, or the count for it will
never reach zero and the wrong routines will look worst:

- **An operand inside a block written to run at another address.**  A
  386-byte block assembled at `&7460` and copied to `&46CC` has twenty
  operands that are addresses in `&46CC-&484C`; a label from the
  assembling page names the wrong page's byte.  The honest treatment is
  a comment: *`&483A` once this block is moved*.
- **A placeholder a later step fills.**  `JP &0000` / `CALL &0000` whose
  operand a signature search or an installer writes at boot.  Comment
  it with what writes it, if that is known.
- **A window address** -- the other bank seen through a mapping window.
  Often expressible as `OTHERLABEL + WINDOW_OFFSET`, which is a name;
  when the other bank's label is not in this assembly unit, a comment.
- **A register clear** -- `LD H,&00`.  Leave it.

## Name only what you can defend

A wrong name is worse than a number: the number is honest about not
being understood, and the name is not.  Read the routine before naming
anything in it; name from the code, not from pattern-matching on the
value.  `&1F` was a page mask in one routine and a file-type mask in
the next, and both already had names.  Say in the notes file which
numbers were left bare on purpose and why.

Where a number's meaning was worked out from a reference -- a token
table, a hardware manual -- say where.  `SUB &AB` became legible only
when the ROM's token table showed `&AB` is the command adjacent to the
one the routine was thought to serve, which meant the routine served
both.

## The counter

Print, on every build, per half: instructions carrying a number, and
of those the ones with no explanation.  Then per routine, worst first,
as `NAME unexplained/instructions` -- the denominator matters, because
eight in forty instructions is a different thing from eight in four
hundred.  That turns the remainder into a queue.

A site is outstanding when:

1. the operand carries a hex literal, and
2. the line has no comment, and
3. no symbol stands beside the literal in the operand.

Two more decisions the rule needs: data directives (`DEFW &C000` in a
table) are a different job and are out; and a routine is the run from
a label to the next label that is neither one of its own internal
labels nor a synthetic name for a referenced address.

## Four faults this counter had

All found by doing a routine against it and watching what the number
did.  None was visible to a green build.

1. **Synthetic labels treated as routine heads.**  `L7467` names an
   address seven bytes into a block and took the block's other 143
   instructions with it, so a label that is not a routine topped the
   worst list.  A synthetic name is never a head.
2. **Counting unnamed rather than unexplained.**  Naming five sites
   moved the count; explaining four more, correctly, moved it not at
   all.  The deliberate exceptions inflated exactly the routines most
   worth working.
3. **The symbol test matched the hex.**  `[A-Za-z_][A-Za-z0-9_]{2,}`
   finds an identifier inside `&C000` and inside the `FFC` of `&7FFC`,
   because A-F are letters.  It excluded 327 sites, 232 with no symbol
   in them.  Strip the literals, then look for a name.
4. **The symbol test saw the mnemonic.**  Applied to the whole
   instruction, `SUB &1F` strips to `SUB ` and the mnemonic passes as a
   three-letter symbol.  `LD`, `CP`, `JP` are two letters and did not,
   which made the shortfall look random.  Test the operand only.

Three of the four flattered the number.  The fourth was found only by
writing the rule a second time over the listing *text* and refusing to
accept that the two implementations disagreed.  **Keep two
implementations and reconcile them**; a debug hook that prints the
addresses one of them counted for a named routine makes the diff a
one-liner.

## Where to start

Rank by unexplained count, but look at the top entry before starting
it: it may be a block written for another address, more than half
exempt.  Prefer the half whose numbers are concentrated -- where the
top twelve routines hold a third of the total -- over the half whose
are a long tail with no leverage in it.
