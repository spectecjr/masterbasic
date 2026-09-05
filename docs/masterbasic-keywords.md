# The keywords in MBKEYS

The 28 names MasterBASIC adds to SAM BASIC, in the order `MBKEYS` lists them —
which is the order that gives them their tokens. How they get a token, and how
the ROM comes to call MasterBASIC for them, is in
[masterbasic-tokens.md](masterbasic-tokens.md).

The descriptions are from the MasterBASIC manual in
[docs/original](original), whose Appendix A gives the same token for every one
of these names as `HGTTK`'s arithmetic produces. The addresses given for the
commands are from `CTAB` in the MasterDOS half --
[listings/clean/masterdos.asm](../listings/clean/masterdos.asm) to read it, or
[listings/disasm/masterdos.asm](../listings/disasm/masterdos.asm) for the working notes. The
functions are dispatched through `HEVV2` and the sixteen-entry vector table at
`&78EB`, every entry of which points into the MasterBASIC page; which slot
belongs to which token I have not pinned down, so no address is given for them.

Seven of the names are not MasterBASIC's own work. `TIME$`, `DATE$`, `INP$`,
`DIR$`, `FSTAT`, `DSTAT` and `FPAGES` are MasterDOS's, documented in
[ref/masterdos/docs/functions.md](../ref/masterdos/docs/functions.md);
MasterBASIC keeps them at the tokens MasterDOS gave them, so a program written
for the DOS alone still tokenises the same way, and extends three of them.
`BACKUP` and `DATE` are MasterDOS commands too.

---

## Statements

### `EXIT PROC` — `FF 26`

Leaves a `DEF PROC` early. `GO TO` the `END PROC` would do it, but wrecks the
indentation and stops the interpreter skipping the procedure if it runs into it;
`EXIT PROC` has neither problem and works from inside a loop.

```
140 IF INKEY$=" " THEN EXIT PROC
```

### `EXIT DO` — `FF 27`

Leaves a `DO` loop, jumping to the statement after the matching `LOOP` and over
any nested `DO` loops on the way. Written because people kept resorting to
`EXIT IF 1`, which is always true and reads oddly.

### `EXIT FOR` — `FF 28`

Leaves a `FOR` loop without setting the control variable out of range or `GO
TO`ing past the `NEXT`. The control variable keeps its value.

---

## Data-handling functions

### `LOCN` — `FF 29`

```
LOCN(start,length,a$)
LOCN(start,length,a$,ABS)
```

Searches memory for a string and returns the address, or 0. `#` in the target
matches anything, as in `INSTR` and `INARRAY`. Case-insensitive at about
90K/second; add `ABS` for an exact match at over 200K/second.

### `RESERVED` — `FF 2A`

```
RESERVED(n)
```

Claims `n` bytes of the system heap and returns the address; `RESERVED(-n)`
gives them back. Meant for the short paging stubs that call machine code in
another page. It grows at the expense of BASIC's `GOSUB`/`DO`/`PROC` stack, so
over-use makes "BASIC stack full" more likely, and de-allocating space someone
else reserved will crash the machine.

### `EQU` — `FF 2B`

```
EQU(a$,b$)
```

Compares two strings ignoring case, so `EQU(nm$,"Jones")` accepts `jONES` and
`jOnEs`. Convenient for checking input without forcing it into a format first.

### `TICS` — `FF 2C`

Seconds elapsed in the month so far, 0 to 2678399, read from the SAMBus clock
through MasterDOS. Restarts at midnight on the last day of the month. Under
`TIME +` it returns a floating-point value good to about 0.0002s — MasterBASIC
does the division by the fast-mode factor for you. See [`TIME`](#time--248).

### `SHIFT$` — `FF 2D`

```
SHIFT$(a$,n)
```

| `n` | |
|---|---|
| 1 | force upper case |
| 2 | force lower case |
| 3 | reverse case |
| 4 | make the string printable: control codes become a full stop, characters above 127 lose the top bit |

Option 4 exists for reading memory as text — `PRINT SHIFT$(MEM$(n TO n+255),4)`
where a plain `PRINT` would fail on the control codes. `DVAR 24` and `DVAR 25`
change what option 4 does with high characters and which character stands in for
a control code. Strings must be 16383 characters or less.

### `SVAL$` — `FF 2E`

```
SVAL$(number,characters)
```

Packs a number into a 2, 3, 4 or 5-character string, so numeric data can sit in
a fixed-width field of a string array or a random-access record. `NVAL` is the
inverse.

| Characters | Range and precision |
|---|---|
| 2 | whole numbers 0–65535 |
| 3 | full range, about 5 digits correct |
| 4 | full range, about 7 digits |
| 5 | full range, 9 digits — the Coupé's own precision |

An array of these sorts about four times faster than the equivalent numeric
array would, which is the manual's stated reason for `SORT` not supporting
numeric arrays at all. Printing the result often gives "Invalid colour", since
it may contain bytes that are print control codes.

### `USING$` — `FF 2F`

```
USING$(format$,number)
```

Formats a number to a fixed number of digits either side of the point. `#` in
the format string means a leading space, `0` a leading zero, and other leading
characters are copied through. Rounds to the last printed digit; `%` marks
overflow. Small numbers like `1E-8` are converted out of exponent form
automatically, and trailing spaces in the format are ignored.

```
USING$("###.#",12.3456)      ->  " 12.3"
USING$("$00.00",12.3456)     ->  "$12.35"
```

Unlike the `PRINT USING` other BASICs offer, the result is a string, so it can
be `LET` into a fixed field of a record and then sorted on.

### `SCRAD` — `FF 37`

The address of the start of the current screen. Needed for `POKE` or `LOAD
... CODE` to the screen in a program that has to work on both 256K and 512K
machines, where the screen is not in the same place.

### `INARRAY` — `FF 38`

```
INARRAY(a$(start),target$)
INARRAY(a$(start,slicer),target$)
INARRAY(a$(start,slicer),target$,ABS)
```

The array version of `INSTR`: searches a string array from the given element for
a target string and returns the number of the first string containing it, or 0.
Case-insensitive unless `ABS` is given, which is also faster. A slicer limits
the search to part of each string and speeds it up further. After a successful
search, `DPEEK XVAR 3` gives the position within the string.

### `XVAR` — `FF 68`

```
XVAR n
```

The address of one of MasterBASIC's own variables, the counterpart of the ROM's
`SVAR` and the DOS's `DVAR`. `PRINT XVAR 0` gives the start of MasterBASIC,
since `PUTSWA` sits at its very beginning.

| | |
|---|---|
| 0 | `PUTSWA` (2 bytes) — holds the *address* of the `PUT` switch, not the switch |
| 2 | `SOFV` — screen blanking delay; 12 ≈ 1 minute, 0 ≈ 22 |
| 3 | `IAPOS` (2 bytes) — where the last `INARRAY` match was found within the string |
| 5 | `DTTH` — how many times a `DUMP` strikes the paper; 2 for double-strike |
| 6 | `SORP` — zero after `LPRINT MODE 1`, non-zero after `MODE 2`; read at BOOT time |
| 7 | `VERSION` — MasterBASIC's version times ten |
| 8 | `ILPC` — characters sent per interrupt by interrupt-driven printing, normally 15 |
| 9 | `ILPD` (2 bytes) — how long to wait for a not-ready printer, in units of ~25µs |
| 11 | `SPORT` — the serial driver's port, normally 236 |
| 12 | `BAUD` — baud rate, 187 for 9600; read at `LPRINT MODE 2` or BOOT |
| 13 | `DBITS` — data bits, 147 for 8 |
| 14 | `SBITS` — stop bits, 31 for 2 |
| 15 | `SDORI` — `DUMP` orientation: sideways, mirrored, forced upright |

`XVAR 16` to `XVAR 89` are the rest of the printer and `DUMP` control: the area
to dump, the Epson escape sequences sent before and after the bit-image data,
the substitutes for the pound and hash characters, and the auto-line-feed
setting copied into `SVAR 15` at BOOT. Manual pages 48–51 give every byte.

The errata note that `XVAR 9` now starts at 20 rather than the 12 the manual
prints, and that `MODMSG1` at `XVAR 63` should read `4,27,82,3,35,0,0,0`.

### `NVAL` — `FF 6A`

```
NVAL a$
```

Turns a 2–5 character `SVAL$` string back into a number.

---

## Functions MasterDOS provides

`TIME$` (`FF 30`), `DATE$` (`FF 31`), `INP$` (`FF 32`), `DIR$` (`FF 33`),
`FSTAT` (`FF 34`), `DSTAT` (`FF 35`) and `FPAGES` (`FF 36`) are MasterDOS's.
MasterBASIC extends three of them:

- **`FSTAT`** grows from four options to eight — adding 5 start address, 6
  auto-start line or execute address, 7 the file date as a number like 231291,
  and 8 the file flags, whose bits mark a file that `MERGE` cannot stop, a
  compressed file, and a `SAVE MODE 3` screen.
- **`DIR$`** takes a `?` after the name string to list every file on the disk,
  subdirectories included: `PRINT DIR$("*"?)`.
- **`INP$`** accepts a count of zero, meaning "read to a carriage return", so
  `LET a$=INP$(#5,0)` does what `INPUT #5;a$` does but without clearing the
  lower screen, without the keyclick, and several times faster.

---

## Commands

### `BACKUP` — 247 → MasterDOS's own `BACKUP`

MasterDOS's command, and the one `CTAB` entry of the seven that still points
into the DOS page. MasterBASIC's only change is an alternative syntax shared
with `COPY`, `RENAME` and `MOVE`: a comma in place of `TO`, so `BACKUP
"d1","d2"`.

### `TIME` — 248 → MasterBASIC `&486A`

MasterDOS sets and reads the SAMBus clock with `TIME`. MasterBASIC adds two
forms:

```
TIME +      switch the clock into its high-speed test mode
TIME -      switch back
```

The test mode runs 5416.3 times faster than real time, which is what makes
`TICS` useful for timing. MasterBASIC saves the real time and date on the way in
and corrects them on the way out, so ordinary use costs nothing — but leaving
the mode on for more than about eight real minutes overruns the correction, and
turning the machine off in it leaves the clock fast until the next boot.

### `DATE` — 249 → MasterBASIC `&485B`

MasterDOS's command for setting the calendar, taken over by MasterBASIC along
with `TIME` so that the two stay consistent across the fast-mode switch.

### `ALTER` — 250 → MasterBASIC `&54CA`

Three unrelated jobs under one keyword.

```
ALTER (reference) TO (reference) [,first[,last]]
```

Search and replace through the program text. A reference is a variable, a
number or a sequence of characters, following the same rules as `REF`: bare
names match only whole words and are not found inside strings, a quoted string
is found anywhere, and brackets around a variable name mean "use its value".
Altering a number changes the invisible five-byte form with it — but altering it
to a *quoted* number does not, which leaves a listing that looks right and does
not run. `ALTER "word" TO ""` deletes.

```
ALTER DEVICE logical TO physical
```

Points a logical drive number at a different real drive, the readable form of
poking MasterDOS's table at `DVAR 111`. `ALTER DEVICE 1 TO 3` makes `DIR 1` and
`LOAD "d1:name"` use drive 3, which is how you move software onto a RAM disc
without changing it.

```
ALTER DISPLAY screen TO screen LINE y
```

Shows the top of one screen and the bottom of another, switching at line `y`.
The two need not be in the same `MODE`, so `MODE 4` graphics can sit above
`MODE 3` text.

### `SORT` — 251 → MasterBASIC `&460B`

```
SORT [ABS] [INVERSE] a$
```

Sorts the strings of a string array, or the characters of a plain string, in
place. Plain `SORT` ignores case — bit 5 of each character's code is not
considered. `SORT ABS` sorts strictly by character code, which is what
`SVAL$`-packed numbers and other coded data need, and is slightly faster.
`INVERSE` reverses the order.

Slicers select what to sort and what to sort on:

```
SORT a$(1 TO 20)        the first twenty strings
SORT a$(30 TO )         from the thirtieth on
SORT a$()(2 TO )        every string, ordered on the second character onwards
SORT ABS q$(4 TO 9)(1 TO 5)
```

The second slicer names the part of each string to compare, which is why sorting
the whole array on a field needs an empty first slicer. 100 ten-character
strings take about 0.14s, 800 about 6s; string length matters much less than
the count.

### `JOIN` — 252 → MasterBASIC `&6DFC`

Two jobs.

```
JOIN [line]
```

Joins a program line to the one below it, dropping the second line number and
separating the two with a colon. Without a line number it acts on the line under
the cursor. The inverse — splitting a line — has no keyword: type `/` after the
colon and press RETURN.

```
JOIN TO a$,b$
```

Appends the second string or string array to the first. `JOIN TO a$,b$` is
`LET a$=a$+b$` but faster and in less free memory; the second string is
unchanged. Arrays can be joined when their strings are the same length, and the
first array grows by the number of strings in the second.

*(The manual's worked example on page 16 has `JOIN TO a$,a$` at line 30; the
errata correct it to `JOIN TO a$,b$`.)*

### `EDIT` — 253

```
EDIT [#stream;] [AT y,x;] [prompt;] variable
```

`INPUT` with the variable's present value offered for editing rather than a
blank line — the fix for mistyping a long string. The syntax follows `INPUT`,
including `AT`, `TAB`, `LINE`, `#stream` and prompts, but only the first
variable is edited; any others are treated as plain `INPUT`. If the variable
does not exist yet, `EDIT` is exactly `INPUT`.

`EDIT` is the one keyword in `MBKEYS` with no `CTAB` entry, so it is reached
through the ROM's `CMDV` vector rather than through the DOS's command table.
