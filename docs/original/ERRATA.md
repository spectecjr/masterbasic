# ERRATA

(From the MasterBASIC installer)

## Found by reading the code (not from the installer)

On the "Screen dumps" page, `DUMP 1,2` is **double width, single**
**height**, not the other way round, and `DUMP 3,1` is single width,
treble height. The two magnifications are exchanged for an upright dump.
They are as documented for a sideways one, which is what `DUMP 3` and
anything in MODE 3 get -- so the MODE 3 advice on the same page ("`DUMP
1,2` or `DUMP 2,3` can be used to reduce the width relative to the
height") is correct as it stands.

Measured from the printer stream: see `docs/bugs.md` 5.

## Late News

User Manual p. 16, program line 30 should read `JOIN TO a$,b$`.

On p. 49, the initial value of `XVAR 9` is now 20.

On page 51, the byte sequence for `MODMSG1` should be `4,27,82,3,35,0,0,0`.

`[ESC]` + `[TAB]` can be used as a more powerful form of `[ESC]` that is
less drastic than pressing the `[BREAK]` button.
