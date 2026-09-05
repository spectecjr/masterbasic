# Disassembling MD+MBAS17

`file/MasterBasicMasterDos.bin` is the file `MD+MBAS17` from
[dsks/MasterDOS2_3_MasterBasic1_7.mgt](../dsks/MasterDOS2_3_MasterBasic1_7.mgt),
the only file on that disk. It is MasterDOS 2.3 and MasterBASIC 1.7 built into
one bootable DOS image.

The disassembly is two halves, written out three ways by `tools/build.sh`:

| | |
|---|---|
| [clean/masterdos.asm](../clean/masterdos.asm) | file bytes 0–16319, the reading copy |
| [clean/masterbasic.asm](../clean/masterbasic.asm) | file bytes 16320–32639, the reading copy |
| [disasm/masterdos.asm](../disasm/masterdos.asm) | the same, with the working notes left in |
| [disasm/masterbasic.asm](../disasm/masterbasic.asm) | the same, with the working notes left in |

`clean/` is where to start reading. `disasm/` is the same code carrying the
argument as well as the conclusion -- where a name came from, what an earlier
reading got wrong, what is still open -- and this document quotes `disasm/`
because that is the copy whose claims can be traced.

**Assembling either with pyz80 reproduces its half of the file byte for byte**,
which is what makes the listings trustworthy: a misreading shows up as a
mismatch rather than as quietly wrong text.

## The file

32640 bytes — exactly 64 sectors of 510 payload bytes, the MGT sector size once
the two link bytes are taken off. The first nine bytes are the DOS's own header
(see [ref/masterdos/docs/file-formats.md](../ref/masterdos/docs/file-formats.md)):

| Byte | Value | Meaning |
|---|---|---|
| 0 | `&13` | type 19, SAM `CODE` |
| 1–2 | `&3F77` | length within the last page |
| 3–4 | `&8000` | start address |
| 5–6 | `&FFFF` | never written, always `&FFFF` |
| 7 | `&01` | one whole 16K page |
| 8 | `&63` | start page 99 — see below |

so 1 × 16384 + 16247 = 32631 bytes of data after the header. The header itself is
part of the image the boot sector loads, not something to skip.

## Two pages, both at &4000

### What the start page really is

It reads 99 here, and 97 and 125 in the bootable files on
`dsks/MasterBasic1.7.dsk`, none of which is a page a 512K SAM has — it runs 0
to 31. That is worth setting out properly, because it is easy to build a wrong
theory on and this project built two.

The page byte is not a hardware page and not a flag word: it is the address
divided by 16384. The ROM's `SAVE "name" CODE` path builds those three bytes
at `HDR+HDN`, which `vars.asm` gives as offset 31:

```asm
      LD DE,HDR+HDN         ; the header numbers
      CALL EXPT1NUM         ; evaluate the address
      CALL UNSTLEN          ; "GET NUMBER IN AHL IN PAGE/ADDR FORM"
      LD (HL),A             ; the page byte
      INC HL / LD (HL),E
      INC HL / SET 7,D      ; the high byte forced into the &8000 window
      LD (HL),D
```

`UNSTLEN` is described in this project's own equate list as "split the
calculator stack top into a page count and an offset", so `A` is simply
`address DIV 16384` — and `SET 7,D` is why the stored address always looks
like `&8xxx` or `&Bxxx`.

Reading the four files that way gives long addresses of about 1.6 to 2 MB:

| file | page | start | long address |
|---|---|---|---|
| `MBMC` | 97 | `&8009` | 1589257 |
| `MBASC` | 97 | `&BFC0` | 1605568 |
| `MD+MBAS17` | 99 | `&8000` | 1622016 |
| `samdos2` | 125 | `&8009` | 2048009 |

and one of those checks the reading rather than assuming it: **`MBMC` ends at
1605568 and `MBASC` begins at 1605568**, exactly contiguous, which is what
two halves saved from one 32K run should look like.

All four are past 512K, so they were saved from external memory on the
machine that built them — 8-bit paging, where the user's own numbering puts
97, 99 and 125 in Module 1. None of it is consulted here: `PAGE1` is written
once, at `&63A7`, and the only access to `&4151` in either half is that one
`LD (PAGE1),A`. A file loads by following its sector chain.

The boot sector works the layout out for itself:

1. The ROM reads the first 512-byte sector to `&8000` and calls it.
2. It clears the SAM page-allocation table entries at `&5101`–`&511F` that hold
   `&D0`–`&D7`, then scans down from the current HMPR page for a free one.
3. It loads 32 sectors into the page it was given, then points LMPR at the free
   page and loads the remaining 32 sectors there.
4. It copies 943 bytes out of the second page into the first, at `&BC00` as
   the boot sector has the pages mapped, and jumps to it.

So the file is two 16320-byte halves that end up in two different RAM pages.
**Both are assembled to run at `&4000`–`&7FBF`**, and each is written to see the
other at `&8000`–`&BFBF`. Which is which depends on the paging at the time: with
the DOS in at `&4000` the extension is at `&8000`, and when the extension takes
over the two swap.

That is why the DOS's message pointer at `&4210` holds `&9200` while the
extension calls `&BD79` — each is reaching into the other page. The two halves
are therefore two address spaces, not one, and get a file each; a reference to
`&8000`–`&BFBF` is resolved against the other half and written with its label
under a `DOS_` or `MB_` prefix:

```
               CALL DOS_FIND_ROM_CODE          ; 75FE CD 79 BD
```

The boot sector is the exception at both ends: it runs before either page is in
place, with its own half visible at `&8000`, so between `&4000` and `&41FF` an
address of `&8000` and up means *this* page `&4000` higher, and is written as
`LABEL+&4000`. The block at `&75E1` needs no such caveat — it runs under
exactly the paging these listings assume, which is why its addresses read
normally.

That block is more than an installer. It is copied to `&7C00` in the DOS page
and MasterBASIC goes on calling into the copy for the rest of the session:
`&7D79` from twenty-seven separate sites, and four further addresses once each.
The bytes the file itself holds at `&7C00` are not that code — they are whatever
was in the DOS's buffers when the image was saved, and the copy overwrites them
at boot — so the five entry points are named `MBCOPY_xxxx` after the address in
the extension page they were copied from, which is where the code that actually
runs there can be read.

The three entry points the ROM knows about are where MasterDOS always puts them,
at page offset `&0200`:

```
4200  JP HOOK     ; the RST &08 hook handler
4203  JP SYNTAX   ; unrecognised command
4206  JP NMI      ; the snapshot button
```

## How the listings are built

`tools/build.sh` runs five steps.

**1. Build the references.** The
[annotated MasterDOS source](../ref/masterdos/annotated-src/masterdos23.asm) is
assembled with pyz80 for its symbol map and listing, and checked against
`ref/masterdos/res/MDOS23.bin`. The SAM ROM is assembled too, for its symbol
table and its BASIC token tables.

**2. Carry the DOS's label names across** (`tools/xfer.py`). The combined build
is the same source with material inserted, so routines have moved and every
absolute operand differs — matching raw bytes finds almost nothing. Instead each
MasterDOS label becomes a byte pattern with the operand bytes of in-image
references wildcarded, and that pattern is searched for in the first half. A name
is carried only where the pattern matches in exactly one place, and matches that
break the overall ordering are dropped. That places **861 of MasterDOS's own
labels** — `HOOK`, `SETSTK`, `NRRDD`, `PTM`, `ERRTBL`, `DVAR` and the rest — onto
the right addresses here.

**3. Trace and disassemble** (`tools/z80.py`, `tools/disasm.py`, `tools/dis_mb.py`).
A recursive trace of both pages at once, from the boot sector, the three entry
points and the installer, with each page seeding the other across the page
boundary. Then:

- *Inline parameters.* `CALL NRRDD` / `DEFW addr`, `CALL CMR` / `DEFW addr` and
  `RST &08` / `DEFB code` all put data immediately after the call. The tracer
  recognises these routines by their opening instructions — `EX (SP),HL`, or
  `POP HL` followed by the read-a-word-and-push-it-back idiom — so it steps over
  the parameter instead of decoding it as an instruction. MasterBASIC has copies
  of the `CMR` idiom of its own.
- *Pointer tables.* The hook table and the command tables are reached only
  through an indexed jump, so runs of in-page pointers in unclaimed space are
  followed.
- *Gap sweeps.* Routines nothing points at are recovered by disassembling the
  holes between traced regions, preferring the alignment whose decode ends
  exactly where the next known instruction begins.
- *Conflict repair.* Where two paths disagree about instruction alignment, one of
  them started mid-instruction. The bytes are handed back to the path that
  arrived from a call or jump target and re-decoded. A jump that lands inside an
  instruction counts as the same evidence: that is `LD HL,nn` being used to skip
  two bytes, which is how MasterBASIC chains its error entry points together, and
  a linear decode hides every entry but the first.

**4. Carry the DOS's commentary across** (`tools/carrydoc.py`). The label
names are only half of what the annotated source knows. Its routine headers and
line comments describe code that is mostly still here, so they are carried too —
but only where it can be shown that they still apply. The carried labels give a
coarse map, one anchor every eighteen bytes or so; between two anchors the two
instruction sequences are matched against each other, first by walking them in
lockstep and then by diffing them, so a routine that agrees at both ends but not
in the middle still contributes both ends. An instruction matches only up to its
operands, since an absolute address here is nearly always different and a
relative jump's displacement changes whenever anything was inserted between.

That places **1703 line comments, 164 routine headers and 10 section banners**.

It also puts the source's **names where the listing printed bare hex**. The
disassembly can only name an address that something in the image refers to, so a
constant comes out as a number and a self-modified byte as an address:

```
LD C,&80        LD A,(&4110)        LD (&48DC),A
LD C,DRSEC      LD A,(DSC)          LD (LDB6+1),A
```

A name is used only where it evaluates to the number already there, which is the
whole safety argument: the bytes cannot change, and a symbol whose value moved
with the splice simply fails the test. That names the operands of **448
instructions**. Of the names it needs, 65 turn out to be addresses in this page,
and become labels — so the DOS variables the byte-pattern match could not place
read as `DSC` and `DCT` rather than `V4110` and `V4111`. The 30 left over are
genuine constants, controller commands and directory field offsets among them,
and are written as equates at the top of the file.
Where the two streams diverge, nothing is carried: eight routines — `MRTAB`,
`GETSCR`, `FDHF`, `GTVAL`, `AUTNAM`, `MCHWR`, `INPST` and `CMR` — keep too few
of stock MasterDOS's instructions to be described by it, and each is headed by a
note saying so and by how much. The source also says which addresses it reserves
rather than assembles, which is how the DOS's variable block at `&40F9` stopped
being read as a page of `NOP`s.

**5. Prove it.** Each listing is assembled and compared with its half of the
original file.

## Documented routines

The MasterBASIC manual is transcribed at
[masterbasic-manual.md](masterbasic-manual.md), with the corrections from
`original/ERRATA.md` applied in place. Every routine one of the dispatch tables
names now carries that manual's description of what the keyword does, so
`CMD_SORT` in the listing is headed by `SORT`'s syntax and behaviour. The
`XVAR` block at the start of the MasterBASIC page is named and annotated
straight from the manual's XVAR section.

A first pass at the routines behind MasterBASIC's new keywords is written up in
[masterbasic-tokens.md](masterbasic-tokens.md), and the same commentary appears
above each routine in the listings: the four ROM vectors the scheme rests on,
the keyword matcher `HGTTK` and the arithmetic that turns a match into a token,
the `GTDT` stub that gets an `&FF` prefix past the ROM's tokeniser, the command
table `CTAB` and the hook table `SAMHK` with their cross-page flag, and the
paging helpers both halves use to reach the ROM and each other.

The 28 keywords themselves — what each does and how it is written — are in
[masterbasic-keywords.md](masterbasic-keywords.md).

## The extension page, which has no source to carry from

Everything above rests on a reference that assembles to the same bytes.
MasterBASIC 1.7 has none, and it is not MasterDOS code in disguise — running the
same matcher over the second half finds 63 labels and drops 78 as out of order,
which is coincidence, not shared code.

What it does have is a dozen routines of the form `CALL CMR / DEFW <rom> / RET`,
which page the ROM in, call one address and come back. Those are not inference
at all: `L4461` **is** the ROM's `NEXTCHAR`, and is now called `CALL_NEXTCHAR`.
Thirteen of them are named this way, and they are among the busiest labels in the
file.

Naming those makes a second thing possible. A `CP` that follows a call to one of
the character fetchers is comparing a *token*, so the ROM's own keyword table
names it; a `CP` that does not is comparing something else. That distinction
matters, because `ADD A,&10 / CP &FE` looks like a test for a token until you
notice A came from stepping a screen address, and `LD A,H / CP &FF` is a range
check on a pointer. Both are rejected, because nothing fetched a character first.
The walk backwards stops at anything that writes to A, and passes *through*
conditional jumps — which is what a run of `CP` tests against different tokens
looks like:

```
               CP CH_COMMA                     ; 4B69 FE 2C
               JR Z,PARSE_OPTIONAL_RANGE_1     ; 4B6B 28 10
               CP T_TO                         ; 4B6D FE 8E
```

Two more rules read `AND &1F` near a paging port as the page-number mask, and
`AND &DF` on a byte just loaded from memory as the fold to upper case.

That names **83 immediates**, and the 21 equates it needs are written into the
file under a heading saying plainly that they are read from the code rather than
carried from a source, each with the reason, so the reading can be judged. Every
other immediate in the page — the bit masks and counts with nothing to anchor
them — is left as hex on purpose.

## Calling the other page

The busiest routine in the extension is at `&42C1`, and forty-five sites call it:

```
               CALL CALLDOS
               DEFW <address>
```

It picks up the word after the call, saves LMPR, writes the page number the boot
sector patched into its `LD H,&00`, and calls through — so the address is read
*after* the paging has changed. That makes its parameter unlike every other
inline `DEFW` in the file: `&4000` and up is the other page, not the ROM
variables that share those addresses, and only below `&4000` is it really ROM,
which the switch leaves in place. Those parameters are now written as the other
page's own label less `&4000`, the mirror of the `+&4000` used for the bit-15
pointers in the dispatch tables:

```
               CALL CALLDOS                    ; 4A41 CD C1 42
               DEFW DOS_POINT-&4000            ; 4A44 AC 4F
```

Following them also gives the tracer three DOS entry points it had no other way
to reach.

Finding this fixed a misplacement. Both halves carry this code, but the DOS's
entry is `&42BD`, where `LD IY,(&7FFC)` restores the ROM's IY before falling into
the shared body; the extension has five zero bytes there and starts at `&42C1`.
The name and the description had been hardcoded to `&42BD` in both, so in the
extension they sat on the padding while every real call site went to an unnamed
label.

## Routines the two halves share

Eight routines appear in both pages — `NRRDD`, `NRRD`, `NRWRD`, `NRWR` and the
byte and word primitives under them, which reach the ROM's system variables.
The global alignment cannot find them, because the extension is not MasterDOS and
matching it wholesale yields more out-of-order matches than good ones. Anchoring
on the name settles it: where a label here has a MasterDOS routine's name *and*
the two bodies agree instruction for instruction down to the first return, it is
that routine. Each now says so, and points at the DOS listing where the same code
carries its cross-references.

## The calculator's literal lists

`RST FPCALC` is followed by a list of one-byte operations, not by instructions —
the ROM's entry at `&0028` does `EX (SP),IX` so that IX points at the byte after
the restart, and walks it from there. Decoding those bytes as Z80 is how `&25 &27`
came out as `DEC H` / `DAA`. All eight lists are now read properly, and their
numbers translated:

```
               RST FPCALC                      ; 44AE EF
               DEFB FPC_DUP                   ; 44AF DUP
               DEFB FPC_FIVELIT,&91,&00,&00,&00,&00 ; 44B0 FIVELIT = 65536
               DEFB FPC_STO5                  ; 44B6 STO5 -- store to memory 5
               DEFB FPC_MOD                   ; 44B7 MOD
```

The names are parsed out of `ref/samrom/fpcmain.asm`, whose table is a run of
`DW FPMULT ;00 MULT`. The counts of bytes each literal consumes are not in any
table and had to come from the routines — `FP5LIT` does `LD B,5`, `FPSOMELIT`
reads a count byte first, `LKADDRSR` reads a word. So do the two terminators, and
they differ in a way that matters: `&33 EXIT` returns to just past the list, so
execution resumes there, while `&34 EXIT2` drops the calculator's caller as well
and nothing follows it. The four ranges the table does not cover — the constants
at `&E0`, and recall, store and store-with-delete below them — are named from the
arithmetic `FPCMAIN` uses to reach them.

Each list is summarised in one line above the `RST` that starts it, by walking it
with expressions on the stack instead of numbers and folding the arithmetic:

```
               ; calculator: leaves x MOD 65536, x DIV 65536 (last on top)
               ; calculator: = x when x >= 0, otherwise x + 65536
               ; calculator: = DPEEK DOS_TEMPW1
```

The first splits a value into its low and high sixteen bits; the second reads a
signed value as unsigned. `x` is whatever was already on the calculator stack.

Six lists summarise. The other two do not, and that is the point of trying: a
code the ROM does not name, or a constant index past the end of FPCTAB, means the
`RST` that led there is a byte being decoded as an instruction rather than a real
call. Both of those turned out to be exactly that — one is `DVAR 150`, the DOS's
clock-port byte — and they are no longer presented as calculator lists at all.

Two checks fall out of the decode for free. A `JPTRUE` displacement resolves to
the address of the `EXIT` that ends its own list, and an `LKADDRW` address is the
same one the instruction above it had just written to.

## Names instead of numbers

Every name in the listings is read out of one of the two source trees in `ref/`;
none is invented. `tools/romsyms.py` collects them.

| | |
|---|---|
| **Hardware ports** | The symbols the two trees write into an `IN` or `OUT`, or load into `C` for the `OUT (C)` form. So `LRPORT` and `URPORT` rather than anything made up. A name written straight into an `IN`/`OUT` beats one merely loaded into `C`, which is how `&80` comes out as the MegaRAM port `MRPRT` and not the controller's read-sector command `DRSEC`. |
| **ROM routines and variables** | Mostly from MasterDOS's own inline parameters: `CALL NRRDD / DEFW CHADD` names a system variable and `CALL CMR / DEFW BEEPR` a routine, so its listing gives an authoritative value-to-name map under the names its author used. The SAM ROM's map file fills in the rest for code addresses, and its export file for the `&4000`–`&5FFF` variable area. The ROM's jump table at `&0100` is mostly unlabelled, so each entry is named after the routine it leads to (`J_GRCOMP`, `J_IMSCSR`). |
| **`RST &08` codes** | A DOS error name from [errors.md](../ref/masterdos/docs/errors.md), or a hook code — 128 plus an index into the image's own hook table at `&44A6`, so the code is named after the routine it dispatches to (`HK_HOFLE`, `HK_MCHRD`). |
| **The other page** | Its own label with a `DOS_`/`MB_` prefix. |
| **Error numbers** | From the ROM's own `ERRMVAL` table, expanded through the substring dictionary it is compressed against, and from [errors.md](../ref/masterdos/docs/errors.md) for the DOS's own. `RST &08 / DEFB ERR_LOADING_ERROR` rather than `DEFB &13`. |
| **The dispatch tables** | Whatever a table points at is named for the entry that points at it: `CMD_SORT`, `FN_INARRAY`, `HK_HCLOS`, and `HK_175` upwards for the eleven hooks MasterBASIC adds beyond the ones MasterDOS names. A name carried from MasterDOS wins where there is one, so the DOS's own `FSTAT` and `HGTHD` keep their names. This is the only source of names for the MasterBASIC page, which has no reference source of its own. |
| **Everything else** | Every address either listing refers to gets a label: `L` where it starts an instruction, `V` where it is data. |

### Addresses hidden behind an offset

Three conventions in this code write an address as something other than
itself, and the listings undo all three.

`NAME+&4000` on a **system variable** is the windowing the `NR` routines do
— `SET 7,H` then `RES 6,H`, which for `&4000`–`&7FFF` comes to adding `&4000`.
Code that does it inline rather than calling `NRRD` leaves the windowed form in
the operand, so `LD DE,(&9C65)` is `LD DE,(STKEND+&4000)`. It is also how
MasterDOS's own source writes such an address, as `NAME+FS`.

`NAME+&4000` on a **stored pointer** is bit 15 set, the flag `INDJP` and `CTAB`
use for "not in this page". The name is the other page's label.

`LABEL+&4000` in the **boot sector** is that fragment running `&4000` above
where it is assembled.

Two deliberate restraints. A 16-bit *immediate* — `LD BC,&0004` — is left as a
number unless it points into the page: outside the image it is as likely to be a
count as an address. And a *memory* operand outside the image keeps its number
too, because what lives at a given address depends on the paging at the time.
Only jump and call targets, and inline parameters, are named from the ROM.

Runs of three or more `NOP`s are written as `DEFS n` — pyz80 zero-fills, so this
round-trips, and in the DOS's variable area that is what the bytes are.

## A number is not an address just because a label has that value

The disassembler names an operand by looking its value up among the labels.
That is right most of the time and wrong in a way worth stating, because it has
now produced the same error in four separate parts of the listing.

`&4000`–`&7FBF` is the DOS's own page. It is *also* where the ROM's system page
appears whenever `LMPR` puts it in section B, which is what `SYSPAGE_IN_B`
(`&1F`) does and what `CMR` does on the way to ROM 1. So an operand anywhere in
that range is genuinely ambiguous, and the namer always resolves it one way.

Three kinds of number get caught:

| the number | what it really is | what it was named |
|---|---|---|
| `&4A62`, `&4A64` | the net-patch stubs in the system page | `SVBL2_1`, `SVBSI` |
| `&4A99`, `&4B00` | a system-page address; the ROM's `HDR` buffer | `FNS2_1`, `TSTD_DONE` |
| `&4000`, `&6EF9` | a byte count of 16384; `TABLE+8` | `HEADER`, `MCHRD` |

The last row is the awkward one: those are not addresses at all. A count, a
table base and a bit mask can each equal some label's address by arithmetic
accident, and nothing distinguishes them from a reference.

**The peer page has a mechanism and this does not.** An `&8xxx` operand that
resolves into the other half goes through `no_peer`, which exists precisely
because that resolution is often a coincidence — and the habit of suspecting it
is well established. An own-page collision has no equivalent, so it passes
silently and then reads as a cross-reference: `MCHRD` still lists a caller that
only loads `TABLE+8`.

The fix for a single instance is an `expr` note, which rewrites the operand and
is checked against the number when the listing is assembled, so it cannot drift.
What would catch them in bulk is a pass that flags any operand naming a label
whose address lies in the system page's range while the code around it has the
system page mapped. That has not been written.


## Internal labels

Every address either listing refers to gets a name. Most of them are named by
something — MasterDOS's symbol table, the dispatch tables, the hook list, a
file in `notes/` — but a few hundred are internal branch targets that nothing
names, and those used to read `L45D9`: the address, which the address column
already gives.

They now carry the routine they belong to, and a suffix where the flow says
what they are with certainty:

| suffix | when | count |
|---|---|---|
| `_LOOP` | a branch comes back to it | 276 |
| `_DONE` | it returns within a few instructions | 60 |
| `_FAIL` | it reports an error | 8 |
| `_1`, `_2`, … | none of the above is certain | 527 |

So `CHECK_BREAK_LOOP2` says more than `L6016` did, and `BOOT_17` at least says
whose it is. Nothing here is a reading of what the code means: the three
suffixes are properties of the flow graph, and where the graph says nothing
the label gets a number rather than a guess. A name in `notes/` still beats
all of it — those are applied first, and an address named there never becomes
synthetic in the first place.

Which routine a label belongs to is the label above it, except where every
reference to it comes from one routine that starts earlier: a routine can
have a named loop inside it that something else calls, and a branch landing
past that loop still belongs to the routine that made the branch.

### Why a branch is taken

The header over each label says which addresses reach it. It now also says on
what, where that can be read off the instruction in front of the branch:

```
; ---- CHECK_BREAK_LOOP3 ---- from &5FFC when A is not 0, &6027 when B is not 0 yet
```

The search steps back over instructions that leave the flags alone and stops
at any address something else can jump to, since past that the flags are not
this code's to know. `CP`, `SUB`, `AND`, `OR A`, `XOR`, `BIT`, `INC`, `DEC`,
the rotates and shifts, the block instructions and `DJNZ` are read; anything
else says nothing rather than something vague. That covers 1006 branches.


## The BASIC at the end of the extension page

`&7E6B`–`&7FBF` (`MBTEXT`) is not code but tokenised SAM BASIC: fragments of
program text MasterBASIC pastes together and runs, including the profiler's
report and its key prompts. It is written out with the keywords named:

```
;
; 11400 PRINT "   TOTAL FRAMES: ";CODE g$(frms)
               DEFB T_PRINT                   ; 7E77 PRINT
               DEFM """   TOTAL FRAMES: "";"
               DEFB FN_PFX,F_CODE             ; 7E8C CODE
               DEFM "g$(frms)"
               DEFB TK_CR                     ; 7E96 end of line
               DEFB &2C,&92                   ; 7E97 line 11410
               DEFW 111                       ; length
```

`tools/sambasic.py` reads the names out of `KEYWTAB` in the assembled SAM ROM and
follows the mapping `tprint.asm` uses to turn a token byte back into a name —
command tokens `&85`–`&FE` index four sub-lists, function tokens are `&FF`
followed by `&3B`–`&84` and index three more. The comment above each line is what
`LIST` would show, spacing included.

The format is otherwise as SAM stores a program: two bytes of line number high
first, two of length low first, the statement, then `&0D`. A number is its digits
followed by `&0E` and five bytes of value; embedded `PAPER` and friends are a
control byte and its parameter; and inside a string `&80`–`&A8` are graphics
characters rather than keywords, which the renderer tracks. Every token in the
block resolves to a ROM keyword — MasterBASIC's own additions are not tokenised
here.

## MasterBASIC's keywords

The name table at `&50D8` in the extension page (`MBKEYS`) holds the 28 commands
and functions MasterBASIC adds to SAM BASIC, each ended by bit 7 of its last
character:

`EXIT PROC`, `EXIT DO`, `EXIT FOR`, `LOCN`, `RESERVED`, `EQU`, `TICS`, `SHIFT$`,
`SVAL$`, `USING$`, `TIME$`, `DATE$`, `INP$`, `DIR$`, `FSTAT`, `DSTAT`, `FPAGES`,
`SCRAD`, `INARRAY`, `XVAR`, `NVAL`, `BACKUP`, `TIME`, `DATE`, `ALTER`, `SORT`,
`JOIN`, `EDIT`.

## What the listings cover

| | bytes |
|---|---|
| Code | 28376 (86.9%) |
| Variables and other data | 2636 |
| Inline call parameters | 893 |
| Message and keyword text | 696 |
| `RST &08` codes | 29 |
| Pointer tables | 10 |
| Unclassified | 0 |

`tools/build.sh` prints this table on every run, so it can be checked
rather than remembered.

15413 instructions and 2421 labels. **Every byte is accounted for.** What was
left at the end was not a third kind of thing: 29 bytes of zero fill, 17 of
message text, and 103 bytes that are the *other* reading of bytes an overlapping
instruction has already claimed — the skipped `&21` of an entry chain, the opcode
a caller steps over by entering a byte later. Both readings are real and only one
can be written down, so the byte left behind carries a comment saying what it
also reads as. The code figure is lower than it was once
the DOS's buffer area at `&7C00` and its two variable blocks -- the one
at `&40F9` inside the boot sector, and `DVAR` at `&4220` -- were recognised for
what they are — bytes that are never executed as they stand,
which a linear sweep had been reading as instructions, the variable block as a
long run of `NOP`s. The unclassified remainder is written out as `DEFB` and is still
byte-exact.

No labels land inside an instruction any more. The fourteen that did were not
misalignments at all: thirteen were entry points hidden behind the `&21` skip —
`LD HL,nn` swallowing the two bytes after it so a chain of `LD A,<error>` entries
can fall through into common code — and one was `LD IY,nn` with an `FD` prefix
that a caller entering a byte later reads as `LD HL,nn`. The author's own comment
on that one is `"JR+3"`. All are now shown as the entry points they are, with the
swallowed opcode as a `DEFB`.

## What the equates mean

The names at the top of each listing are the ROM's and the DOS's own, and they
are terse — `AFTERCR`, `BSTKEND`, `CHADP`. Each now carries a note:

```asm
LRPORT:        EQU  &FA    ; LMPR: the page at &0000, and the ROM switches
URPORT:        EQU  &FB    ; HMPR: the page at &8000
STATPORT:      EQU  &F9    ; read: STATUS, key rows and interrupt flags; write: line interrupt
COMM:          EQU  &E0    ; DISC PORTS
CHADD:         EQU  &5A97  ; address of the character being interpreted
PROG:          EQU  &5AA0  ; address of the BASIC program
```

The Coupé's own ports are from the *SAM Coupé Technical Manual v3.0*; the disk
and printer ports are the DOS's, and its source says what they are. Everything
else is harvested from the comments already in `ref/samrom` and the annotated
MasterDOS source — an `EQU` with a trailing comment, a label with one, the ROM's
jump table (whose entries wrap onto following comment lines), or a whole-line
comment sitting directly above a label.

Three things had to be filtered or resolved to make that usable. The ROM's author
wrote sizes as `;(2)` and MasterDOS's wrote usage counts as `;3*`, neither of
which is a description. Timings like `ARRIVE IN ABOUT 113 T` are not either. And
the sources name a pointer and its page as a pair —

```asm
PROGP:         EQU  &5A9F          ; page holding the BASIC program
PROG:          EQU  &5AA0          ; (2) address of it
```

— so `address of it` on its own says nothing, and the subject is taken from the
line above. Where two names share an address, as `CHAD` and `CHADD` do, the note
is shared with them.

That describes 146 of 147 equates in the extension listing and 50 of 51 in the
DOS. One in each is left bare — `INP2` in the extension listing, `BEEPR` in the
DOS — because they are not described anywhere I have, and inventing a gloss for
them would be worse than the silence. A table of 54 entries in
`tools/romsyms.py` fills in well-known variables the sources never bothered to
comment — `STKEND`, `RAMTOP`, `FLAGX` — and those are my words rather than the
ROM author's, which is why the heading says *mostly*.

## Adding your own labels

Everything above derives its names from something — the annotated MasterDOS
source, the ROM's tables, the manual, the shape of the code. `notes/*.txt` is the
way in for knowledge that comes from a person instead. It is plain text rather
than another Python module, so adding a name costs one line:

```text
MB &5934 SERINIT
    Set up the SCC2691 for LPRINT MODE 2.

    C is SPORT, the port the Comms Interface is jumpered to, and B
    selects one of the chip's eight registers.

MB &593F : CR = &10, reset the MR pointer

DOS &4220-&42BC data DVAR
MB &7E6B-&7FBF text
```

Nine kinds of line. A page (`MB` or `DOS`) and an address name that address, and
any indented lines below become its header, blank lines included. A `:` after the
address is a comment on that one instruction. A range with `data`, `text` or
`code` marks it as such, and may name its start as well. Addresses are written as
the listings write them, `&4000`–`&7FBF` in either page, and a range includes both
ends.

Two more work by the name of a label rather than its address, so that you never
have to look one up. `DOC` heads a routine:

```text
DOC CHECK_WRITE_STATUS
    Waits for the controller to be ready for the next byte.

    The port is patched in by the caller, so this works for whichever
    drive and side is selected.
```

and `AFTER` comments the instruction a label sits on:

```text
AFTER CHECK_WRITE_STATUS : read the controller status through the patched port
AFTER CHECK_WRITE_STATUS+1 : carry now holds bit 0 of the status, DRQ
```

`+n` steps on n instructions from the label. Both run after every other entry, so
a label named further down the same file can be referred to further up. A name
that matches nothing, or that matches an address in both pages — `NRRD` is in
both — is refused with a message rather than guessed at. `DOCUMENT` and
`ADDCOMMENTAFTER` are accepted as longer spellings.

A fifth names a number in one instruction only:

```text
DOS &4835 value DISKCTL_0_BASE
```

`&E0` is the disk command register nearly everywhere in the DOS, but in `SELD`
it is the base of drive 1's port block, so a global name would be wrong in one
place or the other. The value is read back out of the instruction rather than
given, so the equate cannot disagree with the byte, and an instruction with no
number in it — or two — is refused with a message saying so.

Two more do not take an address, because they name rather than place:

```text
EQU STKEND : end of the calculator stack
RENAME ULA BORDER
```

`EQU` describes one of the ROM names in the equate block at the top of a listing.
`RENAME` changes a name wherever it is written — the label tables, the equate
blocks, and the operand text of any instruction that carries an overridden name.
It runs after every other pass for that reason: a name can be put on the page by
one pass and written into an instruction by another, so renaming has to be last
and everywhere at once.

Files are read in filename order, so `notes/00-disk.txt` lands before
`notes/10-printer.txt` if that matters to you. Nothing else needs editing.

**Hand-written entries win**, and disagreements are reported rather than resolved
silently:

```text
notes/: trial.txt:12: PAGESAVE is already the name of &7B00
notes/: trial.txt:13: &9999 is not in the DOS page
notes/: trial.txt:14: &5934 was SERINIT, now MYSERIALINIT
```

The first is refused — two labels with one name would not assemble. The second is
refused as out of range. The third is applied, because replacing a derived name
with your own is the point; it is reported so that you can see what you
displaced. A duplicate name or a bad address will not break the build.

The notes are applied after every other naming pass and before `autolabel`, so
your name beats anything worked out and no synthetic `L1234` is invented for an
address you have named. They reach `speculate/` too.

## Regenerating

```
python -m pip install pyz80
tools/build.sh
```

Exit status is 0 only if all six listings came back byte-identical -- the two
in `clean/`, the two in `disasm/` and the two in `speculate/`.

The run also rebuilds `postinstall/syspage.asm`, which cannot be checked that
way because there is no original to compare it with, and prints the byte census
and description count that the tables above are set from.

## Tools

| File | |
|---|---|
| `tools/z80.py` | Z80 decoder: the full instruction set plus the undocumented DD/FD half-registers, `SLL`, the ED oddities and the DDCB group |
| `tools/test_z80.py` | Decodes every encoding, reassembles it with pyz80 and checks the bytes come back unchanged |
| `tools/disasm.py` | Flow tracer, label and cross-reference bookkeeping, output |
| `tools/xfer.py` | Carries MasterDOS's label names across |
| `tools/carrydoc.py` | Aligns the two instruction streams and carries the annotated source's commentary across |
| `tools/romsyms.py` | ROM routines, system variables, ports and `RST &08` codes |
| `tools/sambasic.py` | SAM BASIC token tables from the ROM, and the `MBTEXT` renderer |
| `tools/annotate.py` | Names, commentary and the dispatch-table renderers |
| `tools/infer.py` | Reads the extension page's immediates from the code around them |
| `tools/notes.py` | Reads your own labels and descriptions from `notes/*.txt` |
| `tools/features.py` | What the manual says each named routine does |
| `tools/dis_mb.py` | This image: the two pages, the calling conventions, the seeding passes |
| `tools/nrfam.py` | The `NR` family, which is how a page reaches the ROM's system variables |
| `tools/hooks.py` | The fourteen hook codes MasterBASIC adds and the DOS's source does not name |
| `tools/fpcalc.py` | The floating-point calculator's literal streams, which follow `RST FPCALC` instead of instructions |
| `tools/serial.py` | The serial driver, read against the SCC2691 datasheet |
| `tools/serial_note.py` | What the DOS's own "serial" names turn out to mean |
| `tools/syspage.py` | Builds `postinstall/syspage.asm`: the ROM's system page as MasterBASIC leaves it |
| `tools/regs.py` | What each instruction reads and writes, for deriving register contracts |
| `tools/speculate.py` | Builds `speculate/`: a reading of every routine, marked as such |
| `tools/specrender.py` | Turns that analysis into the text `speculate/` carries |
| `tools/build.sh` | Regenerate and verify |
