# How MasterBASIC works

This describes the program, not the disassembly. For how the listings are
produced see [disassembly.md](disassembly.md); for what to read first see
the [README](../README.md).

Claims are marked where the evidence is unusual. **Confirmed on hardware**
means checked against a dump of a machine that had booted
(`file/MBPOST.bin`, `file/SYSPAGE.bin`). **Open** means unsettled, and the
listing says so too.

---

## 1. One file, two pages, three address spaces

`file/MasterBasicMasterDos.bin` is 32640 bytes: a nine-byte header and two
halves of 16320. Both halves are assembled to run at `&4000`-`&7FBF`, and
each expects to see the other at `&8000`-`&BFBF`.

| | |
|---|---|
| first half | MasterDOS 2.3, with MasterBASIC patches spliced in |
| second half | MasterBASIC 1.7 |

At run time three pages are in play, and nearly every difficulty in reading
this code comes from losing track of which one is at `&4000`:

- **the system page** (page 0), holding the ROM variables — `CHANS` at
  `&5C4F`, `FLAGS` at `&5C3B`, `PROG` at `&5AA0`. This is at `&4000` most
  of the time.
- **the DOS page**, swapped in while the DOS runs.
- **the MasterBASIC page**, swapped in while the extension runs.

So `&5BE0` is the ROM routine `PAGER` in one context and MasterBASIC code
in another, and the only way to tell is to trace `LMPR` and `HMPR` back
from the instruction. Setting `HMPR` to zero puts the system page at
`&8000`, which is why `CHANS+&4000` appears as `&9C4F`.

## 2. Boot, in order

`BOOT` begins at `&4009`. The header at `&4000`-`&4008` is part of the
loaded image, not something stripped off.

**Find the ROM.** `RESOLVE_ROM_ENTRIES` at `&7990` runs twenty searches for
ROM entry points and patches each answer into the code that calls it.
MasterBASIC holds almost no hard-coded ROM addresses — see section 4.

**Patch, then copy.** The blocks about to be installed are patched in place
first, so the copies carry the resolved addresses with them. *Confirmed on
hardware:* the source at `&7460` differs from the file in six bytes and the
source at `&7BA4` in twenty, and the installed copies at `&46CC` and
`&484D` differ in the same six and twenty, at the same offsets.

**Install into the system page.** `INSTALL_ROM_PATCHES` at `&7B03` sets
`HMPR` to zero — so every `&8xxx` in it means the system page `&4xxx` — and
copies:

| from | to | bytes |
|---|---|---|
| `&7460` | `&46CC` | 385 |
| `&7BA4` | `&484D` | 671 |
| `&7B80` | `&4BA0` | 36 |

It also patches two instructions in the second block with MasterBASIC own
page number, so they can page the extension back in when needed. *Confirmed
on hardware:* those bytes hold `&1C` in the dump, at `L7CF5+1` and
`L7D46+1` exactly.

**Point the ROM at it.** `INSTALL_ROM_VECTORS` at `&76DA` writes the
installed addresses into the ROM vector variables:

| vector | to | vector | to |
|---|---|---|---|
| `INSLV` | `&46CC` | `PATOUT` | `&49A9` |
| `EDITV` | `&4866` | `RST8V` | `&4AB8` |
| `CMDV` | `&488E` | `PRTOKV` | `&4BB0` |
| `FRAMIV` | `&4986` | `EVALUV` | `&4BBA` |

It also moves the BASIC stack down to `&45A1`, because the ROM `BSTACK` at
`&4AFF` sits inside the second installed block and had to move.

## 3. How the ROM ends up calling MasterBASIC

**The vectors above.** The ROM calls these in its ordinary course, so
MasterBASIC takes over editing, command dispatch, token printing and
expression evaluation without the ROM knowing anything changed. This code
runs in the system page with MasterBASIC paged *out*, which is why it is
written for `&46CC` and `&484D` rather than where it is stored.
`postinstall/syspage.asm` shows it at its real addresses.

**`CTAB` and `SYNTAX`.** When the ROM meets a command it does not
understand it reports an error, and the DOS intercepts. `SYNTAX` takes the
byte at the start of the statement and walks `CTAB` at `&42EA` — a count,
then ascending token/address triples, ending with a zero that never matches
so the search falls through to "command not found".

The first entry is not a token. It is `&2F`, the character `/`, which is
MasterBASIC SPLIT: a slash as the first non-space character after a colon
cuts the line in two. It sorts first because the table ascends and a
character is below every token.

**`FNVEC`** at `&78EB` does the same for functions.

**Hooks.** `RST &08` followed by a code byte. `SAMHK` at `&44A6` maps codes
128-185 to routines; an address with bit 15 set belongs to the other page
and is reached through `CALLMB`. This is the fine-grained mechanism — a
hook planted at one point inside one ROM routine.

## 4. How MasterBASIC calls the ROM

**By signature, not by address.** `FIND_ROM_CODE`, kept at `&775A` and
copied into the DOS page at boot where it is called at `&BD79`, takes six
inline bytes after the call:

```
byte 0      first byte of a three-byte instruction signature
bytes 1,2   the two after it
bytes 3,4   where to start looking, high byte first
byte 5      a signed offset from what is found to what is wanted
```

It scans with a three-byte sliding window and returns a pointer, which the
caller always stores with an `LD (nn),HL` immediately after. 27 sites do
this. The signatures are ordinary instructions — `LD A,(BC) : CP " "`,
`LD A,D : CPIR`, `LD HL,&5140` — and the start address says which ROM to
search: below `&4000` is ROM 0, `&C000` and up is ROM 1.

*Confirmed on hardware:* running these searches against the ROM this
project assembles gives, for the fifteen whose result is stored plainly,
exactly the values the dumped machine holds. Seventeen of the 27 land on a
named entry point — `INSERTLN`, `PRMAIN`, `LOOKVARS`, `MATCHER`, `POKE2`,
`EDPRT`, `ENDOUTP`, `DOCOMP`, `COMDF`, `COMLEN`, `LKCALL`, `LKFC`, `EPSUB`,
`CCRESTOP`, `POSTFF`, `EDKY1`, `AULLP` — which reads as a summary of what
MasterBASIC takes over. The other ten land inside a routine, which is what
intercepting one looks like.

This is why MasterBASIC survives a ROM it was not built against.

**Through fixed entry points.** `CMR` followed by `DEFW <ROM address>`.
One of these, at `L45F3`, has no fixed target at all: its `DEFW` is written
by a signature search, so the call goes wherever the search found.

**The `NR` family.** `NRRD`, `NRRDD`, `NRWR`, `NRWRD` and `NRWRHL`, each
followed by `DEFW <ROM variable>`, read and write ROM variables from a page
where they are not visible.

## 5. Code written at run time

Three mechanisms, each meaning the file does not hold what executes.

**The ROM code buffer.** `CDBUFF` at `&4D00` in the system page is described
by the ROM variable table as a buffer "for e.g. MULTI-LDI, max len &181".
`L735D` assembles a routine into it at `+&11` from 66 bytes of ROM and 219
of MasterBASIC, then patches two; hook 185 builds a different routine at
`+&50`. The relocated block calls `&4D11` — whatever was last built there.

**Patch sites.** The two-byte holes filled by signature searches, and single
bytes holding page numbers. These read as `&0000` in the listing, which is
what was assembled, not what runs.

**Self-modifying operands.** Written as `LABEL+1` where the target could be
identified, so `LD (&45AF),A` reads as `LD (CHECK_WRITE_STATUS+1),A`.

## 6. Where to find things

| what | where |
|---|---|
| boot and installation | `INSTALL_ROM_PATCHES` `&7B03`, `INSTALL_ROM_VECTORS` `&76DA`, `RESOLVE_ROM_ENTRIES` `&7990` |
| the code the ROM calls | `postinstall/syspage.asm`; sources at `&7460`, `&7BA4` |
| command dispatch | `CTAB` `&42EA`, `SYNTAX`, `CMD_*` |
| functions | `FNVEC` `&78EB`, `FN_*` |
| hooks | `SAMHK` `&44A6`, `HK_*` |
| ROM lookup | `FIND_ROM_CODE`, the 27 `signature` lines |
| parser front end | `&43A1`-`&44E2`, `EXPECT_*`, `TEST_RUNNING` |
| line editing | `CMD_SPLIT_LINE`, `OPEN_GAP_AT_LINE`, `FIND_LINE_*` |
| disc | `notes/disk.txt`, `notes/diskcmd.txt`, the DOS half |
| serial | `SERINIT`, `SERCMD`, `SPORT` |
| the calculator | `FPCALC`, `FPC_*` |

## 7. What is not settled

- **How `PATCH_45A2` at `&7800` reaches the system page.** The dump settles
  *that* it does: ten fragments below `&46CC` trace back to `&7879`-`&799B`
  in this half, two of them ten bytes at `&45A2` and `&45B9`, which are
  exactly this routine's first and last LDIRs. This half's own
  `&45A2`-`&46CB` is unchanged but for three ROM patch sites. What does not
  work is the route: those LDIRs only reach the system page if it is at
  `&4000`, yet the code arrives via `JP L7841`, an absolute jump that needs
  *this* half at `&4000`, and nothing between touches `LMPR`. No reference
  to the sources through the window exists anywhere either. The likeliest
  answer is that this code is itself moved before it runs, as the blocks at
  `&7460` and `&7BA4` are — but nothing found so far moves it, and the boot
  sector is not part of this file.
- **The dispatcher at `&7C51`** switches on values that are command tokens
  at the low end and something else past `&B9`.
- **499 bytes of the DOS page** differ after boot and are largely
  unexamined; `&4131`-`&417C` alone is 75 bytes of structure.
