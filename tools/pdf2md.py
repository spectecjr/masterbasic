# -*- coding: utf-8 -*-
"""Rebuild docs/original/MasterBASIC User Manual.md from the manual PDF.

    pdftotext -layout -enc UTF-8 "docs/original/SAM Coupe MasterBASIC Manual.pdf" m.txt
    python tools/pdf2md.py m.txt "docs/original/MasterBASIC User Manual.md"

The PDF is an OCR of the printed manual, so neither extractor is trustworthy on
its own.  pypdf keeps the two halves of a table on the same row where pdftotext
-layout shifts one column against the other; pdftotext works out the reading
order where pypdf's text-layer coordinates drift down the page in jumps.  This
takes the lines from pypdf, the order from pdftotext, and the paragraph breaks
from the vertical gaps, which are quantised: 11 points is the next line of the
same paragraph, 22 a new one, and a block jump adds 101 to either.
"""

import io, json, pypdf, re, sys

PDF = r'docs/original/SAM Coupé MasterBASIC Manual.pdf'
FOOTER = re.compile(r'Sam Coup. MasterBasic page')


def pdf_lines(page):
    chunks = []
    def v(text, cm, tm, fd, fs):
        t = text.replace('\n', ' ').rstrip()
        if t.strip() and not FOOTER.search(t):
            chunks.append((round(tm[5], 1), round(tm[4], 1), t))
    page.extract_text(visitor_text=v)
    chunks.sort(key=lambda c: (-c[0], c[1]))
    rows, cur = [], []
    for c in chunks:
        if cur and abs(cur[0][0] - c[0]) < 4:
            cur.append(c)
        else:
            if cur: rows.append(cur)
            cur = [c]
    if cur: rows.append(cur)

    out, prev = [], None
    for grp in rows:
        grp.sort(key=lambda c: c[1])
        txt = grp[0][2].strip()
        for a, b in zip(grp, grp[1:]):
            gap = b[1] - (a[1] + len(a[2]) * 5.6)
            txt += ('  ' if gap > 8 else ' ') + b[2].strip()
        y = grp[0][0]
        out.append({'y': y, 'x': grp[0][1], 'text': txt,
                    'gap': 0.0 if prev is None else round(prev - y, 1)})
        prev = y
    return out


def key(s):
    return re.sub(r'\s+', ' ', s).strip()


def reorder(lines, layout):
    """Sort by where each line's opening words fall in pdftotext's stream."""
    ref = [key(l) for l in layout.split('\n') if l.strip()]
    used, order = [False] * len(ref), []
    for i, l in enumerate(lines):
        k = key(l['text'])
        head = k[:18]
        pos = None
        for j, r in enumerate(ref):
            if not used[j] and head and r.startswith(head[:min(len(head), len(r))]) \
                    and r.startswith(head[:12]):
                pos = j; used[j] = True; break
        order.append((pos, i))
    # lines that matched nothing keep the place of the line above them
    last = -1
    fixed = []
    for pos, i in order:
        if pos is None:
            pos = last + 0.5
        last = pos
        fixed.append((pos, i))
    fixed.sort(key=lambda t: (t[0], t[1]))
    out = [lines[i] for _, i in fixed]
    # the gap above each line, now that the neighbours are the final ones;
    # where the reorder moved a line up the page, fall back on its indent
    prev = None
    for l in out:
        if prev is None:
            l['gap'] = 0.0
        elif prev['y'] > l['y']:
            l['gap'] = round(prev['y'] - l['y'], 1)
        else:
            l['gap'] = 11.3 if abs(prev['x'] - l['x']) < 2 else 22.7
        prev = l
    return out


def extract(layout):
    r = pypdf.PdfReader(PDF)
    doc = []
    for n, page in enumerate(r.pages):
        ls = pdf_lines(page)
        if n < len(layout):
            ls = reorder(ls, layout[n])
        doc.append(ls)
    return doc


LAYOUT = open(sys.argv[1], encoding='utf-8').read().split(chr(12))
OUT = sys.argv[2]
LINES = extract(LAYOUT)
FOOTER = re.compile(r'Sam Coup. MasterBasic page')
LEFT = 85.1

KEYWORDS = set("""LET PRINT LPRINT INPUT DIM FOR NEXT IF THEN ELSE END GOTO GOSUB
RETURN STOP READ DATA RESTORE REM RUN LIST NEW SAVE LOAD MERGE VERIFY POKE DPOKE
CALL CLS CLEAR PLOT DRAW CIRCLE FILL BLITZ RECORD SOUND BEEP PAUSE PEN PAPER
BORDER INK FLASH BRIGHT INVERSE OVER MODE CSIZE PALETTE BLOCKS PUT GRAB ROLL
SCROLL SCREEN WINDOW AUTO POP DEF DEFAULT PROC LOCAL EXIT DO LOOP WHILE UNTIL
SORT JOIN DELETE EDIT SPLIT TRACE ON OFF KEY OPEN CLOSE FORMAT ERASE COPY RENAME
BACKUP MOVE DIR BOOT DEVICE RESERVE ALTER TIME DATE LABEL DISPLAY OUT IN
RANDOMIZE CONTINUE GO SET RESET SEARCH CHANGE HIDE LOCN RESERVED TICS SCRAD
INARRAY USING$ SVAL$ NVAL SHIFT$ EQU MEM$ FSTAT DSTAT DIR$ INP$ INKEY$ XVAR DVAR
SVAR PEEK DPEEK LENGTH ITEM DUMP REF RENUM""".split())


def gap_kind(g):
    """11 = next line of the same paragraph, 22 = new paragraph; a block jump
    adds 101 to either."""
    while g > 60 and g - 101 >= 8:
        g -= 101
    if g < 17:
        return 'cont'
    if g < 30:
        return 'break'
    return 'bigbreak'


def blocks(page):
    """Group a page's lines into paragraphs."""
    ls = [l for l in LINES[page] if not FOOTER.search(l['text'])]
    out, cur, prev, kind = [], [], None, 'break'
    for l in ls:
        k = 'break' if prev is None else gap_kind(l['gap'])
        if k != 'cont' and cur:
            cur[0]['gap'] = kind; out.append(cur); cur = []; kind = k
        cur.append(l)
        prev = l
    if cur:
        cur[0]['gap'] = kind; out.append(cur)
    split = []
    for b in out:
        left = [l for l in b if l['x'] < 100]
        mid = [l for l in b if l['x'] >= 140]
        if left and mid and len(left) + len(mid) == len(b):
            split.append(left); split.append(mid)
        else:
            split.append(b)
    return split

# ---- the contents ------------------------------------------------------
def parse_contents():
    secs, ents, cur = [], [], None
    for p in (1, 2):
        for l in LINES[p]:
            s = re.sub(r'\s+', ' ', l['text']).strip()
            if not s or FOOTER.search(s) or s.replace(' ', '') == 'CONTENTS':
                continue
            m = re.match(r'^(.*?)\s+(\d{1,3})$', s)
            if m and len(m.group(1)) > 3:
                t = m.group(1).strip()
                if ents and ents[-1][2] is None:
                    t = ents[-1][0] + ' ' + t; ents.pop()
                ents.append((t, cur, int(m.group(2))))
            elif s.endswith(':'):
                cur = s[:-1]; secs.append(cur)
            elif s.startswith('('):
                if secs:
                    secs[-1] += ' ' + s
                    for i, e in enumerate(ents):
                        pass
                cur = secs[-1] if secs else cur
            else:
                ents.append((s, cur, None))
    return secs, ents

SECTIONS, ENTRIES = parse_contents()
BY_PAGE = {}
for t, sec, p in ENTRIES:
    BY_PAGE.setdefault(p, []).append(t)

def norm(s):
    return re.sub(r'[^a-z0-9$*]+', ' ', s.lower()).strip()

def heading_here(page, s, seen=()):
    n = norm(s)
    if not n:
        return None
    hit = None
    for p in (page, page - 1, page + 1):
        for t in BY_PAGE.get(p, []):
            b = norm(t).split()
            if n.split()[0] == b[0] and len(b[0]) >= 3:
                if t not in seen:
                    return t
                hit = hit or t
    return hit

def caps_ratio(s):
    L = [c for c in s if c.isalpha()]
    return sum(c.isupper() for c in L) / len(L) if L else 0

def basic_line(s):
    return bool(re.match(r'^\d{1,5}\s+[A-Za-z*]', s.strip()))

def keyword_line(s):
    s = re.sub(r'^(?:or|e\.g\.|E\.g\.|eg\.?)\s+', '', s.strip())
    if not s or len(s) > 56 or s[0].islower():
        return False
    if s.endswith((',', ':', ';', '?', '!', '-')):
        return False
    if s.endswith('.') and not re.search(r'[)"$\d]\.$', s):
        return False
    if not re.search(r'[ (]', s):
        return False
    w = s.split()
    if len(w) > 1 and re.match(r'^[A-Z][a-z]{2,}$', w[1]):
        return False
    return re.split(r'[^A-Za-z$*]+', s)[0].upper() in KEYWORDS

DEFENT = re.compile(r'^(\d{1,3})\s+([A-Z][A-Za-z0-9$]*)\.\s*(.*)$')
TABLE = re.compile(r'\S {2,}\S')

# ---- turn one page's blocks into markdown -------------------------------
def align(texts):
    rows = [re.split(r'\s{2,}', t.strip()) for t in texts]
    n = max(len(r) for r in rows)
    if n < 2:
        return texts
    w = [max((len(r[i]) for r in rows if len(r) > i and i < len(r) - 1), default=0)
         for i in range(n)]
    return ['  '.join(f.ljust(w[i]) if i < len(r) - 1 else f
                      for i, f in enumerate(r)).rstrip() for r in rows]


def title_case(s):
    if re.match(r'^\d+\s*=', s.strip()):
        return False
    w = [x for x in re.split(r'\s+', s.strip()) if len(x) > 2]
    return len(w) >= 2 and sum(x[0].isupper() for x in w) / len(w) >= .75


def render(page, seen, doc):
    for blk in blocks(page):
        texts = [b['text'].rstrip() for b in blk]
        x0 = min(b['x'] for b in blk)
        first = texts[0]

        # a running section head, centred on the page
        if len(blk) == 1 and x0 > 140 and caps_ratio(first) >= .7:
            doc.append(('h2', first)); continue

        # a heading the contents vouches for
        if len(blk) <= 5 and len(first) < 58:
            t = heading_here(page, first, seen)
            if t and t not in seen:
                seen.add(t)
                doc.append(('h2', first))
                if texts[1:]:
                    for extra in texts[1:]:
                        t2 = heading_here(page, extra, seen)
                        if t2:
                            seen.add(t2)
                    doc.append(('code', texts[1:]))
                continue

        # an XVAR / DVAR entry
        if page in range(48, 53):
            m = DEFENT.match(first)
            if m:
                rest = ' '.join([m.group(3)] + texts[1:]).strip()
                doc.append(('p', '**%s %s.** %s' % (m.group(1), m.group(2), rest)))
                continue

        # tabulated lines keep their columns
        if sum(bool(TABLE.search(t)) for t in texts) >= max(2, len(texts) * .6):
            doc.append(('pre', align(texts))); continue

        # program listings and typed-in commands
        if (all(basic_line(t) or keyword_line(t) for t in texts) and not (
                len(texts) == 1 and caps_ratio(first) >= .9
                and len(first.split()) >= 3)):
            doc.append(('code', texts)); continue

        # a short capitalised line on its own is a sub-heading
        if (len(blk) == 1 and len(first) < 58 and x0 < 140
                and (caps_ratio(first) >= .7 or title_case(first)
                     or blk[0].get('gap') == 'bigbreak')
                and len(first.split()) <= 8):
            doc.append(('h3', first)); continue

        doc.append(('p', ' '.join(texts), len(texts[-1])))

# ---- assemble -----------------------------------------------------------
doc, seen = [], set()
for p in range(3, 59):
    if not LINES[p]:
        continue
    if p in (53, 54, 55):
        rows = [l.rstrip() for l in LAYOUT[p].splitlines()
                if l.strip() and not FOOTER.search(l)]
        head = rows.pop(0).strip()
        m = re.match(r'^(APPENDIX A.*?)(?:\s{2,}page (\d)\.)?$', head)
        doc.append(('h2', 'APPENDIX A — ASCII and keyword codes') if not m.group(2)
                   else ('h3', 'Codes, part %s' % m.group(2)))
        if p == 53:
            intro, rest = [], []
            for r in rows:
                (rest if rest or r.lstrip().startswith('Dec ') else intro).append(r)
            doc.append(('p', ' '.join(x.strip() for x in intro), 0))
            rows = rest
        doc.append(('pre', rows))
        continue
    n = len(doc)
    render(p, seen, doc)
    # a paragraph broken by the page turn
    if n and n < len(doc) and doc[n - 1][0] == 'p' and doc[n][0] == 'p':
        prev, nxt = doc[n - 1], doc[n]
        if len(prev) > 2 and prev[2] >= 55 and (
                nxt[1][0].islower() or not prev[1].rstrip().endswith(('.', '!', '?', ':', '"'))):
            doc[n - 1] = ('p', prev[1] + ' ' + nxt[1], nxt[2] if len(nxt) > 2 else 0)
            del doc[n]

out = []
def emit(s=''):
    if s or (out and out[-1]):
        out.append(s)

emit('# SAM Coupé MasterBASIC — User Manual')
emit()
emit('*© 1991 Andrew J. A. Wright. First edition, June 1991. All rights reserved.*')
emit()
emit('Converted to Markdown from `SAM Coupé MasterBASIC Manual.pdf`, the PDF that')
emit('Steve Parry-Thomas compiled in December 2004 from an OCR of the printed')
emit('manual. Lines have been rejoined into paragraphs, typed-in examples set as')
emit('code and tables kept in the columns they were laid out in. The wording is')
emit("otherwise as the PDF has it, OCR slips and all; the one exception is the")
emit("machine's own name, which the OCR mangled in two different ways and which")
emit("is spelt properly here. Page numbers in the contents are the printed")
emit("manual's. Regenerate with `tools/pdf2md.py`.")
emit()
emit('---')
emit()
emit('## Contents')
emit()
last = object()
for t, sec, p in ENTRIES:
    if t.startswith('APPENDIX'):
        sec = None
    if sec != last:
        last = sec
        if sec:
            emit(); emit('**%s**' % sec); emit()
    emit('- %s — *page %s*' % (t, p))
emit()
emit('---')
emit()

for item in doc:
    k = item[0]
    if k == 'h2':
        emit(); emit('## ' + item[1]); emit()
    elif k == 'h3':
        emit(); emit('### ' + item[1]); emit()
    elif k == 'p':
        emit(item[1]); emit()
    elif k == 'code':
        emit('```basic'); out.extend(item[1]); emit('```'); emit()
    elif k == 'pre':
        emit('```text'); out.extend(item[1]); emit('```'); emit()

txt = re.sub(r'\n{3,}', '\n\n', '\n'.join(out)).replace('Coupè', 'Coupé').replace('Coup6', 'Coupé')
io.open(OUT, 'w', encoding='utf-8', newline='\n').write(txt.rstrip() + '\n')
print('wrote %d lines; %d of %d contents entries matched' % (
    txt.count('\n') + 1, len(seen), len(ENTRIES)))
print('unmatched:', [t for t, s, p in ENTRIES if t not in seen])
