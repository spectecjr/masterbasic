"""Z80 instruction decoder.

Complete coverage of the documented instruction set plus the undocumented
DD/FD half-register forms, SLL, the ED I/O oddities and the DDCB/FDCB
"rotate and copy" group.  decode() returns an Insn describing one
instruction at `addr`; nothing here knows about labels or files.

The `asm` field of an Insn says whether pyz80 will assemble the text.
Where the encoding has no mnemonic pyz80 accepts, asm is False and the
caller emits DEFB instead.
"""

R = ('B', 'C', 'D', 'E', 'H', 'L', '(HL)', 'A')
RP = ('BC', 'DE', 'HL', 'SP')
RP2 = ('BC', 'DE', 'HL', 'AF')
CC = ('NZ', 'Z', 'NC', 'C', 'PO', 'PE', 'P', 'M')
ALU = ('ADD A,', 'ADC A,', 'SUB ', 'SBC A,', 'AND ', 'XOR ', 'OR ', 'CP ')
ROT = ('RLC', 'RRC', 'RL', 'RR', 'SLA', 'SRA', 'SLL', 'SRL')
IM = ('0', '0', '1', '2', '0', '0', '1', '2')
BLI = (('LDI', 'CPI', 'INI', 'OUTI'),
       ('LDD', 'CPD', 'IND', 'OUTD'),
       ('LDIR', 'CPIR', 'INIR', 'OTIR'),
       ('LDDR', 'CPDR', 'INDR', 'OTDR'))

# Flow classes
NORMAL, JUMP, CJUMP, CALL, CCALL, RET, CRET, RST, JPHL, HALT_ = range(10)


class Insn:
    __slots__ = ('addr', 'length', 'text', 'flow', 'target', 'asm')

    def __init__(self, addr, length, text, flow=NORMAL, target=None, asm=True):
        self.addr = addr
        self.length = length
        self.text = text
        self.flow = flow
        self.target = target        # absolute address for jumps/calls/16-bit immediates
        self.asm = asm

    @property
    def end(self):
        return self.addr + self.length

    def falls_through(self):
        return self.flow in (NORMAL, CJUMP, CALL, CCALL, CRET, RST)

    def __repr__(self):
        return '<%04X %s>' % (self.addr, self.text)


def hexn(n, width=2):
    return '&%0*X' % (width, n)


class Decoder:
    """Decodes out of a flat bytes-like `mem` based at `base`."""

    def __init__(self, mem, base):
        self.mem = mem
        self.base = base
        self.limit = base + len(mem)

    def byte(self, addr):
        i = addr - self.base
        if 0 <= i < len(self.mem):
            return self.mem[i]
        return None

    def word(self, addr):
        lo, hi = self.byte(addr), self.byte(addr + 1)
        if lo is None or hi is None:
            return None
        return lo | (hi << 8)

    # -- number formatting hooks, overridden by the labelling pass ---------
    def n8(self, v):
        return hexn(v, 2)

    def n16(self, v):
        return hexn(v, 4)

    def a16(self, v):
        """A 16-bit value used as a jump or call target."""
        return hexn(v, 4)

    def mem16(self, v):
        """A 16-bit value used as a memory address: LD (nn),rr and friends."""
        return self.a16(v)

    def imm16(self, v):
        """A 16-bit immediate: LD rr,nn.  As often a count as an address."""
        return self.a16(v)

    def port8(self, v):
        """An 8-bit immediate used as an I/O port number."""
        return hexn(v, 2)

    def disp(self, v):
        """Signed IX/IY displacement, formatted with its sign."""
        return ('+' + hexn(v, 2)) if v >= 0 else ('-' + hexn(-v, 2))

    # ---------------------------------------------------------------------
    def decode(self, addr):
        b = self.byte(addr)
        if b is None:
            return None
        if b == 0xCB:
            return self._cb(addr)
        if b == 0xED:
            return self._ed(addr)
        if b in (0xDD, 0xFD):
            return self._index(addr, b)
        return self._base(addr, b, 'HL', 1)

    # -- unprefixed, and the body of a DD/FD instruction -------------------
    def _base(self, addr, op, hl, n):
        """`n` counts the bytes before `op`; `hl` is HL, IX or IY."""
        x, y, z = op >> 6, (op >> 3) & 7, op & 7
        p, q = y >> 1, y & 1
        idx = hl != 'HL'
        L = n

        def rp(i):
            return hl if RP[i] == 'HL' else RP[i]

        def rp2(i):
            return hl if RP2[i] == 'HL' else RP2[i]

        def reg(i, d=None):
            if not idx:
                return R[i]
            if i == 6:
                return '(%s%s)' % (hl, self.disp(d))
            if i == 4:
                return hl + 'H'
            if i == 5:
                return hl + 'L'
            return R[i]

        def imm8():
            return self.byte(addr + L)

        def imm16():
            return self.word(addr + L)

        def sdisp():
            d = self.byte(addr + n)
            return d - 256 if d > 127 else d

        if x == 0:
            if z == 0:
                if y == 0:
                    return Insn(addr, L, 'NOP')
                if y == 1:
                    return Insn(addr, L, "EX AF,AF'")
                d = imm8()
                t = (addr + L + 1 + (d - 256 if d > 127 else d)) & 0xFFFF
                if y == 2:
                    return Insn(addr, L + 1, 'DJNZ ' + self.a16(t), CJUMP, t)
                if y == 3:
                    return Insn(addr, L + 1, 'JR ' + self.a16(t), JUMP, t)
                return Insn(addr, L + 1, 'JR %s,%s' % (CC[y - 4], self.a16(t)), CJUMP, t)
            if z == 1:
                if q == 0:
                    v = imm16()
                    return Insn(addr, L + 2, 'LD %s,%s' % (rp(p), self.imm16(v)), NORMAL, v)
                return Insn(addr, L, 'ADD %s,%s' % (hl, rp(p)))
            if z == 2:
                if q == 0:
                    if p == 0:
                        return Insn(addr, L, 'LD (BC),A')
                    if p == 1:
                        return Insn(addr, L, 'LD (DE),A')
                    v = imm16()
                    if p == 2:
                        return Insn(addr, L + 2, 'LD (%s),%s' % (self.mem16(v), hl), NORMAL, v)
                    return Insn(addr, L + 2, 'LD (%s),A' % self.mem16(v), NORMAL, v)
                if p == 0:
                    return Insn(addr, L, 'LD A,(BC)')
                if p == 1:
                    return Insn(addr, L, 'LD A,(DE)')
                v = imm16()
                if p == 2:
                    return Insn(addr, L + 2, 'LD %s,(%s)' % (hl, self.mem16(v)), NORMAL, v)
                return Insn(addr, L + 2, 'LD A,(%s)' % self.mem16(v), NORMAL, v)
            if z == 3:
                return Insn(addr, L, '%s %s' % ('INC' if q == 0 else 'DEC', rp(p)))
            if z in (4, 5):
                mn = 'INC' if z == 4 else 'DEC'
                if idx and y == 6:
                    return Insn(addr, L + 1, '%s %s' % (mn, reg(6, sdisp())))
                return Insn(addr, L, '%s %s' % (mn, reg(y)))
            if z == 6:
                if idx and y == 6:
                    d = sdisp()
                    v = self.byte(addr + n + 1)
                    return Insn(addr, L + 2, 'LD %s,%s' % (reg(6, d), self.n8(v)))
                return Insn(addr, L + 1, 'LD %s,%s' % (reg(y), self.n8(imm8())))
            return Insn(addr, L, ('RLCA', 'RRCA', 'RLA', 'RRA', 'DAA', 'CPL', 'SCF', 'CCF')[y])

        if x == 1:
            if y == 6 and z == 6:
                return Insn(addr, L, 'HALT', HALT_)
            if idx and (y == 6 or z == 6):
                d = sdisp()
                if y == 6:
                    return Insn(addr, L + 1, 'LD %s,%s' % (reg(6, d), R[z]))
                return Insn(addr, L + 1, 'LD %s,%s' % (R[y], reg(6, d)))
            return Insn(addr, L, 'LD %s,%s' % (reg(y), reg(z)))

        if x == 2:
            if idx and z == 6:
                return Insn(addr, L + 1, ALU[y] + reg(6, sdisp()))
            return Insn(addr, L, ALU[y] + reg(z))

        # x == 3
        if z == 0:
            return Insn(addr, L, 'RET ' + CC[y], CRET)
        if z == 1:
            if q == 0:
                return Insn(addr, L, 'POP ' + rp2(p))
            if p == 0:
                return Insn(addr, L, 'RET', RET)
            if p == 1:
                return Insn(addr, L, 'EXX')
            if p == 2:
                return Insn(addr, L, 'JP (%s)' % hl, JPHL)
            return Insn(addr, L, 'LD SP,%s' % hl)
        if z == 2:
            v = imm16()
            return Insn(addr, L + 2, 'JP %s,%s' % (CC[y], self.a16(v)), CJUMP, v)
        if z == 3:
            if y == 0:
                v = imm16()
                return Insn(addr, L + 2, 'JP ' + self.a16(v), JUMP, v)
            if y == 2:
                return Insn(addr, L + 1, 'OUT (%s),A' % self.port8(imm8()))
            if y == 3:
                return Insn(addr, L + 1, 'IN A,(%s)' % self.port8(imm8()))
            if y == 4:
                return Insn(addr, L, 'EX (SP),%s' % hl)
            if y == 5:
                return Insn(addr, L, 'EX DE,HL')
            if y == 6:
                return Insn(addr, L, 'DI')
            return Insn(addr, L, 'EI')
        if z == 4:
            v = imm16()
            return Insn(addr, L + 2, 'CALL %s,%s' % (CC[y], self.a16(v)), CCALL, v)
        if z == 5:
            if q == 0:
                return Insn(addr, L, 'PUSH ' + rp2(p))
            v = imm16()
            return Insn(addr, L + 2, 'CALL ' + self.a16(v), CALL, v)
        if z == 6:
            return Insn(addr, L + 1, ALU[y] + self.n8(imm8()))
        return Insn(addr, L, 'RST %s' % hexn(y * 8, 2), RST, y * 8)

    # -- CB ----------------------------------------------------------------
    def _cb(self, addr):
        op = self.byte(addr + 1)
        if op is None:
            return None
        x, y, z = op >> 6, (op >> 3) & 7, op & 7
        if x == 0:
            return Insn(addr, 2, '%s %s' % (ROT[y], R[z]))
        mn = ('BIT', 'RES', 'SET')[x - 1]
        return Insn(addr, 2, '%s %d,%s' % (mn, y, R[z]))

    # -- ED ----------------------------------------------------------------
    def _ed(self, addr):
        op = self.byte(addr + 1)
        if op is None:
            return None
        x, y, z = op >> 6, (op >> 3) & 7, op & 7
        p, q = y >> 1, y & 1
        if x == 1:
            if z == 0:
                if y == 6:
                    return Insn(addr, 2, 'IN F,(C)', asm=False)
                return Insn(addr, 2, 'IN %s,(C)' % R[y])
            if z == 1:
                if y == 6:
                    return Insn(addr, 2, 'OUT (C),0', asm=False)
                return Insn(addr, 2, 'OUT (C),%s' % R[y])
            if z == 2:
                return Insn(addr, 2, '%s HL,%s' % ('SBC' if q == 0 else 'ADC', RP[p]))
            if z == 3:
                v = self.word(addr + 2)
                # The HL forms have a shorter unprefixed encoding (22/2A) that
                # pyz80 will always pick, so they have to go out as DEFB.
                ok = (p != 2)
                if q == 0:
                    return Insn(addr, 4, 'LD (%s),%s' % (self.mem16(v), RP[p]), NORMAL, v, asm=ok)
                return Insn(addr, 4, 'LD %s,(%s)' % (RP[p], self.mem16(v)), NORMAL, v, asm=ok)
            if z == 4:
                return Insn(addr, 2, 'NEG', asm=(y == 0))
            if z == 5:
                return Insn(addr, 2, 'RETI' if y == 1 else 'RETN', RET, asm=(y < 2))
            if z == 6:
                return Insn(addr, 2, 'IM ' + IM[y], asm=(y in (0, 2, 3)))
            return Insn(addr, 2, ('LD I,A', 'LD R,A', 'LD A,I', 'LD A,R',
                                  'RRD', 'RLD', 'NOP', 'NOP')[y], asm=(y < 6))
        if x == 2 and z <= 3 and y >= 4:
            return Insn(addr, 2, BLI[y - 4][z])
        return Insn(addr, 2, 'NOP', asm=False)      # invalid ED escape

    # -- DD / FD -----------------------------------------------------------
    _AFFECTED = None

    @classmethod
    def _affected(cls):
        if cls._AFFECTED is None:
            s = set()
            s.update((0x09, 0x19, 0x29, 0x39))
            s.update((0x21, 0x22, 0x23, 0x2A, 0x2B))
            s.update((0x24, 0x25, 0x26, 0x2C, 0x2D, 0x2E))
            s.update((0x34, 0x35, 0x36))
            for op in range(0x40, 0x80):
                if op == 0x76:
                    continue
                y, z = (op >> 3) & 7, op & 7
                if y in (4, 5, 6) or z in (4, 5, 6):
                    s.add(op)
            for op in range(0x80, 0xC0):
                if (op & 7) in (4, 5, 6):
                    s.add(op)
            s.update((0xE1, 0xE3, 0xE5, 0xE9, 0xF9, 0xCB))
            cls._AFFECTED = s
        return cls._AFFECTED

    def _index(self, addr, pfx):
        hl = 'IX' if pfx == 0xDD else 'IY'
        op = self.byte(addr + 1)
        if op is None or op not in self._affected():
            # The prefix does not touch what follows: it executes as a
            # one-byte no-op.  Emit it as data so the bytes round-trip.
            return Insn(addr, 1, 'DEFB %s' % hexn(pfx, 2), asm=False)
        if op == 0xCB:
            return self._idxcb(addr, hl)
        if op == 0xE9:
            return Insn(addr, 2, 'JP (%s)' % hl, JPHL)
        return self._base(addr, op, hl, 2)

    def _idxcb(self, addr, hl):
        d = self.byte(addr + 2)
        op = self.byte(addr + 3)
        if op is None:
            return None
        d = d - 256 if d > 127 else d
        x, y, z = op >> 6, (op >> 3) & 7, op & 7
        ref = '(%s%s)' % (hl, self.disp(d))
        if x == 0:
            if z == 6:
                return Insn(addr, 4, '%s %s' % (ROT[y], ref))
            return Insn(addr, 4, '%s %s,%s' % (ROT[y], ref, R[z]), asm=False)
        if x == 1:
            return Insn(addr, 4, 'BIT %d,%s' % (y, ref), asm=(z == 6))
        mn = 'RES' if x == 2 else 'SET'
        if z == 6:
            return Insn(addr, 4, '%s %d,%s' % (mn, y, ref))
        return Insn(addr, 4, '%s %d,%s,%s' % (mn, y, ref, R[z]), asm=False)
