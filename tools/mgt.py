# -*- coding: utf-8 -*-
"""Read an MGT disk image: list the directory, or pull a file out of it.

    python tools/mgt.py dsks/MasterBasic1.7.dsk
    python tools/mgt.py dsks/MasterBasic1.7.dsk MBMC out.bin

The format is in ref/masterdos/docs/disk-format.md and nothing here departs
from it: 80 tracks, 2 sides, 10 sectors of 512 bytes, the last two bytes of
each sector linking to the next, and a directory of 256-byte entries filling
the first DTKS tracks of side 1.
"""

import os
import sys

SECTOR = 512
PAYLOAD = 510                       # the last two bytes are the link
SECTORS_PER_TRACK = 10
ENTRY = 256

TYPES = {0: 'erased', 1: 'ZX BASIC', 2: 'ZX num array', 3: 'ZX str array',
         4: 'ZX code', 5: 'ZX 48K snapshot', 6: 'Microdrive', 7: 'SCREEN$',
         8: 'special', 9: 'ZX 128K snapshot', 10: 'Opentype', 11: 'ZX exec',
         16: 'BASIC', 17: 'num array', 18: 'str array', 19: 'code',
         20: 'SCREEN$', 21: 'directory', 22: 'drive', 23: 'unidos create'}


def offset(track, sector):
    """Where a sector lives in the image file."""
    side = 1 if track & 0x80 else 0
    return (((track & 0x7F) * 2 + side) * SECTORS_PER_TRACK + sector - 1) * SECTOR


class Disk:
    def __init__(self, path):
        self.raw = open(path, 'rb').read()
        self.path = path
        # Byte 255 of entry 0 holds the directory tracks beyond the standard
        # four, which is what makes a SAMDOS disk read correctly: it leaves
        # zero there and zero means four.
        self.dir_tracks = 4 + self.sector(0, 1)[255]

    def sector(self, track, n):
        o = offset(track, n)
        return self.raw[o:o + SECTOR]

    def entries(self):
        """Every used directory entry, as (index, dict)."""
        out = []
        i = 0
        for track in range(self.dir_tracks):
            for n in range(1, SECTORS_PER_TRACK + 1):
                s = self.sector(track, n)
                for half in (0, ENTRY):
                    e = s[half:half + ENTRY]
                    if e[0]:
                        out.append((i, self.describe(e)))
                    i += 1
        return out

    @staticmethod
    def describe(e):
        return {
            'type': e[0] & 0x1F,
            'protected': bool(e[0] & 0x40),
            'hidden': bool(e[0] & 0x80),
            'name': e[1:11].decode('latin-1').rstrip(),
            'sectors': (e[11] << 8) | e[12],
            'track': e[13],
            'sector': e[14],
            'header': e[211:220],
            'raw': e,
        }

    def read(self, ent):
        """Follow the sector chain and return the file's bytes."""
        out = bytearray()
        track, n = ent['track'], ent['sector']
        seen = set()
        while track or n:
            if (track, n) in seen:
                raise ValueError('sector chain loops at %d/%d' % (track, n))
            seen.add((track, n))
            s = self.sector(track, n)
            out += s[:PAYLOAD]
            track, n = s[PAYLOAD], s[PAYLOAD + 1]
        return bytes(out)


def main():
    disk = Disk(sys.argv[1])
    if len(sys.argv) == 2:
        print('%s: directory of %d tracks, %d entries used'
              % (os.path.basename(disk.path), disk.dir_tracks,
                 len(disk.entries())))
        print('%-4s %-11s %-14s %7s %7s  %s'
              % ('#', 'name', 'type', 'sectors', 'bytes', 'header'))
        for i, e in disk.entries():
            h = ' '.join('%02X' % b for b in e['header'])
            print('%-4d %-11s %-14s %7d %7d  %s'
                  % (i, e['name'], TYPES.get(e['type'], '?%d' % e['type']),
                     e['sectors'], e['sectors'] * PAYLOAD, h))
        return
    want = sys.argv[2]
    for _, e in disk.entries():
        if e['name'] == want:
            data = disk.read(e)
            open(sys.argv[3], 'wb').write(data)
            print('%s: %d bytes written to %s' % (want, len(data), sys.argv[3]))
            return
    print('no file called %r on that disk' % want)
    sys.exit(1)


if __name__ == '__main__':
    main()
