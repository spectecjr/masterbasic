# -*- coding: utf-8 -*-
"""Deterministic guards for this project, run by Claude Code hooks.

    python .claude/hooks/guard.py <check>      hook JSON arrives on stdin

Each check enforces one rule from CLAUDE.md that was broken, or nearly
broken, by hand at least once.  Which event runs which is in
.claude/settings.json.

  git-add        deny `git add -A` / `--all` / `.` -- another session
                 shares this clone; stage by path
  listings       deny Edit/Write under listings/ -- they are generated,
                 and the next build silently overwrites the edit
  heredoc-patch  deny a shell heredoc that imports patch -- escapes get
                 mangled; write the edits to a .py file
  patch-build    deny a .py that patches and build.sh in one command -- a
                 failed patch scrolls past and the build runs green on
                 unmodified code.  Any .py the command runs is read to
                 see whether it patches, and one that cannot be read
                 counts as one that does
  checkdocs      after an edit under docs/ notes/ design/, run
                 tools/checkdocs.py and hand back anything stale
  commit         before git commit, report build.log's last line and
                 whether anything under listings/ notes/ tools/ has
                 changed since it was written, and whether base.asm is
                 modified but not named -- a `value` note that makes a
                 new equate declares it there, and staging the halves by
                 name drops it.  Advisory only.

A deny prints the reason; the tool call does not run.  Anything
unexpected -- no stdin, odd JSON -- exits 0 with no output, so a broken
hook can never lock the session.
"""
import io
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def out(obj):
    sys.stdout.write(json.dumps(obj))
    sys.exit(0)


def deny(reason):
    out({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason}})


def advise(event, context, message=None):
    o = {"hookSpecificOutput": {"hookEventName": event,
                                "additionalContext": context}}
    if message:
        o["systemMessage"] = message
    out(o)


# ---- the checks ----------------------------------------------------

HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n(.*?)^\2\s*$",
                     re.S | re.M)


def without_heredocs(cmd):
    """The command with its heredoc bodies removed.

    A commit message fed through `git commit -F - <<'EOF'` is content,
    not a command, and one that *describes* `git add -A` or a patch
    followed by a build must not trip the guards for them.  The first
    commit of these hooks did exactly that.
    """
    return HEREDOC.sub("<<heredoc>>", cmd)


GIT_ADD_ALL = re.compile(
    r"\bgit\s+add(?:\s+[^\s|;&]+)*\s+(?:-A|--all|\.)(?=\s|$|[|;&])")


def git_add(cmd, path):
    if GIT_ADD_ALL.search(without_heredocs(cmd)):
        deny("git add -A / --all / . is blocked: another session shares this "
             "clone. Look at git status and stage by explicit path.")


def listings(cmd, path):
    if re.search(r"(^|/)listings/", path):
        deny("%s is generated. Edit notes/ (or notes/clean/ for the reading "
             "copy) and rebuild; an edit here is overwritten by the next "
             "build." % path)


def heredoc_patch(cmd, path):
    if re.search(r"python3?\s+-\s*<<", cmd) and "from patch import" in cmd:
        deny("A patch through a shell heredoc: escapes like \\b and \\d get "
             "mangled on the way in. Write the edits to a .py file with the "
             "Write tool and run that.")


PY_RUN = re.compile(r"python3?(?:\s+-[A-Za-z]\w*)*\s+(\S+\.py)")
BUILD_SH = re.compile(r"(^|[\s;&|(])(?:bash\s+|sh\s+)?\S*tools/build\.sh")
IMPORTS_PATCH = re.compile(r"\b(?:from|import)\s+patch\b")


def patches(script):
    """Whether a .py the command runs is a patch script.

    Read it if it is there.  A script that cannot be read counts as one
    that patches: an unreadable name and the build in a single command is
    exactly the shape the rule is about, and guessing `harmless' is the
    guess that lets the failure through.  The first version of this rule
    matched only paths with `scratchpad' in them, and a script written to
    $TEMP walked straight past it -- the patch landed, but only because
    it was checked by hand afterwards.
    """
    name = script.strip("\"'")
    if "$" in name or "%" in name:      # an unexpanded variable: unreadable
        return True
    for cand in (name, os.path.join(ROOT, name)):
        try:
            with io.open(cand, encoding="utf-8", errors="replace") as f:
                return bool(IMPORTS_PATCH.search(f.read()))
        except (OSError, IOError):
            continue
    return True


def patch_build(cmd, path):
    # The .py has to be RUN and the build INVOKED -- a command that merely
    # mentions both, in a commit message say, is not the thing.
    c = without_heredocs(cmd)
    if not BUILD_SH.search(c):
        return
    if IMPORTS_PATCH.search(c) or any(patches(s) for s in PY_RUN.findall(c)):
        deny("A patch and tools/build.sh in one command: if the patch fails "
             "its assertion scrolls past and the build runs on unmodified "
             "code. Run the patch, read its output, then build.")


PROSE = re.compile(r"(^|/)(docs|notes|design)/")


def checkdocs(cmd, path):
    if not PROSE.search(path):
        return
    try:
        r = subprocess.run(["python", os.path.join("tools", "checkdocs.py")],
                           cwd=ROOT, capture_output=True, text=True,
                           timeout=120)
    except Exception as e:  # noqa: BLE001 -- never lock the session
        advise("PostToolUse", "checkdocs could not run: %s" % e)
    text = (r.stdout + r.stderr).strip()
    last = text.split("\n")[-1] if text else ""
    if r.returncode != 0 or "except" in last:
        stale = [l for l in text.split("\n") if l.strip().startswith("stale:")]
        advise("PostToolUse",
               "tools/checkdocs.py after editing %s:\n%s\n%s"
               % (os.path.relpath(path, ROOT) if path.startswith(ROOT.replace("\\", "/")) else path,
                  "\n".join(stale[:20]), last),
               message="checkdocs: " + last)
    # quiet on success: "N prose files check out" is the normal case


def newest_under(dirs):
    best = (0, None)
    for d in dirs:
        top = os.path.join(ROOT, d)
        for dp, _dn, fns in os.walk(top):
            if "__pycache__" in dp:
                continue
            for fn in fns:
                p = os.path.join(dp, fn)
                try:
                    m = os.path.getmtime(p)
                except OSError:
                    continue
                if m > best[0]:
                    best = (m, os.path.relpath(p, ROOT))
    return best


BASE_ASM = ("listings/clean/base.asm", "listings/disasm/base.asm",
            "listings/speculate/base.asm")


def base_left_out(cmd):
    """base.asm files modified in the tree but not named in this commit.

    A `value` note that makes a NEW equate declares it in base.asm and
    not in either half, and base.asm is three files.  Staging
    listings/*/masterbasic.asm by name is right until a note adds a
    symbol and then silently wrong: the listings go out referring to a
    name nothing declares.  The build cannot see it -- the build reads
    the working tree and the commit reads the index.
    """
    if re.search(r"commit\b[^|;]*\s-a\b", cmd):
        return []                       # -a stages every tracked change
    try:
        p = subprocess.run(["git", "status", "--porcelain", "--"] +
                           list(BASE_ASM), cwd=ROOT,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        text = p.stdout.decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return []
    # Each path is tested on its own: naming one tree's base.asm says
    # nothing about the other two, and all three move together.
    return [f for f in (l[3:].strip() for l in text.splitlines() if l.strip())
            if f not in cmd]


def commit(cmd, path):
    if not re.search(r"\bgit\s+commit\b", without_heredocs(cmd)):
        return
    stray = base_left_out(without_heredocs(cmd))
    if stray:
        advise("PreToolUse",
               "base.asm is modified and not in this commit: %s. A `value` "
               "note that makes a new equate declares it there, so the "
               "listings would go out referring to a name nothing defines. "
               "Check `git diff --stat -- listings/*/base.asm`."
               % ", ".join(stray), "base.asm left out")
    log = os.path.join(ROOT, "build.log")
    if not os.path.exists(log):
        advise("PreToolUse", "build.log does not exist: nothing has been "
               "built in this checkout.", "no build.log")
    with io.open(log, encoding="utf-8", errors="replace") as f:
        lines = [l.rstrip() for l in f if l.strip()]
    last = lines[-1] if lines else "(empty)"
    built = os.path.getmtime(log)
    age = int((time.time() - built) / 60)
    m, newest = newest_under(("listings", "notes", "tools"))
    if m > built:
        later = int((m - built) / 60)
        ctx = ("build.log: %r, %d min old. STALE: %s changed %d min after "
               "that build. A prose-only change needs only checkdocs; "
               "anything under listings/ notes/ tools/ needs a rebuild "
               "before this commit." % (last, age, newest, later))
        advise("PreToolUse", ctx, "build is stale: " + newest)
    advise("PreToolUse",
           "build.log: %r, %d min old; nothing under listings/ notes/ "
           "tools/ has changed since." % (last, age))


CHECKS = {
    "git-add": git_add,
    "listings": listings,
    "heredoc-patch": heredoc_patch,
    "patch-build": patch_build,
    "checkdocs": checkdocs,
    "commit": commit,
}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in CHECKS:
        sys.stderr.write(__doc__)
        return
    try:
        data = json.load(sys.stdin)
    except Exception:  # noqa: BLE001
        return
    ti = data.get("tool_input") or {}
    cmd = ti.get("command") or ""
    path = (ti.get("file_path") or "").replace("\\", "/")
    CHECKS[sys.argv[1]](cmd, path)


if __name__ == "__main__":
    main()
