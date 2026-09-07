---
name: z80-idioms
description: Use when reading or annotating Z80 machine code — ROMs, DOSes, extensions, anything hand-assembled — and a sequence looks wrong, wasteful or unmotivated. Carries the recurring idioms that trip a disassembler and a reader alike (skip bytes, inline parameters after CALL, self-modifying operands, RST-plus-byte hooks, the two-value SUB/ADC test, SP-based clears, signature searches), what each looks like in the bytes, and how a listing should write it so both readings are visible. Marks which idioms are generic Z80 and which belong to bank-switched machines. Trigger on "what is this doing", "this decodes as nonsense", "DEFB in the middle of code", "EX (SP),HL", "why RST here", "self-modifying".
---

# Z80 idioms a listing has to show

Each entry: what it looks like, why it was written, how to write it
down so a reader sees both readings.  Generic Z80 unless marked.

## Skip bytes -- one opcode swallowing the next instruction

Two entry points, the later one needing a register loaded and the
earlier one not:

```
      LD B,A
      DEFB &21              ; the opcode of LD HL,nn
ENTRY_2:
      LD B,&FF              ; which is the two bytes it swallows
```

Falling in from above executes `21 06 FF` = `LD HL,&FF06`, whose
operand eats the `LD B,&FF`, so B keeps the value just computed.
Jumping to `ENTRY_2` executes `LD B,&FF`.  One byte instead of a `JR`,
and HL is scratch on that path.

Two-byte skips: `&21` (LD HL), `&11` (LD DE), `&31` (LD SP).  One-byte
skips: `&3E` (LD A), `&0E` (LD C), `&16` (LD D), `&F6` (OR n), `&FE`
(CP n).  **The choice is about what is clobbered**: `&FE` is cheapest
when the flags are about to be set anyway; where the branch below
tests flags an earlier `AND` set, it has to be `&0E`, which clobbers
only C.

A tracing disassembler follows the jump, decodes `LD B,&FF`, and then
finds `&21` as a lone byte it cannot place -- or follows the fall-in
and hides the entry point inside `LD HL,&FF06`.  Write the swallowed
opcode as `DEFB SKIP_2_VIA_LD_HL` with a note: *skipped: reads as
LD HL,&FF06 from here, swallowing the bytes below it*.  Declare the
eight skip opcodes as equates once.

## Inline parameters after a CALL

```
      CALL READVAR
      DEFW SOMEVAR          ; data, not the next instruction
READVAR:
      EX (SP),HL            ; HL <- return address = the DEFW
```

`EX (SP),HL` as the first instruction of a routine means *what follows
my caller's CALL belongs to me, not to the instruction stream*.  On
the way out it is exchanged back with HL stepped past the parameter.
Usually the parameter is data.  The rule is about ownership, not type:
one routine RETs *into* its parameter and the two bytes are executed.

Six-byte parameter blocks after a call are common -- a signature to
search for, a start address, a signed step.  A sniffer that decides
how many inline bytes a routine takes must stop at a CALL: a routine
whose *first* instruction is a CALL with an inline signature whose
first bytes happen to decode as `RET : EX (SP),HL` will otherwise be
read as taking a two-byte parameter it does not take, and every caller
shifts by one.

## Self-modifying operands

```
      IN A,(PORT)
      LD (LATER+1),A        ; patches the operand of the LD at LATER
```

Port numbers, page numbers and jump targets are poked into instructions
rather than kept in variables.  Write it `LABEL+1` wherever the patched
instruction can be identified; `LD (&4532),A` on its own says nothing.
A write landing on an instruction *start* is replacing code, not
patching an operand, and is a different thing.  The listing shows the
*assembled* operand -- often `&0000` -- and the comment says what runs.

## `SUB n` then `ADC A,&00` -- is A one of two values?

`SUB n` leaves zero when A is n, no borrow.  When A is n-1 it leaves
`&FF` **with** a borrow, and `ADC A,&00` adds it back: zero again.
Every other value stays non-zero.  Four bytes, no branch, fourteen
T-states: **A is n or n-1**.  Used where the two cases that matter are
numbered adjacently.  Do not confuse with `ADD HL,rr : ADC A,&00`, the
ordinary 24-bit carry; the idiom is the `SUB`.

## `RST &08` plus a byte -- the hook / error interface

`RST` is one byte where `CALL` is three; the byte after it is fetched
by the handler from the return address.  A tracing disassembler reads
the code byte as the next opcode.  Name the codes (`ERR_...`,
`HKC_...`) and mark the byte as data after the RST.  A table indexed
by code, with a flag bit meaning "handler is in another bank", is the
usual shape.

## Clearing memory through the stack pointer

`LD SP,top : LD HL,0 : PUSH HL` in a loop -- 8 pushes per iteration
and DJNZ -- clears 16 bytes per pass at about six T-states a byte.
The price is SP saved and restored and interrupts off.  `8 x 256 x 4`
is 8192 *pushes* of two bytes, which is 16K; count the bytes, not the
pushes.

## Finding a routine by what it looks like

Code that must survive a ROM it was not built against searches the
ROM for a three-byte instruction signature from a start address with a
signed step, and stores the result into the operand of the instruction
that will use it.  Such code contains almost no hard-coded ROM
addresses; the listing should resolve each search against the ROM
images to hand and say what it finds and whether that is a named entry
point or a place *inside* a routine to rejoin it.

## Bank-switched machines only

- **Window arithmetic.**  When a bank is visible through a window at a
  different address from where it was assembled, an operand is the
  label plus the window offset.  Write it `LABEL + IN_WINDOW`, never a
  bare number, and never the label alone -- the bare number hides the
  relationship and the bare label is the wrong address.
- **Blocks written to run elsewhere.**  A block copied at boot into
  another bank is assembled for its destination.  Its internal
  addresses cannot take the assembling bank's labels; comment them
  with *once this block is moved*.
- **Rotating-window walks.**  `BIT 6,H : JR Z : INC page : RES 6,H`
  steps a pointer across a bank boundary.  It is safe only because the
  structure walked ends in a terminator before the page number can
  carry into the mode bits above it -- a fact about the data, not the
  hardware.  Do not write it as a hardware property.
- **Paging out from under yourself.**  A routine that switches the
  bank it is executing from must be positioned so the same bytes are
  at the same address in both banks, or jump through a stub that is.
