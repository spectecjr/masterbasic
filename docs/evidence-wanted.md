# Evidence wanted

Four things this project cannot settle by reading, in the order they would
help. Each says what to capture, why, and what it would decide — so that
whoever has the hardware or the emulator can do it without reading the rest
of the repository first.

---

## 1. How was `file/MBPOST.bin` made? *(highest value, and cheap)*

This was "who copies 381 bytes into `&7E43`" until two breakpoints said
nobody does. Watching writes to `&7E6B` and then to `&7E8E` on a real machine
caught only the ROM's `MNINIT` clearing the page at reset. The second address
is a good one — it is inside the copy of `KTAB`, non-zero after boot and
different from the file — so if anything wrote it, that would have fired.

So the keyboard table in `MBPOST.bin` did not get there by booting, and the
question is no longer about MasterBASIC at all. It is about the dump.

**What I need.** Either of these:

- **A sentence** saying how `MBPOST.bin` was produced — which disk was booted,
  and what was run to write the three dumps out.
- **Or a look at `&7E90` after a clean boot of
  `dsks/MasterDOS2_3_MasterBasic1_7.mgt`.** The file has `28 66 72 6D 73 29`
  there — `(frms)`, out of a fragment of somebody's BASIC program. If a clean
  boot shows that, `MBPOST` is not a clean-boot dump and the matter is closed.

**Why it matters.** Two things fit every observation. The machine may have
booted a file that had been through `SAVE BOOT`, which *has* the keyboard
table at `&7E43` because `SAVE_BOOT`'s eighth block reads `&5896`–`&5A12` out
of the system page and writes it into the file. Or whatever took the dumps
used the top of this page as a buffer — it is dead space once the installer
has run, which makes it an obvious choice.

Either way nothing is wrong with the disassembly; what would be wrong is
leaving a "copy with no copier" in the notes when the copy is an artefact of
how the evidence was gathered.

---

## 2. The system page above `&5BFF`

**Why.** `postinstall/syspage.asm` reconstructs the ROM's system page as
MasterBASIC leaves it. Below `&5C00` that reconstruction is *checked*: the
copy rules predict `file/SYSPAGE.bin` and `file/SYS2.bin` to within 28 bytes,
and every one of those is a hole the file carries as zero and the machine
carries filled in. Above `&5BFF` nothing has checked it, and the file says so.

**What to capture.** A dump of the ROM's system page from `&5C00` to `&7FFF`
— 8192 bytes — from a booted machine, the same way `SYS2.bin` was made.
Saving it as a CODE file on a disk image is ideal; I can extract it.

**What it decides.** Whether the four ROM vectors and the stubs behave as
modelled where the model is currently unverified, and it would let the build
report agreement across the whole page instead of half of it.

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
