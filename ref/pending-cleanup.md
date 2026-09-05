# Cleanup owed once the technical-manual PR lands

This file exists because a submodule is temporarily in a state the
repository cannot record, and the tidy-up cannot be done until someone
else acts. **Delete it once the list below is done.**

## The PR

[stefandrissen/sam-coupe-technical-manual#5](https://github.com/stefandrissen/sam-coupe-technical-manual/pull/5)
— four corrected addresses in the system variable tables, from
`spectecjr:fix-sysvar-addresses`. The reasoning is in
[notes/samtech.txt](../notes/samtech.txt), under "FOUR ERRORS IN THE
TRANSCRIPTION ITSELF".

## Why the submodule looks dirty

`ref/sam-coupe-technical-manual` is checked out on the branch
`fix-sysvar-addresses`, not on the commit this repository records. That
is deliberate and harmless: the branch is pushed to the fork, so nothing
is only in the working tree.

**The recorded commit is upstream's `a29a93e`, and it must stay that
way until the PR is merged.** It was briefly `4004be3` — the branch's
own commit — which would have broken a fresh clone: that SHA exists only
on `spectecjr/sam-coupe-technical-manual`, while the submodule's
`origin` is `stefandrissen/...`, so `git submodule update --init` could
not have fetched it. Restored, but worth watching: a `git add -A` in the
repository root will record whatever the submodule is checked out at, so
check `git diff --cached ref/` before committing while this file exists.

## When the PR is merged

```sh
cd ref/sam-coupe-technical-manual
git checkout main
git pull origin main              # picks up the merged change
git branch -d fix-sysvar-addresses
git remote remove fork            # only needed while the PR is open
cd ../..
git add ref/sam-coupe-technical-manual
git commit -m "Track the technical manual's merged address fixes"
```

Then check the four rows are actually right in the merged file — a
maintainer may have taken the change in a different shape:

| | should read |
|---|---|
| `OVERT` | `5A53` |
| `Reserved` | `5A71` |
| `TEMPW1` | `5AC8` |
| `LSPTR` | `5B8B` |

and update `notes/samtech.txt`, which currently states all four as
present in the transcription. It should say they were found here and
fixed upstream, with the PR number, so the next reader does not go
looking for errors that are gone.

## If part of it is not taken

`LSPTR` is the one to watch. The other three are a single OCR
substitution — `5A` read as `53`, three times — and are squarely within
what the project says it fixes. `LSPTR 5B8E -> 5B8B` may be an error in
the printed manual rather than in the scan, and a maintainer could
reasonably prefer to keep the transcription faithful to the page.

If it is dropped, leave it in the typo list in `notes/samtech.txt` and
say it is the manual's own and knowingly not fixed upstream — the same
treatment `SQN`/`SOR` and `NOTE` already get there.

## If the PR is rejected or goes stale

Nothing here depends on it. The corrections are recorded in
`notes/samtech.txt` and every address in the manual is checked against
`ref/samrom/vars.asm` before this project relies on it, which is what
found them in the first place. Reset the submodule to `main`, delete the
branch, and delete this file.
