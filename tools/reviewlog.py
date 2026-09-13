# -*- coding: utf-8 -*-
"""The review score log, and whether the rounds are converging.

    python tools/reviewlog.py            # every round, then the trend
    python tools/reviewlog.py --csv      # the rows as read, for checking

design/reviews.csv holds one row per region per round, with the counts
the audit produced: findings, their [C]/[P]/[G] split as filed, and how
many were confirmed, partly right, refuted or deferred on audit.  Rows
from before the log existed carry blanks where nothing was written down
at the time; a blank is "not recorded", never zero.

Three figures are printed per round, because each answers a different
question and no one of them is the stopping signal on its own:

  * findings per 100 lines of this project's prose -- how dense the
    errors still are where the reviewer looked.  Falling means the
    commentary is getting cleaner; it is the number to watch.
  * confirmed rate -- how far the reviewer's claims survive the audit.
    This has stayed near 100% by design (the prompt spends a third of
    its length on not guessing), so a drop says the brief has drifted,
    not that the code got harder.
  * the [C] share of what was filed -- when a round starts coming back
    mostly [G], the reviewer is reaching for suspicions, which is what
    a region with little left to find looks like from the outside.

The rows are data, not a leaderboard.  A region that returns nothing is
evidence the commentary there is sound; a region that returns twenty
is one to re-read by hand, because a review samples the errors and does
not exhaust them.
"""
import csv
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, 'design', 'reviews.csv')


def num(s):
    """An integer cell, or None for a blank or a note in words."""
    s = (s or '').strip()
    return int(s) if s.isdigit() else None


def rows():
    with io.open(LOG, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def main(argv):
    data = rows()
    if '--csv' in argv:
        for r in data:
            print(r)
        return
    rounds = {}
    for r in data:
        rounds.setdefault(r['round'], []).append(r)
    print('%-6s %-11s %-6s %6s %8s %6s %7s %5s %7s %7s'
          % ('round', 'date', 'half', 'lines', 'findings', 'conf', 'rate',
             'C', 'C+P+G', 'per100'))
    trend = []
    for k in sorted(rounds, key=lambda x: (len(x), x)):
        rs = [r for r in rounds[k] if r['shape'] == 'review']
        if not rs:
            continue
        lines = [num(r['own_lines']) for r in rs]
        finds = [num(r['findings']) for r in rs]
        conf = [num(r['confirmed']) for r in rs]
        cs = [num(r['C']) for r in rs]
        marked = [(num(r['C']) or 0) + (num(r['P']) or 0) + (num(r['G']) or 0)
                  for r in rs if num(r['C']) is not None]
        f_tot = sum(x for x in finds if x is not None)
        c_tot = sum(x for x in conf if x is not None)
        scored = sum(f for f, c in zip(finds, conf) if f is not None and c is not None)
        rate = '%3d%%' % (100.0 * c_tot / scored) if scored else '  --'
        l_tot = sum(x for x in lines if x is not None)
        f_on_lines = sum(f for f, l in zip(finds, lines) if f is not None and l is not None)
        per100 = '%6.1f' % (100.0 * f_on_lines / l_tot) if l_tot else '    --'
        c_sum = sum(x for x in cs if x is not None)
        m_sum = sum(marked)
        cshare = '%3d%%' % (100.0 * c_sum / m_sum) if m_sum else ' --'
        dates = sorted({r['date'] for r in rs if r['date']})
        halves = ''.join(sorted({r['half'] for r in rs}))
        print('%-6s %-11s %-6s %6s %8d %6d %7s %5s %7d %7s'
              % (k, dates[0] if dates else '', halves,
                 l_tot or '--', f_tot, c_tot, rate, cshare, m_sum, per100))
        if l_tot:
            trend.append((k, 100.0 * f_on_lines / l_tot))
    print()
    print('%d regions reviewed, %d findings, %d confirmed on audit'
          % (sum(1 for r in data if r['shape'] == 'review' and num(r['findings']) is not None),
             sum(num(r['findings']) or 0 for r in data if r['shape'] == 'review'),
             sum(num(r['confirmed']) or 0 for r in data if r['shape'] == 'review')))
    if len(trend) >= 2:
        first, last = trend[0][1], trend[-1][1]
        print('findings per 100 own lines: round %s %.1f -> round %s %.1f'
              % (trend[0][0], first, trend[-1][0], last))
    else:
        print('findings per 100 own lines is recorded for %d round(s); '
              'the trend needs two' % len(trend))
    blanks = sum(1 for r in data if r['shape'] == 'review' and num(r['own_lines']) is None)
    if blanks:
        print('%d review rows have no own-line count, so they are outside the density figure'
              % blanks)


if __name__ == '__main__':
    main(sys.argv[1:])
