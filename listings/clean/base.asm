; base.asm -- both halves of the image, in one assembly.
;
; masterdos.asm and masterbasic.asm are the two halves, and each is
; assembled at &4000, because that is where it runs and where its own
; labels have to land.  They cannot both hold &4000 in the output, so
; each is DUMPed to a page of its own -- pyz80 keeps ORG and DUMP apart
; for exactly this.  The 64 bytes between them, &7FC0 to &7FFF, are not
; padding anyone wrote: a half is 16320 bytes and a page is 16384.
;
; Assembling this file produces 32704 bytes.  The first 16320 are the
; DOS half and the 16320 from &4000 in are MasterBASIC's; each is
; compared with its half of the image on every build, so a fault still
; says which half it is in.
;
; THE EQUATES BELOW ARE THE ONES NEITHER HALF OWNS.  Most are names both
; halves declared, once in each file, because neither file could see the
; other; here they are said once.  The rest are four families that
; belong here whether one half uses them or both -- the hook codes, the
; DOS error codes, SAM BASIC's keyword tokens, and the
; skip-the-next-n-bytes idioms.  Every hook code is used only by MasterBASIC and every one of
; them is MasterDOS's; which half names a fact about the machine is an
; accident of what that half does.
;
; THE PEER EQUATES AT THE FOOT OF THE FILE ARE WHY THIS EXISTS.  DOS_BOOT
; used to read EQU &8009 -- a number nothing checked, which would go on
; meaning &8009 after BOOT had moved.  Written as BOOT + IN_PAGE_C it is a
; reference, and the assembler resolves it: a routine that moves now
; takes its peer equate with it.

; ---------------------------------------------------------------------
; The machine, in as much as the code needs
; ---------------------------------------------------------------------
;
; The SAM Coupe is a Z80B at 6MHz with 256K or 512K of RAM, addressed
; 16K at a time through four pages.  Two ports do the paging:
;
;   LMPR  &FA   the page at &0000, plus two switches.  The machine has
;               32K of ROM in two halves: ROM 0 sits over &0000-&3FFF
;               and is normally in, and setting bit 5 takes it out --
;               the manual calls that bit RAM0, "RAM replaces the first
;               half of the ROM".  Bit 6 is the other way round: setting
;               it brings ROM 1 in over &C000-&FFFF, and it is normally
;               out.
;   HMPR  &FB   the page at &8000
;
; So an address says nothing on its own -- &8000 is whatever page HMPR
; last named.  Almost every awkward thing in these listings follows from
; that one fact.
;
; The image is two halves of 16320 bytes, both assembled to run at
; &4000-&7FBF, in different pages.  Each sees the other at &8000-&BFBF,
; so an operand in that range is an address in the other page and is
; written with a DOS_ or MB_ prefix.  &4000 is the difference between
; the two views: a routine that hands out a pointer to itself for the
; other half to call adds &4000 to its own address, and a table entry
; with bit 15 set means "not in this page".
;
; The ROM's own variables live at &5A00-&5CFF in page 0, the system
; page, which is at &4000 when the ROM is running -- the same &4000
; both halves occupy.  Neither can simply read them.  A half either
; calls the ROM's NRRD and NRWR, which page the system page in and out
; around a single access, or it does the same thing inline.  A name
; written NAME+&4000 in an operand is that second case: the system
; page seen through the window.
;
; ---------------------------------------------------------------------
; How to read a line
; ---------------------------------------------------------------------
;
;     LD A,(DSC)              ; 451B 3A 10 41  the drive's port base
;     \_______/                 \__/ \______/  \__________________/
;      the code                 addr  the bytes  what it is for
;
; The address is where the byte sits when that half is paged at &4000.
; The bytes are the assembled instruction, so any line can be checked
; against the image by hand.
;
; A routine is introduced by a banner and, where anything calls it, by
; a line saying from where:
;
;     ; ---- TRCKP ---- from &46FE, &4751
;
; A routine with no such line is not dead code.  Several are reached
; from the ROM's system page, or from the other half, or from a copy of
; themselves somewhere else entirely; each one says so in its banner.

; Idioms.
; Some of this half is assembled at &4000 and executed at
; &8000, through the window, because the boot copies it
; there or because the ROM calls it with the pages the
; other way round.  Its own labels are what the assembler
; put them at, so reaching one from code that is running
; high means adding the 16K between the two views.
IN_PAGE_C:                      EQU  &4000                                   ; the window, less where this is assembled

; Disk controller status
DISK_STATUS_CRC_ERROR:          EQU  &08                                     ; what was read did not check out
DISK_STATUS_DRQ:                EQU  &02                                     ; a byte is waiting to be taken, or wanted
DISK_STATUS_LOST_DATA:          EQU  &04                                     ; a byte was not moved in time and is gone
DISK_STATUS_RECORD_NOT_FOUND:   EQU  &10                                     ; the sector was not on the track

; Numbers named in notes/, each for one instruction
; where the same value means something else elsewhere.
ENABLE_ROM1:                    EQU  &40                                     ; LMPR bit 6: ROM 1 in at &C000. Does not
                                                                             ; move the page in section B
SKIP_1_VIA_CP:                  EQU  &FE                                     ; CP n, skipping one byte and clobbering
                                                                             ; the flags
SKIP_1_VIA_LD_A:                EQU  &3E                                     ; LD A,n, standing here only to swallow the
                                                                             ; byte after it
SKIP_1_VIA_LD_C:                EQU  &0E                                     ; LD C,n, skipping one byte and clobbering
                                                                             ; C
SKIP_1_VIA_LD_D:                EQU  &16                                     ; LD D,n, skipping one byte and clobbering
                                                                             ; D
SKIP_1_VIA_OR:                  EQU  &F6                                     ; OR n, skipping one byte and clobbering A
                                                                             ; and the flags
SKIP_2_VIA_LD_DE:               EQU  &11                                     ; LD DE,nn, skipping two bytes and
                                                                             ; clobbering DE
SKIP_2_VIA_LD_HL:               EQU  &21                                     ; LD HL,nn, standing here only to swallow
                                                                             ; the two bytes after it -- see
                                                                             ; docs/idioms.md
SKIP_2_VIA_LD_SP:               EQU  &31                                     ; LD SP,nn, skipping two bytes and
                                                                             ; clobbering SP
SYSPAGE_IN_B:                   EQU  &1F                                     ; LMPR &1F: page 31 at &0000, so section B
                                                                             ; gets page 32, which wraps to the system
                                                                             ; page. The ROM source calls it PAGE1F
SYS_CHAR_WIDTH:                 EQU  &4AEE

; The byte after RST &08: a DOS error, or a hook code, which is
; 128 plus the index of an entry in the DOS hook table at &44A6.
; A hook code says which routine to run and the routine says
; what it does, so each line points at the one that answers it.
ERR_OUT_OF_MEMORY:              EQU  &01
ERR_NOT_FOUND:                  EQU  &02
ERR_SUBSCRIPT_WRONG:            EQU  &04
ERR_NEXT_WITHOUT_FOR:           EQU  &05
ERR_MISSING_DEF_PROC:           EQU  &0C
ERR_BREAK_INTO_PROGRAM:         EQU  &0F
ERR_LOADING_ERROR:              EQU  &13
ERR_END_OF_FILE:                EQU  &16
ERR_ARGUMENT:                   EQU  &1B
ERR_NOT_UNDERSTOOD:             EQU  &1D
ERR_INTEGER_OUT_OF_RANGE:       EQU  &1E
ERR_PUT_BLOCK:                  EQU  &25
ERR_STRING_TOO_LONG:            EQU  &2A
ERR_TRK_NNN_SCT_NN_ERROR:       EQU  &55
ERR_FORMAT_TRK_NNN_LOST:        EQU  &56
ERR_CHECK_DISK_IN_DRIVE:        EQU  &57
ERR_VERIFY_FAILED:              EQU  &5D
ERR_WRONG_FILE_TYPE:            EQU  &5E
ERR_READING_A_WRITE_FILE:       EQU  &63
ERR_WRITING_A_READ_FILE:        EQU  &64
ERR_NO_AUTO_FILE:               EQU  &65
ERR_NO_SUCH_DRIVE:              EQU  &67
ERR_DISK_IS_WRITE_PROTEC:       EQU  &68
ERR_DISK_FULL:                  EQU  &69
ERR_DIRECTORY_FULL:             EQU  &6A
ERR_FILE_NAME_USED:             EQU  &6D
ERR_STREAM_USED:                EQU  &6F
ERR_CHANNEL_USED:               EQU  &70
ERR_DIRECTORY_NOT_FOUND:        EQU  &71
ERR_DIRECTORY_NOT_EMPTY:        EQU  &72
ERR_PAGE_OVERLAP:               EQU  &76
ERR_SIZE_MISMATCH:              EQU  &77
HKC_LPRINT_BYTE:                EQU  &9A                                     ; Put one byte in the interrupt-driven
                                                                             ; printer buffer, waiting if it is full.
                                                                             ; (see HOOK_LPRINT_BYTE)
HKC_CSIZE:                      EQU  &9B                                     ; CSIZE, the manual's "Improved CSIZE
                                                                             ; command". (see HOOK_CSIZE)
HKC_SWAPCHARS:                  EQU  &9C                                     ; BLOCKS -- and the argument 0, 1 or 2 is
                                                                             ; the manual's: (see HOOK_SWAPCHARS)
HKC_PROGPREP:                   EQU  &9D                                     ; Rebuild the compile pass for a program
                                                                             ; that has changed. (see HOOK_PROGPREP)
HKC_MCHWR:                      EQU  &A7                                     ; HOOK ROUTINE TO WRITE BYTE IN A TO DISC.
                                                                             ; (see MCHWR)
HKC_MCHRD:                      EQU  &A8                                     ; HOOK ROUTINE TO READ BYTE FROM DISC. (see
                                                                             ; MCHRD)
HKC_HPRTOK:                     EQU  &A9                                     ; Hook 169, and the ROM's PRTOKV points
                                                                             ; here, so LIST and the error printer both
                                                                             ; come through it. (see HPRTOK)
HKC_HPFF:                       EQU  &AA                                     ; Hook 170: the second byte of a two-byte
                                                                             ; token has arrived. (see HOOK_HPFF)
HKC_HGTTK:                      EQU  &AB                                     ; Hook 171 -- match a keyword while
                                                                             ; tokenising. (see HGTTK)
HKC_HKLEN:                      EQU  &AC                                     ; Hook 172 -- evaluate a function. (see
                                                                             ; HKLEN)
HKC_HCMDV:                      EQU  &AD                                     ; Hook 173 -- dispatch one of MasterBASIC's
                                                                             ; commands. (see HCMDV)
HKC_RCPTCH:                     EQU  &AE                                     ; see HOOK_RCPTCH
HKC_MERGECOMPFLG:               EQU  &AF                                     ; Hook code 175, and the label is right
                                                                             ; only for its first twenty-seven bytes.
                                                                             ; (see HOOK_MERGECOMPFLG)
HKC_TOKENARG:                   EQU  &B1                                     ; Read the argument after one of
                                                                             ; MasterBASIC's keywords. (see
                                                                             ; HOOK_TOKENARG)
HKC_SKIPNAME:                   EQU  &B2                                     ; DELETE, for strings and string arrays.
                                                                             ; (see CMD_DELETE)
HKC_XVARNVAL:                   EQU  &B3                                     ; The XVAR and NVAL functions. (see
                                                                             ; HOOK_XVARNVAL)
HKC_SERSEND:                    EQU  &B4                                     ; Send one character over the serial line.
                                                                             ; (see HOOK_SERSEND)
HKC_SERRECV:                    EQU  &B5                                     ; Read one character from the serial line.
                                                                             ; (see HOOK_SERRECV)
HKC_SUBCHAR:                    EQU  &B6                                     ; Replace one character with a string on
                                                                             ; its way to the printer. (see
                                                                             ; SUBSTITUTE_PRINTER_CHAR)
HKC_COMADENT:                   EQU  &B7                                     ; Find an entry through COMAD. (see
                                                                             ; HOOK_COMADENT)
HKC_VARSPACE:                   EQU  &B8                                     ; Check the room above the variables area.
                                                                             ; (see HOOK_VARSPACE)
HKC_SETUPREGS:                  EQU  &B9                                     ; Build a routine in the ROM's code buffer.
                                                                             ; (see HOOK_SETUPREGS)

; Read from the code, not carried from a source.  MasterBASIC
; has no published source, so unlike the names above these are
; an interpretation of what the surrounding instructions do,
; given here so it can be judged.  Each is written only where
; the byte already had that value, so the file still assembles
; to the original either way.
T_BOOT:                         EQU  &E9                                     ; the BASIC keyword BOOT
T_CLEAR:                        EQU  &B3                                     ; the BASIC keyword CLEAR
T_DEVICE:                       EQU  &F0                                     ; the BASIC keyword DEVICE
T_DISPLAY:                      EQU  &E8                                     ; the BASIC keyword DISPLAY
T_INVERSE:                      EQU  &A5                                     ; the BASIC keyword INVERSE
T_MODE:                         EQU  &AA                                     ; the BASIC keyword MODE
T_OFF:                          EQU  &89                                     ; the BASIC keyword OFF
T_REF:                          EQU  &CE                                     ; the BASIC keyword REF
T_TO:                           EQU  &8E                                     ; the BASIC keyword TO

; SAM BASIC's keyword tokens, read out of the ROM's own
; token tables -- see MBTEXT.
T_AT:                           EQU  &87
T_DEF_PROC:                     EQU  &CA
T_END_PROC:                     EQU  &CB
T_LET:                          EQU  &9C
T_OVER:                         EQU  &A6
T_PRINT:                        EQU  &BB
T_STEP:                         EQU  &8F

; The machine both halves sit on, included before either of
; them so the names exist by the time anything uses one.
               INC  "samhw.asm"
               INC  "samrom.asm"

               ORG  &4000
               DUMP 0,&0000
               INC  "masterdos.asm"

               ORG  &4000
               DUMP 1,&0000
               INC  "masterbasic.asm"

; The two halves, each reaching the other.  These come after
; the INCLUDEs because they name labels the INCLUDEs define;
; pyz80's second pass is what makes that legal.

; MasterDOS reaching MasterBASIC.
MB_BUILD_TRACK_IMAGE:           EQU  BUILD_TRACK_IMAGE + IN_PAGE_C
MB_BYTE_TO_DECIMAL:             EQU  BYTE_TO_DECIMAL + IN_PAGE_C
MB_CMD_ALTER:                   EQU  CMD_ALTER + IN_PAGE_C
MB_CMD_BLITZ:                   EQU  CMD_BLITZ + IN_PAGE_C
MB_CMD_CLS:                     EQU  CMD_CLS + IN_PAGE_C
MB_CMD_COPY_SCREEN:             EQU  CMD_COPY_SCREEN + IN_PAGE_C
MB_CMD_DATE:                    EQU  CMD_DATE + IN_PAGE_C
MB_CMD_DUMP:                    EQU  CMD_DUMP + IN_PAGE_C
MB_CMD_JOIN:                    EQU  CMD_JOIN + IN_PAGE_C
MB_CMD_LINE:                    EQU  CMD_LINE + IN_PAGE_C
MB_CMD_LPRINT:                  EQU  CMD_LPRINT + IN_PAGE_C
MB_CMD_MERGE:                   EQU  CMD_MERGE + IN_PAGE_C
MB_CMD_PRINT:                   EQU  CMD_PRINT + IN_PAGE_C
MB_CMD_RECORD:                  EQU  CMD_RECORD + IN_PAGE_C
MB_CMD_REF:                     EQU  CMD_REF + IN_PAGE_C
MB_CMD_SAVE:                    EQU  CMD_SAVE + IN_PAGE_C
MB_CMD_SORT:                    EQU  CMD_SORT + IN_PAGE_C
MB_CMD_SPLIT_LINE:              EQU  CMD_SPLIT_LINE + IN_PAGE_C
MB_CMD_TIME:                    EQU  CMD_TIME + IN_PAGE_C
MB_COMPRESS_FILE:               EQU  COMPRESS_FILE + IN_PAGE_C
MB_COMPRESS_SCREEN_FILE:        EQU  COMPRESS_SCREEN_FILE + IN_PAGE_C
MB_EXPAND_FILE:                 EQU  EXPAND_FILE + IN_PAGE_C
MB_EXPR_TO_32BIT:               EQU  EXPR_TO_32BIT + IN_PAGE_C
MB_FILE_NUMBER_TO_TRACK_SECTOR: EQU  FILE_NUMBER_TO_TRACK_SECTOR + IN_PAGE_C
MB_FIND_LINE_FROM_START:        EQU  FIND_LINE_FROM_START + IN_PAGE_C
MB_FN_EQU:                      EQU  FN_EQU + IN_PAGE_C
MB_FN_INARRAY:                  EQU  FN_INARRAY + IN_PAGE_C
MB_FN_LOCN:                     EQU  FN_LOCN + IN_PAGE_C
MB_FN_RESERVED:                 EQU  FN_RESERVED + IN_PAGE_C
MB_FN_SCRAD:                    EQU  FN_SCRAD + IN_PAGE_C
MB_FN_SHIFT_S:                  EQU  FN_SHIFT_S + IN_PAGE_C
MB_FN_SVAL_S:                   EQU  FN_SVAL_S + IN_PAGE_C
MB_FN_TICS:                     EQU  FN_TICS + IN_PAGE_C
MB_FN_USING_S:                  EQU  FN_USING_S + IN_PAGE_C
MB_HCMDV:                       EQU  HCMDV + IN_PAGE_C
MB_HGTTK:                       EQU  HGTTK + IN_PAGE_C
MB_HOOK_COMADENT:               EQU  HOOK_COMADENT + IN_PAGE_C
MB_HOOK_CSIZE:                  EQU  HOOK_CSIZE + IN_PAGE_C
MB_HOOK_FARSCAN:                EQU  HOOK_FARSCAN + IN_PAGE_C
MB_HOOK_HORDER:                 EQU  HOOK_HORDER + IN_PAGE_C
MB_HOOK_HPFF:                   EQU  HOOK_HPFF + IN_PAGE_C
MB_HOOK_LPRINT_BYTE:            EQU  HOOK_LPRINT_BYTE + IN_PAGE_C
MB_HOOK_MERGECOMPFLG:           EQU  HOOK_MERGECOMPFLG + IN_PAGE_C
MB_HOOK_PROGPREP:               EQU  HOOK_PROGPREP + IN_PAGE_C
MB_HOOK_RCPTCH:                 EQU  HOOK_RCPTCH + IN_PAGE_C
MB_HOOK_SERRECV:                EQU  HOOK_SERRECV + IN_PAGE_C
MB_HOOK_SERSEND:                EQU  HOOK_SERSEND + IN_PAGE_C
MB_HOOK_SETUPREGS:              EQU  HOOK_SETUPREGS + IN_PAGE_C
MB_HOOK_SKIPNAME:               EQU  CMD_DELETE + IN_PAGE_C
MB_HOOK_SWAPCHARS:              EQU  HOOK_SWAPCHARS + IN_PAGE_C
MB_HOOK_TOKENARG:               EQU  HOOK_TOKENARG + IN_PAGE_C
MB_HOOK_VARSPACE:               EQU  HOOK_VARSPACE + IN_PAGE_C
MB_HOOK_XVARNVAL:               EQU  HOOK_XVARNVAL + IN_PAGE_C
MB_HPRTOK:                      EQU  HPRTOK + IN_PAGE_C
MB_MULTIPLY_BY_100:             EQU  MULTIPLY_BY_100 + IN_PAGE_C
MB_NEXT_SCREEN_BYTE_1:          EQU  NEXT_SCREEN_BYTE_1 + IN_PAGE_C
MB_PRINT_OPEN_FILE_COUNT:       EQU  PRINT_OPEN_FILE_COUNT + IN_PAGE_C
MB_SET_DCT_COMPILE_BITS:        EQU  SET_DCT_COMPILE_BITS + IN_PAGE_C
MB_SORT_NAMES:                  EQU  SORT_NAMES + IN_PAGE_C
MB_STAMP_WITH_DATE:             EQU  STAMP_WITH_DATE + IN_PAGE_C
MB_SUBSTITUTE_PRINTER_CHAR:     EQU  SUBSTITUTE_PRINTER_CHAR + IN_PAGE_C
MB_TRACK_SECTOR_TO_FILE_NUMBER: EQU  TRACK_SECTOR_TO_FILE_NUMBER + IN_PAGE_C
MB_WAIT_FOR_CLOCK:              EQU  WAIT_FOR_CLOCK + IN_PAGE_C

; MasterBASIC reaching MasterDOS.
DOS_BOOT:                       EQU  BOOT + IN_PAGE_C
DOS_BOOTNM:                     EQU  BOOTNM + IN_PAGE_C
DOS_CKPT:                       EQU  CKPT + IN_PAGE_C
DOS_DATDT:                      EQU  DATDT + IN_PAGE_C
DOS_DRIVE:                      EQU  DRIVE + IN_PAGE_C
DOS_ENDS:                       EQU  ENDS + IN_PAGE_C
DOS_END_OF_CHANNELS:            EQU  END_OF_CHANNELS + IN_PAGE_C
DOS_EPCOM_1:                    EQU  EPCOM_1 + IN_PAGE_C
DOS_EVAL_STRING_IF_RUNNING:     EQU  EVAL_STRING_IF_RUNNING + IN_PAGE_C
DOS_EVFINS:                     EQU  EVFINS + IN_PAGE_C
DOS_EVNAM:                      EQU  EVNAM + IN_PAGE_C
DOS_EVNUMX:                     EQU  EVNUMX + IN_PAGE_C
DOS_EXDT1_DONE:                 EQU  EXDT1_DONE + IN_PAGE_C
DOS_FFPG:                       EQU  FFPG + IN_PAGE_C
DOS_FIND_ROM_CODE:              EQU  FIND_ROM_CODE + IN_PAGE_C
DOS_FNS56:                      EQU  FNS56 + IN_PAGE_C
DOS_HEADER:                     EQU  HEADER + IN_PAGE_C
DOS_HOOK_HSAVE_1:               EQU  HOOK_HSAVE_1 + IN_PAGE_C
DOS_HOOK_SBYT:                  EQU  HOOK_SBYT + IN_PAGE_C
DOS_LBYT:                       EQU  LBYT + IN_PAGE_C
DOS_MBCOPY_7774:                EQU  MBCOPY_7774 + IN_PAGE_C
DOS_MBCOPY_778B:                EQU  MBCOPY_778B + IN_PAGE_C
DOS_MBCOPY_7829:                EQU  MBCOPY_7829 + IN_PAGE_C
DOS_NEXTST:                     EQU  NEXTST + IN_PAGE_C
DOS_OFSM_1:                     EQU  OFSM_1 + IN_PAGE_C
DOS_PARK_WORD:                  EQU  PARK_WORD + IN_PAGE_C
DOS_PLNS:                       EQU  PLNS + IN_PAGE_C
DOS_POINT:                      EQU  POINT + IN_PAGE_C
DOS_POINTC:                     EQU  POINTC + IN_PAGE_C
DOS_PORT2:                      EQU  PORT2 + IN_PAGE_C
DOS_PRINTABLE_FORM:             EQU  PRINTABLE_FORM + IN_PAGE_C
DOS_PTH1:                       EQU  PTH1 + IN_PAGE_C
DOS_PTH2:                       EQU  PTH2 + IN_PAGE_C
DOS_REPORTA:                    EQU  REPORTA + IN_PAGE_C
DOS_ROOM_LEFT_IN_SECTOR:        EQU  ROOM_LEFT_IN_SECTOR + IN_PAGE_C
DOS_SAMCNT:                     EQU  SAMCNT + IN_PAGE_C
DOS_SCFSM:                      EQU  SCFSM + IN_PAGE_C
DOS_SNPRT2:                     EQU  SNPRT2 + IN_PAGE_C
DOS_STACK_ON_ENTRY:             EQU  STACK_ON_ENTRY + IN_PAGE_C
DOS_STACK_VAR_ADDRESS:          EQU  STACK_VAR_ADDRESS + IN_PAGE_C
DOS_SVHDR:                      EQU  SVHDR + IN_PAGE_C
DOS_TEMPW1:                     EQU  TEMPW1 + IN_PAGE_C
DOS_TIMDT:                      EQU  TIMDT + IN_PAGE_C
DOS_UNPARK_WORD:                EQU  UNPARK_WORD + IN_PAGE_C
DOS_V4222:                      EQU  V4222 + IN_PAGE_C
DOS_V5000:                      EQU  V5000 + IN_PAGE_C
DOS_V7CFF:                      EQU  V7CFF + IN_PAGE_C
DOS_V7DE8:                      EQU  V7DE8 + IN_PAGE_C
DOS_V7E98:                      EQU  V7E98 + IN_PAGE_C
DOS_V7EA6:                      EQU  V7EA6 + IN_PAGE_C
DOS_V7EFC:                      EQU  V7EFC + IN_PAGE_C
DOS_V7F0D:                      EQU  V7F0D + IN_PAGE_C
DOS_V7F6B:                      EQU  V7F6B + IN_PAGE_C
DOS_V7FA5:                      EQU  V7FA5 + IN_PAGE_C
