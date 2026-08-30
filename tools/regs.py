"""What each instruction reads and writes, for working out contracts.

The decoder produces text, so this reads the text rather than carrying a
second table alongside z80.py.  Registers are tracked as single bytes --
HL is H and L -- because a routine that returns a value in L and junk in
H is common enough that saying "HL" would be a lie.

MEM stands for any memory access and CALL for "this instruction hands
control somewhere else", which the caller resolves by propagation.
"""

import re

BYTE = ('A', 'B', 'C', 'D', 'E', 'H', 'L', 'I', 'R')
PAIRS = {'BC': ('B', 'C'), 'DE': ('D', 'E'), 'HL': ('H', 'L'),
         'AF': ('A', 'F'), "AF'": ('A', 'F'),
         'IX': ('IXh', 'IXl'), 'IY': ('IYh', 'IYl'), 'SP': ('SP',)}
IDX = {'IXh', 'IXl', 'IYh', 'IYl'}
CONDS = ('NZ', 'Z', 'NC', 'C', 'PO', 'PE', 'P', 'M')

ARITH = ('ADD', 'ADC', 'SUB', 'SBC', 'AND', 'OR', 'XOR', 'CP')
SHIFT = ('RLC', 'RRC', 'RL', 'RR', 'SLA', 'SRA', 'SRL', 'SLL')


def parts(text):
    """Mnemonic and operand list."""
    bits = text.split(None, 1)
    if len(bits) == 1:
        return bits[0], []
    out, depth, cur = [], 0, ''
    for ch in bits[1]:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if ch == ',' and depth == 0:
            out.append(cur.strip())
            cur = ''
        else:
            cur += ch
    out.append(cur.strip())
    return bits[0], out


def regs_of(operand):
    """The registers an operand names, and whether it touches memory."""
    op = operand.strip()
    if op.startswith('(') and op.endswith(')'):
        inner = op[1:-1].strip()
        found = set(['MEM'])
        m = re.match(r'^(IX|IY)\s*[-+]', inner)
        if m:
            found |= set(PAIRS[m.group(1)])
        elif inner in PAIRS:
            found |= set(PAIRS[inner])
        elif inner in BYTE:
            found.add(inner)
        return found
    if op in PAIRS:
        return set(PAIRS[op])
    if op in BYTE or op in IDX:
        return {op}
    return set()


def effects(text):
    """(reads, writes) for one instruction, as sets of byte registers."""
    op, args = parts(text)
    r, w = set(), set()

    if op in ('NOP', 'DI', 'EI', 'HALT', 'DEFB'):
        return r, w
    if op == 'EXX':
        both = set('BCDEHL')
        return both, both
    if op == 'EX':
        if args and args[0] == 'AF':
            return {'A', 'F'}, {'A', 'F'}
        got = set()
        for a in args:
            got |= regs_of(a)
        return got, got - {'MEM'}
    if op in ('LDIR', 'LDDR', 'LDI', 'LDD'):
        both = set('BCDEHL')
        return both | {'MEM'}, both | {'MEM', 'F'}
    if op in ('CPIR', 'CPDR', 'CPI', 'CPD'):
        return set('ABCHL') | {'MEM'}, set('BCHL') | {'F'}
    if op == 'DJNZ':
        return {'B'}, {'B'}
    if op in ('JP', 'JR', 'CALL', 'RET', 'RST'):
        if args and args[0] in CONDS:
            r.add('F')
        if op in ('CALL', 'RST'):
            w.add('CALL')
        if op == 'JP' and args and args[0].startswith('('):
            r |= regs_of(args[0]) - {'MEM'}
        return r, w
    if op == 'PUSH':
        return regs_of(args[0]) | {'SP'}, {'MEM', 'SP'}
    if op == 'POP':
        return {'MEM', 'SP'}, regs_of(args[0]) | {'SP'}
    if op == 'LD':
        dst, src = args[0], args[1]
        r |= regs_of(src)
        if dst.startswith('('):
            r |= regs_of(dst)
            w.add('MEM')
        else:
            w |= regs_of(dst)
        return r, w
    if op in ('IN',):
        # `IN A,(n)` does put A on A8-A15, but no one writes it meaning
        # that, and counting A as an input would put it in the contract
        # of every routine that reads a port.
        r |= {'B', 'C'} if args[-1] == '(C)' else set()
        w |= regs_of(args[0]) | {'F'}
        return r, w
    if op == 'OUT':
        r |= {'B', 'C'} if args[0] == '(C)' else {'A'}
        r |= regs_of(args[1]) if len(args) > 1 else set()
        return r, w
    if op in ARITH:
        if len(args) == 2 and args[0] in ('HL', 'IX', 'IY'):
            r |= set(PAIRS[args[0]]) | regs_of(args[1])
            if op in ('ADC', 'SBC'):
                r.add('F')
            w |= set(PAIRS[args[0]]) | {'F'}
            return r, w
        rest = args[-1]
        # XOR A and SUB A are how a Z80 programmer writes A = 0; calling
        # A an input there would put it in every contract that clears it.
        if not (rest == 'A' and op in ('XOR', 'SUB')):
            r |= {'A'}
        r |= regs_of(rest)
        if op in ('ADC', 'SBC'):
            r.add('F')
        w |= {'F'} if op == 'CP' else {'A', 'F'}
        return r, w
    if op in ('INC', 'DEC'):
        got = regs_of(args[0])
        r |= got
        w |= got | ({'F'} if len(got - {'MEM'}) <= 1 else set())
        return r, w
    if op in SHIFT:
        got = regs_of(args[-1])
        return got, got | {'F'}
    if op in ('RLCA', 'RRCA', 'RLA', 'RRA', 'DAA', 'CPL', 'NEG'):
        return {'A', 'F'}, {'A', 'F'}
    if op in ('SCF', 'CCF'):
        return {'F'}, {'F'}
    if op == 'BIT':
        return regs_of(args[-1]), {'F'}
    if op in ('SET', 'RES'):
        got = regs_of(args[-1])
        return got, got
    return r, w


PRETTY = (('B', 'C', 'BC'), ('D', 'E', 'DE'), ('H', 'L', 'HL'),
          ('IXh', 'IXl', 'IX'), ('IYh', 'IYl', 'IY'))


def show(names):
    """Join a register set, pairing halves that are both present."""
    left = set(names) - {'MEM', 'CALL'}
    out = []
    for hi, lo, pair in PRETTY:
        if hi in left and lo in left:
            out.append(pair)
            left -= {hi, lo}
    for one in ('A', 'F', 'B', 'C', 'D', 'E', 'H', 'L', 'SP', 'I', 'R',
                'IXh', 'IXl', 'IYh', 'IYl'):
        if one in left:
            out.append(one)
            left.discard(one)
    out.extend(sorted(left))
    order = {'AF': 0, 'A': 1, 'F': 2, 'BC': 3, 'B': 4, 'C': 5, 'DE': 6,
             'D': 7, 'E': 8, 'HL': 9, 'H': 10, 'L': 11}
    return ', '.join(sorted(out, key=lambda x: order.get(x, 99)))
