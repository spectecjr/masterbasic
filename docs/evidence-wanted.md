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

**An emulator with a memory-write breakpoint.** SimCoupe's debugger will do
this. Boot `dsks/MasterDOS2_3_MasterBasic1_7.mgt` and break on a **write to
logical address `&7E6B`**.

That is the whole instruction, and the logical address is deliberate. There
is no fixed page number to give: MasterBASIC's page is decided at boot, and
the installer finds it the same way everything else does —

```asm
      IN A,(LMPR)
      INC A
      AND PAGEMASK
```

— so it is whatever `LMPR` + 1 happens to be. The page byte in the file's own
header is no help either: it is the saved address divided by 16384, from a
machine with external memory, and nothing reads it. `PAGE1` is written once,
at `&63A7`, and the only access to `&4151` anywhere in either half is that one
`LD (PAGE1),A`. See `docs/disassembly.md` for the working.

A breakpoint on logical `&7E6B` will also fire for the DOS half, which sits
at the same addresses when its own code runs. That is fine and costs nothing:
there should be few hits, and the PC says which half it was.

What I need back is just **the PC when it stops** — the address of the
instruction doing the write. One line is enough. If it stops somewhere in
`&4000`–`&7FBF` I can tell from the surrounding code which half it belongs
to; if you can also say what `LMPR` held, that settles it outright.

### If a breakpoint is not available

Two dumps of MasterBASIC's page taken at known moments would narrow it
almost as well:

- **A** — immediately after boot, with nothing typed at all.
- **B** — after one specific action, and say which: a `KEY` command, a
  `DUMP`, a `SAVE`, or just pressing a few keys.

If `&7E6B`–`&7FBF` already holds the keyboard table in **A**, it happens
during boot and I will look again at the installer with that in mind. If it
only appears in **B**, whatever you did is the trigger and that tells me
where to look.

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
