"""MasterBASIC's serial driver, read against the SCC2691 datasheet.

The extension drives the SAM Comms Interface -- a Philips SCC2691 UART
at ports &EC to &EF, whichever the jumper selects.  The port number is
not in the code: it is XVAR 11, SPORT, which the manual gives as
"normally 236", and 236 is &EC, the manual's default.  That is why a
sweep for port constants does not find this driver.

The chip has eight registers, selected by its A0-A2 lines.  The Z80
puts B on A8-A15 during an `OUT (C),r`, so the interface must wire the
register select to the high half of the address bus: everything below
loads C with SPORT and B with the register number.  That reading is
what makes the rest fall out, since every value then lands on the
register the datasheet says it should.

    B   read            write
    0   MR1, MR2        MR1, MR2
    1   SR              CSR
    2   BRG test        CR
    3   RHR             THR
    4   -               ACR
    5   ISR             IMR
    6   CTU             CTUR
    7   CTL             CTLR
"""

SERINIT_DOC = """\
Set up the SCC2691 for LPRINT MODE 2.

C is SPORT, the port the Comms Interface is jumpered to, and B selects
one of the chip's eight registers.  The whole sequence is the
datasheet's own reset-and-enable order:

    B=2  CR  = &10   reset the MR pointer, so the next two writes to
                     register 0 land on MR1 and then MR2
    B=0  MR1 = DBITS XVAR 13.  &93 is eight data bits: MR1[1:0] = 11.
                     146, 145 and 144 step down to seven, six and five,
                     which is the manual's table exactly
         MR2 = SBITS XVAR 14.  &1F is two stop bits, MR2[3:0] = 1111;
                     &17 is 1111-4 = one stop bit
    B=1  CSR = BAUD  XVAR 12.  The top nibble is the receiver clock and
                     the bottom one the transmitter, and MasterBASIC
                     sets both the same -- which is why the manual's
                     values look odd and go up in seventeens.  &BB is
                     1011 in both halves, 9600 baud
    B=4  ACR = &38   ACR[7]=0 selects baud rate set 1, the column the
                     table above is read from
    B=5  IMR = 0     no interrupts: both directions are polled
    B=6  CTUR = 0
    B=7  CTLR = 0    the counter/timer is unused, so the divisors are
                     cleared rather than left as found
    B=2  CR  = &20   reset receiver
         CR  = &30   reset transmitter
         CR  = &40   reset error status
         CR  = &50   reset break-change interrupt
         CR  = &05   enable receiver (CR[0]) and transmitter (CR[2])
         CR  = &A0   assert RTSN

DBITS and SBITS are fetched as one word -- `LD HL,(DBITS)` -- because
XVAR 13 and 14 are adjacent and go to MR1 and MR2 in that order.  The
six command bytes are written in pairs through the routine below, and
the last pair is reached by falling into it rather than calling it."""

SERCMD_DOC = """\
Write two bytes to whichever register B selects.

H first, then L, so the caller writes the pair the way it reads:
`LD HL,&2030` sends &20 and then &30.  Used only for the run of
command-register writes at the end of the setup above, which is why
the last `LD HL` before it has no CALL -- it falls straight in."""

SERTX_DOC = """\
Send one character over the serial line.  Hook code 180.

    B=1  read SR, the channel status register
         wait for bit 3, TxEMT
    B=3  write the character to THR

The wait is on TxEMT, transmitter *empty*, and not on TxRDY in bit 2,
which is the one that says the holding register can take another
character.  Waiting for empty gives up the chip's one-character
lookahead and sends strictly one at a time.

The poll calls the escape check, so a line with nothing listening can
be broken out of instead of hanging the machine."""

SERRX_DOC = """\
Read one character from the serial line.  Hook code 181.

    B=1  read SR
         wait for bit 0, RxRDY
    B=3  read the character from RHR

RxRDY is set while any of the receiver's three FIFO positions is
occupied, so this drains characters that arrived while something else
was happening.  Nothing looks at SR bits 4 to 7 -- overrun, parity,
framing and received break -- so a line error is not reported, it just
yields a wrong character.

Carry is set before the return, and the character comes back through
`PUSH AF / POP BC`."""

ESCCHK_DOC = """\
Has ESC been pressed?  Reports "Escape requested" if it has.

Reads the keyboard row through the status port and returns unless the
key is down, the SAM's matrix being active low.  Both serial polling
loops call this, which is what stops a missing or silent device at the
other end from locking the machine up: the wait can always be broken
out of."""
