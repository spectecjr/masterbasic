# How MasterBASIC adds keywords to SAM BASIC

Every step below is in [disasm/masterdos.asm](../disasm/masterdos.asm) and
[disasm/masterbasic.asm](../disasm/masterbasic.asm), where the routines named
here carry the same commentary. The scheme is MasterDOS's, described in
[ref/masterdos/docs/functions.md](../ref/masterdos/docs/functions.md); what
follows is what MasterBASIC does with it.

## The problem

SAM BASIC's tokeniser works from tables in ROM. A DOS can claim a token the ROM
already has — that is all SAMDOS could do — but it cannot add a word to the
ROM's tables. MasterDOS gets around this by repointing four ROM vectors at boot,
and MasterBASIC takes three of the four over:

| ROM vector | Address | Hook | Points at |
|---|---|---|---|
| `PRTOKV` | `&5ADE` | 169 | `HPRTOK`, MasterBASIC `&500E` — print one of our tokens |
| `MTOKV` | `&5AFA` | 171 | `HGTTK`, MasterBASIC `&4FB7` — match one of our keywords |
| `EVALUV` | `&5AF6` | 172 | `HEVV`, MasterDOS `&7893` — evaluate one of our functions |
| `CMDV` | `&5AF4` | 173 | `HCMDV`, MasterBASIC `&4E96` — dispatch one of our commands |

A vector cannot point straight at either page, because neither is mapped when
BASIC is running. So each holds the address of a short stub planted in the ROM's
own system page at `&4BA0` — copied there from `&7B8C` in the MasterBASIC page —
and the stub does the reaching:

```
               CP &F7                          ; a command token of ours?
               RET C                           ; no: leave it to the ROM
               POP HL
               LD HL,(&5AA3)
               RST &08
               DEFB HK_HPRTOK                  ; = 169
               RET
```

`RST &08` with a code of 128 or more is the DOS's hook interface: the ROM pages
the DOS in and calls it at page offset `&0200`, and `HOOK` doubles the code to
index `SAMHK`, the hook table at `&44A6`. MasterBASIC's routines live in the
*other* page again, so their `SAMHK` entries have bit 15 set — see [Reaching the
other page](#reaching-the-other-page) below.

Each stub filters before it fires, so the ROM keeps its own work: the one above
passes only tokens from `&F7` up, and the `EVALUV` stub only `&21`–`&25`.
`EVALUV` still lands on MasterDOS's own evaluator, `HEVV`: MasterBASIC did not
need to replace it.

`SAMHK` runs to 58 entries here, codes 128–185. MasterDOS 2.3 has 47, so
MasterBASIC has added eleven hooks of its own at 175–185.

## Tokenising: `HGTTK`

The ROM calls hook 171 for any word its own tables did not recognise.

```
HGTTK:         LD C,&FB                        ; save HMPR
               IN B,(C)
               PUSH BC
               XOR A
               OUT (URPORT),A                  ; HMPR := 0
               LD HL,GTDT
               LD DE,&8F00                     ; the ROM's workspace at &4F00
               LD BC,&000E
               LDIR                            ; plant the fourteen-byte stub
               IN A,(LRPORT)
               INC A
               AND &1F
               OUT (URPORT),A                  ; my page at &8000 as well as &4000
               CALL CALLDOS
               DEFW &788E
               LD HL,&90D6                     ; MBKEYS-2, as seen at &8000
               LD A,&1D                        ; 29 = names + 1
               CALL CMR
               DEFW JGTTOK                     ; the ROM's own matcher
```

Two paging tricks in nine instructions. The keyword list has to be visible to
ROM code, which can only be trusted with `&8000`–`&BFFF`, so `HMPR := LMPR+1`
puts this page there as well as at `&4000` — and that is why the list is reached
as `&90D6` rather than `&50D6`. And the stub `GTDT` is copied into the ROM's own
workspace, for the reason in the next section.

The matching itself is the ROM's `GETTOKEN`, reached through the jump table at
`&018A`. It returns 1 for the first name in the list, 2 for the second, and so
on, or Z if nothing matched.

## Turning an index into a token

```
               CP &16
               JR NC,HGTTK_DONE                     ; 22 and up: a command
               EX DE,HL
               AND A
               SBC HL,DE
               ADD A,&25                       ; functions: index + &25
               CP &39
               JR C,HGTTK_DONE2                      ; &26-&38, carry set
               CP &3A
               CCF
               ADC A,&2F                       ; index 20, 21 -> &68, &6A
               SCF
               JR HGTTK_DONE2
HGTTK_DONE:         ADD A,&A6                       ; commands
HGTTK_DONE2:         PUSH AF
               POP BC                          ; token in B, flags in C
               RET
```

Carry out means "this is a function", which needs an `&FF` prefix in front of
the token. For commands the ROM's own tokeniser adds `&3B` to what comes back,
so `index + &A6 + &3B` = `index + &E1`, putting the first command at 247.

That the arithmetic is read correctly is not a matter of trust: the six command
entries in `CTAB` sit at tokens `&F7`–`&FC`, which is exactly where indices
22–27 land, and the seven function tokens `&30`–`&36` are the ones MasterDOS
already used for the same seven names.

## The `&FF` prefix

The ROM's tokeniser has no provision for a two-byte token from outside its own
tables. `GTDT` is the fourteen bytes that get around it:

```
GTDT:          POP IY
               LD BC,&0011                     ; 17
               ADD IY,BC                       ; 17 bytes into the tokeniser
               POP DE
               ADD HL,DE
               EX DE,HL
               LD (HL),&FF                     ; the function prefix
               JP (IY)
```

Copied into the ROM's workspace and entered from there, it writes the `&FF` into
the BASIC line itself and rejoins the tokeniser seventeen bytes further on, past
the point where the ROM would have written a single-byte token. MasterDOS plays
the same trick with its own `GTDT`; MasterBASIC's is byte-identical.

## The tokens

`MBKEYS`, at `&50D8` in the MasterBASIC page, holds the 28 names, each ended by
bit 7 of its last character, in the order `HGTTK` numbers them.

| # | Keyword | Token | | # | Keyword | Token |
|---|---|---|---|---|---|---|
| 1 | `EXIT PROC` | `FF 26` | | 15 | `FSTAT` | `FF 34` |
| 2 | `EXIT DO` | `FF 27` | | 16 | `DSTAT` | `FF 35` |
| 3 | `EXIT FOR` | `FF 28` | | 17 | `FPAGES` | `FF 36` |
| 4 | `LOCN` | `FF 29` | | 18 | `SCRAD` | `FF 37` |
| 5 | `RESERVED` | `FF 2A` | | 19 | `INARRAY` | `FF 38` |
| 6 | `EQU` | `FF 2B` | | 20 | `XVAR` | `FF 68` |
| 7 | `TICS` | `FF 2C` | | 21 | `NVAL` | `FF 6A` |
| 8 | `SHIFT$` | `FF 2D` | | 22 | `BACKUP` | 247 |
| 9 | `SVAL$` | `FF 2E` | | 23 | `TIME` | 248 |
| 10 | `USING$` | `FF 2F` | | 24 | `DATE` | 249 |
| 11 | `TIME$` | `FF 30` | | 25 | `ALTER` | 250 |
| 12 | `DATE$` | `FF 31` | | 26 | `SORT` | 251 |
| 13 | `INP$` | `FF 32` | | 27 | `JOIN` | 252 |
| 14 | `DIR$` | `FF 33` | | 28 | `EDIT` | 253 |

Three of these are slots the SAM ROM reserved and never used, and MasterBASIC
has filled them with the very names the ROM's own source pencils in against
them — `text.asm` writes `DB "-"+&80 ; UNUSED INARRAY` at `&38`, and leaves
`&68` and `&6A` blank in the floating-point list where `XVAR` and `NVAL` now
sit. Seven more, `TIME$` through `FPAGES` at `&30`–`&36`, are MasterDOS's own,
kept at the values MasterDOS gave them so that a program written for the DOS
alone still tokenises the same way. `SCRAD` at `&37` is a name MasterDOS's
source has commented out; MasterBASIC has finished it.

What each of the 28 keywords actually does is in
[masterbasic-keywords.md](masterbasic-keywords.md).

## Listing: `HPRTOK`

Hook 169, at MasterBASIC `&500E`, is the other end of the same mapping: `LIST`
and the error printer hand it a token and it prints the name. `SUB &E1` turns a
command token back into its index into `MBKEYS`, undoing the `+ &A6` and the
ROM's `+ &3B` in one step.

## Running a command

Two routes, depending on which table the token is in.

**Through `CMDV`.** Hook 173, at MasterBASIC `&4E96`, is where the ROM sends a
statement it could not run. It reads the ROM's `COMAD`, records the token in
`CURCMD`, and indexes a table by token minus `&90`.

**Through `CTAB`.** The DOS's own command table at `&42EB` — a count byte, then
three bytes per entry, a token and an address. `SYNTAX` walks it with the token
in A; the last entry's token is zero, which nothing matches, so an unrecognised
statement always ends on `CNF`.

MasterBASIC has both taken commands over and added its own here:

| Token | Command | Runs in |
|---|---|---|
| `&8C` | `LINE` | MasterBASIC `&6117` |
| `&94` | `SAVE` | MasterBASIC `&63E6` |
| `&96` | `MERGE` | MasterBASIC `&5169` |
| `&9D` | `BLITZ` | MasterBASIC `&5AD4` |
| `&9F` | `CLS` | MasterBASIC `&71A4` |
| `&BB` | `PRINT` | MasterBASIC `&5641` |
| `&BC` | `LPRINT` | MasterBASIC `&5578` |
| `&BF` | `DUMP` | MasterBASIC `&67F0` |
| `&CE` | `REF` | MasterBASIC `&5662` |
| `&EF` | `RECORD` | MasterBASIC `&5BD8` |
| 247 | `BACKUP` | MasterDOS's own `BACKUP` |
| 248 | `TIME` | MasterBASIC `&486A` |
| 249 | `DATE` | MasterBASIC `&485B` |
| 250 | `ALTER` | MasterBASIC `&54CA` |
| 251 | `SORT` | MasterBASIC `&460B` |
| 252 | `JOIN` | MasterBASIC `&6DFC` |

`BACKUP` is the one command MasterDOS already implemented, and MasterBASIC has
left it alone. `EDIT`, token 253, is in `MBKEYS` but not in `CTAB`, so it is
reached through `CMDV` rather than through the DOS.

Fifteen entries are MasterDOS's, unchanged: `WRITE`, `DIR`, `FORMAT`, `ERASE`,
`MOVE`, `LOAD`, `OPEN`, `CLOSE`, `CLEAR`, `READ`, `COPY`, `RENAME`, `CALL`,
`PROTECT` and `HIDE`. One more is odd: the first entry in the table carries
token `&2F`, which is `USING$` — a *function* token — and points into the
MasterBASIC page at `&6E62`. I have not worked out how `SYNTAX` comes to be
handed it.

## Reaching the other page

Both dispatch tables use the same convention, and `INDJP` at MasterDOS `&78CD`
implements it:

```
INDJP:         LD H,&00
               ADD HL,DE                       ; DE = table, L = 2 * index
               LD E,(HL)
               INC HL
               LD D,(HL)
               EX DE,HL
               BIT 7,H
               JR NZ,BUILD_PUT_BLOCK_5                     ; bit 15: the other page
               JP (HL)                         ; this page: go straight there
BUILD_PUT_BLOCK_5:         RES 7,H
               LD (V78E2),HL                   ; patch the DEFW below
               EXX
               CALL CALLMB
V78E2:         DEFW &0000
               RET
```

`CTAB` does the same thing inline. With bit 15 cleared, what is left is the
address as the *other* page numbers it — both pages run at `&4000`–`&7FBF` — and
`CALLMB` gets there:

```
CALLMB:        LD IY,(&7FFC)                   ; the ROM's stack pointer
               EXX
               POP HL                          ; the DEFW after the call
               LD E,(HL)
               INC HL
               LD D,(HL)
               INC HL
               PUSH HL
               LD C,&FA                        ; LMPR
               IN B,(C)
               LD H,&00                        ; <- patched at boot
               OUT (C),H
               ...
```

The `&00` is a placeholder. The boot sector pokes the other page's number, less
one, into it once it has found a free page — `LD A,L / DEC A / LD (&82CD),A` in
the installer for the DOS's copy, and `LD (&42CD),A` in the boot sector for
MasterBASIC's. After that, `CALLMB` in the DOS pages MasterBASIC in at `&4000`
and jumps to it, and `CALLDOS` in MasterBASIC does the reverse. Each returns
through a stub that puts LMPR back.

## The routines the pages call each other's work through

Both halves carry the same small set of helpers, MasterBASIC's copied from
MasterDOS. They account for most of the calls in either listing.

| MasterDOS | MasterBASIC | |
|---|---|---|
| `CMR` `&7BB2` | `CMR` `&44F0` | `CALL CMR / DEFW addr` — call the main ROM |
| `CALLMB` `&42BD` | `CALLDOS` `&42BD` | call the other page |
| `NRRDD` `&5053` | `NRRDD` `&455F` | `CALL NRRDD / DEFW var` — read a ROM variable into BC |
| `NRRD` `&505E` | `NRRD` `&456A` | read a byte into A |
| `NRWRD` `&5069` | `NRWRD` `&4577` | write BC |
| `NRWR` `&5074` | `NRWR` `&4582` | write A |
| `GTHL` `&50D9` | `GTHL` `&45E1` | fetch the inline word and step past it |

The `NR` family exists because a page cannot simply address the ROM's system
variables: it occupies the same `&4000`–`&7FFF` they live in. The primitives set
`HMPR` to 0 and move the address into the `&8000`–`&BFFF` window — `SET 7,H`
then `RES 6,H`, so `&5A97` is reached as `&9A97` — then put `HMPR` back.

This is also why the disassembly can name so many ROM addresses: an inline
parameter is always a ROM address, and MasterDOS's own source gives the names.
See [disassembly.md](disassembly.md).
