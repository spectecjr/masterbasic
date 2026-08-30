#!/bin/bash
#
# build.sh -- regenerate the two listings in disasm/ and prove them correct.
#
# Assembles the annotated MasterDOS 2.3 source to get a symbol table and
# listing, disassembles file/MasterBasicMasterDos.bin against them, then
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

out="$root/disasm"
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

# --- prove it round-trips --------------------------------------------------
for half in masterdos masterbasic; do
    pyz80 --obj="$work/$half.out" -o "$work/$half.dsk" "$out/$half.asm"         >"$work/$half.log" 2>&1 || {
        echo "*** $half reassembly failed ***"; tail -20 "$work/$half.log"; exit 1; }
done

for half in masterdos masterbasic; do
    pyz80 --obj="$work/spec_$half.out" -o "$work/spec_$half.dsk"           "$root/speculate/$half.asm" >"$work/spec_$half.log" 2>&1 || {
        echo "*** speculate/$half.asm reassembly failed ***"
        tail -20 "$work/spec_$half.log"; exit 1; }
done

python - "$work" "$root" <<'EOF' || exit 1
import sys, os
work, root = sys.argv[1], sys.argv[2]
raw = open(os.path.join(root, 'file', 'MasterBasicMasterDos.bin'), 'rb').read()
half = len(raw) // 2
ok = True
for name, part in (('masterdos', raw[:half]), ('masterbasic', raw[half:]),
                   ('spec_masterdos', raw[:half]),
                   ('spec_masterbasic', raw[half:])):
    got = open(os.path.join(work, name + '.out'), 'rb').read()
    got = got[:len(part)]
    shown = name.replace('spec_', 'speculate/') if name.startswith('spec_')         else name
    if got == part:
        print('%s.asm: BYTE-IDENTICAL' % shown)
    else:
        ok = False
        bad = [i for i in range(min(len(got), len(part))) if got[i] != part[i]]
        print('*** %s.asm DIFFERS in %d bytes, first at &%04X ***'
              % (shown, len(bad) + abs(len(got) - len(part)),
                 0x4000 + (bad[0] if bad else min(len(got), len(part)))))
sys.exit(0 if ok else 1)
EOF

[ "$keep" -eq 1 ] && echo "build directory kept at $work"
exit 0
