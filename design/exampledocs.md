# Example documentation style to copy

If I was going to document part of the masterdos.asm file, I might do it like this:

```asm
; Memory constatns
MAX_INTERNAL_PAGE:        EQU &1F
PAGE_VALUE_MASK:          EQU &1F
MIN_RAMDRIVE_PAGE_TYPE:   EQU &D0
MAX_RAMDRIVE_PAGE_TYPE:   EQU &D7
SCREEN_PAGE_TYPE:         EQU &30

; Boot loader constants
FIRST_GROUP_SECTOR_COUNT: EQU &1F    ; Number of sectors to load in the first wave (DOS).

; Disk constants
MAX_SECTOR_RETRY_COUNT:   EQU 10     ; Maximum number of attempts to read a sector during boot.
SECTOR_LENGTH:            EQU 512    ; Length of a sector on disk
DISK_CMD_RESPONSE_DELAY:  EQU &14

; Registers
DISKCTL0_SIDE1_CMD:       EQU &E0
DISKCTL0_SIDE2_CMD:       EQU &E4

; Commands
DISK_RESTORE_TRACK_0_CMD: EQU &09    ; Restore to track 0; motor disable spin-up, 3ms step time
DISK_READ_SECTOR_CMD:     EQU &80    ; Reads the target sector from the disk
DISK_STEP_OUT_CMD:        EQU &7B    ; Step the disk out one track
DISK_STEP_IN_CMD:         EQU &5B    ; Step the disk in one track

; Flags
DISK_STATUS_DATA_RQ_BX:       EQU 1

DISK_STATUS_BUSY:             EQU 1
DISK_STATUS_DATA_RQ:          EQU 2
DISK_STATUS_LOST_DATA:        EQU 4
DISK_STATUS_CRC_ERROR:        EQU 8
DISK_STATUS_RECORD_NOT_FOUND: EQU 16
DISK_STATUS_RECORD_TYPE:      EQU 32
DISK_STATUS_WRITE_PROTECT:    EQU 64
DISK_STATUS_MOTOR_ON:         EQU 128

DISK_SECTOR_READ_ERROR_FLAGS: EQU DISK_STATUS_BUSY | DISK_STATUS_LOST_DATA | DISK_STATUS_CRC_ERROR


; Idioms
IN_PAGE_C:                EQU &4000  ; Some of this code is compiled to run in
                                     ; &8000 but compiled as if loaded in &4000.

               ORG  &4000

BOOT_SECTOR_START:

;; --------------------------------------------------------------------
;; The nine-byte header, which is part of the image the boot sector loads
;; rather than something stripped off it.  It is the DISCiPLE/+D header the
;; SAM DOSes inherited, which is why the execute field is never written:
;; that word is a Spectrum autostart field, and SAMDOS spent it on two page
;; bytes instead.
;;
;;     type      19, SAM CODE
;;     length    bytes within the last page, 14 bits
;;     start     the address it was saved from
;;     exec      never written; always &FFFF
;;     pages     whole 16K pages, so the length is pages*16384 + length
;;     page      the page the start address is in
;;
;; The &8000 start is where the file was saved from, not where it runs; see
;; the note at the top of this listing.  Once the DOS is running this is
;; overwritten by NSAM, the free-sector map.
;; --------------------------------------------------------------------

HEADER:
               DEFB &13                        ; 4000 type 19, SAM CODE
               DEFW &3F77                      ; 4001 length within the last page
               DEFW &8000                      ; 4003 start address
               DEFW &FFFF                      ; 4005 execute address: never written
               DEFB &01                        ; 4007 whole 16K pages, so 32631 bytes in all
               DEFB &63                        ; 4008 start page (99)

;; -----------------------------------------------------------------------------
;; BOOT entrypoint
;; 
;; Runs after the boot sector has been loaded. Resets the page allocations used
;; for RAM disks in previous DOS instances.
;; 
;; Called from MB &7B75
;; -----------------------------------------------------------------------------

BOOT:
               DI                              ; 4009 F3

; Reset the frame interrupt vector to the default ROM implementation.

               LD HL,&0000                     ; 400A 21 00 00
               LD (FRAMIV),HL                  ; 400D 22 E2 5A

               LD L,&49                        ; 4010 2E 49
               LD (BOOT_22),HL                 ; 4012 22 70 5B

; Scan the ALLOCT table and clean up RAM disk pages allocated in previous
; DOS/MasterBASIC boots.

; Point HL at last entry of internal memory page allocation table (ALLOCT)

               LD HL,ALLOCT + MAX_INTERNAL_PAGE ; 4015 21 1F 51 
ALLOCT_SCAN_LOOP:
               LD A,(HL)                       ; 4018 7E

; Is it in the RAM Drive range (&D0-&D7)?
               
               CP MIN_RAMDRIVE_PAGE_TYPE       ; 4019 FE D0
               JR C,NOT_A_RAM_DRIVE            ; 401B 38 06

               CP MAX_RAMDRIVE_PAGE_TYPE + 1   ; 401D FE D8
               JR NC,NOT_A_RAM_DRIVE           ; 401F 30 02

; Yes - this slot was a RAM drive that existed from a previous BOOT. We should
; clear its page table entry so that we don't leak memory.

               LD (HL),&00                     ; 4021 36 00

; Check the next entry.
NOT_A_RAM_DRIVE:
               DEC L                           ; 4023 2D
               JR NZ,ALLOCT_SCAN_LOOP          ; 4024 20 F2

; Find the current page running in upper memory, and subtract 1
; from it. 
               IN A,(HMPR)                     ; 4026 DB FB
               AND PAGE_VALUE_MASK             ; 4028 E6 1F
               LD L,A                          ; 402A 6F
               DEC L                           ; 402B 2D

; Note: H is still the upper-byte of the address of ALLOCT

               LD (V40F9+IN_PAGE_C),SP             ; 402C ED 73 F9 80
               LD SP,&C000                     ; 4030 31 00 C0

; Finds a free page in the ALLOCT table. It will also use a screen page
; if necessary.
; 
; Keep scanning down from the current HMPR page in the ALLOCT table until
; we hit the system page (0).

FIND_FREE_PAGE_LOOP:
               LD A,(HL)                       ; 4033 7E

; Did we find a free page (0)?
               AND A                           ; 4034 A7
               JR Z,FOUND_PAGE_FOR_DOS         ; 4035 28 09

; Did we find a screen page? If so we can use that.
               CP SCREEN_PAGE_TYPE             ; 4037 FE 30
               JR Z,BOOT_FOUND_PAGE            ; 4039 28 05
               DEC L                           ; 403B 2D
               JR NZ,FIND_FREE_PAGE_LOOP       ; 403C 20 F5

; No pages to allocate the DOS/MasterBASIC in; we hit the system page (0).
; Report out of memory.

               RST ERR_HOOK                    ; 403E CF
               DEFB ERR_OUT_OF_MEMORY          ; 403F 01 error 1, "Out of memory"

; Found a free page (00) OR screen page (C0) in L. Now load the rest of our DOS/
; MB combo into memory.

FOUND_PAGE_FOR_DOS:
               PUSH HL                         ; 4040 E5

; Find the next sector address in the file sector chain by reading it from the
; end of the boot sector. 

               LD HL,HEADER + SECTOR_LENGTH - 1 + &4000  ; 4041 21 FF 81

; Read the next sector number into E, then the track number into D.
               LD E,(HL)                       ; 4044 5E
               DEC HL                          ; 4045 2B
               LD D,(HL)                       ; 4046 56
               LD B,FIRST_GROUP_SECTOR_COUNT   ; 4047 06 1F

BOOT_READ_DOS_FILE_LOOP:
               PUSH BC                         ; 4049 C5
               XOR A                           ; 404A AF
               LD (DISK_RETRY_COUNT + IN_PAGE_C),A ; 404B 32 FD 80
               LD (SECTOR_LOAD_ADDRESS + IN_PAGE_C),HL ; 404E 22 FB 80

               LD C,DISKCTL0_COMMAND_PORT ; 4051 0E E0

; Is this track on side 1 or 2?

               BIT 7,D                         ; 4053 CB 7A
               JR Z,BOOT_SET_SECTOR            ; 4055 28 04

; It's on side 2. Clear bit 7, which indicates the side, as the disk controller
; doesn't recognize sector sides; we control which head is energized.
               RES 7,D                         ; 4057 CB BA

; Set the base disk port we're using for Side 2 access (bit 2 = disk head to
; energize, 0 = side 1, 4 = side 2)

               LD C,DISKCTL0_SIDE2_CMD         ; 4059 0E E4

; Increment C to point to the sector I/O register, and set the value to the
; requested sector.

BOOT_SET_SECTOR:
               INC C                           ; 405B 0C
               INC C                           ; 405C 0C
               OUT (C),E                       ; 405D ED 59

; Restore C to the disk status/command I/O register.
               DEC C                           ; 405F 0D
               DEC C                           ; 4060 0D

; Read the drive ctonroller ready status, and loop until it is
; ready. 
BOOT_WAIT_READY:
               IN A,(C)                        ; 4061 ED 78
               RRA                             ; 4063 1F
               JR C,BOOT_WAIT_READY            ; 4064 38 FB

; Advance C to track I/O register.
               INC C                           ; 4066 0C
; Read track register.
               IN A,(C)                        ; 4067 ED 78

BOOT_5:
; Restore C to command/status I/O register.
               DEC C                           ; 4069 0D

; Check if track read from controller matches requested track in D.
               CP D                            ; 406A BA

; Already on the correct track? Great!
               JR Z,BOOT_FOUND_TRACK          ; 406B 28 0E

; The track doesn't match. We need to step in or step out the drive head.

; Is current track higher than target? If so, step out.
               LD A,DISK_STEP_OUT_CMD          ; 406D 3E 7B
               JR NC,BOOT_STEP_DRIVE_HEAD      ; 406F 30 02

; Current track is lower than target. Step in.
               LD A,DISK_STEP_IN_CMD           ; 4071 3E 5B

BOOT_STEP_DRIVE_HEAD:
               OUT (C),A                       ; 4073 ED 79

; Delay for command to start before checking status.

               LD B,DISK_CMD_RESPONSE_DELAY    ; 4075 06 14
               DJNZ $                          ; 4077 10 FE

               JR BOOT_WAIT_READY              ; 4079 18 E6

BOOT_FOUND_TRACK:
               LD A,DISK_READ_SECTOR_CMD       ; 407B 3E 80
               OUT (C),A                       ; 407D ED 79

BOOT_WAIT_AFTER_READ_SECTOR_CMD:

               LD B,DISK_CMD_RESPONSE_DELAY    ; 407F 06 14
               DJNZ $                          ; 4081 10 FE

; Get write address for sector data
               LD HL,(SECTOR_LOAD_ADDRESS + IN_PAGE_C) ; 4083 2A FB 80

; ---- BOOT_13 ---- from MB &5A0B
BOOT_13:
               LD B,C                          ; 4086 41
               INC B                           ; 4087 04

; ---- BOOT_14 ---- from MB &5A17
BOOT_14:
               INC B                           ; 4088 04

; ---- BOOT_15 ---- from MB &5A0F
BOOT_15:
               INC B                           ; 4089 04
               JR BOOT_CHECK_READ_CMD_STATUS   ; 408A 18 08

; This loop reads the sector data one byte at a time from the disk controller.

BOOT_READ_SECTOR_DATA_LOOP:
; Set C to data register
               LD C,B                          ; 408C 48

; Read data byte that is waiting for us, and write it to the
; destination address.
               IN A,(C)                        ; 408D ED 78
               LD (HL),A                       ; 408F 77
               INC HL                          ; 4090 23

; Point C at the cmd/status register
               DEC C                           ; 4091 0D
               DEC C                           ; 4092 0D
               DEC C                           ; 4093 0D

BOOT_CHECK_READ_CMD_STATUS:

; Read command status register.

               IN A,(C)                        ; 4094 ED 78

; Is a data byte waiting for us? If so, read it.

               BIT DISK_STATUS_DATA_RQ_BX,A    ; 4096 CB 4F
               JR NZ,BOOT_READ_SECTOR_DATA_LOOP; 4098 20 F2

; Check busy bit. If it's still busy, we're still waiting for the next byte.

               RRCA                            ; 409A 0F
               JR C,BOOT_CHECK_READ_CMD_STATUS ; 409B 38 F7

; Wasn't busy. The command must have completed - successfully or not.

; Check the CRC and DATA LOST bits, and make sure that we're not busy. If all
; that is true? We completed the sector read successfully.

               AND DISK_SECTOR_READ_ERROR_FLAGS ; 409D E6 0D
               JR Z,BOOT_SECTOR_READ_SUCCESS   ; 409F 28 1F

; We didn't read successfully.

; Increment the sector read retry count.
               LD A,(DISK_RETRY_COUNT + IN_PAGE_C)              ; 40A1 3A FD 80
               INC A                           ; 40A4 3C
               LD (DISK_RETRY_COUNT + IN_PAGE_C),A              ; 40A5 32 FD 80

               PUSH AF                         ; 40A8 F5

; Every 3rd failure, seek to track 0 

               AND &02                         ; 40A9 E6 02
               JR Z,SKIP_RESTORE_TRACK_0       ; 40AB 28 08

; Do the seek.
               LD A,DISK_RESTORE_TRACK_0_CMD   ; 40AD 3E 09
               OUT (C),A                       ; 40AF ED 79

; Wait for disk controller to settle.
               LD B,DISK_CMD_RESPONSE_DELAY    ; 40B1 06 14
               DJNZ $                          ; 40B3 10 FE

SKIP_RESTORE_TRACK_0:
               POP AF                          ; 40B5 F1

; How many retries have we attempted now?

               CP MAX_SECTOR_RETRY_COUNT       ; 40B6 FE 0A

; Not too many - try to read the sector again.

               JR C,BOOT_WAIT_READY            ; 40B8 38 A7

; Too many retries.

; Page system page back into section B so that we can output an error message.

               LD A,SYSPAGE_IN_B               ; 40BA 3E 1F
               OUT (LMPR),A                    ; 40BC D3 FA

               RST ERR_HOOK                    ; 40BE CF
               DEFB ERR_LOADING_ERROR          ; 40BF 13 error 19, "Loading error"

BOOT_SECTOR_READ_SUCCESS:
               POP BC                               ; 40C0 C1

; Read next sector address from file chain at end of sector.

               DEC HL                               ; 40C1 2B
               LD E,(HL)                            ; 40C2 5E
               DEC HL                               ; 40C3 2B
               LD D,(HL)                            ; 40C4 56

; Are we at the end of the file chain?

               LD A,D                               ; 40C5 7A
               OR E                                 ; 40C6 B3
; Yes!
               JR Z,BOOT_LOAD_COMPLETE              ; 40C7 28 17

; No. Do we still have sectors to load? If so, continue. 
               DJNZ TRAMPOLINE_BOOT_READ_FILE_LOOP  ; 40C9 10 12

; We've loaded the first set of sectors (the DOS set), so
; perform some of the installation work.

               PUSH BC                              ; 40CB C5
               PUSH DE                              ; 40CC D5
               CALL INSTALL_TAIL_INTO_SYSPAGE+&4000 ; 40CD CD 60 BD
               POP DE                               ; 40D0 D1
BOOT_19:
               POP BC                          ; 40D1 C1
PTHRD:
; Get the current page we're writing to.
               POP HL                          ; 40D2 E1
               PUSH HL                         ; 40D3 E5

; Page it into the lower memory page, and continue this routine from the upper
; half.

PTHRD_1:
               LD A,L                          ; 40D4 7D
               DEC A                           ; 40D5 3D
               OR ENABLE_ROM1                  ; 40D6 F6 40
               OUT (LMPR),A                    ; 40D8 D3 FA
               LD HL,&4000                     ; 40DA 21 00 40

TRAMPOLINE_BOOT_READ_FILE_LOOP:

; Note: This is an absolute jump, so we need to adjust for being in page C, but
; compiled to run from page B. It also allows an earlier DJNZ to operate across
; a distance further than it usually can.

               JP BOOT_READ_DOS_FILE_LOOP+&4000 ; 40DD C3 49 80

; ---- BOOT_21 ---- from &40C7
BOOT_LOAD_COMPLETE:
               LD HL,PTHRD_2                   ; 40E0 21 E1 75
               LD DE,DOSBUF+&4000              ; 40E3 11 00 BC
               LD BC,&03AF                     ; 40E6 01 AF 03
               LDIR                            ; 40E9 ED B0
               IN A,(HMPR)                     ; 40EB DB FB
               AND &1F                         ; 40ED E6 1F
               DEC A                           ; 40EF 3D
               LD (L42CC+1),A                  ; 40F0 32 CD 42  patches the operand of the LD at &42CC
               XOR A                           ; 40F3 AF
               OUT (&E9),A                     ; 40F4 D3 E9
               JP DOSBUF + IN_PAGE_C           ; 40F6 C3 00 BC

; Original stack pointer when BOOT was called
STACK_POINTER_ON_BOOT:
               DEFW 0

; 16-bit address that the next sector in the boot image will be loaded to.
SECTOR_LOAD_ADDRESS:     DEFW 0

; Number of retries so far for a given sector.
DISK_SECTOR_RETRY_COUNT: DEFB &00

```