# Evidence wanted

What this project cannot settle by reading. Each entry says what to capture,
why, and what it would decide — so that whoever has the hardware or the
emulator can do it without reading the rest of the repository first. Two of
the four are now answered, and are kept because the answers are worth more
than the questions were.

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

## 3. `SIZE_EXTERNAL_MEMORY` at `&77DB` — runs, but nothing calls it

**This was "is it dead code", and the answer is no.** Every dump in `file/`
was taken under SimCoupe with one 1MB external module fitted, which turned
out to settle it. `MBPOST.bin` carries the DOS page of a booted machine, so
`MRTAB` — the bitmap of MegaRAM pages in use, DVARs 118–149 at `&4296` — can
be read straight out of it. The shipped image has 32 bytes of `&00` there;
`MBPOST` has 8 of `&00` and 24 of `&FF`. Sixty-four pages free, 192 not, and
64 pages of 16K is exactly the 1MB fitted.

Nothing else could have done it. Searching every binary and every dump for
`OUT (&80),A` finds two in the running system: the DOS's `&75B2`, a single
select inside ordinary MegaRAM access, and `&77E5`, which is this walk. The
routine is MasterDOS's own `MRINIT`, relocated — 153 of 176 bytes identical
to `MDOS23.bin`, every difference a two-byte address operand — and `autoMBM`
moved it out of the DOS page, where its code no longer appears at any offset.

**What is left, and it is small.** `&77DB` still has no reference anywhere in
either half, and the operands inside the block do not agree on one relocation
delta. **A breakpoint on `&77DB`, or on the `OUT` to port `&80`, would name
the caller in one go** — the PC when it stops is all I need.

---

## 4. The two pages a `SAVE BOOT` file cannot show

**Why.** `MBPOST.bin` is the only view this project has of the two pages a
running machine holds, and it is not a complete one. Only blocks 2 and 5 are
the live pages they appear to be, so it covers:

| page | covered | blind |
|---|---|---|
| DOS | `&4100`–`&7D5F` | `&4000`–`&40FF`, `&7D60`–`&7FBF` |
| MasterBASIC | `&4000`–`&7B7F` | `&7B80`–`&7FBF` |

Both blind spots are blind for the same reason: `SAVE BOOT` fills those slots
from elsewhere *because* the running machine no longer holds what belongs
there. `&4000`–`&40FF` is the boot sector and `&7D60`–`&7FBF` the DOS's tail —
boot-time-only code, overwritten by the time anything could save it.

**What to capture.** A 16K dump of each of the two pages from a booted
machine, the same way the page-0 dumps were made. Dumping by physical page in
SimCoupe's debugger is safest; the two are told apart by MasterBASIC's page
opening with the XVARs (`PUTSWA` at `&4000`) and the DOS page having its
variables around `&4100`.

**What it decides.** It is where a boot-time routine would live, and it is the
one part of a running machine nothing here covers — which means every search
that came up empty in "the DOS page after boot" was really a search of
`&4100`–`&7D5F` only. `SIZE_EXTERNAL_MEMORY` above is the live example: these
dumps might answer item 3 without a breakpoint at all.

---

## 5. Nothing needed: the rest of the disc code

Formatting, the directory as a structure, and the RAM discs are reading time
rather than evidence. `docs/disc.md` follows a read and a write end to end;
what is either side of those two paths is unread, and the disk images in
`dsks/` give enough test data to check any claims against.

---

## Notes on capturing

- Anything saved as a CODE file on an `.mgt` or `.dsk` image can be dropped
  in `dsks/` and extracted here — the directory format and sector chains are
  understood, and `ref/masterdos/docs/disk-format.md` documents them.
- Raw binaries are just as good; `file/` is where the existing dumps live.
- Say which ROM version the machine is running if it is not 3.0. The fifteen
  signature searches in the dump all resolve against ROM 3.0, which is how
  the current one was identified.
