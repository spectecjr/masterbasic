# speculate/

`disasm/` holds what can be shown. This folder holds what I think the code is
doing. They are separate folders because those are different things, and mixing
them is how a guess becomes a fact by attrition.

Both files here still assemble to the original bytes — everything added is a
comment — so `tools/build.sh` checks these as well as the listings they came
from.

## What is in a banner

Every routine gets one. It carries three kinds of material, and they are not
equally trustworthy.

```
;; NRRD -- &456A to &4574
;;
;; This routine moves the return address about with EX (SP),HL, so the
;; register tracking below cannot be trusted: read it as a list of what
;; is touched, not of what is destroyed.
;;
;; Takes:     DE, HL
;; Leaves:    A, F, HL
;; Preserves: DE (saved and restored)
;; Ends:      JR, RET
;;
;; ? reaches the ROM through DKP2; calls CMR, WRTBC.
```

**Takes / Leaves / Preserves / Ends** are *derived*. They come from dataflow over
the instructions — which registers are read before being written, which are
written, which are pushed and popped in balanced pairs — propagated through calls
until it settles. An unconditional jump out of a routine is followed as if it
were part of it, because that is what a shared tail is: `NRRD` ends `JR L4598`,
and `L4598` is where its registers are put back.

**A line beginning `?` is a guess.** It is composed from what the routine
demonstrably touches — the ROM variables it names through the inline-parameter
conventions, the routines it calls, the tokens it compares against, the errors it
can report — but the step from "touches these" to "is for this" is mine.

## Where this is wrong

**Segmentation is the weak link.** A routine is taken to start where something
calls it, or where it has a name. This code falls from one routine into the next
constantly, as a way of saving bytes, and it has multiple entry points into the
same body all over. Wherever the split is in the wrong place, the contract
computed from it is wrong with it.

**`EX (SP),HL` defeats the register tracking**, and the whole `NR` family is built
on it. Push/pop tracking cannot follow a routine that swaps its return address
for a saved value. Those routines say so at the top of their banner; the contract
below it is a list of what gets touched, not of what gets destroyed.

**Conditional paths are not explored.** The walk is linear, so a register written
only on a branch that is rarely taken is reported the same as one written every
time.

Where `disasm/` already had a hand-written description, it is reproduced under
"Shown for this routine in disasm/" — that part is not a guess, and where it
disagrees with the derived contract above it, believe the hand-written one.

## Per-line notes

Lines carry a note where a sequence has one settled meaning in this codebase:

| | |
|---|---|
| `CALL NRRD` / `DEFW` | read the named ROM system variable |
| `CALL CMR` / `DEFW` | call the ROM with ROM1 paged in |
| `CALL CALLDOS` / `DEFW` | call the other page, whose paging changes first |
| `SET 7,H` / `RES 6,H` | window `&4000`–`&7FFF` into `&8000`–`&BFFF` |
| `BIT 6,H` | the rotating window check: HL has crossed from section C into D |
| `EX (SP),HL` at an entry | the return address is the inline parameter |
| `LD (nnnn),A` into an instruction | self-modifying: which operand it patches |
| `RST FPCALC` | what the calculator list computes |

The self-modifying ones are worth the price of admission on their own: this code
patches port numbers and jump displacements into its own instructions in a dozen
places, and nothing about `LD (&4532),A` says so until you look up what lives at
`&4532`.

## Regenerating

`tools/build.sh` writes these along with `disasm/`. The clean listings are
written first, because the speculation is produced by adding to the same headers
and notes.
