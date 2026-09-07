# Skills extracted from the masterbasic disassembly

Each folder is a Claude Code skill (`SKILL.md` with frontmatter), laid
out so the whole directory can be moved into `.claude/skills/` of
another project, or a shared skills location, as it stands.

Start with `re-project-setup/`: it is written for the person, not the
assistant, and says what to gather before any code is read.

| skill | what it carries | generic to |
|---|---|---|
| `re-project-setup/` | what to collect and decide before starting: the binary and its provenance, a round-tripping assembler, the reference sources, the dumps that turn readings into proof, a second build, a machine | any RE project |
| `byte-identical-disassembly/` | the gate (assemble, compare, nothing you write can change a byte), three trees, hand-written notes as the only input, figures printed by the build not kept in prose.  Ships `patch.py`. | any RE project |
| `adversarial-review/` | agents that review commentary against instructions: the rules that do not bend, the dispatch template with its facts slot, the audit, what the score means | any RE project |
| `auditing-re-prose/` | what goes wrong in *documentation* of reverse-engineered code, which is a different fault class from what goes wrong in the code | any RE project |
| `magic-numbers/` | the target ("no unexplained number in a worked routine", not zero), which numbers can never be named, and the four traps a counter for it fell into | any RE project |
| `evidence-register/` | keeping the open questions: what each needs to close it, what it would cost, and the ones that turn out to need no evidence | any RE project |
| `re-bug-reports/` | the shape of a defect found by reading rather than running, and the discipline of saying so | any RE project |
| `z80-idioms/` | the idioms that recur in Z80 code and how a listing should write each; marked where an idiom is generic and where it is a bank-switched-machine thing | any Z80 target |
| `sam-coupe/` | the machine: sections and paging ports bit by bit, the ROMs, the system page with absolute addresses for every vector and buffer, the DOS interface, the NMI path, ROM versions, reference sources | any SAM Coupé project |

## What stays behind

This image.  MasterDOS 2.3's and MasterBASIC 1.7's own addresses, the
two-halves window between them, `SAMHK`, `CALLDOS`/`CALLMB`, the
dumps and what each proved -- that is `CLAUDE.md` and `design/` in this
repository.  The machine facts are in `sam-coupe/` because they are
true of every SAM project; this program's facts are not.

The tools other than `patch.py`.  `z80.py` and `disasm.py` are a Z80
decoder and a tracing disassembler and are portable to any Z80 target;
`checkdocs.py`, `sites.py` and `deadnotes.py` are portable in *design*
but read this project's listing format.  They are referenced from the
skills that need them rather than copied.

## Where each came from

Distilled from `design/reviewprocess.md`, `design/cleanstyle.md`,
`docs/idioms.md`, `docs/bugs.md`, `docs/evidence-wanted.md`,
`CLAUDE.md`, `ref/samrom/vars.asm`, the Technical Manual, and the
commit history of September 2026.  Where a skill states a number --
"31 copies", "four faults", "204 of 208", "33 bytes" -- it is a fact
about this project offered as calibration, not a claim about the next.
Where `sam-coupe/` states an address, it was read from the ROM source
or verified against a dump in this repository.
