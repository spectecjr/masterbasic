# Evidence wanted

What this project cannot settle by reading. Each entry says what to capture,
why, and what it would decide — so that whoever has the hardware or the
emulator can do it without reading the rest of the repository first. All four
are now answered, and are kept because the answers are worth more than the
questions were. Two captures are still wanted, and both are cheap: the
second `SAVE BOOT` in item 1, and one printed page for item 6.

---

## 1. Answered — `file/MBPOST.bin` is a `SAVE BOOT` file, not a dump

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

**Still wanted, and cheap:** the same `SAVE BOOT` again after changing
something a user would change — a `KEY` assignment, or a `DUMP` setting. Block
8 should carry the change and block 5 should not, which would demonstrate what
`SAVE BOOT` is for rather than only what it copies.

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

## 6. Wanted — which way round `DUMP n,m` magnifies

**What to capture.** Two printed pages from a machine with an Epson-compatible
printer, in MODE 4 with something obviously taller than it is wide on the
screen:

```basic
10 MODE 4: CLS: FOR n=0 TO 90: PLOT 128,n: NEXT n
20 DUMP 1,2
30 DUMP 2,1
```

Anything that makes the two directions distinguishable will do; a rectangle is
easier to measure than a line.

**Why.** The manual says the first number is the width magnification and the
second the height — "`DUMP 1,2` single width, double height". Read against the
code, that holds for a sideways dump and appears to be the wrong way round for
an upright one.

The routine works in two axes of its own: one that fills the eight bits of a
bit-image byte (magnified by the **first** number, at `&693E`–`&6952`) and one
that steps from byte to byte (magnified by the **second**, at `&6995`). Which
of those is the paper's width depends on the orientation, and
`TRANSFORM_DUMP_COORDS` exchanges them for an upright dump. `DUMP 3` and
anything in MODE 3 are forced sideways, where the manual's names are right;
an ordinary `DUMP 1` or `DUMP 2` in MODE 1, 2 or 4 is upright, where they
appear to swap.

**What it would decide.** Whether this is a genuine inconsistency in the
program — worth an entry in `docs/bugs.md` — or a misreading here. If the
first number turns out to magnify the width in an upright dump too, then the
axis reasoning in `notes/mb-dumpshaded.txt` is wrong somewhere and wants
finding.

---


## Notes on capturing

- Anything saved as a CODE file on an `.mgt` or `.dsk` image can be dropped
  in `dsks/` and extracted here — the directory format and sector chains are
  understood, and `ref/masterdos/docs/disk-format.md` documents them.
- Raw binaries are just as good; `file/` is where the existing dumps live.
- Say which ROM version the machine is running if it is not 3.0. The fifteen
  signature searches in the dump all resolve against ROM 3.0, which is how
  the current one was identified.
