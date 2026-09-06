# Defects in the shipped software

Not defects in this project — defects in MasterDOS 2.3 and MasterBASIC 1.7
as they were sold. The listings cannot be corrected: they assemble to the
original image byte for byte, and that is the point of them. So a defect
gets written down here and explained where it sits.

Eight are confirmed and one is suspected. The three sweeps this file used to
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

**Written up at** `&409D` in `listings/clean/masterdos.asm`, with the two other
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

**Written up at** `&46DF` in `listings/clean/masterdos.asm`.

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

**Written up at** `&4CDB` in `listings/clean/masterdos.asm`.

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
twice, in `dumps/printmode4dump1,2.txt` and `dumps/printmode4dump2,1.txt`. Every
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


## 6. A year of 00 stops the date stamp half-written

**Where** `STAMP_WITH_DATE` at MasterBASIC `&4A39`, the loop at `&4A4F`.

**What** The stamp is five bytes at offset `&F5` of the directory entry: day,
month, year, hour, minute. The first three are read in a loop:

```asm
      LD B,&03                        ; 4A4D  day, month, year

READ_CLOCK_FIELDS_LOOP2:
      CALL TWO_DIGITS_FROM_DE         ; 4A4F  two characters, one byte
      AND A                           ; 4A52  a zero field means the clock is unset
      JR Z,READ_CLOCK_FIELDS_DONE2    ; 4A53  so stop and leave the stamp alone
      LD (HL),A                       ; 4A55
      INC HL                          ; 4A56
      DJNZ READ_CLOCK_FIELDS_LOOP2    ; 4A57
```

The zero test is a sentinel for "the clock was never set", and as a sentinel it
is sound for the **day**: a day of zero cannot be real, which is what the
routine's own commentary says. But the same test runs on all three fields, and
a **year** of zero is legal — it is 2000.

**Consequence** In that year the loop writes the day and the month, then reads
`00` for the year and jumps out. `READ_CLOCK_FIELDS_DONE2` is past the time
loop as well, so the hour and minute are never written either. The entry keeps
whatever was in those three bytes before — on a re-used slot, the previous
file's year and time.

Nothing downstream notices. `PRINT_DATE_IF_SET` tests only the day byte at
`&F5` (`INC A` / `CP &02`, so `&00` and `&FF` both mean "no stamp"), and the
day is non-zero, so a full catalogue prints all five bytes: today's day and
month against a stale year and a stale time.

**Scope** One year in a hundred. The time loop at `&4A5E` has no such test and
writes unconditionally, so midnight and the top of the hour are safe. The fault
is only that a sentinel written for the first field of a loop is applied to all
of them.

**Not observed.** This is read out of the instructions, not seen on a machine.
Testing it needs the clock set to a year of 00 and a file saved onto a
directory slot that already held a stamped one.

---


## 7. SORT INVERSE reverts to ascending after the first 256 elements

**Where** MasterBASIC `&46FF`, the exit from the descending scan.

**What** SORT picks one of three scan routines into IX and calls it once per
pass: ascending at `&46A4`, case-folding ascending at `&46CD`, and descending at
`&46F7`. Each is a 16-bit countdown -- `DEC C` every element, and when C wraps
the routine drops into its own tail, which does `DJNZ` on the high half and
carries on comparing.

The descending scan jumps to the wrong tail:

```asm
      DEC C                           ; 46FE
      JR Z,CMD_SORT_DONE              ; 46FF 28 B9   -> &46BA
```

`&46BA` is the **ascending** scan's tail. Its `DJNZ` continues at `&46AE`, which
is the ascending comparison, so from that point the pass is scanning the wrong
way round.

**The right tail is there and nothing reaches it.** Three bytes sit at `&470F`,
after the descending scan's last jump:

```asm
      DEFB &10,&F0,&C9                ; 470F   reads as DJNZ &4701 : RET
```

`DJNZ &4701` continues at the *descending* comparison, which is what the exit
needed. The jump at `&46FF` would have reached it with an operand of `&0E`; the
image has `&B9`. One byte.

**Consequence** `C` is the high half of the element count plus one, so it wraps
only once every 256 elements. An array of 256 or fewer never reaches the faulty
exit and sorts correctly. Above that, every block after the first is scanned
ascending, so `SORT INVERSE` on a large array returns something that is neither
ascending nor descending but a run of alternating orders.

**Scope** Only the descending scan. `SORT` and `SORT ABS` reach `&46BA`
legitimately, because it is their own tail.

**Not observed.** This is read out of the instructions, not seen on a machine.
It wants an array of more than 256 strings and a `SORT INVERSE`. The dead three
bytes decoding as exactly the instruction the exit should reach is what makes it
worth writing down rather than a suspicion.

---

## 8. COPY SCREEN's MODE 2 fast path tests for a mode number it never gets

**Where** `&6DB7` in `COPY_SCREEN_CONVERT`, on the fast path taken when the
two screens have the same layout.

**What** The fast copy picks how many bytes to move from the mode, and means
to choose between three answers:

```
AND A     : JR Z   ->  BC = &1B00   MODE 1, 6144 pixels + 768 attributes
LD B,&38
SUB &20   : JR Z   ->  BC = &3800   MODE 2, pixels and attributes &2000 apart
                   ->  A = 1, BC = &2000   MODE 3 or 4, one page + &2000
```

`SUB &20` tests for `&20`, which is the mode in bits 5 and 6 of a `VMPR`-style
byte. But `A` here is the 0-to-3 mode that `SCREEN_NUMBER_ARGUMENT` builds at
`&6DF0`–`&6DF3` with `RLCA` three times and `AND &03`, and every other test in
the routine — `CP &02` at `&6CD4`, `&6CE3` and `&6CE9` — reads it that way. So
`SUB &20` gives `&E1`, `&E2` or `&E3` and never zero.

**What follows** The MODE 2 branch is unreachable, the `LD B,&38` two bytes
above it is dead, and a MODE 2 to MODE 2 `COPY SCREEN` falls through to the
MODE 3/4 case and moves 24576 bytes where 14336 would do.

**Harmless, and worth writing down anyway.** The extra 10K is read from and
written to the same offsets of the two screens' own page pairs, so the copy
still lands correctly and nothing outside the screens is touched; the command
is slower than it needs to be and that is all. It is here because the dead
branch is evidence about the code rather than about the picture: someone
changed the mode representation and left one test behind.

**Not observed.** Read out of the instructions. `&20` is MODE 2 in `VMPR`
terms, which is what makes the intent legible.

---

## 9. `NVAL` writes `STKEND` back 256 too low when the copy crosses a page

**Where** `&4211`–`&421C` in `FN_NVAL_STACK`, the tail of `NVAL` that pushes a
three-, four- or five-character `SVAL$` string onto the calculator stack.

**What** The five bytes are copied by `LDIR`, and `STKEND` has to be written
back past them. `STKEND` is read as the ROM sees it, in `&4000`–`&7FFF`, and
has to be turned into a windowed address to be written through:

```
LD DE,(STKEND+&4000)   ; the ROM's view
LD A,D                 ; keep the ROM-view high byte
SET 7,D : RES 6,D      ; window it: &4x -> &8x
LD BC,&0005
LDIR                   ; DE advances by five
LD D,A                 ; put the ROM-view high byte back
LD (STKEND+&4000),DE   ; and store it
```

`LD D,A` restores the high byte *as it was before the `LDIR`*. When `E` was
`&FB` to `&FF` the `LDIR` carried out of `E` into `D`, and that carry is thrown
away — so the `STKEND` written at `&421C` is 256 below where the calculator
stack actually ends.

**What follows** The ROM reads `NVAL`'s result from `STKEND`, so it gets stale
bytes, and the calculator stack is left inconsistent for whatever comes next.
`RES 7,D : SET 6,D` in place of `LD D,A` would undo the windowing on the
*post-`LDIR`* high byte and be correct, at a cost of three bytes.

**Five alignments in 256.** `STKEND` where `NVAL` runs depends on the
expression around it, so this shows up as `NVAL` of a 3-, 4- or 5-character
string going wrong in some contexts and not others — which is the shape of
fault that survives testing. The two-character integer path is not affected: it
goes through the ROM's own stacking routine, which maintains `STKEND` itself.

**Not observed.** Read out of the instructions. The windowing either side of
the `LDIR` is what makes the intent legible: the author knew `D` had to be
converted back and reached for the saved copy rather than the arithmetic.

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

## The skip note claims an overlap it never tests for

Not a bug in the software: a bug in this repository's generator, left
open because the obvious fix is wrong.

A run of bytes the trace could not reach gets one of two notes, and
`skipped_runs` in `tools/dis_mb.py` chooses between them by whether the
decode from the run's start overruns the run's end:

```
d.comments.setdefault(
    s, ('skipped: reads as %s from here, and as part of the '
        'instruction above it' % first.text) if p > e else
       ('reads as %s, and nothing the trace can follow '
        'reaches it' % first.text))
```

"As part of the instruction above it" is a claim about what comes
BEFORE the run. `p > e` is a fact about the other side of it. The two
coincide often enough that the note is usually right, and at `&5DBD` it
is: `&5DBC` is `CB F6`, `SET 6,(HL)`, and `&5DBD` is its second byte, so
entering there really does give `OR &C9` instead.

At `&5DBF` it is false. `&5DBE` is `C9`, a whole `RET`, and nothing
above reaches past it; `&5DBF` is the head of an eleven-byte fragment
that `&5CCC` copies to `&5031`, and it overran its end for that reason.

**The obvious fix does not work.** Replacing the test with a scan back
through `d.insns` for an instruction that ends after `s` suppresses the
note *everywhere* — the count goes from six to nought, and `&7409`, a
genuine `&21` skip that `docs/idioms.md` documents, loses its
`SKIP_2_VIA_LD_HL` name with it. So `d.insns` does not hold what that
scan assumes at the point `skipped_runs` runs, and the real fix starts
by finding out what it does hold. `checkdocs` caught the regression,
which is the check working: `docs/idioms.md` quotes the line.

## Eighteen labels credit a caller that does not exist

Another generator bug rather than a MasterDOS one, and this entry exists
because the size of it was not known until it was counted.

A `notes/` entry of the form `DOS &742F expr RDDT-3` rewrites an
operand so it reads as an expression rather than as whatever label
happens to sit at that address. The rewrite works, and the build proves
it still assembles to the same byte. What does not happen is the
retraction: the address was already recorded in `d.xrefs` when the
operand first resolved, so the label it used to name goes on listing
that instruction as a caller.

`&742F` is the example that turned it up. It reads `LD HL,RDDT-3`, which
is `&4244`, and `&4244` is also exactly `EAPG`'s address — so `EAPG`'s
header still says `; ---- EAPG ---- from &43DC, &742F`, crediting a read
that the instruction does not perform. The 1991 source writes the same
operand as `RDDT-3`, and `GFPA` three instructions later already renders
`FIPT-3` correctly, so the operand text was never in doubt.

**There are 108 `expr` notes and 18 of them leave a stale cross-reference
behind.** They can be listed by walking `notes/` for `expr` entries and
grepping each listing for a `; ---- ` line that still names the address.
Two are worse than the rest: `PTH2` is credited `MB &773A`, which is the
wrong page as well as the wrong instruction, and `V7C0E` collects three
of them.

`notes.py` carries a comment saying this was attempted and abandoned —
removal from `d.xrefs` in the `expr` branch, against both the raw
`&hhhh` operand and the resolved label name, on the deep copy
`write_clean` makes, and something afterwards puts it back. The
candidates for that "something" are the passes that run after
`notes.apply`: `decode_marked_code`, `render_tables` and `render_drtab`,
each of which resolves operands again. None of them was eliminated, so
the next attempt should start by finding which one it is rather than by
trying the removal a third time.

## DVAR 22, "ADDR OF HOOKS", points into the middle of a routine

A MasterDOS bug, and a user-facing one: `DVAR 22` is documented as the
address of the hook table, and a program that reads it to find the
table is sent to the wrong place.

In this image `&4236` holds `&43F3`:

```
DEFW &43F3    ; 4236 F3 43  22 (2) ADDR OF HOOKS
```

The hook table, `SAMHK`, is at `&44A6` — 179 bytes further on. `&43F3`
is `LD L,C`, in the middle of a routine.

The 1991 source writes this entry as `DEFW SAMHK`, a symbolic reference
that cannot go stale, so the fault is not in the source. It is in this
build: `autoMBM` relocates MasterDOS to make room for MasterBASIC, and
this word was not moved with the table it names. Nothing patches it
afterwards — the boot loader and `INSTALLER` between them write several
operands into this half, and `&4236` is not among them.

The consequence is narrow, because nothing inside either half reads
`DVAR 22`: every internal reference to the hook table reaches it by
label. It is only a program outside the DOS, following the documented
DVAR, that would be misled.

The standalone `res/MDOS23.bin` could not be checked against this: it is
a different build (15750 bytes against this half's 16320), and the eight
bytes at this image's `&44A6` do not occur in it at any offset, so
neither the table nor the pointer can be aligned between the two.
