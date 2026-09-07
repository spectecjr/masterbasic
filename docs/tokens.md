# Every token: SAM BASIC, MasterDOS, MasterBASIC

One table for all three layers, because a program file does not say which
layer wrote it. The names here are not typed in: `tools/tokentab.py` reads
`KEYWTAB` out of [ref/samrom/text.asm](../ref/samrom/text.asm) and applies
`HGTTK`'s arithmetic to `MBKEYS`, so the table is whatever the ROM and the
extension actually hold.

```
python tools/tokentab.py            # the flat list
python tools/tokentab.py --md       # the tables below
```

*How* the extensions get a token at all is
[masterbasic-tokens.md](masterbasic-tokens.md); *what each new keyword does*
is [masterbasic-keywords.md](masterbasic-keywords.md) and
[ref/masterdos/docs/](../ref/masterdos/docs/). This file is the reference a
translator needs: token in, name out, and back again.
[sam-basic-grammar.txt](sam-basic-grammar.txt) is the same list in
machine-readable form, with the syntax of each keyword beside it.

## How a token is stored

A tokenised line holds a keyword as either **one byte from `&85` to `&FD`**
or **`&FF` followed by a second byte from `&26` to `&83`**. There is no third
form. `&FF` is never a token on its own — `text.asm` marks it *"FF (FUNCTION
PREFIX) AND TEMP 'INK' TOKEN"*, and the tokeniser converts the temporary one
to `PEN` (`&A1`) before it reaches the line.

| Range | What it is |
|---|---|
| `&85`–`&8F` | qualifiers — words that only appear inside another statement |
| `&90`–`&F6` | the ROM's statements, dispatched through `CMDADT` on token − `&90` |
| `&F7`–`&FD` | the seven MasterDOS/MasterBASIC statements |
| `&FE` | never used |
| `&FF 26`–`&FF 38` | MasterDOS's and MasterBASIC's functions, below the ROM's range |
| `&FF 3B`–`&FF 52` | the ROM's *immediate* functions — no argument, a bracketed one, or `#` |
| `&FF 53`–`&FF 79` | the ROM's floating-point functions, taking one argument |
| `&FF 7A`–`&FF 83` | the binary operators that have names |

Two of MasterBASIC's names, `XVAR` and `NVAL`, sit at `&FF 68` and `&FF 6A`
inside the floating-point range rather than below it: both are spare slots in
the ROM's own list, written `DB "-"+&80` in `text.asm`.

Which set of tokens a file uses depends on what was loaded when it was typed.
The **From** column says which: `ROM` needs nothing, `MasterDOS` needs the DOS,
`MasterBASIC` needs both. A file using no `MasterBASIC` token loads and lists
correctly under MasterDOS alone; one that does will list as `?` for the token
it cannot name.

## Statements and qualifiers — one byte

| Token | Dec | Keyword | Role | From |
|---|--:|---|---|---|
| `&85` | 133 | `USING` | qualifier | ROM |
| `&86` | 134 | `WRITE` | statement | ROM |
| `&87` | 135 | `AT` | qualifier | ROM |
| `&88` | 136 | `TAB` | qualifier | ROM |
| `&89` | 137 | `OFF` | qualifier | ROM |
| `&8A` | 138 | `WHILE` | qualifier | ROM |
| `&8B` | 139 | `UNTIL` | qualifier | ROM |
| `&8C` | 140 | `LINE` | statement | ROM |
| `&8D` | 141 | `THEN` | qualifier | ROM |
| `&8E` | 142 | `TO` | qualifier | ROM |
| `&8F` | 143 | `STEP` | qualifier | ROM |
| `&90` | 144 | `DIR` | statement | ROM |
| `&91` | 145 | `FORMAT` | statement | ROM |
| `&92` | 146 | `ERASE` | statement | ROM |
| `&93` | 147 | `MOVE` | statement | ROM |
| `&94` | 148 | `SAVE` | statement | ROM |
| `&95` | 149 | `LOAD` | statement | ROM |
| `&96` | 150 | `MERGE` | statement | ROM |
| `&97` | 151 | `VERIFY` | statement | ROM |
| `&98` | 152 | `OPEN` | statement | ROM |
| `&99` | 153 | `CLOSE` | statement | ROM |
| `&9A` | 154 | `CIRCLE` | statement | ROM |
| `&9B` | 155 | `PLOT` | statement | ROM |
| `&9C` | 156 | `LET` | statement | ROM |
| `&9D` | 157 | `BLITZ` | statement | ROM |
| `&9E` | 158 | `BORDER` | statement | ROM |
| `&9F` | 159 | `CLS` | statement | ROM |
| `&A0` | 160 | `PALETTE` | statement | ROM |
| `&A1` | 161 | `PEN` | statement | ROM |
| `&A2` | 162 | `PAPER` | statement | ROM |
| `&A3` | 163 | `FLASH` | statement | ROM |
| `&A4` | 164 | `BRIGHT` | statement | ROM |
| `&A5` | 165 | `INVERSE` | statement | ROM |
| `&A6` | 166 | `OVER` | statement | ROM |
| `&A7` | 167 | `FATPIX` | statement | ROM |
| `&A8` | 168 | `CSIZE` | statement | ROM |
| `&A9` | 169 | `BLOCKS` | statement | ROM |
| `&AA` | 170 | `MODE` | statement | ROM |
| `&AB` | 171 | `GRAB` | statement | ROM |
| `&AC` | 172 | `PUT` | statement | ROM |
| `&AD` | 173 | `BEEP` | statement | ROM |
| `&AE` | 174 | `SOUND` | statement | ROM |
| `&AF` | 175 | `NEW` | statement | ROM |
| `&B0` | 176 | `RUN` | statement | ROM |
| `&B1` | 177 | `STOP` | statement | ROM |
| `&B2` | 178 | `CONTINUE` | statement | ROM |
| `&B3` | 179 | `CLEAR` | statement | ROM |
| `&B4` | 180 | `GO TO` | statement | ROM |
| `&B5` | 181 | `GO SUB` | statement | ROM |
| `&B6` | 182 | `RETURN` | statement | ROM |
| `&B7` | 183 | `REM` | statement | ROM |
| `&B8` | 184 | `READ` | statement | ROM |
| `&B9` | 185 | `DATA` | statement | ROM |
| `&BA` | 186 | `RESTORE` | statement | ROM |
| `&BB` | 187 | `PRINT` | statement | ROM |
| `&BC` | 188 | `LPRINT` | statement | ROM |
| `&BD` | 189 | `LIST` | statement | ROM |
| `&BE` | 190 | `LLIST` | statement | ROM |
| `&BF` | 191 | `DUMP` | statement | ROM |
| `&C0` | 192 | `FOR` | statement | ROM |
| `&C1` | 193 | `NEXT` | statement | ROM |
| `&C2` | 194 | `PAUSE` | statement | ROM |
| `&C3` | 195 | `DRAW` | statement | ROM |
| `&C4` | 196 | `DEFAULT` | statement | ROM |
| `&C5` | 197 | `DIM` | statement | ROM |
| `&C6` | 198 | `INPUT` | statement | ROM |
| `&C7` | 199 | `RANDOMIZE` | statement | ROM |
| `&C8` | 200 | `DEF FN` | statement | ROM |
| `&C9` | 201 | `DEF KEYCODE` | statement | ROM |
| `&CA` | 202 | `DEF PROC` | statement | ROM |
| `&CB` | 203 | `END PROC` | statement | ROM |
| `&CC` | 204 | `RENUM` | statement | ROM |
| `&CD` | 205 | `DELETE` | statement | ROM |
| `&CE` | 206 | `REF` | statement | ROM |
| `&CF` | 207 | `COPY` | statement | ROM |
| `&D1` | 209 | `KEYIN` | statement | ROM |
| `&D2` | 210 | `LOCAL` | statement | ROM |
| `&D3` | 211 | `LOOP IF` | statement | ROM |
| `&D4` | 212 | `DO` | statement | ROM |
| `&D5` | 213 | `LOOP` | statement | ROM |
| `&D6` | 214 | `EXIT IF` | statement | ROM |
| `&D7` | 215 | `IF` | statement | ROM |
| `&D8` | 216 | `IF` | statement | ROM |
| `&D9` | 217 | `ELSE` | statement | ROM |
| `&DA` | 218 | `ELSE` | statement | ROM |
| `&DB` | 219 | `END IF` | statement | ROM |
| `&DC` | 220 | `KEY` | statement | ROM |
| `&DD` | 221 | `ON ERROR` | statement | ROM |
| `&DE` | 222 | `ON` | statement | ROM |
| `&DF` | 223 | `GET` | statement | ROM |
| `&E0` | 224 | `OUT` | statement | ROM |
| `&E1` | 225 | `POKE` | statement | ROM |
| `&E2` | 226 | `DPOKE` | statement | ROM |
| `&E3` | 227 | `RENAME` | statement | ROM |
| `&E4` | 228 | `CALL` | statement | ROM |
| `&E5` | 229 | `ROLL` | statement | ROM |
| `&E6` | 230 | `SCROLL` | statement | ROM |
| `&E7` | 231 | `SCREEN` | statement | ROM |
| `&E8` | 232 | `DISPLAY` | statement | ROM |
| `&E9` | 233 | `BOOT` | statement | ROM |
| `&EA` | 234 | `LABEL` | statement | ROM |
| `&EB` | 235 | `FILL` | statement | ROM |
| `&EC` | 236 | `WINDOW` | statement | ROM |
| `&ED` | 237 | `AUTO` | statement | ROM |
| `&EE` | 238 | `POP` | statement | ROM |
| `&EF` | 239 | `RECORD` | statement | ROM |
| `&F0` | 240 | `DEVICE` | statement | ROM |
| `&F1` | 241 | `PROTECT` | statement | ROM |
| `&F2` | 242 | `HIDE` | statement | ROM |
| `&F3` | 243 | `ZAP` | statement | ROM |
| `&F4` | 244 | `POW` | statement | ROM |
| `&F5` | 245 | `BOOM` | statement | ROM |
| `&F6` | 246 | `ZOOM` | statement | ROM |
| `&F7` | 247 | `BACKUP` | statement | MasterDOS |
| `&F8` | 248 | `TIME` | statement | MasterDOS |
| `&F9` | 249 | `DATE` | statement | MasterDOS |
| `&FA` | 250 | `ALTER` | statement | MasterBASIC |
| `&FB` | 251 | `SORT` | statement | MasterBASIC |
| `&FC` | 252 | `JOIN` | statement | MasterBASIC |
| `&FD` | 253 | `EDIT` | statement | MasterBASIC |

## Functions and operators — `&FF` and a second byte

| Token | Dec | Keyword | Role | From |
|---|--:|---|---|---|
| `&FF 26` | 38 | `EXIT PROC` | statement | MasterBASIC |
| `&FF 27` | 39 | `EXIT DO` | statement | MasterBASIC |
| `&FF 28` | 40 | `EXIT FOR` | statement | MasterBASIC |
| `&FF 29` | 41 | `LOCN` | function | MasterBASIC |
| `&FF 2A` | 42 | `RESERVED` | function | MasterBASIC |
| `&FF 2B` | 43 | `EQU` | function | MasterBASIC |
| `&FF 2C` | 44 | `TICS` | function | MasterBASIC |
| `&FF 2D` | 45 | `SHIFT$` | function | MasterBASIC |
| `&FF 2E` | 46 | `SVAL$` | function | MasterBASIC |
| `&FF 2F` | 47 | `USING$` | function | MasterBASIC |
| `&FF 30` | 48 | `TIME$` | function | MasterDOS |
| `&FF 31` | 49 | `DATE$` | function | MasterDOS |
| `&FF 32` | 50 | `INP$` | function | MasterDOS |
| `&FF 33` | 51 | `DIR$` | function | MasterDOS |
| `&FF 34` | 52 | `FSTAT` | function | MasterDOS |
| `&FF 35` | 53 | `DSTAT` | function | MasterDOS |
| `&FF 36` | 54 | `FPAGES` | function | MasterDOS |
| `&FF 37` | 55 | `SCRAD` | function | MasterBASIC |
| `&FF 38` | 56 | `INARRAY` | function | MasterBASIC |
| `&FF 3B` | 59 | `PI` | function | ROM |
| `&FF 3C` | 60 | `RND` | function | ROM |
| `&FF 3D` | 61 | `POINT` | function | ROM |
| `&FF 3E` | 62 | `FREE` | function | ROM |
| `&FF 3F` | 63 | `LENGTH` | function | ROM |
| `&FF 40` | 64 | `ITEM` | function | ROM |
| `&FF 41` | 65 | `ATTR` | function | ROM |
| `&FF 42` | 66 | `FN` | function | ROM |
| `&FF 43` | 67 | `BIN` | function | ROM |
| `&FF 44` | 68 | `XMOUSE` | function | ROM |
| `&FF 45` | 69 | `YMOUSE` | function | ROM |
| `&FF 46` | 70 | `XPEN` | function | ROM |
| `&FF 47` | 71 | `YPEN` | function | ROM |
| `&FF 48` | 72 | `RAMTOP` | function | ROM |
| `&FF 4A` | 74 | `INSTR` | function | ROM |
| `&FF 4B` | 75 | `INKEY$` | function | ROM |
| `&FF 4C` | 76 | `SCREEN$` | function | ROM |
| `&FF 4D` | 77 | `MEM$` | function | ROM |
| `&FF 4F` | 79 | `PATH$` | function | ROM |
| `&FF 50` | 80 | `STRING$` | function | ROM |
| `&FF 53` | 83 | `SIN` | function | ROM |
| `&FF 54` | 84 | `COS` | function | ROM |
| `&FF 55` | 85 | `TAN` | function | ROM |
| `&FF 56` | 86 | `ASN` | function | ROM |
| `&FF 57` | 87 | `ACS` | function | ROM |
| `&FF 58` | 88 | `ATN` | function | ROM |
| `&FF 59` | 89 | `LN` | function | ROM |
| `&FF 5A` | 90 | `EXP` | function | ROM |
| `&FF 5B` | 91 | `ABS` | function | ROM |
| `&FF 5C` | 92 | `SGN` | function | ROM |
| `&FF 5D` | 93 | `SQR` | function | ROM |
| `&FF 5E` | 94 | `INT` | function | ROM |
| `&FF 5F` | 95 | `USR` | function | ROM |
| `&FF 60` | 96 | `IN` | function | ROM |
| `&FF 61` | 97 | `PEEK` | function | ROM |
| `&FF 62` | 98 | `DPEEK` | function | ROM |
| `&FF 63` | 99 | `DVAR` | function | ROM |
| `&FF 64` | 100 | `SVAR` | function | ROM |
| `&FF 65` | 101 | `BUTTON` | function | ROM |
| `&FF 66` | 102 | `EOF` | function | ROM |
| `&FF 67` | 103 | `PTR` | function | ROM |
| `&FF 68` | 104 | `XVAR` | function | MasterBASIC |
| `&FF 69` | 105 | `UDG` | function | ROM |
| `&FF 6A` | 106 | `NVAL` | function | MasterBASIC |
| `&FF 6B` | 107 | `LEN` | function | ROM |
| `&FF 6C` | 108 | `CODE` | function | ROM |
| `&FF 6D` | 109 | `VAL$` | function | ROM |
| `&FF 6E` | 110 | `VAL` | function | ROM |
| `&FF 6F` | 111 | `TRUNC$` | function | ROM |
| `&FF 70` | 112 | `CHR$` | function | ROM |
| `&FF 71` | 113 | `STR$` | function | ROM |
| `&FF 72` | 114 | `BIN$` | function | ROM |
| `&FF 73` | 115 | `HEX$` | function | ROM |
| `&FF 74` | 116 | `USR$` | function | ROM |
| `&FF 76` | 118 | `NOT` | operator | ROM |
| `&FF 7A` | 122 | `MOD` | operator | ROM |
| `&FF 7B` | 123 | `DIV` | operator | ROM |
| `&FF 7C` | 124 | `BOR` | operator | ROM |
| `&FF 7E` | 126 | `BAND` | operator | ROM |
| `&FF 7F` | 127 | `OR` | operator | ROM |
| `&FF 80` | 128 | `AND` | operator | ROM |
| `&FF 81` | 129 | `<>` | operator | ROM |
| `&FF 82` | 130 | `<=` | operator | ROM |
| `&FF 83` | 131 | `>=` | operator | ROM |


## The slots with no name

`text.asm` writes `DB "-"+&80` for a slot it has reserved but not filled, and
those bytes are the ones an extension can claim. `tokentab.py` drops them from
the tables above; here is what each one is, since a translator has to decide
what to do when it meets one.

| Token | The ROM's comment | Now |
|---|---|---|
| `&D0` | `DRIVER` in `CMDADT` | still unused; `CMDADT` points it at `NONSENSE` |
| `&FE` | — | never used by anything |
| `&FF 49` | `UNUSED INARRAY` | still unused — MasterBASIC's `INARRAY` is `&FF 38` |
| `&FF 4E` | `UNUSED CHAR$` | still unused |
| `&FF 51` | `UNUSED USING$` | still unused — MasterBASIC's `USING$` is `&FF 2F` |
| `&FF 52` | `UNUSED SHIFT$` | still unused — MasterBASIC's `SHIFT$` is `&FF 2D` |
| `&FF 68` | `-`; calculator code `&4E`, `UNUSED` | MasterBASIC's `XVAR` |
| `&FF 6A` | `-`; calculator code `&50`, `NUMBER` | MasterBASIC's `NVAL` |
| `&FF 75` | `CORRESPONDS TO INKEY$ FPC CODE` | still unused |
| `&FF 77`–`&FF 79` | — | still unused |
| `&FF 7D` | `-` | `BXOR` — see below |
| `&FF 84` | — | still unused |

MasterBASIC did not take those last two at random. A token becomes a
floating-point calculator code by subtracting `&1A`, so `&FF 68` and `&FF 6A`
are codes `&4E` and `&50`, and `fpcmain.asm`'s dispatch table has something to
say about each. `&4E` is `DW NONSENSE ;4E UNUSED`, sitting among the entries
`eval.asm` describes as *"SIN-EOF/PTR/POS"* — a numeric argument giving a
numeric result, which is what `XVAR n` is. `&50` is `DW NONSENSE ;50 NUMBER`,
under the heading *"PRIORITY 15, STRING ARG, NUMERIC RESULT"* — which is
exactly `NVAL a$`. The ROM had reserved a string-to-number function and never
written it; `NVAL` is that function.

`&FF 7D` is the odd one. It has no name in `KEYWTAB`, so it cannot be typed and
will not be listed, but `OPPRIORT` in [eval.asm](../ref/samrom/eval.asm) gives
it priority `&C2` against the comment `;B  BXOR`, the same priority as `BOR`
and `OR`. The operation exists and the word to reach it does not.

The tech manual's own list of reserved slots names four words MGT expected a
disk BASIC to use — `SORT`, `ALTER`, `USING$`, `SHIFT$`, `INARRAY`, `NUMBER`,
`CHAR$`, `JOIN`. MasterBASIC supplies five of the eight, but at tokens of its
own choosing rather than in the reserved slots, because `HGTTK` numbers its
whole list in one run. `NUMBER` and `CHAR$` were never written.

## Four things that will catch a translator out

**`INK` is not a token.** Typing `INK` matches `KEYWTAB`'s last entry, which is
`&FF` — the function prefix wearing a second hat. `TOK42` in
[miscx2.asm](../ref/samrom/miscx2.asm) spots it and stores `&A1` (`PEN`)
instead, so `INK` is an input spelling for `PEN` and never appears in a file.

**`IF` and `ELSE` are each stored under two tokens, and the tokeniser only ever
writes one of them.** `I-F` matches `&D7` (long `IF`) because that entry comes
first in the list; the syntax-check pass then overwrites the byte in the
program with `&D8` (short `IF`) if a `THEN` follows — `LD (HL),&D8 ;SIFTOK` in
[do.asm](../ref/samrom/do.asm). `ELSE` works the same way, tokenising as `&D9`
and being rewritten to `&DA` when the `IF` it belongs to was short. Both spell
identically when listed. A translator that tokenises text must therefore write
`&D7`/`&D9` and then apply the same rewrite, or its output will not match what
the machine would have stored.

**Above `&7F` inside a string is not a token.** `PRGR80` in
[tprint.asm](../ref/samrom/tprint.asm) checks `INQUFG` and `FLAGX` first: in
quotes, or in an `INPUT LINE`, bytes `&80` and up are graphics characters —
*"QUOTES FORCES UDGS"*. `&80`–`&84` are graphics characters everywhere, even
outside quotes, since no token uses them.

**A number carries an invisible copy.** After the digits of any numeric literal
the line holds `&0E` and five bytes of floating-point form, and it is the five
bytes that get evaluated. Editing the digits without editing them both is how
`ALTER` can leave a listing that looks right and does not run — see
[masterbasic-keywords.md](masterbasic-keywords.md#alter--250--masterbasic-54ca).

## Listing a token back out

`POGEN2` in [tprint.asm](../ref/samrom/tprint.asm) decides the spaces, and
gets them from the token's range rather than from the word:

| Token range | Leading space | Trailing space |
|---|---|---|
| `&85`–`&FE`, statements and qualifiers | yes | yes |
| `&FF 3B`–`&FF 52`, immediate functions | no | only `FN` and `BIN` |
| `&FF 53`–`&FF 79`, floating-point functions | no | yes |
| `&FF 7A`–`&FF 80`, `MOD` to `AND` | yes | yes |
| `&FF 81`–`&FF 83`, `<>` `<=` `>=` | no | no |

Two qualifications on "yes". A leading space is printed only when the last
character already printed was not one — `FLAGS` bit 0, so `GO TO` after `THEN`
gets one space and not two. A trailing space is printed only when the word's
last character is a letter or `$`: `POMSG4` compares against `"A"` and then
`"$"`, which is why `VAL$` is followed by a space and `>=` would not have been.

MasterBASIC's own words go through `HPRTOK` instead, at MasterBASIC `&500E`,
which prints a leading space under the same `FLAGS` bit 0 rule and no trailing
one.
