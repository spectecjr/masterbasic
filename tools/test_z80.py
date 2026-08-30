"""Round-trip test: decode every encoding, reassemble it with pyz80, and
insist the bytes come back unchanged.

    python tools/test_z80.py <workdir>
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from z80 import Decoder, hexn


def candidates():
    ops = []
    for a in range(0x100):
        ops.append(bytes([a, 0x34, 0x12]))
    for a in range(0x100):
        ops.append(bytes([0xCB, a]))
    for a in range(0x100):
        ops.append(bytes([0xED, a, 0x34, 0x12]))
    for pfx in (0xDD, 0xFD):
        for a in range(0x100):
            if a == 0xCB:
                continue
            ops.append(bytes([pfx, a, 0x05, 0x34, 0x12]))
        for a in range(0x100):
            ops.append(bytes([pfx, 0xCB, 0x05, a]))
    return ops


def main(work):
    stream = bytearray()
    lines = []
    skipped = 0
    for seq in candidates():
        d = Decoder(seq, 0)
        ins = d.decode(0)
        assert ins is not None and ins.length <= len(seq), seq.hex()
        raw = seq[:ins.length]
        # Re-decode in place so relative jumps resolve against the real address
        base = len(stream)
        d2 = Decoder(bytes(stream) + raw, 0)
        ins2 = d2.decode(base)
        assert ins2.length == ins.length, (seq.hex(), ins.text)
        if ins2.asm:
            lines.append('%-14s %s' % ('', ins2.text))
        else:
            skipped += 1
            lines.append('%-14s DEFB %s   ; %s'
                         % ('', ','.join(hexn(b, 2) for b in raw), ins2.text))
        stream += raw

    src = os.path.join(work, 'optest.asm')
    obj = os.path.join(work, 'optest.bin')
    with open(src, 'w') as f:
        f.write('%-14s ORG  0\n' % '')
        f.write('\n'.join(lines))
        f.write('\n')
    r = subprocess.run(['pyz80', '--obj=' + obj, '-o', os.path.join(work, 'optest.dsk'), src],
                       capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-4000:], r.stderr[-2000:])
        return 1
    got = open(obj, 'rb').read()
    want = bytes(stream)
    if got == want:
        print('OK  %d encodings, %d bytes, %d emitted as DEFB (no pyz80 mnemonic)'
              % (len(candidates()), len(want), skipped))
        return 0
    print('MISMATCH len %d vs %d' % (len(got), len(want)))
    for i in range(min(len(got), len(want))):
        if got[i] != want[i]:
            print('first difference at %04X: got %02X want %02X' % (i, got[i], want[i]))
            print('context want:', want[max(0, i - 8):i + 8].hex(' '))
            print('context got :', got[max(0, i - 8):i + 8].hex(' '))
            break
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
