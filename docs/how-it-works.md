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
| `INSLV` | `&46CC` string move | `PATOUT` | `&49A9` printable output |
| `EDITV` | `&4866` line editor | `RST8V` | `&4AB8` error handling |
| `CMDV` | `&488E` command dispatch | `PRTOKV` | `&4BB0` token printing |
| `FRAMIV` | `&4986` frame interrupt | `EVALUV` | `&4BBA` function evaluation |

Those roles are read out of the ROM source — `STRMOV1`, `EDITOR`,
`STMTLP3`, `FRAMINT`, `ERROR2`, `PRGR802`, `ABOVLETS` and the `LD IX,
(PATOUT)` in the print path — because the ROM's own variable table leaves
most of them without a comment. `postinstall/syspage.asm` names the
installed code after them.

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

This is why MasterBASIC survives a ROM it was not built against, and the
rule is followed without exception. Of the 69 places in the MasterBASIC
half that call or jump into the ROM at a fixed address:

| | |
|---|---|
| `&0000`-`&003F` restarts | 14 |
| `&0040`-`&00FF` low routines | 7 |
| `&0100`-`&018F` the jump table | 27 |
| `&3F00`-`&3FFF` top-of-ROM vectors | 19 |
| ROM 1 | 2 |
| anywhere else | **0** |

`PRMAIN` shows how tight the rule is. It sits at `&01CC`, which looks like
vector territory, but the jump table ends around `&018C` and `PRMAIN` is an
ordinary routine past it — `RST &30 / DW PROM1-&8000`, a thunk into ROM 1.
It is never called directly anywhere in the image; it is reached only
through the address a signature search finds. The search for it is
`EB E9 F7` with a step of `+2`, which spans a boundary: `EX DE,HL / JP (HL)`
ending `HLJPI`, then `PRMAIN`'s first byte.

The re-entry points those searches find are mostly places to hand control
back: `&2A96` inside `STRMOV1`, `ENDOUTP` for the printable-character
path, `&389E` inside `BUFMV2`. So the searches are not looking for the
front doors of ROM routines, which are already known — they are looking
for the exact point *inside* one at which MasterBASIC wants to rejoin it.

**Through fixed entry points.** `CMR` followed by `DEFW <ROM address>`.
One of these, at `L45F3`, has no fixed target at all: its `DEFW` is written
by a signature search, so the call goes wherever the search found.

**The `NR` family.** `NRRD`, `NRRDD`, `NRWR`, `NRWRD` and `NRWRHL`, each
followed by `DEFW <ROM variable>`, read and write ROM variables from a page
where they are not visible.

## 4a. One routine that uses all of it

The string move is the clearest example of the whole arrangement working
together, and worth following once.

The ROM's `STRMOV1` begins `LD HL,(INSLV) / INC H / DEC H / JP NZ,HLJUMP`,
so setting `INSLV` diverts every string move in the machine. MasterBASIC
sets it to `&46CC` — which is why that block has to be installed in the
system page, since it is called with the extension paged out.

The block starts by deciding whether it is worth the trouble:

```asm
LD A,B : AND A : JR NZ,+        ; 256 or more, handle it here
LD A,C : CP &15 : JP C,&2A96    ; under 21 bytes, let the ROM do it
```

`&2A96` is `LD H,B`, the instruction immediately *after* the `INSLV` test.
Handing back there means the ROM finishes the move with its own code
without calling the hook again — jumping to `STRMOV1` would recurse for
ever, jumping three bytes past it does not.

And it finds that address by searching for it. The signature at `&79EB` is
`C2 05 00`, which is the `JP NZ,HLJUMP` of the vector check itself, with a
step of `+3` to clear it. MasterBASIC locates the ROM by the shape of the
very instruction it has taken over.

So one routine uses a ROM vector to get control, an install into the
system page so the ROM can reach it, a signature search to find its way
back, and a size test to decide when taking over is worth doing at all.

## 5. Code written at run time

Three mechanisms, each meaning the file does not hold what executes.

**The ROM code buffer.** `CDBUFF` at `&4D00` in the system page is described
by the ROM variable table as a buffer "for e.g. MULTI-LDI, max len &181".
`L735D` assembles a routine into it at `+&11` from 66 bytes of ROM and 219
of MasterBASIC, then patches two; hook 185 and `BUILD_PAGE_IN_TRAMPOLINE`
both build at `+&50`. The relocated block calls `&4D11` — whatever was last
built there.

The buffer is the ROM's, not MasterBASIC's, and the ROM uses it the same
way: `POSFIRST` copies the tokeniser into it with `LD DE,TOKFIN+3 ; END OF
THIS ROUTINE, IN CDBUFF` before running it. A dump of a booted machine
finds a mixture — `&4D50` holding ROM 1's `NLTP`, `&4D80` holding this
half's `&4F14`, and `&4D18` holding a byte from neither. So nothing about
the buffer's contents can be inferred from reading any one builder.

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

- **What fills `&45A2`-`&46CB` in the system page.** The dump shows that
  region holding `&7879`-`&799B` from the MasterBASIC half, filled right up
  to `&46CC` where the first stub begins, so the two form one continuous
  installed area. The routine at `&7841` has exactly that destination
  layout — 21 bytes to `&45C6`, 3 to `&45DB`, 238 to `&45DE` — but reads
  its sources from the DOS page, and those bytes are not what is there.
  So something with the same shape and different sources does the real
  filling, and `&7841` either runs and is overwritten or does not run at
  all in an ordinary boot.

- **The dispatcher at `&7C51`** switches on values that are command tokens
  at the low end and something else past `&B9`.
- **499 bytes of the DOS page** differ after boot and are largely
  unexamined; `&4131`-`&417C` alone is 75 bytes of structure.
