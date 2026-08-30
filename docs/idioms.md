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

To reach the system page's `&5A97` while something else is at `&4000`, set
`HMPR` to 0 and add `&4000`:

```asm
XOR A
OUT (HMPR),A            ; the system page is now at &8000
SET 7,H                 ; &5A97 -> &DA97
RES 6,H                 ;       -> &9A97
```

`SET 7,H` then `RES 6,H` adds `&4000` for any address in `&4000`-`&7FFF`,
without needing a spare register and without disturbing the carry flag the way
`ADD HL,DE` would. The pair is worth recognising on sight: **`SET 7,H` /
`RES 6,H` means "the same byte, seen in the window".**

In the listings such an address is written `NAME+&4000`, so `ILPD+&4000` is
`&8009` in the bytes.

## 2. The `NR` family — reading a system variable from anywhere

Because the windowing above needs `HMPR` saved, changed and restored, it is
wrapped up. `WRA` at `&45A4` is the whole pattern in eleven bytes:

```asm
WRA:  PUSH AF                 ; 45A4  the value to write
      IN A,(HMPR)             ; 45A5  save the current paging
      EX AF,AF'               ; 45A7  keep it in A' -- AF is needed
      XOR A                   ; 45A8
      OUT (HMPR),A            ; 45A9  system page into the window
      SET 7,H                 ; 45AB  window HL
      RES 6,H                 ; 45AD
      POP AF                  ; 45AF  the value again
      LD (HL),A               ; 45B0  the actual write
      JR PPXR                 ; 45B1  restore HMPR and return
```

The caller passes an address in `HL` at its *proper* value and never thinks
about paging. This is why `LD H,&51 : LD L,(page) : CALL WRA` writes `ALLOCT` at
`&5100` in the system page even though the caller's own `&5100` is something
else entirely.

## 3. Inline parameters after a `CALL`

The `NR` entry points take the variable's address as *data following the call*,
not in a register:

```asm
CALL NRRD               ; 4292
DEFW CUSCRNP            ; 4295  -- read the ROM's CUSCRNP into A
```

The trick that makes it work is one instruction:

```asm
NRRD: EX (SP),HL        ; 456A
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
RST ERR_HOOK            ; 7B97  = RST &08
DEFB HK_HPRTOK          ; 7B98  hook code &A9
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
CP &F7                  ; 7B90  is this one of the ROM's own tokens?
RET C                   ; 7B92  yes -- returning lets the ROM print it
POP HL                  ; 7B93  no -- drop the return address
LD HL,(XPTR)            ; 7B94
RST ERR_HOOK            ; 7B97  and handle it here instead
DEFB HK_HPRTOK          ; 7B98
RET                     ; 7B99
```

The manual's own worked example writes the second half as
`POP BC ;JUNK RETURN ADDRESS`.

## 6. The rotating window check

Walking a structure longer than 16K, from the Technical Manual:

```asm
BIT 6,H                 ; has HL crossed from section C into D?
JR Z,LAB1
IN A,(HMPAGE)
INC A
OUT (HMPAGE)            ; next page
RES 6,H                 ; and HL back &4000 lower, onto the same byte
LAB1:
```

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
LD L,B                  ; 6C38  keep the row
LD A,B                  ; 6C39
OR A                    ; 6C3A  clears carry, so RRA shifts in a zero
RRA                     ; 6C3B
RRA                     ; 6C3C
RRA                     ; 6C3D  row >> 3
AND &1F                 ; 6C3E  keep five bits
OR &80                  ; 6C40  the display file base
XOR L                   ; 6C42  <-- the merge
AND &F8                 ; 6C43
XOR L                   ; 6C45
LD H,A                  ; 6C46
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

The second use, ten instructions later, merges the column the same way with
`AND &C7`, sandwiched between rotates that put the bits where the mask expects
them.

## 8. The `&21` skip

Two entry points, where the later one needs a register loaded and the earlier one
does not:

```asm
LD B,A                  ; 7408
DEFB &21                ; 7409  the opcode of LD HL,nn
L740A:
LD B,&FF                ; 740A  which is the two bytes this instruction is
POP AF                  ; 740C
```

Falling in from `&7408` executes `21 06 FF` — `LD HL,&FF06` — whose operand
swallows the `LD B,&FF`. Jumping to `&740A` executes the `LD B,&FF` instead. One
byte instead of a `JR`, and `HL` is scratch on that path.

`&3E` (`LD A,n`) does the same for one swallowed byte, and `&36` (`LD (HL),n`)
appears too. In the listings the swallowed opcode is written as a `DEFB` with a
note saying what it also reads as, because only one of the two readings can be
written down.

## 9. Self-modifying operands

Port numbers and jump targets are poked into instructions rather than kept in
variables:

```asm
LD (L4531+1),A          ; 4502  patches the operand of the LD at &4531
```

Written `LABEL+1` wherever the instruction it patches could be identified,
because `LD (&4532),A` on its own says nothing. The disassembler looks for a
write landing inside an instruction and names the owner; a write that lands on an
instruction *start* is replacing code, not patching an operand, and is not
treated as this idiom.

## 10. Calling into another page

An address alone is not enough — the page has to come with it. `PAGER`, which the
ROM reserves fourteen bytes for at `&5BE0` and MasterBASIC fills:

```asm
S5BE0: EX AF,AF'        ; 5BE0  keep the wanted page in A'
       IN A,(&FB)       ; 5BE1  save HMPR
       PUSH AF          ; 5BE3
       EX AF,AF'        ; 5BE4  the wanted page back into A
       CALL &005C       ; 5BE5  ROM: page A in, call HL
       EX AF,AF'        ; 5BE8
       POP AF           ; 5BE9
       OUT (&FB),A      ; 5BEA  paging back as it was
       EX AF,AF'        ; 5BEC
       RET              ; 5BED
```

and the call looks like:

```asm
LD HL,&A485             ; 49D9  the routine, as seen through the window
LD A,&1C                ;       the page it lives in
JP PAGER
```

Four `EX AF,AF'` looks wasteful and is not: `A` is both the page number going in
and the saved `HMPR` coming back, and the alternate accumulator is the only free
place to keep one while using the other.

## 11. Finding a ROM routine by what it looks like

MasterBASIC calls almost no fixed address inside ROM 0. Instead:

```asm
CALL DOS_FIND_ROM_CODE  ; 75FE
DEFB &0A,&FE,&20,&10,&00,&F5
;    ^^^^^^^^^^^^^^^^  three bytes to match
;                      ^^^^^^^^^  where to start looking, big-endian
;                                 ^^^  a signed step from the match
```

Six inline bytes in the convention of idiom 3: a three-byte instruction
signature, a start address, and an offset. Every call site is followed by
`LD (nn),HL`, storing the answer into the operand of the instruction that will
use it — idiom 9. This is what lets one binary work across ROM versions.

## 12. Clearing memory with the stack pointer

`PUSH` writes two bytes and moves the pointer, with no address register and no
per-byte loop overhead:

```asm
FILL_PAGE_WITH_ZERO:
      LD HL,&0000       ; 7800  the value to write
      LD BC,&0004       ; 7803  B=0 (256 iterations), C=4
STACK_FILL_LOOP:
      PUSH HL           ; 7806  eight at a time
      PUSH HL
      PUSH HL
      PUSH HL
      PUSH HL
      PUSH HL
      PUSH HL
      PUSH HL           ; 780D
      DJNZ STACK_FILL_LOOP     ; 780E  256 times = 4096 bytes
      DEC C             ; 7810
      JR NZ,STACK_FILL_LOOP    ; 7811  four times = 16384, one page
```

8 × 256 × 4 is exactly 16K. `SP` has to be saved and restored around it and
interrupts disabled, which is the price; eleven T-states per byte is the return.

## Reading the listings with this in mind

Three consequences worth holding on to:

- **An address in `&4000`-`&7FBF` is ambiguous** until you know which page is at
  `&4000` in that stretch. `&5C59` is a routine in MasterBASIC *and* part of the
  ROM's eight spare system variables; `&5A40` is inside a printer loop here and
  `MODE` there. The listings resolve this per-range, and getting it wrong has
  been the single largest source of wrong labels in this project.
- **An address in `&8000`-`&BFBF` is the other page** — or the system page, or
  whatever was last paged in. The same question, one section along.
- **Data after a `CALL` is normal**, so an operand that looks like nonsense is
  usually a parameter belonging to the instruction above it.
