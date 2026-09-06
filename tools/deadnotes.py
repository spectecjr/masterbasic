"""Line-comment notes that never reach a listing.

A `MB &addr : text` note sets the comment on one instruction. Two things
can stop it arriving, and neither says so:

**Two notes for one address.** One wins and the other is discarded. The
loser is often the longer and better of the two -- `&4ACD` has both a
one-line note and a four-line one explaining why the address has to be
read through the window twice over, and it is the four-line one that is
thrown away. Someone editing the losing note sees no change in the
listing and has no way to tell why.

**A carried comment already holds the slot.** The 1991 author's
upper-case comment is applied after these, so a note on the same
instruction is lost. `&6DF7` is the example: a note in
`notes/joinsplit.txt` about error 43 that appears in no listing, and
which happens also to be wrong -- an unchecked claim in a file that
reads as though every line in it is live.

This reports both. It cannot tell which of two duplicates *should* win;
that is a judgement, and the point is to make the choice visible.

    python tools/deadnotes.py
"""
import io, os, re

ADDR = re.compile(r';\s*([0-9A-F]{4})\s')
NOTE = re.compile(r'^(MB|DOS)\s+&([0-9A-Fa-f]{4})\s*:\s*(.+)$')
HALF = {'MB': 'masterbasic', 'DOS': 'masterdos'}


def commented(half):
    """address -> the comment on its line, continuations included."""
    lines = io.open('listings/clean/%s.asm' % half,
                    encoding='utf-8').read().split('\n')
    out = {}
    for i, l in enumerate(lines):
        m = ADDR.search(l)
        if not m:
            continue
        a = int(m.group(1), 16)
        if not (0x4000 <= a < 0x7FC0) or a in out:
            continue
        j = i + 1
        while j < len(lines) and re.match(r'^\s+;', lines[j]):
            j += 1
        out[a] = ' '.join(lines[i:j])
    return out


def collect():
    """(tag, addr) -> [(file, line, text), ...] for every line note."""
    notes = {}
    for root, _dirs, files in os.walk('notes'):
        for f in sorted(files):
            if not f.endswith('.txt'):
                continue
            path = os.path.join(root, f).replace(os.sep, '/')
            for n, raw in enumerate(io.open(path, encoding='utf-8'), 1):
                m = NOTE.match(raw.strip())
                if m:
                    key = (m.group(1), int(m.group(2), 16))
                    notes.setdefault(key, []).append((path, n, m.group(3)))
    return notes


def main():
    page = {t: commented(h) for t, h in HALF.items()}
    notes = collect()
    total = sum(len(v) for v in notes.values())

    dup = {k: v for k, v in notes.items() if len(v) > 1}
    lost = []
    for (tag, a), entries in sorted(notes.items()):
        if len(entries) > 1:
            continue
        line = page[tag].get(a)
        _path, _n, text = entries[0]
        words = [w for w in re.findall(r"[A-Za-z']{5,}", text)][:3]
        if line is not None and words and not all(w in line for w in words):
            lost.append(((tag, a), entries[0]))

    print('%d line notes at %d addresses.' % (total, len(notes)))
    print('%d addresses carry more than one, so all but one are discarded:'
          % len(dup))
    for (tag, a), entries in sorted(dup.items()):
        print()
        print('  %s &%04X' % (tag, a))
        for path, n, text in entries:
            print('    %s:%d  %s' % (path, n, text[:88]))

    print()
    print('%d single notes whose words are not on the line they name --'
          % len(lost))
    print('a carried comment probably holds the slot:')
    for (tag, a), (path, n, text) in lost:
        print('  %s:%d  %s &%04X  %s' % (path, n, tag, a, text[:80]))


if __name__ == '__main__':
    main()
