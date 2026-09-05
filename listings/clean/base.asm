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
; THE EQUATES BELOW ARE THE ONES BOTH HALVES NEED.  They used to be
; declared twice, once in each file, because neither file could see the
; other.  Here they are said once.
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
;   LMPR  &FA   the page at &0000, plus two switches: bit 5 puts the
;               32K ROM 0 over &0000-&3FFF, bit 6 puts ROM 1 over
;               &C000-&FFFF
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

; Hardware ports, under the names the two source trees use.
; What each one does is from the SAM Coupe Technical Manual.
XMPRL:                          EQU  &80                                    ; External memory lower port address
STAT:                           EQU  &F9                                    ; read: STATUS, key rows and interrupt
                                                                            ; flags; write: line interrupt
LMPR:                           EQU  &FA                                    ; the page at &0000, and the two ROM
                                                                            ; switches
HMPR:                           EQU  &FB                                    ; the page at &8000
VMPR:                           EQU  &FC                                    ; the page the screen is displayed from
KEYBOARD:                       EQU  &FE                                    ; read: keyboard columns; write: border, MIC
                                                                            ; and the speaker

; SAM ROM entry points and system variables.  A page cannot
; address the variables directly -- it occupies the same
; &4000-&7FFF they live in -- so it either calls NRRD/NRWR, which
; page them in, or does the same windowing inline, which is what a
; name written here as NAME+&4000 means.
; The notes are mostly the ROM source's own words.
ANYIV:                          EQU  &5B70                                  ; ANY INTERRUPT VECTOR
BSTKEND:                        EQU  &5BC4                                  ; end of that stack
CHADD:                          EQU  &5A97                                  ; address of the character being interpreted
CHADP:                          EQU  &5A96                                  ; page holding the character being
                                                                            ; interpreted
CHANS:                          EQU  &5C4F                                  ; address of the channel information area
CLSLOW:                         EQU  &0151                                  ; clear the lower screen
CURCHL:                         EQU  &5C51                                  ; address of the current channel
CURCMD:                         EQU  &5B74                                  ; CODE OF CMD BEING EXECUTED
DELBC:                          EQU  &005F                                  ; ROM entry: a delay of BC iterations
DOSSTK:                         EQU  &5C59                                  ; stack pointer saved across a DOS call
ELINE:                          EQU  &5A94                                  ; address of the edit line
ERRSP:                          EQU  &5C3D                                  ; stack pointer to unwind to on an error
EXPEXP:                         EQU  &011E                                  ; evaluate an expression of either type
EXPNUM:                         EQU  &0118                                  ; evaluate a numeric expression at (CHADD)
EXPSTR:                         EQU  &011B                                  ; evaluate a string expression
FLAGS:                          EQU  &5C3B                                  ; bit 7 set while running, clear while
                                                                            ; syntax-checking
FRAMIV:                         EQU  &5AE2                                  ; The Frame interrupt vector - usually this
                                                                            ; reads the keyboard, and updates the frame
                                                                            ; counter.
GETCHAR:                        EQU  &0018                                  ; ROM entry: the character at CHAD, control
                                                                            ; codes skipped
GETINT:                         EQU  &0121                                  ; UNSTACK WORD FROM CALCULATOR STACK TO BC.
                                                                            ; HL=BC, A=C
GETSTR:                         EQU  &0124                                  ; pop a string descriptor: A = page, DE =
                                                                            ; start, BC = length
HLJUMP:                         EQU  &0005                                  ; JP (HL)
INCURPAGE:                      EQU  &3FF2                                  ; ! ;2* page on and wind HL back
                                                                            ; unconditionally
INSTBUF:                        EQU  &4F00                                  ; BUFFER FOR ROM1 XFER CODE, ETC. 0200H
INVERT:                         EQU  &5A54                                  ; 00/FF FOR NORMAL/INVERSE ;
IYJUMP:                         EQU  &0006                                  ; JP (IY)
JCLSBL:                         EQU  &014E                                  ; clear the whole screen if A is zero,
                                                                            ; otherwise the window
JMKRBIG:                        EQU  &010C                                  ; open A*16K + BC bytes at HL
JRECLAIM:                       EQU  &0163                                  ; close up BC bytes at HL
NEXTCHAR:                       EQU  &0020                                  ; ROM entry: step CHAD and fetch the
                                                                            ; character there
PRINT_A:                        EQU  &0010                                  ; ROM entry: print the character in A
PROG:                           EQU  &5AA0                                  ; address of the BASIC program
PROGP:                          EQU  &5A9F                                  ; page holding the BASIC program
RDKEY:                          EQU  &0169                                  ; read a key as INKEY$ does
ROM_BORDCR:                     EQU  &5C4B                                  ; VALUE TO SEND TO BORDER PORT -- the ROM
                                                                            ; calls &5C4B BORDCOL, and BORDCR is a
                                                                            ; different variable at &5C48. The name here
                                                                            ; is MasterDOS's own source's
ROM_CHKHL:                      EQU  &3FEF                                  ; Checks if HL is in the range C000-FFFF,
                                                                            ; and if so, adjusts it back into the range
                                                                            ; 8000-BFFF, and increments the upper page.
STKSTR:                         EQU  &0127                                  ; push a five-byte number from A, E, D, C, B
STREAM:                         EQU  &0112                                  ; select the stream in A
TVFLAG:                         EQU  &5C3C                                  ; television flags
WKROOM:                         EQU  &0109                                  ; open BC bytes at the end of workspace
XPTR:                           EQU  &5AA3                                  ; address of the error marker

; Idioms.
; Some of this half is assembled at &4000 and executed at
; &8000, through the window, because the boot copies it
; there or because the ROM calls it with the pages the
; other way round.  Its own labels are what the assembler
; put them at, so reaching one from code that is running
; high means adding the 16K between the two views.
IN_PAGE_C:                      EQU  &4000                                  ; the window, less where this is assembled

; The ROM's restarts, under the names its own source gives
; them.  A restart is a one-byte call to a fixed address, so
; these are those addresses.
ERR_HOOK:                       EQU  &08                                    ; report an error, or call a DOS hook: the
                                                                            ; byte after is

; Disk controller status
DISK_STATUS_CRC_ERROR:          EQU  &08                                    ; what was read did not check out
DISK_STATUS_DRQ:                EQU  &02                                    ; a byte is waiting to be taken, or wanted
DISK_STATUS_LOST_DATA:          EQU  &04                                    ; a byte was not moved in time and is gone
DISK_STATUS_RECORD_NOT_FOUND:   EQU  &10                                    ; the sector was not on the track

; Numbers named in notes/, each for one instruction
; where the same value means something else elsewhere.
ENABLE_ROM1:                    EQU  &40                                    ; LMPR bit 6: ROM 1 in at &C000. Does not
                                                                            ; move the page in section B
SKIP_1_VIA_CP:                  EQU  &FE                                    ; CP n, skipping one byte and clobbering the
                                                                            ; flags
SKIP_1_VIA_LD_A:                EQU  &3E                                    ; LD A,n, standing here only to swallow the
                                                                            ; byte after it
SKIP_2_VIA_LD_HL:               EQU  &21                                    ; LD HL,nn, standing here only to swallow
                                                                            ; the two bytes after it -- see
                                                                            ; docs/idioms.md
SYSPAGE_IN_B:                   EQU  &1F                                    ; LMPR &1F: page 31 at &0000, so section B
                                                                            ; gets page 32, which wraps to the system
                                                                            ; page. The ROM source calls it PAGE1F
SYS_CHAR_WIDTH:                 EQU  &4AEE

; The byte after RST &08: a DOS error, or a hook code, which is
; 128 plus the index of an entry in the DOS hook table at &44A6.
ERR_OUT_OF_MEMORY:              EQU  &01

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
MB_EXPR_TO_32BIT:               EQU  EXPR_TO_32BIT + IN_PAGE_C
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
MB_HK_COMADENT:                 EQU  HK_COMADENT + IN_PAGE_C
MB_HK_FARSCAN:                  EQU  HK_FARSCAN + IN_PAGE_C
MB_HK_HORDER:                   EQU  HK_HORDER + IN_PAGE_C
MB_HK_HPFF:                     EQU  HK_HPFF + IN_PAGE_C
MB_HK_MERGECOMPFLG:             EQU  HK_MERGECOMPFLG + IN_PAGE_C
MB_HK_PIXELCELL:                EQU  HK_PIXELCELL + IN_PAGE_C
MB_HK_PROGPREP:                 EQU  HK_PROGPREP + IN_PAGE_C
MB_HK_PUTARG:                   EQU  HK_PUTARG + IN_PAGE_C
MB_HK_RCPTCH:                   EQU  HK_RCPTCH + IN_PAGE_C
MB_HK_SERRECV:                  EQU  HK_SERRECV + IN_PAGE_C
MB_HK_SERSEND:                  EQU  HK_SERSEND + IN_PAGE_C
MB_HK_SETUPREGS:                EQU  HK_SETUPREGS + IN_PAGE_C
MB_HK_SKIPNAME:                 EQU  CMD_DELETE + IN_PAGE_C
MB_HK_SWAPCHARS:                EQU  HK_SWAPCHARS + IN_PAGE_C
MB_HK_TOKENARG:                 EQU  HK_TOKENARG + IN_PAGE_C
MB_HK_VARSPACE:                 EQU  HK_VARSPACE + IN_PAGE_C
MB_HPRTOK:                      EQU  HPRTOK + IN_PAGE_C
MB_MBHK_HDUMMY:                 EQU  MBHK_HDUMMY + IN_PAGE_C
MB_MULTIPLY_BY_24:              EQU  MULTIPLY_BY_24 + IN_PAGE_C
MB_NEXT_SCREEN_BYTE_1:          EQU  NEXT_SCREEN_BYTE_1 + IN_PAGE_C
MB_PRINT_OPEN_FILE_COUNT:       EQU  PRINT_OPEN_FILE_COUNT + IN_PAGE_C
MB_SET_DCT_COMPILE_BITS:        EQU  SET_DCT_COMPILE_BITS + IN_PAGE_C
MB_SORT_NAMES:                  EQU  SORT_NAMES + IN_PAGE_C
MB_STAMP_WITH_DATE:             EQU  STAMP_WITH_DATE + IN_PAGE_C
MB_SUBSTITUTE_PRINTER_CHAR:     EQU  SUBSTITUTE_PRINTER_CHAR + IN_PAGE_C
MB_WAIT_FOR_CLOCK:              EQU  WAIT_FOR_CLOCK + IN_PAGE_C

; MasterBASIC reaching MasterDOS.
DOS_BOOT:                       EQU  BOOT + IN_PAGE_C
DOS_BOOTNM:                     EQU  BOOTNM + IN_PAGE_C
DOS_BOOT_FOUND_TRACK:           EQU  BOOT_FOUND_TRACK + IN_PAGE_C
DOS_BOOT_READ_CMD_SETTLE:       EQU  BOOT_READ_CMD_SETTLE + IN_PAGE_C
DOS_BOOT_SETTLE_AFTER_READ_CMD: EQU  BOOT_SETTLE_AFTER_READ_CMD + IN_PAGE_C
DOS_BOOT_STEP_HEAD:             EQU  BOOT_STEP_HEAD + IN_PAGE_C
DOS_BOOT_STEP_SETTLE:           EQU  BOOT_STEP_SETTLE + IN_PAGE_C
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
DOS_HK_HSAVE_1:                 EQU  HK_HSAVE_1 + IN_PAGE_C
DOS_HK_SBYT:                    EQU  HK_SBYT + IN_PAGE_C
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
DOS_V7F77:                      EQU  V7F77 + IN_PAGE_C
DOS_V7FA5:                      EQU  V7FA5 + IN_PAGE_C
