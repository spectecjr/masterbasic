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
      JP NC,RDRSCT                    ; 45BA  no carry: a RAM disc
READ_SECTOR_LOOP:
      CALL RSSR                       ; 45BD  seek, then the read command
      CALL RDDATA                     ; 45C0  the transfer
      CALL RETRY_OR_GIVE_UP           ; 45C3
      JR READ_SECTOR_LOOP             ; 45C6  and round again
```

`TIRDXDCT` is two instructions — clear `DCT`, the disc error counter — and
then falls into `TIRD`, which the listing describes as "checks if the physical
disk device number corresponds to a RAM drive or a floppy disk. Returns carry
set if physical, no-carry if RAM drive". So the very first thing a read does
is branch between the two kinds of device, and the listing's own comment on
`&4589` says where the other one goes: "a RAM disc: copy pages instead".

`RSSR` calls `CTAS` to position, disables interrupts, and issues
`READ_SECTOR_CMD`, which the listing's own equate gives as `&80`.

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

## The other kind of drive

Both `READ_SECTOR` and `WRITE_SECTOR` branch away at their first test, and
the branch is not an error path — it is the whole of the RAM disc support:

```asm
      CALL TIRDXDCT                   ; 45B7
      JP NC,RDRSCT                    ; 45BA  drives 3 to 7 go here
```

`RDRSCT` at `&7533` is the author's own name for it, from the part of the
source `ref/masterdos/docs/ram-discs.md` calls `RAMD`, and what it does is
the design in one routine: the sector is a **memory copy**.

```asm
RDRS2:
      PUSH DE / PUSH HL / PUSH BC     ; 7544
      CALL RDADR                      ; 7547  where is that sector, in pages?
      LD BC,&0200                     ; 754A
      LD DE,DRAM                      ; 754D
      LDIR                            ; 7550
```

`RDADR` turns a track and sector into a page and an offset; `LDIR` moves the
512 bytes into the same `DRAM` buffer a floppy read would have filled. Above
that line nothing knows the difference — the reference documentation puts it
the same way: "**nothing above that level knows the difference**. A RAM disc
has a directory, a sector map, subdirectories, a name and a path exactly as a
floppy does."

One instruction in the shipped code is not in the reference source. There
`RDRSCT` runs `CALL GTBUF` straight into `LD BC,&0200`; here `SDCHK2` goes
between them, and its own comments give the test — "RET IF HL IN DRAM" and
"CY IF HL WILL CROSS PAGE BOUNDARY". A destination that would run off the end
of a page is bounced through `DRAM`; one that will not is read into the
caller's buffer directly, saving the copy. That difference is worth knowing
about generally: the reference source and this binary are the same version
but not the same build, and they drift — `DWAIT` is at `&4495` in the source
and `&4564` here, and by `&6466` the gap has grown to `&204`.

## Formatting, which the two halves do together

A read and a write both send the controller a sector command and shift bytes
through one port. Formatting is the odd one out: the controller's *write
track* command takes a whole track at once — gaps, sync fields, address marks
and all — so something has to lay that image out first, and on this machine
the two halves split the job.

`DFMT` at `&549E` is the DOS's. It steps the head in ten tracks so the
restore below it has somewhere to come back from, reads track 0 sector 1 so
the confirmation prompt can name the disk about to be destroyed — a read
error there is taken as "blank or unreadable" and the prompt skipped — and
then, for every track, does this:

```asm
      CALL GETSCR                     ; 54F0  borrow the screen
      CALL PMOA                       ; 54F3  "FORMAT DISK AT TRACK "
      LD DE,&0001                     ; 54F6  track 0, sector 1
      CALL CALLMB                     ; 54F9  PREPARE TRACK DATA
      DEFW &5352
```

**The image is built in the other page.** `&5352` is `BUILD_TRACK_IMAGE` in
MasterBASIC, and nothing in MasterBASIC calls it — the only two callers are
these, in the DOS. This is the "improved FORMAT" the manual credits
MasterBASIC with, and it is why a SAMDOS machine gets it too.

It builds IBM System 34, the format a WD177x writes:

```text
 60 x &4E                      the post-index gap
 then ten times:
     12 x &00, 3 x &F5, &FE    sync, then the ID address mark
     track, side, sector, &02  &02 is the size code for 512 bytes
      1 x &F7                  the controller writes both CRC bytes
     22 x &4E                  gap 2
     12 x &00, 3 x &F5, &FB    sync, then the data address mark
    512 x &00                  the sector body
      1 x &F7                  CRC again
     27 x &4E                  gap 3
256 x &4E                      the trailing gap
```

Three of those bytes are instructions rather than data. `&F5` makes the
controller write an `A1` with a missing clock bit and reset its CRC
generator; `&F7` makes it write the two CRC bytes it has been accumulating;
everything else goes down as itself. `WRITE_SYNC_AND_MARK` lays the twelve
zeros and three `&F5`s, and its two callers differ only in the mark they pass
in `A`.

That comes to 6306 bytes for a track that holds about 6250, and the surplus
is deliberate: the controller stops at the index hole, so the last gap has to
be longer than the space left rather than shorter.

**It is built in the screen.** `HL` starts at `&A280`, which the DOS's equate
list calls `FTADD` and marks "(SCR in section C)" — which is what `GETSCR` is
for two instructions earlier. Reading the MasterBASIC listing, beware that
the operand renders as `DOS_EXDT1_DONE`: there is a label at the peer page's
`&6280`, and a window address usually does mean the peer. Here it does not.

## The directory

There is only one directory scan in the DOS. `FDHR` at `&4B31` is behind
`DIR`, behind every file lookup, and behind finding somewhere to put a new
file, and which of those it is doing comes from a mode byte kept at `(IX+4)`
so the inner loop can test it without reloading:

| bit | |
|---|---|
| 0 | match the file number |
| 1 | collect names for a sorted listing rather than printing them |
| 2 | print a full listing, with a heading |
| 3 | match the name, honouring `*` and `?` |
| 4 | match the name, ignoring the type |
| 5 | read through `NRSAD`, rebuilding the free-sector map |
| 6 | stop at the first free entry rather than looking for a match |

While it runs it also totals the sectors used and the files on the disk and
in the current directory, remembers the first free slot in `FSLOT`, and
tracks the highest subdirectory tag in `MAXT` so that creating a
subdirectory can pick an unused one.

### The map rebuilds itself

Bit 5 is the one worth stopping on. A directory entry carries the file's own
sector map, and `NSAM` — the DOS's map of sectors in use — is *placed so that
the offsets line up*. So reading the directory can OR each entry's map into
`NSAM` as the bytes arrive, and by the end the free-sector map has been
rebuilt for nothing.

The difficulty is the entries that are free, whose maps must not be counted.
`NRSAD` solves it without a branch in the transfer loop:

```asm
NRS22:
      LD H,D                          ; 4660  NSAM MSB
      AND A                           ; 4661  Z if the entry is erased or unused
      JR NZ,NRS25                     ; 4662
      LD H,A                          ; 4664  dump data to ROM
```

`L'` counts bytes within the entry and wraps every 256; at each wrap this
looks at the first byte of the new entry and points `H'` either at `NSAM`'s
page or at **zero**. A free entry's bytes are still ORed, into ROM, where the
write does nothing. There is no time to test anything per byte — the port
numbers are patched into the `IN` and `OUT` instructions for the same reason
— so the test is hoisted to once per entry and the discard costs nothing.

### The disk's own settings

`SDTKS` at `&7455` is called after track 0 sector 1 is read, and takes three
things out of that first entry: how many directory tracks the disk has beyond
the standard four, its random identifying word, and its name.

```asm
      INC H / DEC HL                  ; 745A  byte 255 of the entry
      LD A,(HL)                       ; 745C
      ADD A,&04                       ; 745D
      LD (DTKS),A                     ; 745F
```

That encoding is the compatibility trick: a SAMDOS disk leaves the byte at
zero, which reads as four tracks, so SAMDOS disks are understood correctly by
a DOS they knew nothing about.

Comparing the random word against the one remembered for the drive is how a
disk change is spotted, and on a change the current directory is reset to the
root — the tag it held belonged to a different disk's tree. If a file is open
on the drive when the disk changes, the DOS beeps and prints `OPEN file`. It
cannot refuse, because the file may legitimately span the swap, but it can
say so.

### Writing an entry back

`SDCM` at `&6E87` writes the entry as the file is closed, and only if bit 5
of `(IX+&0C)` says it was altered. The length goes down **twice**: in the old
sixteen-bit form so that G+DOS can still read the file, and in the page form
MasterDOS uses. For the types that carry a nine-byte header the header is
subtracted first, which is the `AHL = AHL - 9` at `&6EA7`. A file that
already existed replaces its entry; a new one goes into the slot `FSLOT`
remembered.

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
      LD BC,PDIRH_1                   ; 6B13  &5C16 -- the ROM's STRMS, not this label
      AND A                           ; 6B16
      SBC HL,BC                       ; 6B17
      LD A,L                          ; 6B19
      SRL A                           ; 6B1A  two bytes per entry
      LD (SSTR1),A                    ; 6B1C
```

The operand is one to be careful with: `&5C16` is the ROM's `STRMS` in the
system page, and the DOS happens to have `PDIRH_1` at the same address, so the
listing labels it with the wrong one. The line carries a comment saying so.

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
