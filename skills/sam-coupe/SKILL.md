---
name: sam-coupe
description: Use when reading, disassembling or annotating any code for the SAM Coupé — its ROM, a DOS, a BASIC extension, a game. Carries the machine facts an operand cannot be read without: the four 16K sections and the two paging ports, what each bit of LMPR and HMPR does, where the ROMs sit, the system page and its variable block with absolute addresses for the vectors and buffers, the RST entries and the ROM jump table, how a DOS is entered, the NMI path, the ROM versions and how to tell them apart, and where the reference sources are. Trigger on "SAM Coupé", "SAM Coupe", "LMPR", "HMPR", "system page", "MasterDOS", "SAMDOS", "which page is at &4000".
---

# The SAM Coupé, for reading its code

## Memory: four sections, two ports

64K of address space in four 16K sections; up to 32 pages of 16K
internal RAM (512K), pages numbered 0-31, five bits.

| section | range | which page |
|---|---|---|
| A | `&0000`-`&3FFF` | LMPR low 5 bits -- or ROM 0 |
| B | `&4000`-`&7FFF` | A's page **+1** (wraps at 32) |
| C | `&8000`-`&BFFF` | HMPR low 5 bits |
| D | `&C000`-`&FFFF` | C's page **+1** -- or ROM 1 |

**LMPR, port `&FA`.**  Bits 0-4 the page in A.  **Bit 5 set takes ROM 0
*out*** (RAM0); clear, ROM 0 occupies A regardless of the page bits.
**Bit 6 set brings ROM 1 *in*** at D (ROM1).  Bit 7 write-protects A.
So `&1F` = page 31 in A, both ROMs as normal, and section B is page 32
= page 0, the system page.  `&5F` = the same with ROM 1 on -- the ROM
source calls it "both ROMs on, page zero in section B".

**HMPR, port `&FB`.**  Bits 0-4 the page in C.  Bits 5-7 are *not*
page bits: MD3S0, MD3S1 (mode 3 colour-lookup select) and MCNTRL
(external memory).  `INC A` on a page of `&1F` sets bit 5.  A walk
that increments the page is safe only because the data ends first.

**VMPR, port `&FC`.**  The page the screen is displayed from, and the
mode in its upper bits (`&20` = MODE 2 in VMPR terms).

`HMPR` set to 0 puts the system page at C, so a routine that has done
that reads `&8xxx` as system-page `&4xxx` and `&9xxx` as `&5xxx`.  Code
in section B reaching a *different* page through section C adds
`&4000` to that page's address: write it `LABEL + IN_PAGE_C`, never a
bare number.

Other ports: `&F9` STAT (read: status, key rows, interrupt flags;
write: line interrupt), `&F8` CLUT base (16 write-only registers),
`&FE` keyboard / border, `&FF` sound, `&FD` MIDI, `&E8` printer,
`&E0`-`&E7` the disc controller (command, track, sector, data; two
drives, two sides), `&80` external memory low.

## ROM

ROM 0 at A, ROM 1 at D when enabled.  Entries that code depends on:

| addr | |
|---|---|
| `&0005` | `HLJUMP`: `JP (HL)` |
| `&0010` | `RST &10`: print A |
| `&0028` | `RST &28`: the calculator -- `EX (SP),IX` then a literal stream follows the RST, not instructions |
| `&005C` | `OUT (LMPR),A : JP (HL)` -- the paging-and-jump stub, unlabelled in the source, identical in every ROM from 1.0 |
| `&0066` | NMI |
| `&0100`-`&018F` | the jump table; mostly unlabelled, name each entry after where it leads |
| `&3F00`-`&3FFF` | top-of-ROM vectors |

A well-behaved extension calls the ROM only at restarts, the low
routines, the jump table and the top vectors.  Anything else it finds
by **signature search**: three opcode bytes, a start address, a signed
step, result stored into the operand that will use it.

**ROM versions.**  Images `ROM10`-`ROM30` (1.0 to 3.0) plus two
pre-production dumps `ROM01`, `ROM04`.  Code that resolves entries by
signature runs on all of them; the fifteen or so searches a booted
machine resolves identify the ROM it is running.  ROM 3.0 is the one to
assume absent evidence.

## The system page (page 0)

The ROM variables sit at `&5A00`-`&5CFF` in section B when page 0 is
there.  `VAR2 = &5A00`.  Absolute addresses of the ones an extension
touches:

| var | addr | |
|---|---|---|
| `PROG` | `&5AA0` | start of the BASIC program |
| `PRTOKV` | `&5ADE` | vector: expand and print token in A |
| `NMIV` | `&5AE0` | vector called by the ROM's NMI handler; holds `NMISTOP` (`&1C9E` in 3.0) unless something takes it |
| `FRAMIV` | `&5AE2` | vector: frame interrupt |
| `EDITV` | `&5AEC` | vector: line editor |
| `RST8V` | `&5AEE` | vector: error handling; alternates already selected, `CHAD`/`CHADP` copied to `XPTR`/`XPTRP` |
| `RST28V` | `&5AF0` | vector: calculator |
| `CMDV` | `&5AF4` | vector: command dispatch; A = the code about to be syntax-checked or executed |
| `EVALUV` | `&5AF6` | vector: function evaluation; A = current character |
| `MTOKV` | `&5AFA` | vector: spelled-out keyword lookup |
| `INSLV` | `&5BBA` | vector: string move -- `STRMOV1` does `LD HL,(INSLV) : INC H : DEC H : JP NZ,HLJUMP` |
| `DOSFLG` | `&5BC2` | zero if no DOS loaded |
| `PATOUT` | `&5BD2` | vector: printable-character output |
| `PAGER` | `&5BE0` | 14 bytes "reserved for paging S.R." |
| `STREAMS` | `&5C0C`-`&5C35` | streams -5 to 15, two bytes each; stream 0 is at `&5C16` |
| `FLAGS` | `&5C3B` | |
| `CHANS` | `&5C4F` | channel area; `CURCHL` `&5C51` |
| `HUDG` | `&5C7D` | |

The manual's rule for taking a vector: the routine "must be in the
system page to guarantee it is resident when the vector is called";
"making just RET will cause the normal ROM routine to be executed";
to take over completely, "POP the return address so that the ROM
routine is never used".  Resident stubs in the system page, real code
paged in behind them.

Elsewhere in page 0:

| | addr | |
|---|---|---|
| `BSTACK` | `&4AFF` | BASIC stack top; `BSTKEND`/`BASSTK` move it |
| `CDBUFF` | `&4D00` | the ROM's code buffer, "for e.g. MULTI-LDI, max len &181"; the ROM copies its tokeniser to `CDBUFF+&80`.  Shared, so contents depend on what ran last |
| `ALLOCT` | `&5100`-`&5120` | one byte per page plus `&FF` terminator: `00` unused, `40` BASIC, `C0` screen, `60` DOS, `FF` absent |
| `NMISTK` | `&5188` | the ROM's NMI stack |
| `DKBU` | `&5800` | DEF KEY buffer, 128 bytes; `&5880`-`&58DF` is 96 bytes unused |
| `KTAB` | `&58E0` | keyboard table |

## The DOS interface

A DOS lives in its own page and publishes a jump table at its `&4200`:
`&4200 JP HOOK`, `&4203 JP SYNTAX`, `&4206 JP NMI`.  ROM 3.0 calls it
at `&4200`, `&4203` and `&8009` (`BOOT`, at `&4009` through section C)
and nowhere else.  `DOSFLG` non-zero says one is loaded.

Hooks are `RST &08` followed by a code byte; the DOS's table maps codes
128 upward to handlers, with bit 15 of an entry meaning the handler is
in another page.  MasterDOS/SAMDOS document theirs in a hook-interface
list; an extension adds its own above the DOS's range and can also
repurpose DOS codes the DOS source does not name.  `DVAR n` reads the
DOS's variable block.

## NMI

The ROM's handler pushes AF and HL **on the interrupted program's
stack** ("may corrupt 4 bytes if e.g. SP being used to CLS"), saves LMPR
and SP, sets LMPR to `&1F`, moves SP to `NMISTK`, and calls `NMIV`.  In
every dump seen -- pre-boot included -- `NMIV` holds the ROM's own
`NMISTOP`; the DOS's `&4206` entry is reached some other way.  The
manual says the snapshot button works "when the Disk Operating System
Spectrum Emulator is loaded"; the emulator lives in page 3 (page 4 is
the Spectrum's RAM), so anything on that path is outside the ROM and
outside a DOS image.

## Reference sources

All five live in git.  Set them up under `ref/` as submodules so that
every claim can be traced to a URL and a commit:

```
git submodule add https://github.com/simonowen/samrom                        ref/samrom
git submodule add https://github.com/stefandrissen/samdos.git                ref/samdos
git submodule add https://github.com/dandoore/masterdos                      ref/masterdos
git submodule add https://github.com/sam-users/sam-coupe-datasheets.git      ref/sam-coupe-datasheets
git submodule add -b fix-sysvar-addresses \
    https://github.com/spectecjr/sam-coupe-technical-manual.git             ref/sam-coupe-technical-manual
```

**The manual needs the branch.**  Upstream is
`stefandrissen/sam-coupe-technical-manual`, and its `main` has four
system-variable addresses wrong.  The fix -- one commit, "Fix four
addresses in the system variable tables" -- is on the fork's
`fix-sysvar-addresses` branch and had not been merged at the time of
writing.  A plain `submodule add` of upstream silently gets the wrong
addresses.  Check `git -C ref/sam-coupe-technical-manual log --oneline
-1` shows that commit.

What each holds, and the commits the facts above were read at:

| submodule | at | what it is for |
|---|---|---|
| `samrom` | `c3eab12` | the ROM source.  `vars.asm` for the variable block, `main.asm` for the low entries and `&005C`, `fpcmain.asm` for the calculator opcode table, `text.asm` for the token table, `grabput.asm`, `misc31.asm` for the NMI handler |
| `sam-coupe-technical-manual` | `4004be3` (fork branch) | `techmanual.md`: port bits, the vector roles and calling conventions, the rotating-window idiom, the `ALLOCT` table, the snapshot-button note |
| `masterdos` | `e9df97f` | `src/masterdos23.asm`, the DOS author's own text; `res/MDOS23.bin` (15750 bytes), stock 2.3, for telling inherited from introduced; `docs/hook-interface.md`, `docs/errors.md`, `docs/disk-format.md`.  An `annotated-src/` beside `src/` is a later AI annotation, not his -- quote `src/` |
| `samdos` | `d0f9978` | SAMDOS source, the DOS MasterDOS descends from; where a routine is the same in both, a fault can be shown inherited |
| `sam-coupe-datasheets` | `7f3d14a` | PDFs: the Technical Manual v3.0, the Z80 user manual and *The Undocumented Z80 Documented*, the WD1772 disc controller (with corrections), the SCC2691 comms chip, the SAA1099 sound chip, four RTC chips, the bus extension |

`git submodule update --init` after cloning a project that uses these;
the commits above are what the addresses in this skill were checked
against, and a later revision may move them.

## Idioms specific to this machine

`CMR` / `NRRD` / `NRWR` families: call the ROM or read a system
variable from a page where it is not visible, by paging 0 into B or
reaching it through C.  `LD BC,&5FFA : OUT (C),B` = page 0 into B with
both ROMs on.  Signature searches for ROM entries.  Blocks assembled at
one address and copied into page 0 to run at another -- everything the
ROM calls through a vector has to be resident, so an extension installs
stubs and pages itself in behind them.
