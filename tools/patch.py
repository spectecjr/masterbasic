# -*- coding: utf-8 -*-
"""Exact-match text edits, with the failure modes this project hits.

Almost every change to prose or to a generator here is the same shape:
find one exact run of text, replace it, and fail loudly if it is not
there exactly once.  That scaffold had been retyped into thirty-one
throwaway scripts in a single session, which is thirty-one chances to
get one of the details wrong.

    from patch import patch

    patch('docs/how-it-works.md', [
        ('the old text, exactly', 'the new text'),
        ('another', 'another'),
    ])

Nothing is written until every edit in the list has matched, so a
half-applied file is not a state this can leave behind.

THE THREE WAYS THIS GOES WRONG, all of which have happened:

1.  The `old` string is written from memory instead of from the file.
    "The DOS's is a long tail" against a file that says "are".  When a
    match fails, this prints the point where the two diverge and what
    the file has there, which turns a hunt into a glance.

2.  Escapes are mangled getting here.  A shell heredoc eats \\b and \\d,
    and an em dash pasted as "--" will not match a file holding U+2014.
    Write the edits into a .py file and run it; do not pipe them through
    a heredoc.

3.  The script is backgrounded together with the build, so its assertion
    failure scrolls past unread and the build then runs green on
    unmodified code -- with the totals unchanged, which reads like a
    result and is not.  Run the patch, see it print, then build.

Newlines are written as LF: the listings and notes are LF, git converts
on checkout, and a stray CRLF makes the next exact match fail.
"""
import io
import sys


def _diverge(hay, needle):
    """How much of `needle` is in `hay`, by longest matching prefix."""
    lo, hi = 0, len(needle)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if needle[:mid] in hay:
            lo = mid
        else:
            hi = mid - 1
    return lo


def _report(path, old, text, found):
    """Say where the match went wrong, not just that it did."""
    out = ['%s: expected 1 match, found %d' % (path, found)]
    if found > 1:
        out.append('  the text is not unique -- add a line of context')
        out.append('  first: %r' % old[:70])
        return '\n'.join(out)
    n = _diverge(text, old)
    if n == 0:
        out.append('  nothing of it matched; first line: %r' % old.split('\n')[0][:70])
        return '\n'.join(out)
    at = text.index(old[:n])
    out.append('  matched the first %d characters, then diverged:' % n)
    out.append('    file wants: %r' % text[at + n:at + n + 60])
    out.append('    you  wrote: %r' % old[n:n + 60])
    return '\n'.join(out)


def patch(path, edits, quiet=False):
    """Apply (old, new) pairs to a file, each matching exactly once."""
    text = io.open(path, encoding='utf-8').read()
    staged = text
    for old, new in edits:
        found = staged.count(old)
        if found != 1:
            raise SystemExit(_report(path, old, staged, found))
        staged = staged.replace(old, new, 1)
    io.open(path, 'w', encoding='utf-8', newline='\n').write(staged)
    if not quiet:
        print('%s: %d edits applied' % (path, len(edits)))
    return staged


def sub_once(path, old, new, quiet=False):
    """One edit, for when a list of one reads worse than a call."""
    return patch(path, [(old, new)], quiet=quiet)


if __name__ == '__main__':
    print(__doc__.strip())
    sys.exit(0)
