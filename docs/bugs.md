# Defects in the shipped software

Not defects in this project — defects in MasterDOS 2.3 and MasterBASIC 1.7
as they were sold. The listings cannot be corrected: they assemble to the
original image byte for byte, and that is the point of them. So a defect
gets written down here and explained where it sits.

One is confirmed. The rest of this file is a plan for looking properly.

---

## 1. The block transfer loops cannot see a LOST DATA error

**Where** `&409D` in BOOT, `&48E4` in `LDB6`, `&4A33` in `SVB6` — three
copies of the same seven instructions.

**What** Each reads the controller's status, tests DRQ, then uses `RRCA`
to get BUSY into carry, and applies its error mask to what is left. `A`
is therefore the status rotated one place right, and the mask is `&0D`:

```
AND &0D  on A = status ROR 1  ->  DRQ, CRC ERROR, RECORD NOT FOUND
AND &0E  on A = status ROR 1  ->  LOST DATA, CRC ERROR, RECORD NOT FOUND
```

DRQ cannot be set at that point — the loop only leaves when it is clear —
so the test sees CRC ERROR and RECORD NOT FOUND, and nothing else. It
should be `&0E`.

**Why that is not an opinion** Three independent lines agree on the
intended set:

- MasterDOS uses `&0E` for the same question at `&46C6`, on a status
  rotated in the same way.
- The annotated MasterDOS source writes that test as `AND &1C` on an
  unrotated status, and `&1C >> 1` is `&0E`.
- SAMDOS, which MasterDOS grew out of, names the constant:
  `wd.st.errors: equ %00011100 ; mask of lost data, CRC error and record
  not found`.

**How it happened** SAMDOS never rotates: its transfer loops are
unrolled and it tests BUSY with `BIT`, so `A` is the status as read and
`%00011100` is right. MasterDOS rolled the loops up and replaced the
`BIT` with an `RRCA`, saving a byte and a few cycles in the tightest loop
in the DOS. That made a shifted mask necessary. The shift was made
correctly once, at `&46C6`, and wrongly in the three loops.

**What it costs** A sector that arrives with a byte dropped is accepted
as good. The paths affected are the boot loader, `LDB6` and `SVB6` —
which is to say loading the DOS itself, and `LOAD` and `SAVE` of a CODE
block. The ordinary sector read and write are not affected: they reach
`&46C6` and get the right mask. LOST DATA is exactly what a polled
transfer suffers when something holds the processor up too long.

**Written up at** `&409D` in `clean/masterdos.asm`, with the two other
sites pointing at it; and in `notes/disk.txt` for the working copy.

---

## A pass to make, when the narrative work is further on

The one above was found by reading, not by looking. Three sweeps would
be worth running properly, because each has already produced one result
by accident:

**Constants used in the wrong space.** The rotate sweep in
`tools/` found four masks applied to a rotated status and nothing else
in either half. It did not cover bit numbers reached through `PUSH AF`
and `POP AF`, which is how `&46DF` escaped it — and `&46DF` is the second
half of the same story, a `BIT 4` that was not shifted when the mask
beside it was. Extend the walk through the stack.

**Off-by-one in the other direction.** Every mask, bit number and compare
in the disk code, checked against what the WD1772 datasheet says the bit
means for the command that was issued. Type I and Type II commands do
not use the same status bits, and the DOS issues both.

**Divergence from the source.** `carrydoc` already knows where the
shipped code and the annotated source disagree instruction by
instruction, and it reports the count. Those divergences are where
MasterBASIC and later MasterDOS builds changed things, so they are also
where a change could have gone wrong. Reading them as a list, rather than
one at a time when a routine happens to be worked, is the systematic
version of how the `&0D` was found.
