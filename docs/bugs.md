# Defects in the shipped software

Not defects in this project — defects in MasterDOS 2.3 and MasterBASIC 1.7
as they were sold. The listings cannot be corrected: they assemble to the
original image byte for byte, and that is the point of them. So a defect
gets written down here and explained where it sits.

Four are confirmed and one is suspected. The three sweeps this file used to
plan have now been run, and what they found is at the end.

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

## 2. The RECORD NOT FOUND recovery is never chosen by the bit it tests

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
`PORT1` before calling `CDE1`, so the test is applied to a saved `HMPR`
value — a page number. Bit 4 of a page number is set for pages 16 to
31, which exist on a 512K SAM and not on a 256K one. So on a 256K
machine the recovery is dead code; on a 512K machine it *fires at
random*: any failed block save whose transfer address sits in the upper
256K takes the branch and runs the mis-seek recovery, read-address
command and all, for an error that may have been anything. The point
stands either way — on none of the three paths is the branch decided by
the RECORD NOT FOUND bit, which is the only thing it exists to test:
twice a mask has already cleared it, once the byte was never a status.
What varies with the machine is only whether the broken branch does
nothing or does something uncalled-for.

An earlier version of this entry was headed "cannot be reached", which
the 512K case makes literally false. A fresh review caught it.

**What SAMDOS does** Both halves work there. Its mask is `%00011100`,
which includes bit 4, so the bit survives to be tested; and its save path
puts `push af` and `pop af` around the paging, so the status is still in
`A` when `cdec` is called. MasterDOS moved the `AND` before the paging
and let `SVB7` overwrite `A`.

**What it costs** A sector that fails because the head is on the wrong
track is recovered from by the blind route — step in, out, out, in —
rather than by reading an ID field to find out where the head actually
is. `CDE1_1` and `CTS1` between them are some ninety bytes that are never
entered for the reason they were written — and on a 512K machine are
entered for no reason at all.

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

## 4. The NMI menu's exit restores HMPR from the saved LMPR

**Where** `&53C1`, on the path the X key takes out of the snapshot menu.

**What** Three ports are saved when Spectrum mode is entered, at `&5FCE`
onwards, and each into its own byte:

```
IN A,(LMPR) / LD (SNPRT0),A     ; 5FCE
IN A,(HMPR) / LD (SNPRT1),A     ; 5FD3
IN A,(VMPR) / LD (SNPRT2),A     ; 5FD8
```

`SNAP7` puts all three back through the resume stub, and pairs them
correctly: `SNPRT0` to `&B8F8`, `SNPRT1` to `&B8F9`, `SNPRT2` to
`&B8FA`. The X path puts two of them back itself, and pairs one of them
wrongly:

```
LD A,(SNPRT0) / OUT (HMPR),A    ; 53C1   the saved LMPR, into HMPR
LD A,(SNPRT2) / OUT (VMPR),A    ; 53C6   the saved VMPR, into VMPR
```

`SNPRT1` is the byte that holds an `HMPR` value, and it is not read
here at all.

**Nothing puts it back.** The path ends at `JP ENDS`, which unwinds to
the last DOS-command entry and returns through the ROM's `DOSC`
(`misc2.asm`). That restores `LMPR` from the value `PTDOS` saved, and
`SP`, and nothing else:

```asm
DOSC:      POP HL            ;PREV STACK PTR
           POP BC
           DI
           OUT (C),B         ;PREV LRPORT RESTORED
           LD SP,HL          ;PREV STACK
```

`C` is 250, which is `LMPR`. The ROM never saves or restores `HMPR`
around a DOS call, so whatever the DOS leaves there is what BASIC gets
back.

**What it costs** Both ports take a page number in their low five bits,
so the effect is the wrong page at `&8000` rather than anything wilder,
and it lasts only until the next thing that sets `HMPR` -- which the ROM
does whenever it uses the window. If Spectrum mode was never entered
`SNPRT0` is zero and the window ends up holding the system page, which
is harmless. The bug is real; its consequences are mostly invisible.

**Not certain enough to call settled.** The pairing is plainly
inconsistent with the only other place all three are restored, which is
what makes it worth writing down; whether any BASIC program can be made
to notice is another matter. Anyone with a machine can look in a minute:
enter Spectrum mode, press NMI, press X, and `PEEK` through the window.

---

## 5. DUMP's two magnifications are exchanged for an upright dump

**Where** `&693E`–`&6952` and `&6995` in MasterBASIC, and the manual's
"Screen dumps" section.

**What** `DUMP n,m` takes two magnifications. The User Manual says which is
which, and says it plainly:

> The number 1, 2 or 3 actually specifies the width magnification of the dump;
> the height magnification is assumed to be the same unless you specify
> differently by including a second number. E.g.
>
> ```
> DUMP 1,2 - single width, double height
> DUMP 3,1 - treble width, single height
> ```

For an upright dump it is the other way round. `DUMP 1,2` gives **double
width and single height**.

**Measured.** Two captures of the printer stream, a full MODE 4 screen dumped
twice, in `file/printmode4dump1,2.txt` and `file/printmode4dump2,1.txt`. Every
bit-image line begins `ESC "*" CHR$ 4 n1 n2`, and `n1 + 256*n2` is the number
of dot columns across the paper:

| | dot columns | lines | printed size |
|---|---|---|---|
| `DUMP 1,2` | 512 | 24 | 512 × 192 dots — double width, single height |
| `DUMP 2,1` | 256 | 48 | 256 × 384 dots — single width, double height |

The line counts settle it independently: 24 lines of 8 dots is 192, the
screen's own 192 rows unmagnified, and 48 lines is 384.

**Why** The routine works in two axes of its own, and which screen axis each
one is depends on the orientation. The first number sets how many dots a pixel
is worth along the axis that fills the eight bits of a bit-image byte; the
second sets how many bytes are emitted before the other axis advances. A byte
is eight dots up the paper and successive bytes step across it, so the first
number magnifies vertically and the second horizontally.

`TRANSFORM_DUMP_COORDS` exchanges the two axes for an upright dump — that
exchange is what makes it upright — and the manual's names are correct on the
*other* side of it. In a sideways dump, which is what `DUMP 3` and anything in
MODE 3 get, the first number really is the width. The manual's own MODE 3
advice is right for that reason:

> `DUMP 1,2` or `DUMP 2,3` can be used to reduce the width relative to the
> height.

So the manual documents the sideways case and the program inverts it for the
upright one, which is the case an ordinary `DUMP 1` or `DUMP 2` in MODE 1, 2
or 4 takes.

**Consequence** Anyone following the manual to correct a dump's proportions
makes them worse: `DUMP 1,2` to stretch a squat picture vertically stretches
it horizontally instead. `docs/original/ERRATA.md` carries a note.

**Not a misreading of the orientation.** `XVAR 15` (`SDORI`) documents 1 as
sideways and 3 as force-upright, the code stores the poked value through
unchanged, and the defaults follow the manual: sideways for `DUMP 3` or MODE
3, upright otherwise.

---


## The three sweeps, run

Each of these was proposed because it had already produced one result by
accident. All three have now been run properly. One found nothing new, one
found nothing at all, and one turned out to be mostly about the tool.

### Constants used in the wrong space — no new instances

The original sweep walked masks applied to a rotated status. `&46DF` escaped
it because the value travels through `PUSH AF` and `POP AF`, so the walk was
extended through the stack.

Every status read in the driver was followed to every constant applied to it.
The result rederives both known defects and adds nothing:

- Both block-transfer loops (`&48DB`, `&4A28`) read the status, test `BIT 1,A`
  for DRQ, rotate once, and then apply `&0D` — rotated bits 0, 2, 3, which are
  DRQ, CRC and RECORD NOT FOUND. LOST DATA, rotated bit 1, is absent. The `&01`
  is dead, because the `BIT 1` above already jumped away on DRQ. That is
  defect 1.
- `CDE1` reaches `BIT 4,A` at `&46DF` with the status having passed through
  `PUSH AF` / `POP AF`. In rotated space RECORD NOT FOUND is bit 3, and the
  mask above has cleared bit 4 in any case. That is defect 2.

The four transfer loops at `&45AE`, `&45D9`, `&4676` and `&46B3` use the idiom
correctly: two rotates, testing BUSY and then DRQ. `&454C` rotates a track
count rather than a status.

### Off-by-one in the other direction — nothing to find

The concern was that Type I and Type II commands do not use the same status
bits — bit 2 is TRACK 0 for one and LOST DATA for the other, bit 5 is SPIN-UP
against RECORD TYPE — and that the DOS issues both.

**The Type I commands are never polled.** `STEP_HEAD_IN` and `STEP_HEAD_OUT`
issue the step and then call `STPDEL`, which waits out a delay taken from
`STPRAT` or `STPRT2`; no status is read afterwards. The banner on `STEP` says
why: the controller reports a step complete long before the head has settled,
so the wait is the DOS's own. `RESTORE` in the boot at `&40AD` is followed by a
latency loop and then a `POP AF` that recovers the retry count, not the status.

So every status test in the driver follows a Type II or Type III command, and
the ambiguity cannot arise. The one bit-5 test, at `&5511` after WRITE TRACK,
reads the rotated status and so means bit 6, WRITE PROTECT — which is bit 6
for Type III as well.

### Divergence from the source — mostly the check's own fault

`carrydoc` reported five routines as changed from the annotated source. Read as
a list rather than one at a time, four were artefacts:

| | reported | actually |
|---|---|---|
| `MRTAB` | 8 of 48 | data — `DEFS &20`, zeros decoded as instructions |
| `AUTNAM` | 8 of 12 | data — `DEFB 1 / DEFM "AUTO*"` |
| `GETSCR` | 8 of 12 | byte-identical to stock; the span ran on into `PUTSCR` |
| `MCHWR` | 33 of 45 | the same overrun |

Two causes, neither of them a change to the code: data counted as instructions,
and a span measured past the routine because the next one carries no header.
The check now skips declared data and bounds the span by the next label of any
kind. Seven of these banners existed when the sweep began; one does now.

`INPST` is the one real divergence, and it is a feature rather than a fault:
MasterBASIC extended `INP$` so that a count of zero reads until a carriage
return, where stock refuses it as out of range. See `notes/clean/dos-channel.txt`.



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
