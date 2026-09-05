"""Build listings/speculate/: the listings with a reading of every routine.

The files in listings/disasm/ hold what can be shown.  These hold what I think
the code is doing, which is a different thing and is kept in a different
folder for that reason.  Three kinds of material go in, and they are not
equally trustworthy:

  contract   Derived.  Which registers a routine reads before writing,
             which it leaves changed, which it saves and restores, what
             it calls and what it ends with.  This is dataflow over the
             instructions, propagated through calls until it settles, so
             it is as right as the segmentation is.
  idiom      Derived.  Sequences with one meaning in this codebase --
             the HMPR window, an inline parameter, a self-modified
             operand -- named where they occur.
  reading    Guessed.  What the routine seems to be for.  Marked with
             a leading `?` so it can never be mistaken for the rest.

The segmentation is the weak link: a routine is taken to start at a
label something calls or jumps to, and to run to the next such label.
Where a routine has several entry points -- which this code does
constantly, since falling into the next routine is how it saves bytes --
the split will be in the wrong place, and the contract computed from it
will be wrong with it.  Treat a contract as a strong hint, not a promise.
"""

import re

import regs

SYNTHETIC = re.compile(r'^[LV][0-9A-F]{4}$')
TERMINAL = re.compile(r'^(RET$|JP [^,]*$|JR [^,]*$|JP \()')
ROUNDS = 6                      # enough for the call graph here to settle


def routines(d):
    """Split the page into (start, end, name), end exclusive.

    A routine starts where something calls or jumps to a label, or just
    after an instruction that cannot fall through.  Everything from
    there to the next such point is treated as one body.
    """
    starts = set()
    for a, ins in d.insns.items():
        t = ins.target
        if t is not None and d.inside(t) and d._starts_insn(t) \
                and ins.text.startswith(('CALL', 'JP ', 'JR ', 'DJNZ')):
            starts.add(t)
        if TERMINAL.match(ins.text) and d._starts_insn(ins.end):
            starts.add(ins.end)
    for a, name in d.labels.items():
        # A named routine is a routine even if only a dispatch table
        # reaches it, which is how every hook entry gets there.
        if d._starts_insn(a) and (a in d.xrefs
                                  or not SYNTHETIC.match(name)):
            starts.add(a)
    order = sorted(x for x in d.insns)
    marks = sorted(starts & set(order))
    out = []
    for i, s in enumerate(marks):
        e = marks[i + 1] if i + 1 < len(marks) else (max(order) + 1)
        out.append((s, e, d.labels.get(s, 'L%04X' % s)))
    return out


def walk(d, start, end, shared=(), budget=400):
    """The instructions of one body, following unconditional tail jumps.

    Falling into a shared tail is how this code returns: NRRD ends with
    `JR L4598`, and L4598 is where its registers are put back.  Stopping
    at the JR would report the opposite of what the routine does, so an
    unconditional jump out of the body is followed as if it were part of
    it -- which is what it is.
    """
    seen, a, stop = set(), start, end
    while budget > 0:
        if a in seen:
            return
        ins = d.insns.get(a)
        if ins is None or not (start <= a < stop or a in seen or True):
            return
        if ins is None:
            return
        seen.add(a)
        budget -= 1
        yield a, ins
        nxt = ins.end
        if TERMINAL.match(ins.text):
            t = ins.target
            if (t is not None and d.inside(t) and d._starts_insn(t)
                    and t not in shared
                    and ins.text.startswith(('JP ', 'JR '))):
                a, stop = t, d.limit          # carry on in the tail
                continue
            return
        if nxt >= stop and not (start <= nxt < stop):
            return
        a = nxt


def contract(d, start, end, known, shared=()):
    """What a routine consumes, leaves and preserves.

    PUSH/POP pairs are followed on a shadow stack, so a register that is
    saved and restored comes out as preserved rather than corrupted --
    which is the difference between a usable contract and a list of
    every register the routine happened to touch.
    """
    ins_needed, written, saved, stack = set(), set(), set(), []
    calls, ports, ends = set(), set(), set()
    tricky = False
    for a, insn in walk(d, start, end, shared):
        text = insn.text
        r, w = regs.effects(text)
        if text.startswith('PUSH'):
            stack.append(frozenset(regs.regs_of(regs.parts(text)[1][0])))
        elif text.startswith('POP') and stack:
            was = stack.pop()
            got = frozenset(regs.regs_of(regs.parts(text)[1][0]))
            if was == got:
                saved |= got
                written -= got
                continue
        if 'CALL' in w:
            t = insn.target
            sub = known.get(t)
            if sub is not None:
                r = r | sub['in']
                w = w | sub['out']
            elif t is not None and not d.inside(t):
                calls.add(t)
            if t is not None:
                calls.add(t)
        if text.startswith(('IN ', 'OUT ')):
            ports.add(text)
        if text.startswith('EX (SP)'):
            # The return address is being used as data, or swapped for a
            # saved value.  Push/pop tracking cannot follow that, so the
            # contract below is reported with a warning rather than
            # quietly wrong.
            tricky = True
        ins_needed |= (r - written - {'MEM', 'SP', 'CALL', 'F'})
        written |= (w - {'MEM', 'SP', 'CALL'})
        if TERMINAL.match(text):
            ends.add(text.split()[0] if not text.startswith('JP (')
                     else 'JP (HL)')
    return {'in': ins_needed, 'out': written, 'saved': saved - written,
            'calls': calls, 'ports': ports, 'ends': ends, 'tricky': tricky}


def analyse(d):
    """Contracts for every routine, with call effects propagated."""
    bodies = routines(d)
    # A tail jump into something that is also CALLed is not a tail: it is
    # a jump to a routine that stands on its own, and swallowing its
    # contract would say ESCCHK corrupts everything REPORT does.
    shared = set(ins.target for ins in d.insns.values()
                 if ins.text.startswith('CALL') and ins.target is not None)
    # Nor is a jump into something a dozen routines jump to.  REPORT is
    # never called, only jumped to, so the CALL test alone would let
    # every error path swallow the reporter's contract.
    shared |= set(a for a, refs in d.xrefs.items() if len(refs) > 8)
    known = {}
    for _ in range(ROUNDS):
        changed = False
        for s, e, _n in bodies:
            got = contract(d, s, e, known, shared)
            old = known.get(s)
            if old is None or got['in'] != old['in'] or got['out'] != old['out']:
                changed = True
            known[s] = got
        if not changed:
            break
    return bodies, known
