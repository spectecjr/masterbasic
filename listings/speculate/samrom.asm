; samrom.asm -- the SAM ROM's entry points, variables and restarts.
;
; The other half of the machine: addresses in ROM 0 and ROM 1, and the
; system variables at &5A00-&5CFF that neither half can reach without
; paging.  Again neither half owns them, and again each used to carry a
; copy of the ones it used.
;
; base.asm includes this before either half.


; The ROM's restarts, under the names its own source gives
; them.  A restart is a one-byte call to a fixed address, so
; these are those addresses.
ERR_HOOK:       EQU  &08                       ; report an error, or call a DOS hook: the byte after is
                                               ; an error number, or a hook code from 128 up
PRINT_A:        EQU  &10                       ; print the character in A
NEXT_CHAR:      EQU  &20                       ; step CHAD and get the character there
FPCALC:         EQU  &28                       ; the floating-point calculator; the bytes after it are
                                               ; its literals, not instructions

; Entry points and system variables.  Neither half can address
; the variables directly -- both occupy the same &4000-&7FFF the
; variables live in -- so a half either calls NRRD/NRWR, which
; page them in, or does the same windowing inline, which is what
; a name written NAME+&4000 in an operand means.
; The notes are mostly the ROM source's own words.
AFTERCR:        EQU  &5A0F                     ; 0A OR NUL ACCORDING TO WHETHER AUTO LF NEEDED
ALTDISP_BOTTOM: EQU  &5C5C                     ; ALTER DISPLAY: the screen switched to at the split line LINICOLS holds
ALTDISP_TOP:    EQU  &5C5B                     ; ALTER DISPLAY: the screen shown from the top of the frame, and zero
                                               ; when there is no split
ANYI:           EQU  &0049                     ; The ROM's default maskable interrupt handler, reached through ANYIV
ANYIV:          EQU  &5B70                     ; ANY INTERRUPT VECTOR
ATTRP:          EQU  &5A45                     ; ATTR USED BY MODES 0 AND 1
ATTRT:          EQU  &5A4E                     ; attribute used by temporary colour statements
BASSTK:         EQU  &5BC6                     ; base of BASIC's GOSUB, DO and PROC stack
BEEPR:          EQU  &016F
BGFLG:          EQU  &5A34                     ; BLOCK GRAPHICS FLAG
BORDCOL:        EQU  &5C4B                     ; VALUE TO SEND TO BORDER PORT
BORDCR:         EQU  &5C48                     ; ATTRIBUTES FOR LOWER SCREEN IN MODES 1/2
BSTKEND:        EQU  &5BC4                     ; end of that stack
CEXTAB:         EQU  &5B00                     ; COLOUR IS APPLIED TO THIS DATA, SO EG. F0F0
CHAD:           EQU  &5A97                     ; address of the character being interpreted
CHADD:          EQU  &5A97                     ; address of the character being interpreted
CHADP:          EQU  &5A96                     ; page holding the character being interpreted
CHANS:          EQU  &5C4F                     ; address of the channel information area
CHARS:          EQU  &5C36                     ; address of the character set less 256
CLA:            EQU  &5AAF                     ; Current program line address (typically used for GOSUB return values).
CLAPG:          EQU  &5AAE                     ; Current program line address page value
CLSLOW:         EQU  &0151                     ; clear the lower screen
CMDADDRT:       EQU  &5BDA                     ; START OF CMD ADDR TABLE IN ROM0
CMDV:           EQU  &5AF4                     ; the ROM's command vector
COMAD:          EQU  &5BDA                     ; START OF CMD ADDR TABLE IN ROM0
COMPFLG:        EQU  &5B40                     ; FLAG BITS USED BY LABEL/FN/PROC COMPILER
CSTAT:          EQU  &5A7B                     ; address of the start of the current statement
CURCHL:         EQU  &5C51                     ; address of the current channel
CURCMD:         EQU  &5B74                     ; CODE OF CMD BEING EXECUTED
CUSCRNP:        EQU  &5A78                     ; CURRENT SCREEN PAGE
DECURPAGE:      EQU  &3FF9                     ; Adjusts H so that it points to 16KiB lower in memory, and decrements
                                               ; the HMPR page.
DELBC:          EQU  &005F                     ; ROM entry: a delay of BC iterations
DEVICE:         EQU  &5A73                     ; 0=US, 1=LS, 2=PRINTER, 3=
DEVL:           EQU  &5A06                     ; default device letter
DEVN:           EQU  &5A07                     ; default device number
DHADJ:          EQU  &5B82                     ; DOUBLE HEIGHT ADJ. 0 UNLESS BOTTOM OF DH CHAR O/PED
DKP2:           EQU  &4F00                     ; NUMBER OF KEY CODE TO DEFINE
DMPFG:          EQU  &5AB7                     ; IF NZ PRINT O/P DUMPED
DOSCNT:         EQU  &5BC3                     ; BIT 0 IS SET IF DOS IN CONTROL
DOSFLG:         EQU  &5BC2                     ; Z IF NO DOS LOADED
DOSSTK:         EQU  &5C59                     ; stack pointer saved across a DOS call
EDITV:          EQU  &5AEC                     ; vector taken by the editor
ELINE:          EQU  &5A94                     ; address of the edit line
ELINEP:         EQU  &5A93                     ; page holding the edit line
ELINP:          EQU  &5A93                     ; page holding the edit line
EPPC:           EQU  &5C49                     ; line number of the cursor line
ERRSP:          EQU  &5C3D                     ; stack pointer to unwind to on an error
EVALUV:         EQU  &5AF6                     ; vector for evaluating an expression
EXPEXP:         EQU  &011E                     ; evaluate an expression of either type
EXPNUM:         EQU  &0118                     ; evaluate a numeric expression at (CHADD)
EXPSTR:         EQU  &011B                     ; evaluate a string expression
FISCRNP:        EQU  &5C9F                     ; PAGE OF SCREEN 1
FL6OR8:         EQU  &5A35                     ; 00=6 BIT CHARS IN MODE 2, NZ=8 BIT
FLAGS:          EQU  &5C3B                     ; bit 7 set while running, clear while syntax-checking
FLAGX:          EQU  &5C71                     ; flags: bit 5 set while INPUT is in progress
FRAMES:         EQU  &5C78                     ; the frame counter, incremented 50 times a second
FRAMIV:         EQU  &5AE2                     ; The Frame interrupt vector - usually this reads the keyboard, and
                                               ; updates the frame counter.
GCM1:           EQU  &5A16
GCM2:           EQU  &5A1F
GCM3:           EQU  &5A27
GETCHAR:        EQU  &0018                     ; ROM entry: the character at CHAD, control codes skipped
GETINT:         EQU  &0121                     ; UNSTACK WORD FROM CALCULATOR STACK TO BC. HL=BC, A=C
GETSTR:         EQU  &0124                     ; pop a string descriptor: A = page, DE = start, BC = length
HDR:            EQU  &4B00                     ; HEADER LEN=50H. ALSO USED FOR PARPRO RENAME STK
HLJPI:          EQU  &01C7                     ; ROM entry: jump to the address in HL
HLJUMP:         EQU  &0005                     ; JP (HL)
HUDG:           EQU  &5C7D                     ; The high UDG range start pointer (for chars 169+).
INCURPAGE:      EQU  &3FF2                     ; ! ;2* page on and wind HL back unconditionally
INCURPDE:       EQU  &3FEB                     ; Increments the upper RAM page, adjusting DE to make sure it's not in
                                               ; the range C000-FFFF. Uses A, alters D.
INDOPFG:        EQU  &5ABD                     ; INDENTED O/P FLAG
INP2:           EQU  &4F49
INQUFG:         EQU  &5ABA                     ; IN QUOTES FLAG. BIT 0=1 IF IN QUOTES. OUTLINE ZEROS
INSLV:          EQU  &5BBA                     ; The BASIC ROM's Block-Move Vector, which can be patched to implement
                                               ; faster block-moves.
INSTBUF:        EQU  &4F00                     ; BUFFER FOR ROM1 XFER CODE, ETC. 0200H
INSTHASH:       EQU  &5A05                     ; NORMALLY '#'
INVERT:         EQU  &5A54                     ; 00/FF FOR NORMAL/INVERSE ;
IXJUMP:         EQU  &002D                     ; ROM entry: jump to the address in IX
IYJUMP:         EQU  &0006                     ; JP (IY)
JCLSBL:         EQU  &014E                     ; clear the whole screen if A is zero, otherwise the window
JGTTOK:         EQU  &018A                     ; match text at DE against the keyword list at HL+1
JMKRBIG:        EQU  &010C                     ; open A*16K + BC bytes at HL
JMODE:          EQU  &015A                     ; Set screen MODE that is in the A register (0-3 gives MODEs 1-4).
JNCHAR:         EQU  &0184                     ; Call SCREEN$ subroutine. Try to match a character at the provided line
                                               ; and column.
JPFSTRS:        EQU  &017E                     ; Create ASCII version of number on floating-point calculator stack in
                                               ; buffer at 5BA0H. On exit, DE holds 5BA0H and BC holds the number of
                                               ; characters in the buffer.
JRECLAIM:       EQU  &0163                     ; close up BC bytes at HL
J_FARLDDR:      EQU  &0130                     ; Jump table entry for FARLDDR, which copies data using LDDR. A, H, L
                                               ; hold the source page and address, C, D, E hold the destination.
                                               ; PAGCOUNT/MODCOUNT are the number of bytes.
J_FARLDIR:      EQU  &012D                     ; MOVE (PAGCOUNT/MODCOUNT) BYTES FROM PAGE A, HL TO PAGE C, DE, USING
                                               ; LDIR
J_GRCOMP:       EQU  &0187                     ; GRAPHIC COPY SR
J_HEAPROOM:     EQU  &0106                     ; (4200H TO ABOUT 4A00H)
J_SBUFFET:      EQU  &012A                     ; UNSTACK STRING PARAMS AND COPY TO BUFFER IN SYS PAGE. ERROR IF >255
                                               ; BYTES
KCUR:           EQU  &5A9A                     ; address of the cursor in the edit line
KURCHAR:        EQU  &5A01                     ; CURSOR CHARACTERS - LOWER CASE/UPPER CASE
LDSTRT:         EQU  &E679
LINICOLS:       EQU  &5600                     ; per-line colour data for the current screen
LISTSP:         EQU  &5C3F                     ; stack pointer saved before an automatic listing
LPTPRT1:        EQU  &5A10                     ; PRINTER CONTROL PORT/01H STROBE VALUE
LSPTR:          EQU  &5B8B                     ; LINE SCAN PTR
LWRHS:          EQU  &5A3C                     ; Lower-window right-hand side boundary
M23LSC:         EQU  &5A30                     ; M2/3 LOWER SCREEN COLOURS
M23PAPP:        EQU  &5A48                     ; NIBBLES OR DOUBLE BITS MATCH
MNIP:           EQU  &5BDE                     ; ADDR OF MAIN I/P ROUTINE
MNOP:           EQU  &5BDC                     ; ADDR OF MAIN O/P ROUTINE
MODCOUNT:       EQU  &5B84                     ; MOD 16K COUNTER USED BY FARLDIR
MODE:           EQU  &5A40                     ; screen mode, 0 to 3
MTOKV:          EQU  &5AFA                     ; vector for matching a keyword while tokenising
NEXTCHAR:       EQU  &0020                     ; ROM entry: step CHAD and fetch the character there
NRREAD:         EQU  &00AC                     ; ROM entry: read a byte of a system variable
NRWRITE:        EQU  &000D                     ; ROM entry: write a byte of a system variable
NUMBER:         EQU  &00A2                     ; Skips an embedded invisible 6-byte number form (if present) and returns
                                               ; the next character.
NUMEND:         EQU  &5A85                     ; address of the end of the numeric variables
NUMENDP:        EQU  &5A84                     ; NUMEND/NVARS/DATADD MUST BE IN ORDER
NVARS:          EQU  &5A88                     ; address of the numeric variables
NVARSP:         EQU  &5A87                     ; page holding the numeric variables
OPSTORE:        EQU  &5AB5                     ; operator store used by the expression evaluator
OUTLINC:        EQU  &08D2
OVERF:          EQU  &5BB9                     ; 'SAVE OVER' FLAG. 0 IF SAVE OVER, ELSE NZ
PAGCOUNT:       EQU  &5B83                     ; PAGE COUNTER USED BY FARLDIR
PAGER:          EQU  &5BE0                     ; RESERVED FOR PAGING S.R
PALTAB:         EQU  &55D8                     ; the sixteen CLUT entries, as the ROM's copy
PATOUT:         EQU  &5BD2                     ; ADDR OF 'PRINTABLE CHARS' O/P
PPC:            EQU  &5C45                     ; line number of the statement being run
PRAMTP:         EQU  &5CB4                     ; LAST PAGE PRESENT IN MACHINE
PRINTSTR:       EQU  &0013                     ; ROM entry: print BC characters from (DE)
PRINT_A:        EQU  &0010                     ; ROM entry: print the character in A
PRMAIN:         EQU  &01CC                     ; Main ROM Print routine entrypoint. Prints the character in A.
PROG:           EQU  &5AA0                     ; address of the BASIC program
PROGP:          EQU  &5A9F                     ; page holding the BASIC program
PRPTR:          EQU  &5AA9                     ; Proc address (see PRPTRP)
PRPTRP:         EQU  &5AA8                     ; Proc page (see PRPTR)
PRRHS:          EQU  &5A0E                     ; PRINTER RHS LIMIT - 79
PRTOKV:         EQU  &5ADE                     ; vector for printing a keyword token
PSLD:           EQU  &5A06                     ; DEVICE LETTER/NUMBER
RAMTOP:         EQU  &5CB2                     ; last address BASIC may use
RAMTOPP:        EQU  &5CB1                     ; page holding RAMTOP
RDKEY:          EQU  &0169                     ; read a key as INKEY$ does
REFFLG:         EQU  &5A76                     ; Z IF REF VAR BEING WORKED ON
ROM_BORDCR:     EQU  &5C4B                     ; VALUE TO SEND TO BORDER PORT -- the ROM calls &5C4B BORDCOL, and BORDCR
                                               ; is a different variable at &5C48. The name here is MasterDOS's own
                                               ; source's
ROM_CHKHL:      EQU  &3FEF                     ; Checks if HL is in the range C000-FFFF, and if so, adjusts it back into
                                               ; the range 8000-BFFF, and increments the upper page.
ROM_DCT:        EQU  &5BB6                     ; DISC ERROR COUNTER
ROM_DMPTL:      EQU  &5A2D
ROM_DPVARS:     EQU  &5A12
ROM_TEMPW1:     EQU  &5AC8                     ; Temporary word storage in system page (word #1)
RST28V:         EQU  &5AF0                     ; vector taken by the calculator before each literal
RST8V:          EQU  &5AEE                     ; vector taken by RST &08 before the ROM handles it
SAVARS:         EQU  &5A82                     ; ;SAVARS/NUMEND/NVARS MUST BE IN ORDER
SAVARSP:        EQU  &5A81                     ; page holding the string and array area
SCPTR:          EQU  &5C9D                     ; ADDR OF CURRENT SCREEN IN SCLIST
SCRNBUF:        EQU  &5188                     ; Eight bytes at &5188. The ROM's source gives the address two names:
                                               ; NMISTK, the stack used for non-maskable interrupts, and SCRNBUF, "8
                                               ; BYTES USED BY SCREEN$ FOR COMP. FORM". SCRNBUF is the one this listing
                                               ; needs -- PRINT_MAGNIFIED_CHAR builds a character cell there and knows
                                               ; it is full when the pointer reaches CHARSVAL at &5190.
SETCHADP:       EQU  &3FCE                     ; Sets the CHADP (current character) page, disables ROM1, and then pages
                                               ; it in to upper memory.
SLDEV:          EQU  &5BB7                     ; DEVICE LETTER/NUMBER (TEMP)
SOFFCT:         EQU  &5AC4                     ; COUNTER FOR SCREEN OFF
SPOSNL:         EQU  &5A6E                     ; SCREEN POSN (LOWER) 0,19 AFTER CLS
SPSTORE:        EQU  &5AD2                     ; SP STORE EXCLUSIVE TO INTERRUPTS
SREAD:          EQU  &3FBB                     ; SELECT SCREEN, ROM1 OFF
STKEND:         EQU  &5C65                     ; end of the calculator stack
STKSTR:         EQU  &0127                     ; push a five-byte number from A, E, D, C, B
STREAM:         EQU  &0112                     ; select the stream in A
STRLOCN:        EQU  &5BBC                     ; USED BY LOOKVARS
STRM16NM:       EQU  &5B76                     ; TLBYTE/NAME OF VAR THAT STREAM 16 WRITES TO
STRMS:          EQU  &5C16                     ; the table of streams; stream zero first
SUBPPC:         EQU  &5C47                     ; number of that statement within its line
TEMPB2:         EQU  &5ACF                     ; Temporary byte storage in system page (byte #2)
TSURPG:         EQU  &3FDF                     ; Sets the upper memory area to the page in A (from 0-31). Bits 7-5 of
                                               ; the port are read in and preserved.
TVDATA:         EQU  &5BBE                     ; the parameters of a control code being collected
TVFLAG:         EQU  &5C3C                     ; television flags
UNSTLEN:        EQU  &3F8C                     ; ! ;1* split the calculator stack top into a page count and an offset
UWBOT:          EQU  &5A3B                     ; STARTS AT 18 (19 LINES IN UPPER, 2 IN LOWER SCR, 9 PIX)
UWLHS:          EQU  &5A39                     ; STARTS AT 0
UWRHS:          EQU  &5A38                     ; STARTS AT 31
WINDRHS:        EQU  &5A56                     ; right-hand column of the current window
WKROOM:         EQU  &0109                     ; open BC bytes at the end of workspace
WORKSP:         EQU  &5A91                     ; address of the workspace
WORKSPP:        EQU  &5A90                     ; page holding the workspace
XPTR:           EQU  &5AA3                     ; address of the error marker
XPTRP:          EQU  &5AA2                     ; page holding the error marker
