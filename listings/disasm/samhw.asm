; samhw.asm -- the SAM Coupe's ports.
;
; Nothing here belongs to MasterDOS or MasterBASIC.  It is the machine
; both of them run on, and each half used to declare whichever ports it
; happened to touch, so a port that both used was written down twice.
;
; base.asm includes this before either half, so the names exist before
; anything uses them.  What each port does is from the SAM Coupe
; Technical Manual, except the disk and printer ports, which are the
; DOS's own and described by its source.


XMPRL:         EQU  &80                        ; External memory lower port address
COMM:          EQU  &E0                        ; Disk 0 Side 0 Command Register
TRCK:          EQU  &E1                        ; Disk 0 Side 0 Track Register
SECT:          EQU  &E2                        ; Disk 0 Side 0 Sector Register
PPORT:         EQU  &E8                        ; printer data
CLUT:          EQU  &F8                        ; base of the colour look-up table: sixteen write-only 7-bit registers
STAT:          EQU  &F9                        ; read: STATUS, key rows and interrupt flags; write: line interrupt
LMPR:          EQU  &FA                        ; the page at &0000, and the two ROM switches: bit 5 set takes ROM 0 out
                                               ; from under &0000-&3FFF, where it normally sits, and bit 6 set brings
                                               ; ROM 1 in over &C000-&FFFF, where it normally is not
HMPR:          EQU  &FB                        ; the page at &8000
VMPR:          EQU  &FC                        ; the page the screen is displayed from
MIDI:          EQU  &FD                        ; MIDI in and out
KEYBOARD:      EQU  &FE                        ; read: keyboard columns; write: border, MIC and the speaker
SOUND:         EQU  &FF                        ; read: the attribute under the raster; write: sound data, the sound
                                               ; address port being &1FF
