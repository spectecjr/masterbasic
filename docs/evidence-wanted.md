# Evidence wanted

What this project cannot settle by reading. Each entry says what to capture,
why, and what it would decide — so that whoever has the hardware or the
emulator can do it without reading the rest of the repository first. All five
are answered, and are kept because the answers are worth more than the
questions were. Items 7 and 8 are open, and are questions rather than
captures: 8 in particular could be settled by anyone who can save a
compressed screen and look at the directory entry.

---

## 1. Answered — `dumps/MBPOST.bin` is a `SAVE BOOT` file, and it carries settings

Kept here because the answer is worth more than the question was. It was made
by booting `diskimages/MasterDOS2_3_MasterBasic1_7.mgt` under SimCoupe and doing a
`SAVE BOOT` onto a fresh disk, so it is not memory at those addresses — it is
eight blocks assembled from four places, of which only two are the pages they
appear to be. `notes/mb-postboot.txt` has the map.

That closes the "381-byte copy with no copier" this file used to ask about,
and the two write breakpoints that found nothing were both correct: block 8
never was in MasterBASIC's page. It also confirms the block layout from the
outside — every block whose source can be checked against the system page
dumps matches byte for byte over 162, 36, 381 and 670 of the 671 bytes. The
odd one is `&4A97`, which is the operand of an `LD (HL),&00` written after the
copy was made, so the copy rightly still holds the file's `&00`.

**The second capture is in, as `dumps/MDMB2.bin`.** Four `DUMP` settings were
poked and the machine re-saved. The predictions were written down first, in
this file, and all four hold:

| what | file offset | was | now |
|---|---|---|---|
| `XVAR 5` `DTTH` | 16325 | 1 | **3** |
| `XVAR 15` `SDORI` | 16335 | 0 | **4** |
| `XVAR 16` `SDLHS` | 16336 | 0 | **32** |
| `XVAR 19` `SDBOT` | 16339 | 0 | **16** |

Both files are 32640 bytes, and blocks 1, 3, 4, 6, 7 **and 8** are byte-identical
between them — so `SAVE BOOT` does what it is for: a user's settings go into the
file and come back at the next boot.

**What differs, and all of it is accounted for.** Only two blocks move, and they
are exactly the two that are live memory:

*Block 5, the MasterBASIC page — five bytes.* Four are the pokes. The fifth is
`&4062`, a word holding `&7C13` in the first file and `&7C5C` in the second —
the last-line recall pointer. The manual's own description of that feature
names it: CNTRL/up-arrow recalls the line before, again goes back further,
and "you can keep recalling lines until eventually you go right 'round' the
line-storage buffer… (The buffer capacity is 256 bytes.)" Every instruction
that touches the pointer moves it with `INC L` or `DEC L` and never `INC HL`,
which is both the 256 bytes and the going-round, and the code beside it walks
carriage-return-terminated text and trades it with the ROM's `ELINE` and
`KCUR`. The buffer sits at MasterBASIC's `&7C00`, which is one of the blocks
the installer copies into the system page — once copied, the copy here is dead
and this takes it over, the same trick `DUMP` plays at `&7B80` with its grey
map. It differs between the two files because it is live session state: the
two sessions had typed different amounts at it. See `notes/mb-editbuf.txt`.

*Block 2, the DOS page — twenty-four bytes.* The file's own name in two places,
`&413C` and `&7C15` in the channel record, `MBPOST` against `MDMB2`; eight bytes
of the sector map, at `&7C22`–`&7C25` and `&7C2C`–`&7C2F`, moving as the bits
shift for a different allocation; four counters at `&41FC`, `&41FE`, `&42E6` and
`&42E9`; and two more inside the channel record, `DCHAN`+`&12` and `DCHAN`+`&20`,
each exactly eight higher in the larger of the two files. That is all
twenty-four, and all of it is the record of the file being written, not
settings.

**The `KEY` question is answered too, by a third capture.** `dumps/MDMB3.bin` is
a clean boot with no `XVAR` pokes and one `KEY 104,200`. Exactly one byte moved
in a system-page block, and it is the 200:

| | |
|---|---|
| file offset | 32437 |
| block | 8, at +178 |
| system page | `&5948` |
| was | 71, `"G"` |
| now | 200 |

So `SAVE BOOT` **does** preserve key assignments, and they ride in block 8.

*The first attempt at this was void, and the reason is worth keeping.*
`MDMB2.bin` had `KEY 36+70,24` applied and no system-page block moved a byte —
because the manual says two paragraphs earlier that MasterBASIC already performs
that exact assignment at boot, so the command wrote a value over itself. The
suggestion was taken from a manual sentence without reading what the sentence
said. A code that cannot occur by accident, on a key whose default is not
already that code, is what the test needed.

**It confirms two things that had only been read, never seen from outside.**

*The key table's base.* `notes/mb-syspatches.txt` puts the ROM's key table at
`&58E0`, one byte per key, derived by reading what MasterBASIC pokes into it.
Working the other way — from the manual's own `KEY 36+70,24` and `KEY 27+70,25`,
whose codes 24 and 25 appear at `&594A` and `&5941`, nine apart for key numbers
nine apart — gives a base of `&58E0` and makes the changed byte key 104. Two
independent routes, same answer.

*The block map.* Block 8's source was worked out by reading `SAVE_BOOT` at
`&6404`. A byte poked into the live system page at `&5948` turning up at file
offset 32437, which the map says is `&5896 + 178 = &5948`, is that map confirmed
end to end by a write rather than by a comparison.

**Nothing further is wanted here.** All three captures are in `dumps/`.


---

## 2. Answered — the system page, all 16K of it

Three dumps arrived: `dumps/SYSPAGE_before_boot.bin`, taken from a reset
machine with no DOS in memory; `dumps/SYSPAGE_after_MasterDOS_loaded.bin`,
with MasterDOS 2.3 booted alone; and `dumps/SYSPAGE_after_MBMD_boot.bin`,
after the combined DOS/MasterBASIC file. Each is the whole of page 0,
`&4000`–`&7FFF`.

The copy rules now predict the entire page to within 33 bytes: fifteen
two-byte pairs at addresses the machine resolves for itself, and three single
bytes holding MasterBASIC's own page number. The
before-dump made the check a much stronger one — a byte the model gets right
because the ROM already had that value no longer counts as a success — and
the MasterDOS-only dump separated the DOS's 319 bytes from MasterBASIC's.

Two things came out of it that reading alone had not. The boot's last act is
`INSTALL_TAIL_INTO_SYSPAGE`, nineteen bytes at the DOS's `&7D60` that the
listings had as data; it copies the DOS page's tail into the system page and
closes the round trip that `notes/mb-install.txt` had had to leave as "the
likeliest reading of two copies that go the wrong way". And the 36 bytes at
`&4BA0` are already there with the DOS booted alone — though so are the 40 at
`&5896`, and both installers write both, so the dumps cannot say whose work
either block is.

---

## 3. Answered — `SIZE_EXTERNAL_MEMORY` runs at `&7DFA`

It is MasterDOS's `MRINIT`, and it lives inside `INSTALLER` — the 943 bytes
the boot sector copies from MB `&75E1` to `&BC00`. So it runs at DOS `&7C00` +
`&1FA` = `&7DFA`, and its `OUT` to port `&80` at `&7E04`, which is where a
breakpoint caught it. A breakpoint on `&77DB` never fires: every search this
project ran for `&77DB` was looking for something that was never going to be
there.

`dumps/LiveDuringMRINIT.bin` is the DOS page dumped while it ran, and it shows
the copy at `&7C00`–`&7FAE` matching the stored bytes over all 943. The two
operands that never agreed with any relocation — `CALL &7806`, `CALL &77FE`
and `JP &7841` — are calls into the DOS's own `RMRBIT` and `SMRBIT`, which
clear and set a
page's bit in `MRTAB` through `MRADDR`. The listing had been resolving them
against MasterBASIC's half, where those addresses happen to hold other code.

---

## 4. Answered — the last page, from a full memory dump

`dumps/FullMemoryDump_After_MB_Load.bin` is 512K, all 32 pages, taken after the
boot. Both pages were found by content rather than by number: MasterBASIC's
begins `FF 48` — `XVAR 0` `PUTSWA` — and it is **page 28**, with the DOS at
**page 29**.

It confirms every deduction that had been made without it, from an independent
capture: the installer's copy at DOS `&7DFA` and its `OUT` at `&7E04`, `INSTBUF`
at MB `&7DF0` matching syspage `&4F00` in all 446 bytes, and the alternate
character set at MB `&7E64` matching syspage `&4F74` in all 328.

And it shows the tail of MasterBASIC's page, which nothing had — the region
`MBPOST.bin` cannot reach. See `notes/mb-saveboot.txt`: the gap block's source
is overwritten by `INSTBUF`, which is why `SAVE BOOT`'s eighth block has to read
the system page; MB `&7CF7` holds nine `&0D`, which is what a `SAVE BOOT` file
carries where a header would be; and the DOS's boot sector really is kept at
MB `&7D00`.

Nothing here is outstanding.

---

## 5. Nothing needed: the rest of the disc code

Formatting, the directory as a structure, and the RAM discs are reading time
rather than evidence. `docs/disc.md` follows a read and a write end to end;
what is either side of those two paths is unread, and the disk images in
`diskimages/` give enough test data to check any claims against.

---

## 6. Answered — `DUMP n,m` magnifies the other way round from the manual

**Captured.** `dumps/printmode4dump1,2.txt` and `dumps/printmode4dump2,1.txt`:
the printer stream from a full MODE 4 screen, dumped twice. Every bit-image
line begins `ESC "*" CHR$ 4 n1 n2`, and `n1 + 256*n2` is the number of dot
columns across the paper.

| | dot columns | lines of 8 dots | printed size |
|---|---|---|---|
| `DUMP 1,2` | 512 | 24 | 512 × 192 — double width, single height |
| `DUMP 2,1` | 256 | 48 | 256 × 384 — single width, double height |

**Answer.** The reading was right and the manual's general statement is
inverted: for an upright dump the *first* number magnifies the height and the
second the width. The line counts confirm it from the other side — 24 lines of
eight dots is the screen's own 192 rows unmagnified.

The manual is right about the sideways case, which is what `DUMP 3` and MODE 3
get, and its MODE 3 advice is correct for that reason. Written up as
`docs/bugs.md` 5, with a note in `docs/original/ERRATA.md`.

**Worth keeping as a method.** The count bytes made this decidable without a
printer, a photograph, or any judgement by eye: two bytes per line, predicted
in advance, and a second quantity — the line count — that had to agree and
did. The prediction was recorded before the capture, which is what made the
result worth anything.

---

## What is still wanted, at a glance

Three captures and a page of BASIC would close everything below.

| | Closes | Cost |
|---|---|---|
| **A dump of page 3 with the Spectrum emulator loaded**, and of the system page while Spectrum mode is active | 9, and test 10d under it | needs Spectrum mode entered |
| **The word at `&4EFE` in the system page while `SPLIT` runs** | 7 | needs a break in the right place |
| **A directory entry read back after saving a compressed screen** | 8 | easy |
| **Seven short BASIC tests**, 10a to 10g | seven of the nine defects that have never been run | easy — a machine and a few lines each |
| *(10h, 10i and 10j want damaged discs or an unreachable stack, and are listed so nobody spends an afternoon on them)* | — | hard to impossible |

The Spectrum capture is the valuable one: it is the only thing that would
settle where the NMI menu is entered from, and one of the defects below sits on
the same path and cannot be exercised without it.

---

## 7. What the ROM's outermost error handler is while `SPLIT` runs

**Open.** `SPLIT`'s last fifty-five bytes, `MB &6F07-&6F3D`, rewrite the
bottom of the ROM's machine stack. They read the word at `&4EFE` -- the slot
`LD SP,ISPVAL : PUSH HL : LD (ERRSP),SP` fills -- call whatever routine's
address is stored seventeen bytes below it, then put the handler back twelve
bytes earlier than it was and write `&0004` into the five stack words beneath.

The twelve makes sense against `MAINER` and the seventeen does not.
`MAINER` is `&0EED` in ROM 3.0 -- `CD D1 3F` is there and the eighteen bytes
before it are the main loop's tail -- so `&0EED-12` is the `XOR A` that clears
the error number and re-runs the edit line, which is exactly what `SPLIT`
wants to happen next. But `&0EED-17` is `&0EDC`, the middle of `LD HL,FLAGS`,
and the word there is `&5C3B`: a system variable, not a routine.

And the three system-page snapshots in `dumps/` say the base is not `MAINER`
at all:

| snapshot | word at `&4EFE` |
|---|---|
| `SYSPAGE_before_boot.bin` | `&0F78` |
| `SYSPAGE_after_MasterDOS_loaded.bin` | `&0E90` |
| `SYSPAGE_after_MBMD_boot.bin` | `&487F` |

`&487F` is MasterBASIC's own handler in the system page, and it fails both
offsets: seventeen back is `&486E`, whose word is `&F122`, and twelve back is
inside `LD HL,(&4AF1)`.

**What would settle it.** The word at `&4EFE` in the system page at the moment
a line containing a `/` is being scanned -- that is, with `SPLIT` about to run.
Failing that, two cheaper things would each narrow it:

- Whether `SPLIT` works at all on hardware. Type `10 PRINT 1/20 PRINT 2` with
  the `/` where the manual's example puts it, press ENTER, and `LIST`. If the
  two lines come out separately and the remainder is *not* also entered as a
  line of its own, the block is doing what the header guesses and the
  reasoning is wrong only about which address it starts from.
- What `&4EFE` holds after a `RUN` that stops on an error, versus after a
  plain direct command. The handler is pushed afresh at every stack reset, so
  two readings would show whether it is stable enough to be read this way at
  all.

---

## 8. What writes ROM header offsets 24 to 26 when a compressed file is saved

**Open.** MasterBASIC replaces MasterDOS's `HLOAD` hook outright -- the
original is four instructions, `LD BC,&4BB0+HLDP-PVECT / NETPA / DSCHD /
LDBLK` -- and its version at `DOS &6422` branches on bits 2 and 3 of `V42E2`,
which `COPY_HEADER_FIELDS` fills from directory entry offsets 220 and 221.
On the compressed path it does:

    LD A,(&7F85)   ; 6449
    LD H,A
    LD DE,(&7F86)  ; 644D
    CALL CALLMB : DEFW &62A6

and MasterBASIC's `&62A6` takes the first as a page and the second as an
address, folds them with `PAGED_TO_LONG` at `MB &62DC`, and expands the file
there.

**Where those two addresses come from is settled.** `COPY_HEADER_FIELDS` at
`DOS &4EE3` copies entry offsets 210-251 to `STR-30`, which is the copy that
puts a snapshot's registers back at `STR-20` for `SNAP7`. That lands entry
offset 229 on `&7F85` and 230 on `&7F86`, and since entry offset 220 is the
ROM header's offset 15, they are **header offsets 24 and 25-26** -- the
middle of the 48-byte header, between the flags at 15 and the start address
at 31, which the ROM does not use.

**What is not settled is the other end.** Nothing in either half writes
`DIFA+24` by name -- `DIFA+31`, `+34` and `+35` are all written explicitly a
few instructions apart in the same routine, and `+24` is not -- so whatever
puts a page and an address there arrives in one of the block copies that
build the entry, or the field is written through a pointer.

**What would settle it.** Save a compressed screen from MasterBASIC, then
read the directory entry back and look at offsets 229-231:

- If they hold the screen's original page and address, the field is real and
  the writer is worth finding.
- If they are zero or garbage, the LOAD path is reading a field nobody fills,
  and the compressed load only works because the expander does not depend on
  what it was handed -- which would be worth knowing on its own.

A directory sector can be read with `READ AT` or lifted straight out of an
`.mgt` image; `ref/masterdos/docs/disk-format.md` gives the entry layout, and
its table of where the ROM header's fields land stops at 220 and resumes at
236, so 229-231 are not documented there either.

---

## 9. What reaches the DOS's `&4206`, given that `NMIV` does not

`&4206` is the third entry of MasterDOS's jump table and is `JP NMI`, so the
NMI menu is plainly meant to be entered there. Nothing found so far enters it.

- `NMIV` (`&5AE0`) holds `&1C9E` in `SYSPAGE_before_boot.bin`,
  `SYSPAGE_after_MasterDOS_loaded.bin` and `SYSPAGE_after_MBMD_boot.bin`
  alike, and `&1C9E` is the ROM's own `NMISTOP`. `DOSFLG` goes `&00` to `&1D`
  across those dumps, so the later two are genuinely post-boot and the value
  is not a leftover.
- Neither half of the image writes `&5AE0`, and nothing in the 512K
  `FullMemoryDump` does either.
- ROM 3.0 calls the DOS at `&4200`, `&4203` and `&8009`, and nowhere else.

The likeliest answer is that it is the Spectrum emulator's, which the Technical
Manual points at — the snapshot button works "when the Disk Operating System
Spectrum Emulator is loaded" — and which lives in page 3, in neither half of
this image nor in the ROM. `SNAP7`'s resume path already goes through a stub at
`&B900` in that page, so there is precedent for the emulator carrying DOS-aware
code.

**What would settle it.** A dump of page 3 with the emulator loaded, or a dump
of the system page taken while Spectrum mode is active — if `NMIV` reads
`&4206` there rather than `&1C9E`, that is the whole answer.

---

## 10. Defects read out of the instructions and never seen run

Every one of these is written up in [bugs.md](bugs.md) and derived from the
code alone. None has been observed on a machine, and that is the gap: a defect
proved from the instructions and never executed is still a reading. They are in
roughly the order of how cheap they are to try.

**10a. `DVAR 22` points into the middle of a routine.** One line:

```
PRINT DVAR 22
```

Expect **17395** (`&43F3`). The hook table `SAMHK` is at **17574** (`&44A6`),
179 bytes further on, and `&43F3` is an `LD L,C` inside another routine. Any
program that reads `DVAR 22` to find the table is sent to the wrong place. If
it prints 17574, this image is not the one the defect was read out of and that
is worth knowing too.

**10b. Six pairs of file names cannot be told apart.** `CKNAM` folds bit 5 out
of every character, which was meant to make the compare case-blind and also
merges six printable pairs:

```
@ `     [ {     \ |     ] }     ^ ~     _ DEL
```

Save a file called `X^`, then `DIR "X~"`. If it lists, the fold is doing what
the code says. Then save a second file as `X~` and see which of the two a
`LOAD "X^"` fetches — that is the destructive half, and it is worth knowing
whether the DOS offers to overwrite or silently picks one.

**10c. `SORT INVERSE` reverts to ascending after 256 elements.** Fill a string
array with more than 256 elements in random order, `SORT INVERSE`, and print
it. Expect the first block descending and every block after it ascending —
neither sorted nor reversed, but alternating runs. Under 256 elements it should
be correct, which is the control.

**10d. The NMI menu's exit restores `HMPR` from the saved `LMPR`.** Enter
Spectrum mode, press NMI, press `X` to exit, then `PEEK` through the `&8000`
window and see which page answers. `SNPRT0` ships `&1F` and stays `&1F`, so the
window should come back holding page 31 rather than whatever was there.
*Needs the Spectrum capture above, or at least Spectrum mode.*

**10e. `COPY SCREEN`'s MODE 2 fast path.** `COPY SCREEN` in MODE 2 and compare
against the same picture in MODE 3. The fast path tests for a mode number it
never receives, so MODE 2 should take the slow path — visible as time rather
than as a wrong picture, which is why this one wants a stopwatch more than an
eye.

**10f. `LOCN` reads one byte past its own bound.** Put a search pattern at the
very end of a region and `LOCN` for it, with the byte immediately after the
region set to something that would change the answer. The scan bounds itself at
`N = length - patlen + 1` and then compares without a bound of its own, so for
any pattern longer than one character the extra byte is *inside* the region and
its flags are what comes back.

**10g. A year of `00` stops the date stamp half-written.** Set the clock to a
year of `00`, save a file onto a directory slot that already held a stamped
one, and `DIR` it. Expect today's day and month against a garbage year and
time — most often `&FF`, since the entry image comes from `UIFA` and the ROM
leaves that area uninitialised. One year in a hundred, so this is the one that
needs a deliberate clock rather than patience.

**10h. `LOST DATA` on a block transfer.** The block loops mask the controller
status with a value that cannot see `LOST DATA`. Inducing one needs the
processor held up mid-transfer, which is hard to arrange deliberately; a
heavily interrupt-loaded machine doing a large `LOAD` is the best chance.
Listed for completeness rather than as a realistic test.

**10i. `RECORD NOT FOUND` recovery is never chosen by the bit it tests.** Same
difficulty: it wants a disc with a deliberately damaged ID field.

**10j. `NVAL` writes `STKEND` back 256 too low.** Essentially unreachable — it
needs `STKEND` at exactly `&4DFF` when `NVAL` runs, which means about fifty
five-byte values already on the calculator stack. An expression with that many
pending operands would be an achievement in itself. Recorded so that nobody
spends an afternoon on it.

---

## Settled without new evidence

Worth separating from the above, because the answer was already in the
repository and only wanted reading:

- **Which way `SVAL$`'s ordering runs.** Its calculator program at
  `MB &4182`-`&418A` writes `&EF` — `RST &28` — and then opcodes `&31` and
  `&34`. `ref/samrom/fpcmain.asm` names them `RESTACK` and `EXIT2`: one puts
  the value in full floating-point form, the other leaves the calculator, and
  neither touches the sign. So `SVAL$` does not negate, the ordering is
  descending as decoded, and `NVAL` is its exact inverse. See
  `notes/mb-nval.txt`.

---

## Notes on capturing

- Anything saved as a CODE file on an `.mgt` or `.dsk` image can be dropped
  in `diskimages/` and extracted here — the directory format and sector chains are
  understood, and `ref/masterdos/docs/disk-format.md` documents them.
- Raw binaries are just as good; `dumps/` is where the existing dumps live.
- Say which ROM version the machine is running if it is not 3.0. The fifteen
  signature searches in the dump all resolve against ROM 3.0, which is how
  the current one was identified.
