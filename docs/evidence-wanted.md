# Evidence wanted

What this project cannot settle by reading. Each entry says what to capture,
why, and what it would decide — so that whoever has the hardware or the
emulator can do it without reading the rest of the repository first. All five
are answered, and are kept because the answers are worth more than the
questions were. One capture is still wanted, and it is a cheap one: the
second `SAVE BOOT` in item 1.

---

## 1. Answered — `file/MBPOST.bin` is a `SAVE BOOT` file, and it carries settings

Kept here because the answer is worth more than the question was. It was made
by booting `dsks/MasterDOS2_3_MasterBasic1_7.mgt` under SimCoupe and doing a
`SAVE BOOT` onto a fresh disk, so it is not memory at those addresses — it is
eight blocks assembled from four places, of which only two are the pages they
appear to be. `notes/mb-postboot.txt` has the map.

That closes the "381-byte copy with no copier" this file used to ask about,
and the two write breakpoints that found nothing were both correct: block 8
never was in MasterBASIC's page. It also confirms the block layout from the
outside — every block whose source can be checked against the system page
dumps matches byte for byte, 162, 36, 671 and 381 bytes respectively.

**The second capture is in, as `file/MDMB2.bin`.** Four `DUMP` settings were
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
`&4062`, a word holding `&7C13` in the first file and `&7C5C` in the second.
Five instructions use it (`&5428`, `&5455`, `&5461`, `&5481`, `&548C`) and every
one moves it with `INC L` or `DEC L` and never `INC HL`, so it addresses a
256-byte buffer at MasterBASIC's own `&7C00` and the high byte never changes.
The code around it walks carriage-return-terminated text there and exchanges it
with the ROM's `ELINE` and `KCUR`. That region is one of the blocks installed
into the system page at boot; once installed the copy here is dead and gets
reused, the same trick `DUMP` plays with the grey map at `&7B80`. It differs
because it is live session state — where the pointer had got to when the file
was saved.

*Block 2, the DOS page — twenty-four bytes.* The file's own name in two places,
`&413C` and `&7C15` in the channel record, `MBPOST` against `MDMB2`; the sector
map at `&7C22`–`&7C2F` moving as the bits shift for a different allocation; and
four counters at `&41FC`, `&41FE`, `&42E6` and `&42E9`. All of it is the record
of the file being written, not settings.

**Still open, and cheap:** the same again with a `KEY` assignment rather than a
`DUMP` setting. `KEY` writes a table in the system page, so it should land in
one of blocks 4, 6, 7 or 8 — which of them is not established, and this
experiment cannot say, because those four blocks did not move at all.


---

## 2. Answered — the system page, all 16K of it

Three dumps arrived: `file/SYSPAGE_before_boot.bin`, taken from a reset
machine with no DOS in memory; `file/SYSPAGE_after_MasterDOS_loaded.bin`,
with MasterDOS 2.3 booted alone; and `file/SYSPAGE_after_MBMD_boot.bin`,
after the combined DOS/MasterBASIC file. Each is the whole of page 0,
`&4000`–`&7FFF`.

The copy rules now predict the entire page to within 33 bytes, every one of
them a two-byte pair at an address the machine resolves for itself. The
before-dump made the check a much stronger one — a byte the model gets right
because the ROM already had that value no longer counts as a success — and
the MasterDOS-only dump separated the DOS's 319 bytes from MasterBASIC's.

Two things came out of it that reading alone had not. The boot's last act is
`INSTALL_TAIL_INTO_SYSPAGE`, twenty-five bytes at the DOS's `&7D60` that the
listings had as data; it copies the DOS page's tail into the system page and
closes the round trip that `notes/mb-install.txt` had had to leave as "the
likeliest reading of two copies that go the wrong way". And the 36 bytes at
`&4BA0` turn out to be MasterDOS's, not MasterBASIC's — they are already
there with the DOS booted alone.

---

## 3. Answered — `SIZE_EXTERNAL_MEMORY` runs at `&7DFA`

It is MasterDOS's `MRINIT`, and it lives inside `INSTALLER` — the 943 bytes
the boot sector copies from MB `&75E1` to `&BC00`. So it runs at DOS `&7C00` +
`&1FA` = `&7DFA`, and its `OUT` to port `&80` at `&7E04`, which is where a
breakpoint caught it. A breakpoint on `&77DB` never fires: every search this
project ran for `&77DB` was looking for something that was never going to be
there.

`file/LiveDuringMRINIT.bin` is the DOS page dumped while it ran, and it shows
the copy at `&7C00`–`&7FAE` matching the stored bytes over all 943. The two
operands that never agreed with any relocation — `CALL &7806` and `JP &77FE` —
are calls into the DOS's own `RMRBIT` and `SMRBIT`, which clear and set a
page's bit in `MRTAB` through `MRADDR`. The listing had been resolving them
against MasterBASIC's half, where those addresses happen to hold other code.

---

## 4. Answered — the last page, from a full memory dump

`file/FullMemoryDump_After_MB_Load.bin` is 512K, all 32 pages, taken after the
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
`dsks/` give enough test data to check any claims against.

---

## 6. Answered — `DUMP n,m` magnifies the other way round from the manual

**Captured.** `file/printmode4dump1,2.txt` and `file/printmode4dump2,1.txt`:
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




## Notes on capturing

- Anything saved as a CODE file on an `.mgt` or `.dsk` image can be dropped
  in `dsks/` and extracted here — the directory format and sector chains are
  understood, and `ref/masterdos/docs/disk-format.md` documents them.
- Raw binaries are just as good; `file/` is where the existing dumps live.
- Say which ROM version the machine is running if it is not 3.0. The fifteen
  signature searches in the dump all resolve against ROM 3.0, which is how
  the current one was identified.
