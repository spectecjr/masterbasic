# SAM Coupé code idioms

The same dozen tricks appear over and over in this image, in the SAM ROM, and in
MasterDOS. Most are forced by the paging hardware; a few are just the cheapest
way to do something on a Z80. None is obvious on first reading, and several look
like different things than they are.

Everything here is quoted from `disasm/`, `postinstall/` or the reference
sources, with the address it appears at. Where a note elsewhere covers the same
ground it is repeated rather than cross-referenced.

## The problem all the paging idioms solve

Memory is 16K pages in four sections:

| section | addresses | selected by |
|---|---|---|
| A | `&0000`-`&3FFF` | `LMPR` page (ROM 0 unless disabled) |
| B | `&4000`-`&7FFF` | `LMPR` page + 1 |
| C | `&8000`-`&BFFF` | `HMPR` page |
| D | `&C000`-`&FFFF` | `HMPR` page + 1 (ROM 1 if enabled) |

The ROM's system variables live at `&5A00`-`&5CFF` — in section B. So does a
paged-in extension. **They cannot both be at `&4000` at once**, and that single
fact is behind two thirds of what follows.

## 1. Windowing an address

To reach a system variable while something else is at `&4000`, put the system
page in the window and add `&4000` to the address. `HPRTOK_1` does the whole thing
twice over in one stretch — it points the ROM's current output channel at
MasterBASIC's own code and keeps the old address:

```asm
HPRTOK_1:
      CALL CALLDOS                    ; 5066  (the block starts here)
      DEFW &7859                      ; 5069
      LD BC,&00FB                     ; 506B  B = 0, C = HMPR
      IN E,(C)                        ; 506E  the old paging, kept in E
      OUT (C),B                       ; 5070  the system page is now at &8000
      LD B,E                          ; 5072  and kept in B for the way out
      LD HL,(CURCHL+&4000)            ; 5073  the ROM's CURCHL, read at &9C51
      SET 7,H                         ; 5076  what it points at is a system-page
      RES 6,H                         ; 5078  address too, so window that as well
      LD E,(HL)                       ; 507A  the channel's output routine
      INC HL                          ; 507B
      LD D,(HL)                       ; 507C
      LD (OPSTORE+&4000),DE           ; 507D  saved in a ROM variable
      LD DE,SYS_GAP_BLOCK             ; 5081  MasterBASIC's own, at &5896
      LD (HL),D                       ; 5084  written in the channel's place
      DEC HL                          ; 5085
      LD (HL),E                       ; 5086
      OUT (C),B                       ; 5087  paging back as it was
      RET                             ; 5089
```

`SET 7,H` then `RES 6,H` adds `&4000` for any address in `&4000`-`&7FFF`,
without needing a spare register and without disturbing the carry flag the way
`ADD HL,DE` would. The pair is worth recognising on sight: **`SET 7,H` /
`RES 6,H` means "the same byte, seen in the window".**

In the listings such an address is written `NAME+&4000`, so `CURCHL+&4000` is
`&9C51` in the bytes and `OPSTORE+&4000` is `&9AB5`.

Two smaller things in the same block. `LD BC,&00FB` with `IN E,(C)` and
`OUT (C),B` keeps the port in one register pair and both paging values in the
other, so the old setting never has to be stored anywhere. And `SYS_GAP_BLOCK`
is a name this project gives, not the ROM's: the operand is `&5896`, an address
in *the system page* — the forty bytes MasterBASIC installs in the gap the ROM
leaves between the DEF KEY buffer and the keyboard table — while `&5896` in
MasterBASIC's own page is the middle of an unrelated text scan. The
disassembler is told about this one operand; without that it reads the number as
a local address and invents a label for it, which is the problem above all over
again.

## 2. The `NR` family — reading a system variable from anywhere

Because the windowing above needs `HMPR` saved, changed and restored, it is
wrapped up. `WRA` is the whole pattern in fifteen bytes:

```asm
WRA:
      PUSH AF                         ; 45A4  the value to write
      IN A,(HMPR)                     ; 45A5  save the current paging
      EX AF,AF'                       ; 45A7  keep it in A' — AF is needed
      XOR A                           ; 45A8
      OUT (HMPR),A                    ; 45A9  system page into the window
      SET 7,H                         ; 45AB  window HL
      RES 6,H                         ; 45AD
      POP AF                          ; 45AF  the value again
      LD (HL),A                       ; 45B0  the actual write
      JR PPXR                         ; 45B1  restore HMPR and return
```

The caller passes an address in `HL` at its *proper* value and never thinks
about paging. This is why `LD H,&51 : LD L,(page) : CALL WRA` writes `ALLOCT` at
`&5100` in the system page even though the caller's own `&5100` is something
else entirely.

## 3. Inline parameters after a `CALL`

The `NR` entry points take the variable's address as *data following the call*,
not in a register:

```asm
      CALL NRRD                       ; 4292
      DEFW CUSCRNP                    ; 4295  — read the ROM's CUSCRNP into A
```

The trick that makes it work is one instruction:

```asm
NRRD:
      EX (SP),HL                      ; 456A
```

`EX (SP),HL` exchanges `HL` with the return address the `CALL` pushed. So
afterwards `HL` points at the `DEFW`, and the stack holds the old `HL` — which
gets exchanged back on the way out, leaving the return address stepped past the
parameter. **`EX (SP),HL` as the first instruction of a routine always means
"what follows my caller's `CALL` is data, not code."**

The same convention carries `CMR` (call the ROM with ROM 1 paged in), `CALLDOS`
(call the other half), and the six-byte signature searches below.

## 4. `RST &08` plus a byte — the hook interface

```asm
      RST ERR_HOOK                    ; 7B97  = RST &08
      DEFB HK_HPRTOK                  ; 7B98  hook code &A9
```

A restart is one byte and the code after it is one more, so a hook call costs two
bytes against three for a `CALL`. Codes below 128 are error numbers; 128 and up
index `SAMHK`, a table of handler addresses. The dispatcher reads the byte after
the return address exactly as in idiom 3.

An entry in that table can hold an address `&8000` higher than the page it lives
in, meaning "the handler is in the other page, seen through the window" —
twenty-four of them do, because MasterBASIC has taken those hooks over.

## 5. Taking over a ROM vector

The ROM *calls* its vectors; it does not jump to them. So a handler has two ways
to finish, and the Technical Manual states both:

> your routine making just RET will cause the normal ROM routine to be
> executed. … Otherwise, POP the return address so that the ROM routine is never
> used

Both halves in ten bytes, from the stub `PRTOKV` points at:

```asm
PRTOKV_STUB:
      CP &F7                          ; 7B90  is this one of the ROM's own tokens?
      RET C                           ; 7B92  yes — returning lets the ROM print it
      POP HL                          ; 7B93  no — drop the return address
      LD HL,(XPTR)                    ; 7B94
      RST ERR_HOOK                    ; 7B97  and handle it here instead
      DEFB HK_HPRTOK                  ; 7B98
      RET                             ; 7B99
```

The manual's own worked example writes the second half as
`POP BC ;JUNK RETURN ADDRESS`.

## 6. The rotating window check

Walking a structure longer than 16K, from the Technical Manual:

```asm
      BIT 6,H                         ; has HL crossed from section C into D?
      JR Z,LAB1
      IN A,(HMPAGE)
      INC A
      OUT (HMPAGE)                    ; next page
      RES 6,H                         ; and HL back &4000 lower, onto the same byte
LAB1:
```

`HMPAGE` is the manual's name for the port the listings call `HMPR`, and the
`OUT (HMPAGE)` without an operand is the manual's own typo, reproduced here as
it stands.

The ROM keeps C and D as "a rotating window onto memory", so a pointer only ever
needs checking once per iteration. It is safe because the page number's low five
bits cannot carry into the flag bits above them — every structure walked this way
ends in a terminator first.

`BIT 6,H` appears twenty-one times across the two halves. It is easily confused
with idiom 1: **`SET 7,H`/`RES 6,H` moves an address into the window; `BIT 6,H`
asks whether one has fallen out of it.**

## 7. Merging bits from two registers

`MODE1_SCREEN_ADDRESS` at `&6C38` turns row `B`, column `C` into a display
address. The Spectrum-style layout interleaves the row bits, and the code does it
twice with the same three-instruction trick:

```asm
MODE1_SCREEN_ADDRESS:
      LD L,B                          ; 6C38  keep the row
      LD A,B                          ; 6C39
      OR A                            ; 6C3A  clears carry, so RRA shifts in a zero
      RRA                             ; 6C3B
      RRA                             ; 6C3C
      RRA                             ; 6C3D  row >> 3
      AND &1F                         ; 6C3E  keep five bits
      OR &80                          ; 6C40  the display file base
      XOR L                           ; 6C42  <-- the merge
      AND &F8                         ; 6C43
      XOR L                           ; 6C45
      LD H,A                          ; 6C46
```

`XOR L : AND mask : XOR L` is **"take the masked bits from `A`, the rest from
`L`"**, and it works like this:

- `A XOR L` is 1 exactly where the two differ.
- `AND &F8` keeps only the differences that fall inside the mask.
- `XOR L` flips `L` at those positions — turning it into `A` there, and leaving
  it alone everywhere else.

Three bytes, no spare register, and it does not touch the carry. The alternative
— `AND mask` on one, `AND` the complement on the other, `OR` them — needs a
fourth instruction and somewhere to keep the intermediate.

The second use, eight instructions later, merges the column the same way with
`AND &C7`, sandwiched between rotates that put the bits where the mask expects
them.

## 8. The `&21` skip

Two entry points, where the later one needs a register loaded and the earlier one
does not:

```asm
      IN A,(HMPR)                     ; 7402
      AND PAGEMASK                    ; 7404  the page number alone
      OR &80                          ; 7406
      LD B,A                          ; 7408
      DEFB SKIP_2_VIA_LD_HL           ; 7409  &21, the opcode of LD HL,nn
FIND_PROC_ENTRY_1:
      LD B,&FF                        ; 740A  which is the two bytes this
      POP AF                          ; 740C  instruction is made of
      OUT (HMPR),A                    ; 740D
```

Falling in from `&7408` executes `21 06 FF` — `LD HL,&FF06` — whose operand
swallows the `LD B,&FF`, so `B` keeps the page number just computed. Jumping to
`FIND_PROC_ENTRY_1` from `&73E3` executes the `LD B,&FF` instead, and `B` is `&FF`. One byte
instead of a `JR`, and `HL` is scratch on that path.

`&3E` (`LD A,n`) does the same for one swallowed byte, and `&36` (`LD (HL),n`),
`&0E` (`LD C,n`) and `&FE` (`CP n`) appear too. `&FE` is the cheapest of them
when the flags are about to be set anyway: `SORT_NAMES` uses it to skip the `EXX`
that belongs to the other of its two entry points. `MATCH_REFERENCE` uses the last of those to put
two comparisons back to back — `XOR (HL) : AND &DF` for a letter, `CP (HL)` for
anything else — so that falling through gets the case-insensitive one and
jumping past gets the exact one, with one byte between them. In the listings the swallowed opcode is written as a `DEFB` with a
note saying what it also reads as, because only one of the two readings can be
written down — here, *skipped: reads as LD HL,&FF06 from here, and as part of
the instruction above it*.

## 9. Self-modifying operands

Port numbers and jump targets are poked into instructions rather than kept in
variables:

```asm
      IN A,(HMPR)                     ; 4500
      LD (L4531+1),A                  ; 4502  patches the operand of the LD at &4531
      IN A,(LMPR)                     ; 4505
```

Written `LABEL+1` wherever the instruction it patches could be identified,
because `LD (&4532),A` on its own says nothing. The disassembler looks for a
write landing inside an instruction and names the owner; a write that lands on an
instruction *start* is replacing code, not patching an operand, and is not
treated as this idiom.

## 10. Calling into another page

An address alone is not enough — the page has to come with it. `MB_PAGER` is
MasterBASIC's replacement for the paging subroutine the ROM reserves fourteen
bytes for at `PAGER`, `&5BE0`. It is assembled here and copied there at boot,
which is why the addresses below are `&7AFx`:

```asm
MB_PAGER:
      EX AF,AF'                       ; 7AF2  the wanted page, kept in A'
      IN A,(HMPR)                     ; 7AF3  the current paging
      PUSH AF                         ; 7AF5  saved across the call
      EX AF,AF'                       ; 7AF6  the wanted page back into A
      CALL &005C                      ; 7AF7
      EX AF,AF'                       ; 7AFA
      POP AF                          ; 7AFB
      OUT (HMPR),A                    ; 7AFC  paging back as it was
      EX AF,AF'                       ; 7AFE
      RET                             ; 7AFF
```

`&005C` is three bytes in ROM 0, unlabelled in the ROM source and identical in
every image in `ref/samrom/roms/` from 1.8 on:

```asm
      OUT (&FB),A                     ; 005C  D3 FB
      JP (HL)                         ; 005E  E9
```

So the ROM's convention is `A` = page, `HL` = address, and `CALL &005C` turns it
into a subroutine call: the `JP (HL)` runs the routine, whose own `RET` comes
back here, to the instruction after the `CALL`. `MB_PAGER` adds nothing to it
but the save and restore of `HMPR` around it.

The call side, from the code that ends up in the system page:

```asm
      LD HL,&A485                     ; 49D9  the routine, seen through the window
      CALL S49EE                      ; 49DC
      ...
S49EE:
      LD C,A                          ; 49EE
      LD A,&1C                        ; 49EF  MasterBASIC's page number
      JP S5BE0                        ; 49F1  = PAGER
```

`&A485` is `&6485` in MasterBASIC's own page and `&1C` is the page it lives in;
neither means anything without the other. `S49EE` exists because two callers
want the same page and different addresses — `&A485` here, `&A4F3` three
instructions later — so only the `LD HL` differs.

Four `EX AF,AF'` looks wasteful and is not: `A` is both the page number going in
and the saved `HMPR` coming back, and the alternate accumulator is the only free
place to keep one while using the other.

## 11. Finding a ROM routine by what it looks like

MasterBASIC calls almost no fixed address inside ROM 0. Instead:

```asm
      CALL DOS_FIND_ROM_CODE          ; 75FE
      DEFB &0A,&FE,&20,&10,&00,&F5    ; 7601  signature 0A FE 20 from &1000, -11
      LD (V45F6),HL                   ; 7607                     -> &10A0 INSERTLN
      CALL DOS_FIND_ROM_CODE          ; 760A
      DEFB &56,&5A,&C9,&3C,&00,&03    ; 760D  signature 56 5A C9 from &3C00, +3
      LD (L7DA6+1),HL                 ; 7613                     -> &3DA7 CCRESTOP
```

Six inline bytes in the convention of idiom 3: a three-byte instruction
signature to match, a start address to scan from, and a signed step from the
match to the address actually wanted. Every call site is followed by
`LD (nn),HL`, storing the answer into the operand of the instruction that will
use it — idiom 9. The listing resolves each search against the ROM images in
`ref/samrom/roms/` and names what it found, which is where `INSERTLN` and
`CCRESTOP` in those comments come from. This is what lets one binary work across
ROM versions.

## 12. Clearing memory with the stack pointer

`PUSH` writes two bytes and moves the pointer, with no address register and no
per-byte loop overhead:

```asm
FILL_PAGE_WITH_ZERO:
      LD HL,&0000                     ; 7800  the value to write
      LD BC,&0004                     ; 7803  B = 0 (256 iterations), C = 4
STACK_FILL_LOOP:
      PUSH HL                         ; 7806  eight at a time
      PUSH HL
      PUSH HL
      PUSH HL
      PUSH HL
      PUSH HL
      PUSH HL
      PUSH HL                         ; 780D
      DJNZ STACK_FILL_LOOP            ; 780E  256 times = 4096 bytes
      DEC C                           ; 7810
      JR NZ,STACK_FILL_LOOP           ; 7811  four times = 16384, one page
```

8 × 256 × 4 is exactly 16K. `SP` has to be saved and restored around it and
interrupts disabled, which is the price; eleven T-states per byte is the return.

## 13. `LMPR := &1F`, and paging out from under yourself

`LMPR`'s low five bits select the page at `&0000`, and **section B is that page
plus one**. So the value `&1F` — page 31 — puts page 32 in section B, and 32
wraps to 0. `&1F` is how you spell "the ROM's own arrangement": ROM 0 at `&0000`
(bit 5 clear leaves it enabled) and the system page at `&4000`. Bit 6 on top of
that switches ROM 1 in at `&C000`, which is why `&5F` turns up as often as `&1F`.

The ROM's source writes the pair and says what it means:

```asm
PAGE1F:    EQU &1F
           ...
           LD A,PAGE1F+&40
           OUT (250),A       ;BOTH ROMS ON, PAGE ZERO IN SECTION B
```

The listings write these under names, because `&1F` is `PAGEMASK` in most of its
other appearances and `&40` an ordinary bit almost everywhere else:
`ENABLE_ROM1` for bit 6 alone and `SYSPAGE_IN_B` for `&1F`. `&5F` gets no name
of its own — it is written as the two it is made of, `SYSPAGE_IN_B | ENABLE_ROM1`,
and the build checks that the expression really is the number in the instruction.
Fourteen instructions across both halves carry them, and one form still hides in
a register pair, where `&FA` is the port and `&5F` the value:

```asm
      LD BC,&5FFA                     ; 4F79  C = LMPR, B = &5F
      OUT (C),B                       ; 4F7C
```

That one is worth knowing on sight for a second reason: `&5FFA` looks exactly
like an address, and read as one it invents a label. It did, at both of the two
sites, before either was understood.

**Which bits change is the whole question.** `&5F` and `&1F` differ only in bit
6, so writing one after the other turns ROM 1 on and off again and *leaves the
page in section B exactly where it was*. That is what `USING$` does, from a copy
of itself running at `&5000` in the system page:

```asm
      LD A,SYSPAGE_IN_B | ENABLE_ROM1 ; 724A  = &5F, ROM 1 in
      OUT (LMPR),A                    ; 724C
      LD A,&C8                        ; 724E
      CALL HLJUMP                     ; 7250  a ROM 1 routine, from (&017F)+&8002
      LD A,SYSPAGE_IN_B               ; 7253  = &1F, ROM 1 out again
      OUT (LMPR),A                    ; 7255
```

It is running in section B throughout and is perfectly safe there, because
nothing moves underneath it.

A write that *does* change the low five bits swaps the code out from under
itself. There is no pipeline to flush and no cache: the swap takes effect
immediately, and the next instruction is fetched from the new page. So this is
survivable — and deliberately used — whenever the new page holds a sensible
continuation at that address, which in an image whose two halves are both
assembled at `&4000` is not a strange thing to arrange.

What it is not is something to do by accident. `CMR` has to make a real change,
and look at the trouble it takes:

```asm
      JP CMR_1+&4000                  ; 4513  into the window first
CMR_1:
      LD A,B                          ; 4516
      OR SYSPAGE_IN_B                 ; 4517  page zero into section B
      LD HL,(V4076+&4000)             ; 4519
      DI                              ; 451C
      OUT (LMPR),A                    ; 451D  now safe: this is running at &851D
      LD SP,HL                        ; 451F
      EI                              ; 4520
```

The `JP` to `CMR_1+&4000` runs the very next instruction through the `&8000`
window, so that when `OUT (LMPR),A` lands three instructions later the code is in
section C and section B is free to change. The stack is switched in the same
breath, which is why the `DI`.

**So the reading rule is a question, not a proof.** An `OUT (LMPR),A` whose low
five bits differ from the current ones means one of two things, and you have to
say which: either the code has moved itself out of section B first — look for a
`JP` into `&8000`-`&BFBF` just before — or it intends to carry on in whatever the
new page holds at the next address, in which case that page's contents at that
address are worth looking at.

### Telling a relocated block, properly

The reliable evidence is not the paging instruction but the copy itself. `USING$`
runs at `&5000` because sixteen bytes earlier it says so:

```asm
      LD HL,FN_USING_S_1                     ; 7229  the block
      LD DE,&9000                     ; 722C  &5000 in the system page
      LD BC,&00E7                     ; 722F  231 bytes
      ...
      LDIR                            ; 7238
      CALL CMR                        ; 723D
      DEFW GTDT                       ; 7240  = &5000: call what was just put there
```

and that is what makes `CALL &50D7` inside the block resolvable: `&D7` bytes in,
whose source is `&731A`.

For a block with no visible copier, the tell is where its absolute `CALL`s and
`JP`s land. Code written for the address it sits at jumps all over the page. A
relocated block's jumps all fall inside one narrow range — the range the copy
covers — and none outside it. That identified the 385 bytes at `&7460`, and it is
stronger than it sounds: eight jumps landing inside 385 bytes by chance is not
something to explain away.

Sixteen blocks in this image are written for an address they are not stored at.
Between them they hold about 2400 bytes, and every one of them was read wrong
until it was found.

## 14. `SUB n` then `ADC A,&00` — is A one of two values?

Four bytes and no branch, and it appears three times in the file-type code:

```asm
      SUB &14                         ; 4ECD
      ADC A,&00                       ; 4ECF
      JR NZ,GTFL5A                    ; 4ED1  not CODE and not SCREEN$
```

`SUB n` leaves zero when `A` is `n`, with no borrow. When `A` is `n-1` it leaves
`&FF` **with** a borrow, and the `ADC A,&00` adds that borrow back, giving zero
again. Every other value survives both steps non-zero. So the zero flag after
the pair says **`A` is `n` or `n-1`**, which is two compares and two branches
done in four bytes and eight T-states.

The three uses in MasterDOS all ask about file types, which are numbered so that
the pairs it cares about are adjacent:

| site | test | means |
|---|---|---|
| `&4E7F` | `SUB &12 / ADC A,&00` | type is `&11` or `&12` — a numeric or a string array |
| `&4ECD` | `SUB &14 / ADC A,&00` | the type asked for is `&13` or `&14` — CODE or SCREEN$ |
| `&4ED4` | `SUB &14 / ADC A,&00` | the type on the disc is one of those two |

Read it the other way and it is a range test for a range of two, which is why
`CP` twice never appears here.

Do not confuse it with `ADD HL,BC` / `ADC A,&00` at `&6C72` and `&71E8`, which is
the ordinary 24-bit carry into a third byte. The idiom is the `SUB` before it.

## Reading the listings with this in mind

Four consequences worth holding on to:

- **An address in `&4000`-`&7FBF` is ambiguous** until you know which page is at
  `&4000` in that stretch. `&5C59` is a routine in MasterBASIC *and* part of the
  ROM's eight spare system variables; `&5A40` is inside a printer loop here and
  `MODE` there. The listings resolve this per-range, and getting it wrong has
  been the single largest source of wrong labels in this project.
- **An address in `&8000`-`&BFBF` is the other page** — or the system page, or
  whatever was last paged in. The same question, one section along.
- **Data after a `CALL` is normal**, so an operand that looks like nonsense is
  usually a parameter belonging to the instruction above it.
- **Code is not always where it is stored.** Sixteen blocks here are assembled
  for an address they are copied to, and in those the listing's own labels are
  the wrong ones by construction.
