# Getting listings/clean/ to look like design/exampledocs.md

Yes. Every construct in the example assembles, and the gap between it and
what `listings/clean/` prints today is six mechanisms and a long content pass. This
is the plan.

The example was checked against `pyz80` before writing any of this:

```asm
CP  MAX_RAMDRIVE_PAGE_TYPE + 1                    FE D8
LD  HL,HEADER + SECTOR_LENGTH - 1 + IN_PAGE_C     21 FF 81
AND DISK_STATUS_BUSY | DISK_STATUS_LOST_DATA | DISK_STATUS_CRC_ERROR
                                                  E6 0D
BIT DISK_STATUS_LOST_DATA-2,A                     CB 57
DJNZ $                                            10 FE
```

`21 FF 81` is what the image holds at `&4041`, so the example's most
adventurous line is not only legal, it is right.

---

## 1. What the example does that listings/clean/ does not

Side by side on the same six instructions:

| | today | wanted |
|---|---|---|
| narration | none | `; Scan the ALLOCT table and clean up RAM disk pages...` between instruction groups |
| operands | `CP &D0` | `CP MIN_RAMDRIVE_PAGE_TYPE` |
| expressions | `LD HL,V511F` | `LD HL,ALLOCT + MAX_INTERNAL_PAGE` |
| windowing | `LD (V40F9+&4000),SP` | `LD (STACK_POINTER_ON_BOOT + IN_PAGE_C),SP` |
| equates | grouped by where the name came from | grouped by subject: Memory, Disk, Commands, Flags, Idioms |
| flags | `AND &0D` | `AND DISK_SECTOR_READ_ERROR_FLAGS`, itself `EQU A \| B \| C` |
| bit tests | `BIT 1,A` | `BIT DISK_STATUS_DATA_RQ_BX,A` |
| labels | `BOOT_13`, `V40F9` | `BOOT_READ_SECTOR_DATA_LOOP`, `STACK_POINTER_ON_BOOT` |
| data | `V40F9: DEFW 0` | named, with a line saying what it holds |

The narration is the big one. It is most of what makes the example
readable, and it is the one thing the pipeline has no way to express.

---

## 2. Six mechanisms, in dependency order

### M1 — Interleaved narration  *(the biggest change; everything else is decoration without it)*

A block of prose placed **before** an instruction, at column 0, single
`;`, with a blank line above it. New `notes/` entry kind, same parser:

```
DOS &400A step
    Reset the frame interrupt vector to the default ROM implementation.
```

- `notes.py`: parse `step` like `DOC`, store as `d.steps[addr]`.
- `disasm.py` `emit()`: before the instruction at that address, emit a
  blank line then the wrapped prose.
- `asmfmt.py`: column-0 `;` lines are already a handled category (the
  `; ---- NAME ---- from` heads, `format_listing` line 162). Add a rule
  that wraps a step block to `WIDTH` and passes it through.
- A bare `DOS &4033 gap` with no prose gives a paragraph break with no
  words, for grouping that needs no explanation.

**Risk:** low. Contained in three files, and nothing it emits is code.

### M2 — Expression operands

The mechanism that makes `ALLOCT + MAX_INTERNAL_PAGE` possible, and the
one that must not be allowed to lie.

```
DOS &4015 expr ALLOCT + MAX_INTERNAL_PAGE
DOS &401D expr MAX_RAMDRIVE_PAGE_TYPE + 1
DOS &4041 expr HEADER + SECTOR_LENGTH - 1 + IN_PAGE_C
```

- A small evaluator over the listing's own symbol table: `+ - | & ( )`
  and `<< >>`, integers and names, nothing else. No `eval`.
- **The expression is evaluated and compared with the operand bytes
  actually in the image. A mismatch fails the build.** This is the whole
  reason to do it this way rather than by hand: `expr` cannot become a
  comment that has drifted away from its instruction.
- Reuses the existing `value` plumbing for the rendering half.

**Risk:** low, and self-policing. The evaluator is perhaps sixty lines.

### M3 — Equates grouped by subject

Today `header()` groups by provenance — hardware ports, ROM entry
points, peer labels, inferred, notes, and so on — which is the right
grouping for the working copy, because provenance is what listings/disasm/ is
about. The reading copy wants Memory / Disk / Commands / Flags / Idioms.

```
EQU DISK_STATUS_BUSY : Flags : bit 0 of the WD1772 status register
```

- Optional third field on `EQU`, and on `value`, naming the group.
- `header()` in clean mode emits grouped blocks in a declared order,
  with headings, before the provenance blocks; anything ungrouped stays
  where it is now.
- Groups are declared in one place in `clean.py` so the order is stable.

### M4 — Bit numbers, masks, and composed flags

Two families, because `BIT n,A` needs a number and `AND m` needs a mask:

```
EQU= DISK_STATUS_DRQ      : Flags : 2
EQU= DISK_STATUS_DRQ_BIT  : Flags : 1
EQU= DISK_SECTOR_READ_ERROR_FLAGS : Flags :
        DISK_STATUS_BUSY | DISK_STATUS_LOST_DATA | DISK_STATUS_CRC_ERROR
```

- New `EQU=` entry: an equate whose value is an expression, emitted
  textually so the listing shows the composition rather than `&0D`.
- Evaluated by M2's evaluator; the assembler checks it a second time.

### M5 — The `IN_PAGE_C` idiom

76 operands are written `NAME+&4000` today. In clean mode they become
`NAME + IN_PAGE_C`, with the equate declared under "Idioms" and a
sentence saying what it means — code assembled at `&4000` and executed
at `&8000`, which is the single hardest thing about this listing for a
newcomer. One change in the operand renderer.

### M6 — Descriptive labels and named data

No new mechanism: `RENAME` in `notes/clean/` already does it, and it is
already isolated from the working copy. Covers `BOOT_13` →
`BOOT_READ_SECTOR_DATA_LOOP` and `V40F9` → `STACK_POINTER_ON_BOOT`, plus
a `step` line over each data cell saying what it holds.

**Done.** A jump to its own address is written `DJNZ $` in the reading
copy. There are five in the DOS and none in MasterBASIC, and all five are
settle delays, which is where it reads best:

```asm
               LD B,CMD_LATENCY_LOOPS          ; 455F 06 14
               DJNZ $                          ; 4561 10 FE
               RET                             ; 4563 C9
```

The label goes with it — but only where the instruction is the one thing
that refers to it. Four of the five lose theirs; `BOOT_READ_CMD_SETTLE`
keeps its name because MasterBASIC jumps into the middle of that delay
from `MB &5A8E`, which is worth seeing.

---

## 3. What "zero magic numbers" can actually mean

Measured over both clean listings: **3887 one-byte immediate sites, 248
distinct values.** The distribution kills the obvious approach —

```
&00 x867   &80 x144   &20 x107   &01 x97   &04 x89   &02 x84 ...
the 10 commonest values cover 44% of all sites
```

`&00` is 867 sites and means a different thing at nearly every one. So
there is no global value table to write; naming is **per site**, which is
what the existing `value` entry already does, and it belongs inside the
per-routine pass rather than in a sweep of its own.

The workable target is therefore: **no unexplained number in a routine
that has been worked**, with `clean.coverage()` extended to say, per
routine, how many bare immediates are left. Some will stay bare on
purpose — a loop counter of 8 that is just 8 — and the report should let
a routine be marked done with them still there.

The two-byte side is easier: 1160 operands, 676 distinct, and most are
addresses that already resolve to labels.

---

## 4. The content pass

The unit of work is one routine. For each:

1. `RENAME` its labels to say what they are.
2. `step` blocks breaking it into three to six labelled moves.
3. Name every immediate that means something (`value`, `expr`).
4. Rewrite the banner: what it is for, then how, then the traps.
5. Rewrite or replace any remaining capitals from the original source.

**Order** — by dependency, not by address, so that each routine can lean
on names already established:

1. `BOOT` — the example's own subject, the reader's entry point, and the
   place `IN_PAGE_C` has to be explained.
2. The disk primitives — **done**: controller commands, sector in and
   sector out.
3. The layer they call: `RETRY_OR_GIVE_UP`, `CTAS`, `RSSR`, `TIRDXDCT`.
4. Files and the directory.
5. MasterBASIC's command intercepts.

**Scale, honestly.** 545 routines carry the original author's commentary;
1612 of his line comments are still in place; the realistic target is the
557 routines something calls by name. This is many sessions of work, and
the value arrives incrementally — every routine done is done, and the
build reports the remainder rather than implying it.

---

## 5. Guardrails

What makes many iterations safe rather than a slow drift:

- **Byte-identical ×6 stays the gate.** Every mechanism above changes
  only how bytes are *written*, never which bytes.
- **`expr` and `EQU=` are checked against the image**, so a named
  constant cannot quietly stop matching the byte it names.
- **`checkdocs.py`** already holds the prose in `docs/` and `notes/` to
  what the listings say.
- **A per-routine scoreboard** in the build output: worked / not, bare
  immediates left, capitals left.

That last one matters most. The example, written by hand, has
`SCREEN_PAGE_TYPE: EQU &C0` used on an instruction whose byte is `&30`;
`DISK_READ_SECTOR_CMD: EQU &` unfinished; `MAX_RETRY_COUNT` used where
`MAX_SECTOR_RETRY_COUNT` was declared; and `BOOT_8` and
`BOOT_FOUND_PAGE` referenced but never defined. That is not a criticism
of the example — it is a sketch and reads exactly as intended. It is the
argument for the machinery: at 30000 lines, only a generator that
assembles and compares can hold a style like this together.

---

## 6. First iteration — done

M1 and M5 are built, and `BOOT` (`&4009`–`&40FF`) is written in the new
style: 23 steps, 29 renames, 10 named constants, all six listings still
byte-identical.

Two things learned in the doing:

- `notes.rename()` had to be given the folder as well as `notes.apply()`,
  or the `RENAME` lines in `notes/clean/` are read and silently ignored.
- Narration is emitted **before** the label and its caller list, not
  after. The example does both; one rule reads better than two.

**All six mechanisms are now built.** M2 needed no evaluator: the listing
is assembled and compared with the image on every build, so a wrong
expression fails at its own address, which is a better diagnostic than a
hand-written check and was already in place. M4 arrived as `CONST`, which
also covers any named number that belongs to no single instruction. M3 is
a `GROUP` directive that heads the ones written under it.

Two things asmfmt had to learn, both found by reading the output rather
than by the byte check:

- its equate pattern took the value as the first word, so a composed
  equate silently lost everything after the first name;
- the equate comment column is set by the widest equate, so one long
  expression dragged every description in the file out to column 96.

And one thing the byte check cannot see at all: taking a name away leaves
the listing assembling perfectly and reading worse. Two constants were
lost that way while regrouping. `bare_numbers()` now counts the
instructions still carrying an unnamed number, per half, on every build.

## 6a. What the first iteration was

Small enough to judge the whole style on, and it is the example's own
subject:

- Build M1 (`step`) and M5 (`IN_PAGE_C`).
- Apply them to `BOOT`, `&4009`–`&40FF`, with M6 renames.
- Leave M2/M3/M4 until the narration is seen in place, since they are
  cheaper to design once there is a real page to look at.

That gives one screen of `listings/clean/masterdos.asm` that can be held next to
`design/exampledocs.md` and argued about, before committing to the
mechanisms that touch every equate in the file.
