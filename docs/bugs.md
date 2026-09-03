# Defects in the shipped software

Not defects in this project — defects in MasterDOS 2.3 and MasterBASIC 1.7
as they were sold. The listings cannot be corrected: they assemble to the
original image byte for byte, and that is the point of them. So a defect
gets written down here and explained where it sits.

Three are confirmed. The rest of this file is a plan for looking properly.

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

## 2. The RECORD NOT FOUND recovery cannot be reached

**Where** `BIT 4,A` at `&46DF`, in `CDE1`, guarding the jump to
`CDE1_1`.

**What** `CDE1_1` is the informed recovery from a mis-seek: it issues a
read-address command, takes the track number out of the first ID field
to pass under the head, and writes it into the controller's track
register, so the next seek starts from the truth. It is reached only
when the status says RECORD NOT FOUND. It never is.

`CDE1` has three callers, and on none of them does `A` hold a status with
bit 4 available:

| caller | what `A` holds at `&46DF` | bit 4 |
|---|---|---|
| `&46C8` | status `AND &0E` | cleared by the mask |
| `&48EB` | status `AND &0D` | cleared by the mask |
| `&4A51` | `(PORT1)` — a page number | not a status at all |

On the first two the very instruction that decided there was an error
masks off the bit the recovery is selected by. `&0E` is bits 1, 2 and 3;
`&0D` is bits 0, 2 and 3; neither includes bit 4.

**Why bit 4 is the wrong number anyway** `A` is the status rotated one
place right, so RECORD NOT FOUND — status bit 4 — is bit 3 of what is
tested. `BIT 3,A` would be both correct and inside the mask. This is
the same rotate that produced defect 1, in the same routine family.

**The third caller is the worst of the three.** `SVB7` loads `A` from
`PORT1` before calling `CDE1`, so the test is applied to a page number.
Whether that comes out set is not worth working through. The point is
that on none of the three paths is the branch decided by the RECORD NOT
FOUND bit, which is the only thing it exists to test: twice by a mask
that had already cleared that bit, once by a byte that was never a
status. It is broken on all three, and that is enough.

**What SAMDOS does** Both halves work there. Its mask is `%00011100`,
which includes bit 4, so the bit survives to be tested; and its save path
puts `push af` and `pop af` around the paging, so the status is still in
`A` when `cdec` is called. MasterDOS moved the `AND` before the paging
and let `SVB7` overwrite `A`.

**What it costs** A sector that fails because the head is on the wrong
track is recovered from by the blind route — step in, out, out, in —
rather than by reading an ID field to find out where the head actually
is. `CDE1_1` and `CTS1` between them are some ninety bytes that are never
entered for the reason they were written.

**Written up at** `&46DF` in `clean/masterdos.asm`.

---

## 3. Six pairs of file names cannot be told apart

**Where** `AND CASE_BLIND` at `&4CDB`, in `CKNAM`.

**What** The name compare is case blind for nothing: `XOR (HL)` leaves the
bits in which the two characters differ, and `AND &DF` throws away bit 5 —
the one bit that separates `A` from `a`. Zero means the same letter in
either case. No table, no range test, no branch.

Bit 5 separates more than letters, though, and the `AND` cannot tell which
pair it is looking at. Six other pairs come out equal, both ends
printable:

```
@ and `     [ and {     \ and |
] and }     ^ and ~     _ and DEL
```

So `DIR "A["` lists `A{` as well, and a file saved as `X^` loads as `X~`.
Below that there is a second tier: every character from space to `?` is
equal to the control code thirty-two below it. That needs a program to put
the control code in the name, but nothing else stands in the way.

Twenty-six pairs were wanted. Thirty-two came free.

**Why it is reachable** Nothing validates a file name. The "Invalid file
name" error is the ROM's, and the whole of its test is the length and a
null name — `CP H / JR NC,IFNER ; LIMIT NAME LEN` in `tapemn.asm`. Names
come out of BASIC strings, so any byte at all can go into a directory
entry, and five of the six pairs are typeable at the keyboard (`_`'s
partner, DEL, is not).

**What it costs** `CKNAM` is the only name compare in the DOS, and all
three of its callers act on the answer:

| caller | what it is doing |
|---|---|
| `&4BD6` | the directory scan: `DIR`, `LOAD`, `OPEN` |
| `&4C88` | the same scan, looking a specific name up |
| `&5EAA` | `SNDF2`, the resumable search behind `ERASE`, `RENAME` and `COPY` |

The listing paths are a curiosity. The other two are not: `ERASE "A["`
will erase `A{`, and the check that asks whether a name is already on the
disc can find a file that is not the one being saved and offer to
overwrite it. Both destroy a file the user did not name.

**Not MasterDOS's doing** SAMDOS's `cknam` is the same routine with the
same instruction and the same comment — `and &df ; ignore the case bit`.
MasterDOS moved the pattern pointer from `IX` to `DE`, because `IX` now
holds the channel record, and changed nothing else. This one was
inherited, not introduced, which is the opposite of the two above.

**Written up at** `&4CDB` in `clean/masterdos.asm`.

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
