# A read and a write, end to end

The disc code in this image is MasterDOS's, and the listings name every
routine either half calls. What they do not do is tell the story in order.
This does: one read and one write, from the BASIC statement down to the bytes
moving through the controller, with the addresses to look them up by.

Everything here is in [disasm/masterdos.asm](../disasm/masterdos.asm) unless
it says otherwise.

## The four layers

| layer | what it deals in | where |
|---|---|---|
| hooks | a BASIC statement | `HK_HLOAD`, `HK_HSAVE`, `HK_HOPEN`, `SAMHK` |
| streams and channels | `#4`, and the ROM's channel records | `CHANNEL_FOR_STREAM`, `STRMS` |
| files | headers, directory entries, sector chains | `DCHAN`, `FSA`, the `POINT` family |
| the controller | tracks, sectors and the WD1772's ports | `READ_SECTOR`, `WRITE_SECTOR` |

Each layer knows only the one below it, and the boundaries are visible in the
listing: the hooks talk in `HKHL`/`HKBC`/`HKDE`, the channel layer in `IX`
pointing at a record, and the controller layer in nothing but a track, a
sector and a buffer address.

## Where the DOS keeps things

The annotated source lays this out and the addresses are worth having in
front of you, because a dump of a running machine is mostly these:

```
DCHAN   &7C00   the disk channel record
                  SVBC, SVDE (usually a track and sector), RFDH, SVHL,
                  SVIX, REG1, DRIVE, FLAG3, RPT, BUF, NSR
FSA     &7C13   "the 256-byte image of a directory entry"
DRAM    &7D13   "the sector buffer proper"
PTH1    &7F13   the current path for drive 1, PTH2 after it
```

`RESET_BUFFER_POINTERS` at `&4F84` is what puts `IX` on `DCHAN` and `BUF` on
`DRAM`, and everything that starts a fresh transfer comes through it. It
falls into `CLEAR_TRANSFER_COUNT`, which zeroes the two count bytes at
`(IX+&0D)` and `(IX+&0E)` — the pair `BUMP_TRANSFER_COUNT` later steps.

## A read

**1. The statement.** `LOAD` reaches `HK_HLOAD` at `&6422` through the hook
table. It resets the buffer pointers, then looks at two bits of `V42E2` to
decide which kind of load this is — one path hands off to MasterBASIC
through `CALLMB`, which is how a compressed file gets expanded on the way in.

**2. The arguments.** `HOOK_ARGS_TO_HEADER` at `&6482` unpacks the registers
the hook was called with:

```asm
      LD HL,(HKHL)                    ; 6485
      LD (HD0D1),HL                   ; 6488  START
      LD A,(HKBC)                     ; 648B
      LD (PGES1),A                    ; 648F
      LD DE,(HKDE)                    ; 6492
      RES 7,D                         ; 6496
```

That `RES 7,D` is the convention showing through: bit 15 of the address is
the caller's flag for "this is a paged address", and clearing it leaves the
address the header wants.

**3. Finding the file.** The directory is a file like any other, so this is
just reading sectors and comparing names. `FILE_TYPE_AT_POINT` at `&4F6C`
reads a type byte through `POINT` and masks it to five bits;
`CHECK_FILE_TYPE` at `&4E75` bounds it, and does it in a way worth pausing
on:

```asm
      CP &15                          ; 4E7A
      JP NC,REP13                     ; 4E7C  &15 or more: wrong type
      SUB &12                         ; 4E7F
      ADC A,&00                       ; 4E81
      JP Z,REP13                      ; 4E83
```

`SUB &12` then `ADC A,&00` separates the three SAM file types with one
subtract and one add where two comparisons would be the obvious way.

**4. A sector.** `READ_SECTOR` at `&45B7`:

```asm
      CALL TIRDXDCT                   ; 45B7  which device is this?
      JP NC,READ_WITH_ADDRESS_CHECK   ; 45BA  no carry: a RAM disc
L45BD:
      CALL RSSR                       ; 45BD  seek, then the read command
      CALL RDDATA                     ; 45C0  the transfer
      CALL RETRY_OR_GIVE_UP           ; 45C3
      JR L45BD                        ; 45C6  and round again
```

`TIRDXDCT` is two instructions — clear `DCT`, the disc error counter — and
then falls into `TIRD`, which the listing describes as "checks if the physical
disk device number corresponds to a RAM drive or a floppy disk. Returns carry
set if physical, no-carry if RAM drive". So the very first thing a read does
is branch between the two kinds of device, and the listing's own comment on
`&4589` says where the other one goes: "a RAM disc: copy pages instead". `RSSR` calls `CTAS` to
position, disables interrupts, and issues `READ_SECTOR_CMD`, which the
listing's own equate gives as `&80`.

`RETRY_OR_GIVE_UP` at `&46C6` is the loop's other half: `AND &0E` keeps the
controller's error bits, any of them leaves for the error path, and otherwise
the buffer is re-fetched and the read runs again — with the failure counted
into `DCT` on the way.

**5. The bytes.** The transfer is six instructions, and both ports are
written into their own operands before it starts:

```asm
      LD A,(DSC)                      ; 45C8  the WD1772's base port
      LD (CHECK_READ_STATUS+1),A      ; 45CB
      ADD A,DISKCTL_DATA_OFS          ; 45CE  = base + 3
      LD (READ_DATA_LOOP+1),A         ; 45D0
      JR CHECK_READ_STATUS            ; 45D3
READ_DATA_LOOP:
      IN A,(&00)                      ; 45D5  the data port, patched above
      LD (HL),A                       ; 45D7
      INC HL                          ; 45D8
CHECK_READ_STATUS:
      IN A,(&00)                      ; 45D9  the status port, patched above
      RRCA                            ; 45DB  bit 0: still busy?
      RET NC                          ; 45DC  no — the sector is done
      RRA                             ; 45DD  bit 1: a byte waiting?
      JR NC,CHECK_READ_STATUS         ; 45DE  not yet
      JR READ_DATA_LOOP               ; 45E0
```

`DSC` is described in the listing as "base port of the WD1772, with drive and
side selection in the high bits", so one byte carries the controller, the
drive and the side. The two `IN A,(&00)` are never executed as written: the
`&00` is a placeholder and the real port arrives four instructions earlier.
`SELECT_DRIVE` at `&4829` is what puts the right base there in the first
place, choosing `DISKCTL_0_BASE` or `DISKCTL_1_BASE` on the drive number
rather than keeping two copies of the code.

Notice what ends the loop: the controller does. There is no byte count — the
read stops when the status register says the sector is finished.

## A write

`WRITE_SECTOR` at `&4580` is the mirror image, with three things the read
does not need:

```asm
      CALL SELECT_DRIVE               ; 4580
      CALL DWAIT                      ; 4583  is the drive up to speed?
      CALL TIRDXDCT                   ; 4586
      JP NC,RDWSCT                    ; 4589  a RAM disc again
      DI                              ; 458C
      CALL CTAS                       ; 458D
      CALL PRECMX                     ; 4590
      LD A,(DSC)                      ; 4593
      LD (CHECK_WRITE_STATUS+1),A     ; 4596
      ADD A,DISKCTL_DATA_OFS          ; 4599
      LD C,A                          ; 459B  the data port, in C this time
      CALL GTBUF                      ; 459C
```

`DWAIT` — "make sure the drive is up to speed before a write" in the source's
own comment — has no counterpart on the read side. And the data port goes
into `C` rather than into an operand, because the write loop can use `OUTI`:

```asm
WRITE_DATA_LOOP:
      OUTI                            ; 45AC  (HL) to port C, HL up, B down
      IN A,(&00)                      ; 45AE  the status port, patched
      RRCA                            ; 45B0
      RET NC                          ; 45B1
      RRCA                            ; 45B2
      JR C,WRITE_DATA_LOOP            ; 45B3
      JR CHECK_WRITE_STATUS           ; 45B5
```

Five instructions against the read's six, because `OUTI` does the fetch, the
store and the increment in one. The asymmetry is the Z80's: there is no
instruction that reads a port into `(HL)` *and* leaves the value where the
status test can reach it.

## Following a file

A file is a chain of sectors, each holding the track and sector of the next
in `NSR`. `WRITE_AT_LINKED_SECTOR` at `&6FC0` is the step:

```asm
      LD D,(HL)                       ; 6FC0  the next track
      INC HL                          ; 6FC1
      LD E,(HL)                       ; 6FC2  and sector
      PUSH DE                         ; 6FC3
      EX DE,HL                        ; 6FC4
      CALL SWAP_TRACK_AND_SECTOR      ; 6FC5
      CALL WRIF2                      ; 6FC8
```

`SWAP_TRACK_AND_SECTOR` at `&4FCD` reads the channel's current pair out into
`DE` and puts the new one in its place, so one call both remembers where you
were and moves you on. It is built out of `GET_TRACK_AND_SECTOR` and three
instructions — the two-line accessors at `&4FBF` and `&4FC6` exist so that
the third routine can be that short.

## Streams and channels

`HK_HOPEN` at `&6B06` turns a stream number into a channel, and the
arithmetic says exactly what a stream is:

```asm
      LD HL,(HKHL)                    ; 6B0F
      DEC HL                          ; 6B12
      LD BC,&5C16                     ; 6B13  STRMS, the ROM's stream table
      SBC HL,BC                       ; 6B17
      LD A,L                          ; 6B19
      SRL A                           ; 6B1A  two bytes per entry
      LD (SSTR1),A                    ; 6B1C
```

The caller hands over a pointer *into the ROM's stream table*; subtracting
the table's base and halving gives the stream number. `CHANNEL_FOR_STREAM` at
`&7018` goes the other way, taking the displacement `STRMD` returns, treating
zero as "no channel", and adding one less than it to `CHANS`.

`FIRST_DISC_CHANNEL` at `&68AB` shows the channel record's shape: `CHANS`
plus `&1E`, with a carriage return in the first byte meaning the slot is
empty.

## Where MasterBASIC reaches in, and back out

The two halves call each other across this whole stack.

Going in, `HK_HSAVE` picks a compressor on `DVAR 154` and the file type —
`&14`, which the format documentation gives as `SCREEN$` — and calls
`MB_COMPRESS_SCREEN_FILE` or `MB_COMPRESS_FILE` through `CALLMB`. That is the
manual's three `SAVE MODE`s, implemented as one branch.

Coming out, the DOS borrows arithmetic it does not have: `PRINT_BYTE_AS_DECIMAL`
and `REPORT_PAGE_COUNT` both call `MB_BYTE_TO_DECIMAL`, and `TIME_TO_MINUTES`
calls `MB_MULTIPLY_BY_24`. `COLUMNS_FOR_DIRECTORY` at `&5C8B` reaches further
still — it takes `DCOLS` if it is set and otherwise MasterBASIC's
`SYS_CHAR_WIDTH` out of the ROM's system page, so a narrower character size
gives a wider directory listing.

And `RETURN_INTO_BC` at `&7BAC` is the pair to something on the other side:

```asm
      LD HL,(&7FFC)                   ; 7BAC  the ROM's stack pointer
      JP WRTBC                        ; 7BAF
```

It writes `BC` over the word at the ROM's saved stack pointer, so that the
pending return goes to `BC` instead. MasterBASIC does the same thing from its
own side in `STORE_BC_AT_XVAR76`. Neither half could be read as doing it
until both were named.
