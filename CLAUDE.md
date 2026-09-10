# masterbasic

A byte-exact disassembly of `dumps/MasterBasicMasterDos.bin` (SAM Coupé:
MasterDOS 2.3 with MasterBASIC 1.7 spliced in), with a reading copy
written for someone who knows Z80 and not this machine.

## Whose project this is

**Who has been working here.**  These sessions have been Claude's,
across Opus and Fable, and a few habits are worth inheriting rather
than rediscovering.  Verify every finding against the instructions
before applying it -- including findings from your own review agents,
who have been confidently wrong about a `PART` that exists in no tree
and about phantom references that were never phantoms.  When a number
moves, ask whether the definition moved with it.  A total that comes
back *exactly* unchanged after a change that should have moved it is a
failure signal, not a result.

The failures were consistent too, and the guards in `.claude/` exist
because of them.  I have written a rule down and broken it in the same
commit: "the same wrong number is usually in more than one place" was
written while fixing two of its six copies.  I have built patch strings
from memory of what I intended rather than from the file, twice.  Three
of the four faults in the magic-number counter flattered its own
figure, and not one was visible to a green build -- the byte-identity
gate proves everything about the bytes and nothing about whether a
measurement means what it claims.  I have twice written a confident
negative about what this repository contains without listing the
directory first -- "the port is named nowhere this project can reach"
while `ref/sam-coupe-technical-manual/` held the port map that named it,
and a whole `skills/` tree I did not know was there.  **Before recording
that something is absent, look.**  A negative is a claim like any other
and costs one `ls`.  Expect to make these mistakes rather than expecting
to be above them.

**Who you are working with.**  Simon Cooke owns this project and reads
the output closely.  They challenge specific claims with a reason
attached and want the claim *checked*, not withdrawn -- the `SORT
INVERSE` syntax was questioned, verified against the manual, and stood.
They ask the structural question at the right moment (what belongs in a
skill, what should be a hook, what evidence should I be gathering) and
those questions have reshaped this work more than any individual
finding.  They test the tooling rather than trusting it; a deliberately
bogus label name once appeared in `docs/` to see whether `checkdocs`
would catch it.  They give wide latitude -- "go for it", "keep going" --
and in exchange expect to be told plainly what is left, what is
blocked, and what is not worth attempting.  Flag a judgement call as a
judgement call; they will take it seriously either way.

## The gate

    bash tools/build.sh > build.log 2>&1

Must print **6 BYTE-IDENTICAL** lines and `N prose files check out`.  It
takes 5–8 minutes: run it in the background and read `build.log` when it
finishes.  `build.log` is gitignored, which is why every checkable figure
— the byte census, the label tally, the unexplained-number counts — is
printed there rather than kept in a document.

Six listings in three trees, one assembly per tree via `base.asm`:
`listings/disasm/` (working copy, arguments kept), `listings/clean/` (the
reading copy — conclusions only), `listings/speculate/`.  Nothing you
write can change a byte; the build says so if it does.

## The machine, in the six facts an operand cannot be read without

- The image is 32640 bytes: two halves of 16320, the first opening with a
  nine-byte header at `&4000`–`&4008`.  DOS first, MasterBASIC second.
- Both halves assemble at `&4000`–`&7FBF` in their own page, and each sees
  the other at `&8000`–`&BFBF`.  So in the DOS listing an `&8xxx`/`&Bxxx`
  operand is usually MasterBASIC's address plus `&4000`, not a second part
  of the DOS.  `IN_PAGE_C` and `NOT_IN_THIS_PAGE` are both `EQU &4000`.
- Three pages matter at run time: the system page (page 0, the ROM
  variables), the DOS page, and MasterBASIC's (page 28, `&1C`).  Which is at
  `&4000` depends on `LMPR`/`HMPR` and is the main source of misreading.
- `LMPR` is port `&FA`, `HMPR` `&FB`, `STAT` `&F9`.  LMPR bit 5 **set**
  takes ROM 0 *out*; bit 6 **set** brings ROM 1 *in* at `&C000`.  `&1F` is
  both ROMs as normal; `&5F` is "both ROMs on".
- A routine that sets `HMPR` to zero sees the system page at `&8000`, so
  its `&8xxx` means system-page `&4xxx` and `&9xxx` means `&5xxx`.
- `RST &08` + code is a hook; `SAMHK` at DOS `&44A6` maps 128–185, and an
  entry with bit 15 set lives in the other page, reached via `CALLMB`.
  `CALL CALLDOS`/`CALL CALLMB` + `DEFW addr` are the cross-page calls; the
  `DEFW` is data.

## Notes: the only input that is yours

`notes/*.txt` feeds every tree; `notes/clean/*.txt` feeds the reading copy
only.  `DOS` substitutes for `MB`.

    MB &7465 NAME                   label
    MB &7465 : text                 comment on that instruction
    MB &7465-&7470 data|word|text|code
    MB &7465 value NAME             name this operand (an equate is made)
    MB &74A6 expr SECTION_D + 1     rewrite the operand; checked against the bytes
    MB &7465 step text              a line of its own above the instruction
    CONST NAME = &15 : description
    GROUP Heading                   the CONSTs after it, until the next GROUP
    RENAME OLD NEW
    DOC NAME                        banner; indented lines below are the text

`RENAME` says what a label is called *now*, and synthetic numbering is
not stable while the same file is renaming: naming two addresses took
`_1` and `_2` out of a run, the namer renumbered what was left, and the
`RENAME`s for `_3` and `_4` matched nothing -- silently, since three of
five had landed.  Name by address instead; `MB &7CB2 NAME` cannot drift.
`IN_PAGE_C` is declared only in the clean tree, so a shared note writes
`+&4000` and only `notes/clean/` may use the name.

`tools/checkdocs.py` holds `docs/`, `notes/` and `design/` to the listings
for names and quoted instructions, and `docs/sam-basic-grammar.txt` to
the ROM's `CMDADT`: every `@ tok name` against the generated `[TOKENS]`
block, and every `ref/samrom` routine a `:` line cites against the token
that actually reaches it.  That second check exists because `COPY` and
`COPY CHR$` sat under `@ CF COPY` for a while and are DUMP's -- `CMDADT`
points `&BF` at the routine the ROM's source calls COPY and gives `&CF`
NONSENSE.  Prose that merely *names* a routine is not checked, so a
stale name in prose survives the build.

## References, and one trap

`ref/samrom/` is the SAM ROM source.  `ref/masterdos/src/masterdos23.asm`
is the 1991 author's own text.  **`ref/masterdos/annotated-src/` is this
project's AI-assisted annotation, not the author's** — quote `src/`.
`ref/masterdos/res/MDOS23.bin` (15750 bytes) is a *different binary* from
this image's DOS half (16320); it proves things about stock MasterDOS,
not about this one.

The dumps are listed, with what each holds, in `docs/evidence-wanted.md`.
A dump named in prose may not be the one that holds the bytes.  Check.

## skills/, which nothing loads

Nine skills extracted from this work, each a `SKILL.md` with its own
frontmatter: the gate and the three trees, the magic-number target and
the four faults its counter had, the review process, the evidence
register, Z80 idioms, the SAM itself.  `skills/README.md` is the index.

**They are an export.**  They are written to be moved into another
project's `.claude/skills/` and nothing in this repository loads them --
there is no `.claude/skills/` here, `settings.json` configures only
hooks, and Claude Code will not offer them by name.  Read them by path
or you will not find them at all.

What governs work here is this file and the hooks.  So a lesson worth
keeping goes to `skills/` when it is true of any such project and stays
here when it is this image's -- and one that lands in both is one that
will drift, which is the fault this project exists to catch.

## How to make a change

Use `tools/patch.py` for every edit to prose or a generator:

    import sys; sys.path.insert(0, 'tools')
    from patch import patch
    patch('docs/x.md', [('old, exactly, from the file', 'new')])

Write the edits into a `.py` file and run it in the foreground; never
through a heredoc and never in the same command as the build (the
assertion scrolls past and the build runs green on unmodified code).
Build the `old` string from the file, not from memory.

**The heredoc rule holds with a quoted delimiter too**, which is not what
the shell promises.  `cat > x.py <<'EOF'` collapses doubled backslashes
here exactly as an unquoted one does, so a `\\b` written into a regex
arrives in the file as `\b`, and Python -- reading a string that is not
raw -- turns that into a backspace.  That is how `re.compile(r"\b...")`
reached `.claude/hooks/guard.py` as a control character, in a file that
still parsed and still ran.  A doubled backslash is the tell; so is a
`SyntaxWarning: invalid escape sequence` naming a line you wrote with two.
Write the `.py` with the Write tool, or build it with `python -c` in
single shell quotes and no backslashes at all -- `chr(92)` for one you
cannot avoid -- and read back what landed before trusting it.

After correcting any figure, **grep the old value** across `docs/`,
`notes/`, `design/`, `tools/` and `listings/` until it is gone.  The same
wrong number is usually in more than one place, and checking the places
you changed proves nothing.

**A generated name needs the same grep, and a rename you did not intend
is the reason.**  Synthetic labels -- `S%04X`, and anything ending `_1`
or `_2` -- are derived from the nearest underived label above them, so
naming one routine renames its neighbours, and the build stays green
either way.  `checkdocs` catches only prose that quotes an instruction;
prose that merely names a routine survives, as above.  So read the label
diff after any rename, and grep the old *name* across `docs/`, `notes/`
and `design/` exactly as you would an old number.  `WAIT_NEXT_SCANLINE`
carried two labels off with it, one onto &7CF7 -- not an entry point at
all, but the address SAVE BOOT reads its first block from, so a name
about the raster landed on the source of a disc write.

A total that comes back *exactly* unchanged after a change that should
move it is a failure signal, not a result.

Five of these rules are enforced by hooks in `.claude/settings.json`,
implemented in `.claude/hooks/guard.py`: `git add -A`, edits under
`listings/`, a patch through a heredoc, and a patch and the build in one
command are **denied** -- the last of those reads any `.py` the command
runs to see whether it patches, and counts one it cannot read as one that
does, because its first version matched only paths with `scratchpad` in
them and a script written to `$TEMP` walked straight past it; an edit under `docs/`, `notes/` or `design/` runs
`checkdocs` and hands back anything stale; and `git commit` reports
`build.log`'s last line and whether the sources have changed since it
was written.  A denial is the rule working, not a fault -- `/hooks` lists
them.  `guard.py` is pipe-testable: feed it the hook JSON on stdin.

## Git

Another Claude session shares this clone.  Stage by explicit path, never
`git add -A`; look at `git status` first and leave what you did not
touch.  Re-check `HEAD` before committing.

**A `value` note that makes a *new* equate writes it into `base.asm`,
and `base.asm` is three files.**  Staging `listings/*/masterbasic.asm`
by name is right until a note adds a symbol and then silently wrong:
two commits went out referring to `T_LINE` with nothing declaring it --
byte-identical here, an assembly failure on checkout.  The build cannot
catch it, because the build reads the working tree and the commit reads
the index.  A hook now advises; `git diff --stat -- listings/*/base.asm`
is the check.

Because the other session's staged work sits in the same index, prefer
`git commit <paths>` -- the pathspec form -- over `git add` then `git
commit`, which commits everything staged, theirs included.  A `git
status` caught mid-operation can show their files as staged and clear a
moment later; `git diff --cached` settles it.

## Standing work

**Reviews** follow `design/reviewprocess.md`: agents write to scratch
only and never run `build.sh`; every finding is verified against the
instructions before it is applied; a finding right in substance with a
wrong subsidiary number is not confirmed.  Auditors have been wrong —
`PART G1` in the wrong tree, phantoms that were never phantoms — and are
checked like anything else.

**Magic numbers**: the target is *no unexplained number in a routine that
has been worked*, not zero numbers.  Some can never be named — an operand
inside a block written to run at another address, or a `&0000` a
signature search fills at boot — and take a comment saying so instead.
`python tools/sites.py NAME [half]` shows a routine with its outstanding
sites marked; `--list` gives the queue worst-first.

**Read the top entry before starting it.** `RELOCATED_TO_46CC` heads the
MasterBASIC queue and is a poor first target: most of its remaining sites
are operands inside a block that runs at `&46CC`, which can never be
named, only explained. `COPY_SCREEN_CONVERT` and `DUMP_UNSHADED` are
ordinary code and better places to begin. The count ranks sites, not
work; only reading the routine tells you which it is.  Its totals must equal
the build's; if they do not, `SITES_DEBUG=NAME bash tools/build.sh` prints
the addresses `clean.py` counted for that routine, to diff against.  A
second implementation of the same rule is what caught the build excusing
every `SUB`/`AND`/`CALL` line as if the mnemonic were a symbol.  Name only
what you can defend from the code; a wrong name is worse than a number.
