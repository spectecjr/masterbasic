#!/bin/bash
#
# build.sh -- regenerate the two listings in listings/disasm/ and prove them correct.
#
# Assembles the annotated MasterDOS 2.3 source to get a symbol table and
# listing, disassembles dumps/MasterBasicMasterDos.bin against them, then
# assembles the result and compares it with the original file byte for byte.
#
# Needs pyz80:  python -m pip install pyz80
#
#   tools/build.sh [--keep]

set -u

keep=0
[ "${1:-}" = "--keep" ] && keep=1

here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/.." && pwd)

# pyz80's console script lands in the per-user scripts directory on Windows,
# which is often not on PATH.
if ! command -v pyz80 >/dev/null 2>&1; then
    for finder in "sysconfig.get_path('scripts','nt_user')" "sysconfig.get_path('scripts')"; do
        dir=$(python -c "import sysconfig;print($finder)" 2>/dev/null) || continue
        case "$dir" in
            [A-Za-z]:\\*) dir="/$(echo "${dir:0:1}" | tr 'A-Z' 'a-z')/$(echo "${dir:3}" | tr '\\' '/')" ;;
        esac
        if [ -e "$dir/pyz80" ]; then PATH="$PATH:$dir"; export PATH; break; fi
    done
fi
command -v pyz80 >/dev/null 2>&1 || {
    echo "build.sh: pyz80 not found. Install it with:  python -m pip install pyz80" >&2
    exit 2
}

work=$(mktemp -d) || exit 2
[ "$keep" -eq 0 ] && trap 'rm -rf "$work"' EXIT

out="$root/listings/disasm"
mkdir -p "$out"

# --- MasterDOS 2.3, for its symbol table and instruction boundaries --------
( cd "$root/ref/masterdos/annotated-src" &&
  pyz80 --obj="$work/mdos.bin" --mapfile="$work/mdos.map" --lstfile="$work/mdos.lst" \
        --exportfile="$work/mdos.sym" \
        -o "$work/mdos.dsk" masterdos23.asm ) >"$work/mdos.log" 2>&1 || {
    echo "*** MasterDOS build failed ***"; tail -20 "$work/mdos.log"; exit 1; }
cmp -s "$work/mdos.bin" "$root/ref/masterdos/res/MDOS23.bin" ||
    { echo "*** rebuilt MDOS23 does not match res/MDOS23.bin ***"; exit 1; }
echo "MasterDOS 2.3 reference: rebuilt and matches res/MDOS23.bin"

# --- the SAM ROM, for its BASIC token tables -------------------------------
( cd "$root/ref/samrom" &&
  pyz80 --obj="$work/samrom.bin" --mapfile="$work/samrom.map" \
        --exportfile="$work/samrom.sym" \
        -o "$work/samrom.dsk" samrom.asm ) >"$work/samrom.log" 2>&1 || {
    echo "*** SAM ROM build failed ***"; tail -20 "$work/samrom.log"; exit 1; }
echo "SAM ROM 3.0: built, token tables taken from it"

# --- the disassembly -------------------------------------------------------
python "$here/dis_mb.py" "$work" -o "$out" || exit 1

# --- the system page as MasterBASIC leaves it ------------------------------
# Not checkable by assembling -- there is no original -- but it has to be
# regenerated here or it drifts away from the listings it is derived from.
python "$here/syspage.py" || exit 1

# --- prove it round-trips --------------------------------------------------
# One assembly per tree.  base.asm INCLUDEs both halves, each ORGed at
# &4000 and DUMPed to a page of its own, so the object is 32704 bytes:
# the DOS half, 64 bytes of page tail, then MasterBASIC's.
for tree in disasm clean speculate; do
    pyz80 --obj="$work/$tree.out" -o "$work/$tree.dsk"           "$root/listings/$tree/base.asm" >"$work/$tree.log" 2>&1 || {
        echo "*** listings/$tree/base.asm assembly failed ***"
        tail -20 "$work/$tree.log"; exit 1; }
done

python - "$work" "$root" <<'EOF' || exit 1
import sys, os
work, root = sys.argv[1], sys.argv[2]
raw = open(os.path.join(root, 'dumps', 'MasterBasicMasterDos.bin'), 'rb').read()
half = len(raw) // 2
PAGE = 16384
ok = True
for tree in ('disasm', 'clean', 'speculate'):
    got = open(os.path.join(work, tree + '.out'), 'rb').read()
    # Each half is checked separately, as it always was: one assembly
    # now, but still two answers, so a fault still says which half.
    for name, want, at in (('masterdos', raw[:half], 0),
                           ('masterbasic', raw[half:], PAGE)):
        shown = 'listings/%s/%s.asm' % (tree, name)
        mine = got[at:at + len(want)]
        if mine == want:
            print('%s: BYTE-IDENTICAL' % shown)
        else:
            ok = False
            bad = [i for i in range(min(len(mine), len(want)))
                   if mine[i] != want[i]]
            print('*** %s DIFFERS in %d bytes, first at &%04X ***'
                  % (shown, len(bad) + abs(len(mine) - len(want)),
                     0x4000 + (bad[0] if bad else min(len(mine), len(want)))))
    gap = got[half:PAGE]
    if set(gap) - {0}:
        ok = False
        print('*** listings/%s/base.asm: the page tail between the halves is '
              'not empty ***' % tree)
sys.exit(0 if ok else 1)
EOF

# The token tables in docs/ are copies of what the SAM ROM holds, so they
# can go stale the moment anything under ref/ moves -- and a stale table
# and a wrong one look identical on the page.  Regenerate and compare.
python "$here/tokentab.py" --check || exit 1

# The listings are their own proof; the prose around them is not, so check
# that what it quotes and the names it uses are still what the listings say.
python "$here/checkdocs.py"

[ "$keep" -eq 1 ] && echo "build directory kept at $work"
exit 0
