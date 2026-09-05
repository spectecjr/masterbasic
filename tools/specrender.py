"""Turn the analysis into the text that goes in listings/speculate/.

Two things are produced.  Per-line notes name the idioms this codebase
uses over and over, which is the part a Z80 programmer new to it needs
most: the same eight instructions mean "page the ROM's variables in"
everywhere they appear, and saying so once per occurrence is cheaper
than making the reader work it out each time.

Per-routine banners carry the derived contract, then a reading of what
the routine is for.  The reading is composed from what the routine
actually touches -- the ROM variables it names, the routines it calls,
how it ends -- so it is a summary of evidence rather than an
impression.  It still gets a `?`, because a summary of evidence is not
the same as knowing.
"""

import re

import regs

WINDOW = ('SET 7,H', 'RES 6,H')
SYNTHETIC = re.compile(r'^[LV][0-9A-F]{4}$')


def notes_for(d, bodies):
    """Per-line notes, keyed by address."""
    out = {}
    order = sorted(d.insns)
    at = dict((a, i) for i, a in enumerate(order))
    starts = set(s for s, _e, _n in bodies)

    for i, a in enumerate(order):
        text = d.insns[a].text
        nxt = d.insns[order[i + 1]].text if i + 1 < len(order) else ''

        if text == WINDOW[0] and nxt == WINDOW[1]:
            out[a] = ('HMPR is 0, so setting bit 7 and clearing bit 6 turns '
                      'an address in &4000-&7FFF into the same byte of the '
                      "ROM's system page at &8000-&BFFF")
        elif text == 'BIT 6,H':
            out[a] = ("the rotating window check: if HL has walked out of "
                      "section C into section D, the page goes up by one "
                      "and RES 6,H brings HL back &4000 lower onto the same "
                      "byte.  The Technical Manual gives this idiom as the "
                      "standard way to walk a structure longer than 16K")
        elif text.startswith('EX (SP),HL') and a in starts:
            out[a] = ('the return address becomes HL, so what follows the '
                      'call is data this routine reads, not code')
        elif text == 'IN A,(URPORT)':
            out[a] = 'save HMPR before changing what is at &8000'
        elif text == 'IN A,(LRPORT)':
            out[a] = 'save LMPR before changing what is at &0000 and &4000'
        elif text.startswith('JP (') and not text.startswith('JP (SP'):
            out[a] = 'dispatch: the address was worked out above'
        elif text.startswith('LD SP,'):
            out[a] = 'the stack is being reset, so this path does not return'

        # The inline-parameter conventions.  These are most of what the
        # two halves do, and none of them look like a call with an
        # argument unless you already know the convention.
        if a not in out and text.startswith('CALL') and d.inside(a + 3)                 and d.m(a + 3) == 7:                       # PARAM follows
            who = d.labels.get(d.insns[a].target, '')
            v = d.word(a + 3)
            nm = d.word_operand(v, a + 3) if v is not None else '?'
            if who in ('NRRD', 'NRRDD'):
                out[a] = ('read the ROM variable %s -- the word below is its '
                          'address, and the call returns past it' % nm)
            elif who in ('NRWR', 'NRWRD', 'NRWRHL'):
                out[a] = 'write the ROM variable %s' % nm
            elif who == 'CMR':
                out[a] = ('call the ROM at %s with ROM1 paged in, and page '
                          'back on the way out' % nm)
            elif who in ('CALLDOS', 'CALLMB'):
                out[a] = ('call %s in the other page: LMPR is switched '
                          'first, so that address is how the other listing '
                          'numbers it' % nm)

        if a not in out and text in ('EXX', "EX AF,AF'"):
            out[a] = 'to the alternate register set and back again'

        # A write into the middle of an instruction is self-modifying code.
        m = re.match(r'^LD \((&[0-9A-F]{4}|[A-Za-z_]\w*)\),', text)
        if m and a not in out:
            t = d.insns[a].target
            if t is not None and d.inside(t) and d.m(t) == 1:
                pass
            elif t is not None and d.inside(t) and d.m(t) == 2:
                owner = t - 1
                while owner > d.base and not d._starts_insn(owner):
                    owner -= 1
                if d._starts_insn(owner):
                    out[a] = ('self-modifying: patches the operand of the %s '
                              'at &%04X' % (d.insns[owner].text.split()[0],
                                            owner))
    return out


def signals(d, s, e):
    """What a routine names: ROM variables, tokens, errors, ports.

    The inline word after a CALL is the interesting one -- NRRD and CMR
    both take a ROM address there, so it says which variable or routine
    the code is reaching for, which is the best single clue to purpose.
    """
    rom, toks, errs = [], [], []
    for a, insn in walk_body(d, s, e):
        text = insn.text
        if text.startswith('CALL') and d.inside(insn.end)                 and d.m(insn.end) == 7:                    # PARAM
            v = d.word(insn.end)
            if v is not None:
                nm = d.word_operand(v, insn.end)
                if nm and not nm.startswith('&') and nm not in rom:
                    rom.append(nm)
        m = re.match(r'^(?:CP|SUB|LD A,) ?(T_[A-Z_0-9]+|CH_[A-Z]+|FN_PFX)$',
                     d.overrides.get(a, text))
        if m and m.group(1) not in toks:
            toks.append(m.group(1))
        if text.startswith('RST ERR_HOOK') and d.inside(insn.end):
            nm = d.rst8.get(d.byte(insn.end))
            if nm and nm.startswith('ERR_') and nm not in errs:
                errs.append(nm)
    return rom[:5], toks[:5], errs[:3]


def reading(d, s, e, name, c):
    """A sentence about what a routine seems to be for."""
    said = []
    rom, toks, errs = signals(d, s, e)
    calls = [d.labels.get(t) for t in sorted(c['calls'])
             if d.labels.get(t) and not SYNTHETIC.match(d.labels.get(t, 'L0000'))]
    calls = [x for x in calls if x][:4]

    if rom:
        said.append('reaches the ROM through ' + ', '.join(rom))
    if toks:
        said.append('tests for ' + ', '.join(toks))
    if c['ports']:
        said.append('drives ' + ', '.join(sorted(c['ports'])[:2]))
    if calls:
        said.append('calls ' + ', '.join(calls))
    if errs:
        said.append('can report ' + ', '.join(errs))
    if not said:
        # Saying only "falls into what follows" is not a reading, it is a
        # restatement of the last instruction.  Better to say nothing.
        return None
    if 'JP (HL)' in c['ends']:
        said.append('ends by jumping to an address it worked out')
    elif not c['ends']:
        said.append('falls into whatever follows rather than returning')
    return '? ' + '; '.join(said) + '.'


def walk_body(d, s, e):
    a = s
    while a < e:
        ins = d.insns.get(a)
        if ins is None:
            return
        yield a, ins
        a = ins.end


def banner(d, s, e, name, c, existing):
    """The block that goes above a routine in listings/speculate/."""
    lines = ['%s -- &%04X to &%04X' % (name, s, e - 1), '']
    if c['tricky']:
        lines.append('This routine moves the return address about with '
                     'EX (SP),HL, so the')
        lines.append('register tracking below cannot be trusted: read it '
                     'as a list of what')
        lines.append('is touched, not of what is destroyed.')
        lines.append('')
    lines.append('Takes:     %s' % (regs.show(c['in']) or 'nothing in registers'))
    lines.append('Leaves:    %s' % (regs.show(c['out']) or 'registers unchanged'))
    if c['saved']:
        lines.append('Preserves: %s (saved and restored)' % regs.show(c['saved']))
    if c['ends']:
        lines.append('Ends:      %s' % ', '.join(sorted(c['ends'])))
    note = reading(d, s, e, name, c)
    if note:
        lines.append('')
        lines.append(note)
    if existing:
        lines.append('')
        lines.append('Shown for this routine in listings/disasm/:')
        lines.append('')
        for line in existing.split('\n'):
            body = line[3:] if line.startswith(';; ') else line.lstrip(';')
            if body.strip().startswith('---'):
                continue
            lines.append('    ' + body.rstrip())
    return '\n'.join(lines)
