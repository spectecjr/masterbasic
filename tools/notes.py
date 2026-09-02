"""Read hand-written labels and notes from notes/*.txt.

Everything else in this pipeline derives its names from something -- the
annotated MasterDOS source, the ROM's tables, the manual, the shape of
the code.  This is the way in for knowledge that comes from a person
instead, and it is deliberately a plain text file rather than another
Python module, so that adding a name costs one line and no imports.

Eight kinds of entry, one per line, blank lines and # comments ignored
(a range takes one of three markers, which is why the list runs longer):

    MB &5934 SERINIT              name a routine (or any address)
        Set up the SCC2691.       indented lines below become its header
        C is SPORT, B the register.

    MB &593F : CR = &10, reset the MR pointer
                                  a comment on that one instruction

    DOS &4220-&42BC data DVAR     mark a range as data, and name its start
    MB &7E6B-&7FBF text           mark a range as text
    MB &4349-&43A0 code           mark a range as code

    DOS &4835 value DISKCTL_0_BASE
                                  name the number in that one instruction,
                                  where the same value means something
                                  different elsewhere

    EQU STKEND : end of the calculator stack
                                  describe a ROM name in the equate block

    AFTER CHECK_WRITE_STATUS : read the status through the patched port
                                  comment the instruction a label sits on,
                                  without looking its address up; +n steps
                                  on n instructions first

    DOC CHECK_WRITE_STATUS        head a routine by name rather than by
        The indented lines        address, so a rename does not strand it
        below become its header.

    RENAME ULA BORDER             change a name everywhere it is written

The page is MB or DOS.  Addresses are as the listings write them, so
&4000-&7FBF, and a range is inclusive of both ends.

Hand-written entries win.  Where one of these names an address something
else has already named, this one replaces it and the old name is
reported, because a disagreement between a person and a guess is worth
seeing rather than resolving silently.
"""

import os
import re

HEAD = re.compile(r'^(MB|DOS)\s+&([0-9A-Fa-f]{4})'
                  r'(?:\s*-\s*&([0-9A-Fa-f]{4}))?\s*(.*)$')
# A ROM name rather than an address in either page:  EQU STKEND : ...
EQUATE = re.compile(r'^EQU\s+(\w+)\s*:\s*(\S.*?)\s*$')
# AFTER CHECK_WRITE_STATUS : text -- comment the instruction a label sits
# on, without having to look its address up.  +n steps on n instructions.
AFTER = re.compile(r'^(?:AFTER|ADDCOMMENTAFTER)\s+(\w+)\s*(?:\+(\d+))?\s*:\s*(\S.*?)\s*$')
# DOC CHECK_WRITE_STATUS -- head a routine by name, with the indented
# lines below it, so no address has to be looked up.
DOC = re.compile(r'^(?:DOC|DOCUMENT)\s+(\w+)\s*$')
# RENAME ULA BORDER -- change a name everywhere it is written.
RENAME = re.compile(r'^RENAME\s+(\w+)\s+(\w+)\s*$')
KINDS = ('data', 'text', 'code', 'value', 'step')


def parse(path):
    """Entries from one file, in the order they appear."""
    out, cur, bad = [], None, []
    for n, raw in enumerate(open(path, encoding='utf-8'), 1):
        line = raw.rstrip()
        if not line.strip():
            # A blank line inside a description is a paragraph break; one
            # anywhere else just separates entries.
            if cur is not None and cur['doc']:
                cur['doc'].append('')
            continue
        if line.lstrip().startswith('#'):
            continue
        if line[0] in ' \t':                       # continuation
            if cur is None:
                raise ValueError('%s:%d: indented text with nothing above it'
                                 % (path, n))
            cur['doc'].append(line.strip())
            continue
        m = DOC.match(line)
        if m:
            cur = {'page': 'DOC', 'name': m.group(1), 'doc': [], 'addr': None,
                   'end': 0, 'comment': None, 'kind': None,
                   'where': '%s:%d' % (os.path.basename(path), n)}
            out.append(cur)
            continue
        m = AFTER.match(line)
        if m:
            cur = None
            out.append({'page': 'AFTER', 'name': m.group(1),
                        'end': int(m.group(2) or 0), 'comment': m.group(3),
                        'doc': [], 'addr': None, 'kind': None,
                        'where': '%s:%d' % (os.path.basename(path), n)})
            continue
        m = RENAME.match(line)
        if m:
            cur = None
            out.append({'page': 'RENAME', 'name': m.group(1),
                        'comment': m.group(2), 'doc': [], 'addr': None,
                        'end': None, 'kind': None,
                        'where': '%s:%d' % (os.path.basename(path), n)})
            continue
        m = EQUATE.match(line)
        if m:
            cur = None
            out.append({'page': 'EQU', 'name': m.group(1), 'doc': [],
                        'comment': m.group(2), 'addr': None, 'end': None,
                        'kind': None, 'where': '%s:%d'
                        % (os.path.basename(path), n)})
            continue
        m = HEAD.match(line)
        if not m:
            # A bad line is reported and skipped, not raised: one typo in
            # a notes file should not stop the listings being written.
            hint = ''
            if re.match(r'^RENAME\s+&', line):
                hint = ('  RENAME takes the old name; to name an address '
                        'write:  DOS %s' % line.split(None, 1)[1])
            bad.append('%s:%d: cannot read %r%s'
                       % (os.path.basename(path), n, line, hint))
            cur = None
            continue
        page, lo, hi, rest = m.group(1), int(m.group(2), 16), m.group(3), \
            m.group(4).strip()
        cur = {'page': page, 'addr': lo, 'end': int(hi, 16) if hi else None,
               'doc': [], 'comment': None, 'kind': None, 'name': None,
               'where': '%s:%d' % (os.path.basename(path), n)}
        if rest.startswith(':'):
            cur['comment'] = rest[1:].strip()
        else:
            bits = rest.split()
            if bits and bits[0] in KINDS:
                cur['kind'] = bits[0]
                bits = bits[1:]
            if bits:
                # A `value` may be given an expression of names already
                # defined rather than a name of its own, and that has
                # spaces in it: `value SYSPAGE_IN_B | ENABLE_ROM1`.
                cur['name'] = (' '.join(bits) if cur['kind'] == 'value'
                               else bits[0])
        out.append(cur)
    for e in out:
        while e['doc'] and not e['doc'][-1]:
            e['doc'].pop()
    return out, bad


def load(root, folder='notes'):
    """Every entry from the folder, or an empty list if there are none.

    The default is notes/, the working prose.  notes/clean/ holds the
    reading copy's prose, applied over the top of it and winning where
    the two disagree; both are the same eight kinds of entry, read by
    the same parser.
    """
    folder = os.path.join(root, folder)
    if not os.path.isdir(folder):
        return [], []
    out, complaints = [], []
    for name in sorted(os.listdir(folder)):
        if name.endswith('.txt'):
            got, bad = parse(os.path.join(folder, name))
            out.extend(got)
            complaints.extend(bad)
    return out, complaints


def set_header(d, a, doc, banner):
    """Head an address, keeping whatever header was already there.

    Yours goes first, but what it displaces is kept under it: a carried
    header often describes a group of routines and only happens to be
    attached to this one, so replacing it outright would lose what it
    said about the others.
    """
    body = list(doc)
    was = d.headers.get(a)
    if was:
        kept = [x[3:] if x.startswith(';; ') else x.lstrip(';')
                for x in was.split('\n')]
        kept = [x.rstrip() for x in kept
                if not x.strip().startswith('---')]
        while kept and not kept[0].strip():
            kept.pop(0)
        while kept and not kept[-1].strip():
            kept.pop()
        if kept:
            body += ['', 'What was here before:', '']
            body += ['    ' + x for x in kept]
    d.headers[a] = banner('\n'.join(body))


def apply(pages, root, banner, folder='notes'):
    """Put the entries on the pages.  Returns counts and complaints."""
    by_tag = dict((p.tag, p) for p in pages)
    named = noted = marked = stepped = 0
    problems = []
    kinds = {'data': 3, 'text': 5, 'code': 1}

    equates, later, expressions = {}, [], []
    entries, complaints = load(root, folder)
    problems.extend(complaints)
    for e in entries:
        if e['page'] in ('AFTER', 'DOC'):
            later.append(e)             # once every label has its name
            continue
        if e['page'] == 'RENAME':
            continue                    # done later, by rename()
        if e['page'] == 'EQU':
            equates[e['name']] = e['comment']
            # The same ROM address is named ROM_CHKHL in one listing and
            # CHKHL in the other, to keep clear of our own labels.  A
            # description of either is a description of both.
            bare = re.sub(r'^(J_|ROM_)', '', e['name'])
            if bare != e['name']:
                equates.setdefault(bare, e['comment'])
            else:
                for prefix in ('ROM_', 'J_'):
                    equates.setdefault(prefix + e['name'], e['comment'])
            noted += 1
            continue
        d = by_tag.get(e['page'])
        if d is None or not d.inside(e['addr']):
            problems.append('%s: &%04X is not in the %s page'
                            % (e['where'], e['addr'], e['page']))
            continue
        a = e['addr']

        if e['kind'] == 'value':
            # Naming a number in one instruction, not everywhere: &E0 is
            # the disk command register in most of the DOS and the base
            # of drive 1's port block here.  The value is read back out
            # of the instruction, so the equate cannot disagree with it.
            ins = d.insns.get(a)
            text = d.overrides.get(a, ins.text) if ins else None
            lits = re.findall(r'&[0-9A-Fa-f]+', text or '')
            if not ins:
                problems.append('%s: &%04X does not start an instruction'
                                % (e['where'], a))
            elif len(lits) != 1:
                problems.append('%s: %s has %d numbers in it, so which?'
                                % (e['where'], text, len(lits)))
            elif not e['name']:
                problems.append('%s: value needs a name' % e['where'])
            elif re.fullmatch(r'\w+', e['name']):
                d.overrides[a] = text.replace(lits[0], e['name'])
                d.user_equs[e['name']] = int(lits[0][1:], 16)
                named += 1
            else:
                # An expression of names already given, rather than a
                # name of its own: `SYSPAGE_IN_B | ENABLE_ROM1` says what
                # &5F is made of, and inventing a third equate for the
                # pair would say less.  Nothing is defined for it; it is
                # checked against the number instead, so a wrong
                # expression is a build error rather than a quiet lie.
                expressions.append((d, a, lits[0], e['name'], e['where']))
            continue

        if e['kind'] == 'step':
            # Narration.  A line comment says what one instruction does;
            # this says what the next few are for, and is set at the left
            # margin with a blank line above so that a routine reads as
            # the three or four moves it makes rather than as a wall.
            if not e['doc']:
                problems.append('%s: a step needs something under it'
                                % e['where'])
            else:
                d.steps[a] = list(e['doc'])
                stepped += 1
            continue

        if e['kind']:
            end = (e['end'] or a) + 1
            for x in range(a, min(end, d.limit)):
                d.setm(x, kinds[e['kind']])
                if e['kind'] != 'code':
                    d.insns.pop(x, None)
            marked += end - a

        if e['comment'] is not None:
            d.comments[a] = e['comment']
            noted += 1

        if e['name']:
            taken = [x for x, n in d.labels.items()
                     if n == e['name'] and x != a]
            if taken:
                problems.append('%s: %s is already the name of &%04X'
                                % (e['where'], e['name'], taken[0]))
            else:
                was = d.labels.get(a)
                if was and was != e['name'] and not re.match(
                        r'^(TBL_|[LV][0-9A-F]{4}$)', was):
                    problems.append('%s: &%04X was %s, now %s'
                                    % (e['where'], a, was, e['name']))
                # Anything already written as `L45AE+1` has to follow the
                # label, or it names a symbol that no longer exists.
                if was and was != e['name']:
                    pat = re.compile(r'\b%s\b' % re.escape(was))
                    for at, text in list(d.overrides.items()):
                        if pat.search(text):
                            d.overrides[at] = pat.sub(e['name'], text)
                d.labels[a] = e['name']
                named += 1

        if e['doc']:
            set_header(d, a, e['doc'], banner)

    # The AFTER lines run last, so that a label named further down the
    # same file can still be referred to by name further up.
    for d, a, lit, expr, where in expressions:
        want = int(lit[1:], 16)
        env = dict(d.user_equs)
        try:
            got = eval(re.sub(r'\w+', lambda m: str(env[m.group(0)])
                              if m.group(0) in env else m.group(0), expr),
                       {'__builtins__': {}}, {})
        except Exception:
            got = None
        if got != want:
            problems.append('%s: %s is %s, not %s'
                            % (where, expr,
                               '&%X' % got if isinstance(got, int)
                               else 'not a number I can work out',
                               lit))
            continue
        text = d.overrides.get(a, d.insns[a].text)
        d.overrides[a] = text.replace(lit, expr)
        named += 1

    for e in later:
        where = [(d, a) for d in pages
                 for a, n in d.labels.items() if n == e['name']]
        if not where:
            problems.append('%s: nothing is called %s'
                            % (e['where'], e['name']))
            continue
        if len(where) > 1:
            problems.append('%s: %s names %d addresses, so which?'
                            % (e['where'], e['name'], len(where)))
            continue
        d, a = where[0]
        if e['page'] == 'DOC':
            if e['doc']:
                set_header(d, a, e['doc'], banner)
                noted += 1
            else:
                problems.append('%s: DOC %s has no indented lines under it'
                                % (e['where'], e['name']))
            continue
        for _ in range(e['end']):                # step on n instructions
            ins = d.insns.get(a)
            if ins is None:
                break
            a = ins.end
        if not d._starts_insn(a):
            problems.append('%s: %s+%d is not an instruction'
                            % (e['where'], e['name'], e['end']))
            continue
        d.comments[a] = e['comment']
        noted += 1

    for d in pages:
        d.romdesc.update(equates)
    return named, noted, marked, stepped, problems


def rename(pages, root, folder='notes'):
    """Apply the RENAME lines, after every other pass has run.

    A name can have been put on the page by any of half a dozen passes
    and written into instruction text by another, so renaming is done
    last and everywhere at once: the label tables, the equate blocks,
    and the operand text of any instruction that was overridden.
    """
    entries, _ = load(root, folder)
    jobs = [(e['name'], e['comment'], e['where'])
            for e in entries if e['page'] == 'RENAME']
    done, problems = 0, []
    for old, new, where in jobs:
        hit = False
        # Track whether anything the listing actually prints was touched.
        # A name can exist as an unused ROM symbol in the other page --
        # SDC1 did -- and renaming that is not what anyone meant.
        real = False
        for d in pages:
            taken = [k for k, v in d.labels.items() if v == new]
            if taken:
                problems.append('%s: %s is already the name of &%04X'
                                % (where, new, taken[0]))
                continue
            for table in (d.mdos_equs, d.inferred, d.rst_equs,
                          d.basic_equs, d.user_equs):
                if old in table:
                    table[new] = table.pop(old)
                    hit = real = renamed_here = True
            # A ROM name lives in the symbol table rather than in any of
            # ours: it never appears as a label, only as the text an
            # operand resolves to.  Renaming it there is enough, because
            # relabel() regenerates every instruction afterwards.
            if d.syms:
                # code and data hold (expression, defining name, base);
                # vars holds the name on its own.
                for table in (d.syms.code, d.syms.data):
                    for value, (expr, defname, base) in list(table.items()):
                        if defname == old:
                            table[value] = (expr.replace(old, new, 1),
                                            new, base)
                            hit = renamed_here = True
                for value, defname in list(d.syms.vars.items()):
                    if defname == old:
                        d.syms.vars[value] = new
                        hit = renamed_here = True
            if old in d.used_ext:
                d.used_ext.discard(old)
                d.used_ext.add(new)
                hit = real = renamed_here = True

            # Whatever was known about the old name is known about the
            # new one: the name changed, not the thing.
            if old in d.romdesc:
                d.romdesc.setdefault(new, d.romdesc[old])
            for a, v in list(d.labels.items()):
                if v == old:
                    d.labels[a] = new
                    hit = real = renamed_here = True
            for a, v in list(d.ports.items()):
                if v == old:
                    d.ports[a] = new
                    hit = real = renamed_here = True
            # Only rewrite instruction text once the symbol itself has
            # been renamed in this page.  Substituting the text on its
            # own leaves an operand naming something nothing defines,
            # which is what happens when two notes rename one address and
            # the other one got there first.
            if not renamed_here:
                continue
            pat = re.compile(r'\b%s\b' % re.escape(old))
            for a, text in list(d.overrides.items()):
                if pat.search(text):
                    d.overrides[a] = pat.sub(new, text)
                    hit = real = True
        if hit and real:
            done += 1
        elif hit:
            problems.append('%s: %s renamed only something the listings do '
                            'not print -- an unused symbol of that name. Did '
                            'you mean a label?' % (where, old))
        else:
            problems.append('%s: nothing is called %s' % (where, old))

    # A `value` note may have named a number that a RENAME has since
    # given to an existing equate.  One name, two definitions, would not
    # assemble; the existing one wins and the duplicate goes.
    for d in pages:
        others = {}
        for table in (d.mdos_equs, d.inferred, d.rst_equs, d.basic_equs):
            others.update(table)
        for name, value in list(d.user_equs.items()):
            if name not in others:
                continue
            if others[name] == value:
                del d.user_equs[name]
            else:
                problems.append('%s is &%02X here and &%02X elsewhere'
                                % (name, value, others[name]))
    return done, problems


EMITTED = re.compile(r'^([A-Za-z_][A-Za-z_0-9]*):\s+EQU\b')


def check_equates(root, paths):
    """Report EQU lines naming a symbol no listing defines.

    An EQU names a symbol rather than an address, so a mistyped one
    quietly describes a name nothing mentions.  The symbol tables are not
    the place to check it -- ports and ROM entry points reach the listing
    by other routes -- so this reads back what was actually written.
    """
    defined = set()
    for path in paths:
        try:
            with open(path, encoding='utf-8') as f:
                for line in f:
                    m = EMITTED.match(line)
                    if m:
                        defined.add(m.group(1))
        except OSError:
            return []
    if not defined:
        return []
    out = []
    for e in load(root)[0]:
        if e['page'] == 'EQU' and e['name'] not in defined:
            out.append('%s: EQU %s describes no name either listing uses'
                       % (e['where'], e['name']))
    return out
