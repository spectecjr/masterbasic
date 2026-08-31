# Evidence wanted

Four things this project cannot settle by reading, in the order they would
help. Each says what to capture, why, and what it would decide — so that
whoever has the hardware or the emulator can do it without reading the rest
of the repository first.

---

## 1. Who copies 381 bytes into `&7E43`? *(highest value)*

**The fact.** On a booted machine, MasterBASIC's `&7E43`–`&7FBF` is an exact
copy of the ROM's system page at `&5896`–`&5A12` — all 381 bytes. That is the
DEF KEY gap, the whole keyboard table, and the DUMP settings. In the shipped
file those bytes are a fragment of somebody's BASIC program (`TOTAL FRAMES`,
`moveinf`), so something writes them at run time.

**What I have ruled out.** There are exactly three literal address loads in
the whole image that could start such a copy, and none of them is it:

| where | what | why not |
|---|---|---|
| MB `&646F` | `LD HL,&9896` | `SAVE_BOOT`'s own source, reading *out* |
| MB `&5081` | `LD DE,&5896` | the channel pointer |
| MB `&7AC5` | `LD HL,&7E43` | the installer's 40 bytes, going the other way |

No `LD DE,&7E43` or `LD DE,&BE43` exists anywhere in either half. No `LDIR`
in either half carries a length of `&017D`. The installer's copy is
`LD C,&28` — forty bytes — and its operand is not among the boot-time patch
sites. The boot sector has been read and does not do it.

### What would settle it

**A memory-write breakpoint, on `&7E8E`.**

An earlier version of this file asked for `&7E6B`, and that was a bad address:
it lies in the one stretch of the region that is **zero after boot and zero in
the system page as well**, so nothing ever writes it. Watching it finds only
the ROM's `MNINIT` clearing the page at reset, which is exactly what happened
when it was tried.

Here is the region after boot, against the system page it mirrors:

| MasterBASIC | bytes | system page | what |
|---|---|---|---|
| `&7E43` | 39 | `&5896` | the installed gap block — **loaded from the file** |
| `&7E6B` | 35 | `&58BE` | zero, and zero in the system page too |
| `&7E8E` | 210 | `&58E1` | `KTAB`, the keyboard table, which begins at `&58E0` |
| … | | … | short runs on to `&5A12` |

`&7E8E` is the first byte in the region that is **non-zero after boot and
different from the file**, so whatever puts the keyboard table there has to
write it. Anywhere in `&7E8E`–`&7F5F` would do as well.

**Watch all three aliases of it, or the physical byte.** This matters and is
probably why nothing else was caught: a routine copying *into* MasterBASIC's
page would most naturally do it with that page in the `&8000` window, writing
`&BE8E` rather than `&7E8E`. If SimCoupe can break on a page and offset, use
that; otherwise set three breakpoints — `&7E8E`, `&BE8E`, and `&3E8E` for
completeness.

What I need back is the **PC when it stops**, and `LMPR` and `HMPR` if they
are easy to read. One line is enough.

### What the answer would decide

Two possibilities are still open and this separates them.

- If something writes `&7E8E` **after** the file has loaded, there is a copier
  and the PC names it.
- If the only writes are the load itself, then the file's own bytes never
  reach `&7E6B`–`&7FBF` — the region after the gap block would be loader
  output, not file content — and that is a different and more interesting
  question about how much of the file is loaded at all. The file has a
  fragment of a BASIC program at `&7E6B` and the running machine has zero
  there, which is what makes this worth asking.

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
