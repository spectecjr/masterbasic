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

## 3. `SIZE_EXTERNAL_MEMORY` at `&77DB`

**The problem.** Nothing calls it. It has no reference in either half, is not
one of the addresses the DOS reaches in the copied block, does not appear as
a table word, and is installed nowhere. Its own flow does not close either:
the `CALL` at `&77F5` cannot return, which leaves the instructions that save
`SP` unreached, though the fill needs them to have run.

**What I am doing about it without help.** `dsks/MasterBasic1.7.dsk` holds
`samdos2` and `MBMC`, two other DOS binaries this MasterBASIC runs with. If
either references the routine, it is vestigial here and that is the answer.

**What would help if that fails.** A machine or emulator configured **with
external memory**, and a note of whether MasterBASIC behaves differently —
`FPAGES` reporting more, say. If it behaves identically with and without,
that is good evidence the routine is simply dead.

---

## 4. Nothing needed: the rest of the disc code

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
