"""What the DOS's "serial" names turn out to mean.

Written while checking this image against the SAM Comms Interface
manual and the SCC2691 datasheet, on the reasonable assumption that
MasterDOS's SER2 part and its MIN and MOUT equates -- commented
"serial input port" and "serial output port" in the original source --
drove that hardware.  They do not.  Neither half of this image
addresses the Comms Interface at all, and the two names are not port
numbers.  The evidence is set out in OPSR_DOC below, which goes into
the listing so that the next reader does not repeat the search.
"""

OPSR_DOC = """\
OPSR -- read the access mode at the end of an OPEN.

    OPEN #4;"file" IN     &FF &60   the ROM's IN token
    OPEN #4;"file" OUT    &E0       the ROM's OUT token
    OPEN #4;"file" RND    &FF &3C   the ROM's RND function token

The mode is stored in FSTR1 as MIN, MOUT or MRND, and OUT is what a
filespec with nothing after it gets.  RND is spelled with the function
token for RND because the ROM has no keyword closer to the meaning to
borrow, which is also why the test for it sits under the &FF prefix
with IN rather than beside OUT.

MasterBASIC has rewritten the head of this routine: where MasterDOS
tested for &0D and ":" inline, this calls a helper that does both, so
the annotated source's description of it is not carried automatically.

MIN, MOUT and MRND are access modes and nothing else, whatever their
names suggest.  The original source calls MIN and MOUT the "serial
input port" and "serial output port", but they are never sent to an
IN or an OUT; they are stored in FSTR1 and compared against token
bytes.  Nothing in this page drives a serial chip -- every IN and OUT
here goes to LMPR, HMPR, VMPR, the keyboard, status, border and
palette ports, the disk controller ports patched into the transfer
loops, or, once in the boot code, RESP at &E9 for printer control.

The real serial driver is in the extension page, and it does program
the SCC2691 in the SAM Comms Interface: see SERINIT and the two hooks
beside it in masterbasic.asm.  It takes its port from XVAR 11, SPORT,
so no port number appears in its code either."""
