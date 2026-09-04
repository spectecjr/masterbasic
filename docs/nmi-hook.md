# Hooking the NMI button

MasterDOS takes over the SAM's NMI button and puts a menu behind it. Two of that
menu's keys — **1** and **5** — call an address you supply, with a page you
choose in the window. That is the only user-programmable entry point in the
snapshot code, and this is what you need to know to use it.

Everything here is read out of the listings in `clean/`; addresses are given so
you can check any of it.

---

## The chain, from the button to your code

1. **The hardware** pulls NMI. The Z80 takes it at `&0066` in ROM 0.
2. **The ROM's handler** ([main.asm:108](../ref/samrom/main.asm#L108)) pushes
   `AF` and `HL` **on the interrupted program's stack**, saves `LMPR` and `SP`,
   sets `LMPR` to `&1F` — ROM 0 on, ROM 1 off, the system page at `&4000` — and
   moves `SP` to its own `NMISTK`. Then it calls whatever is in `NMIV`.
   > The ROM's own source comments the first step: *"REGS SAVED IN ORIG PAGE —
   > MAY CORRUPT 4 BYTES IF EG SP BEING USED TO CLS"*. Pressing the button is
   > never entirely free.
3. **MasterDOS owns `NMIV`**, and reaches its own page's offset `&0206`, which
   is `JP NMI` (`&5355`).
4. **`NMI`** saves `SP` into `STR`, switches to a stack of its own inside the
   DOS page, and pushes the whole processor state: `I`, the main set, the
   alternate set, `IX`, `IY`. Then it pushes `SNAP7`'s address and records `SP`
   in `HKSP`.
5. **The menu** (`SNAP29`, `&5374`) puts page 4 in the window, sets `IM 1`, and
   reads the keyboard directly.
6. **Keys 1 and 5** reach `SNAP31` at `&5387`:

```asm
SNAP31:
      LD HL,(NMIKA)                   ; 5387  your vector
      LD A,(NMIKP)                    ; 538A  the page you want at &8000
      OUT (HMPR),A                    ; 538D
      CALL HLJUMP                     ; 538F  &0005 in ROM 0: JP (HL)
      JR SNAP29                       ; 5392  put page 4 back, ask again
```

---

## Setting the vector

The two variables are part of the DOS variable block at `&4220`, reachable from
BASIC with `DVAR`:

| | `DVAR` | Bytes | Default | Meaning |
|---|---|---|---|---|
| `NMIKP` | 26 | 1 | 4 | the page put in `HMPR` before the call |
| `NMIKA` | 27 | 2 | `&0004` | the address called |

`DVAR n` returns the *full machine address* of variable `n` — the DOS's page
times 16384 plus the offset — so it can be poked directly:

```basic
POKE DVAR 26, 20 : REM my code is in page 20
DPOKE DVAR 27, &8000 : REM ...at &8000, which is where NMIKP puts it
```

The default `&0004` is the ROM's `POP HL : JP (HL)`, which returns and does
nothing else — except corrupt `HL`, which nothing downstream cares about.

**`NMIKA` is an address in the window**, `&8000`–`&BFFF`, because `NMIKP` is
what decides which page that is. Anything you write for it must be assembled to
run at `&8000` and up.

---

## What your routine is entered with

| | |
|---|---|
| `&0000`–`&3FFF` | ROM 0 (the ROM's handler put it there) |
| `&4000`–`&7FFF` | **the DOS's page** — the code that called you is at `&5392` |
| | `LMPR` holds ROM 0 and the page below the DOS's — **not** the handler's `&1F`, which would put the system page at `&4000` |
| `&8000`–`&BFFF` | your page, from `NMIKP` |
| `&C000`–`&FFFF` | ROM 1 is **off** |
| `SP` | inside the DOS page, just below `STR` (`&7F90`) — see below |
| Interrupts | disabled, `IM 1` |
| `E` | the keyboard row for keys 1–5, read at `&537D` |
| everything else | undefined |

**`E` is how you tell 1 from 5.** Nothing between the read and the call touches
it, and the bits are active low:

```asm
      BIT 0,E                         ; clear = "1" was down
      BIT 4,E                         ; clear = "5" was down
```

The interrupted program's registers are not yours to read from the CPU — they
are on the DOS's stack, twenty bytes at `STR-20` (`&7F7C`), pushed in this
order and therefore stored in the reverse: `IY`, `IX`, `DE'`, `BC'`, `HL'`,
`AF'`, `DE`, `BC`, `HL`, `AF` (whose `A` half is `I`). The interrupted `SP` is
in `STR` itself, and the interrupted `PC` is on *that* stack, under the `AF` and
`HL` the ROM pushed.

---

## The stack: move it, first thing

**This is the one that will bite you.** `NMI` set `SP` to `STR` and pushed
eleven words, so you are called with `SP` at about `&7F7A` — and the bytes below
it are not spare. `PTH2` is at `&7F39` and `PTH1` at `&7F13`: the current
directory paths for the two drives.

Immediately below is not the path buffer itself. The original comment bounds
`PTH2` "to about `&7F60`", and the listing shows two more items between that
and `STR` — at `&7F6B` and `&7F77`, both reached from MasterBASIC. What `NMI`
pushed is sitting on those. But sixty-odd bytes is still sixty-odd bytes, and
`PTH1` and `PTH2` are what a stack any deeper than that reaches next. Nothing
warns you.

Switch to your own stack as the first thing you do, and put it back before you
return:

```asm
MYNMI:
      LD (SPSAVE),SP
      LD SP,MYSTACK                   ; in your own page
      ...
      LD SP,(SPSAVE)
      RET
```

If you jump to `SNAP7` instead of returning, you need not restore `SP` at
all — see below.

---

## Getting back

There are two honest ways out, and one that will not work.

### Return to the menu — `RET`

Control lands at `&5392`, which is `JR SNAP29`: the window goes back to page 4,
`IM 1` is re-issued, and the keyboard is read again. `A`, `E` and the flags are
all reloaded, so you need preserve nothing — but `SP` must be exactly what you
were called with, and **`LMPR` must be as you found it**, or the `RET` will land
in whatever page you left at `&4000`.

This is the right ending for a routine that displays something, or toggles a
setting, or writes a file. The user is still in the menu and can press 2 to
resume or X to give up.

### Resume the interrupted program — `JP SNAP7`

`SNAP7` (`&5457`) is what key 2 reaches. It is safe to jump to at **any stack
depth**, because it does not unwind — it sets `SP` absolutely:

```asm
SNAP7:
      DI                              ; 5457
      LD A,&03                        ; 5458  the Spectrum page into the window
      OUT (HMPR),A                    ; 545A
      LD HL,&0000                     ; 545C
      LD (HKSP),HL                    ; 545F  no unwind address any more
      LD SP,STR-20                    ; 5462  <-- absolute, not a POP-back
      POP IY / POP IX / ...           ; 5465  everything NMI pushed
```

So `JP SNAP7` from anywhere in your routine, with any stack, resumes the
program. You do not have to restore `SP`, and you must not try to restore the
paging — `SNAP7` does that itself, and does it in a way you cannot.

### What will not work — restoring the paging yourself

`HMPR` alone is easy: ROM 0 holds three bytes at `&005C` that do exactly this
job, and both halves of this image already use them.

```asm
      LD   HL,<where to go>
      LD   A,<page for &8000>
      JP   &005C                      ; OUT (&FB),A : JP (HL)
```

`LMPR` is the problem. The instruction that restores it is the one that takes
your page away, so the jump after it cannot be in your page — or in the DOS's,
if the DOS is what you are paging out. `SNAP7` gets round it by writing the
address the button is to come back to — `NMI` itself — and the three port values
into the Spectrum page at `&B8F6`–`&B8FA`, and jumping to a stub at `&B900`:
code in a page that will still be mapped once the ports have been put back.

That stub is in neither half of this image, and it is not the ROM's either — the
ROM's source has no Spectrum emulation in it at all. Page 3 holds a Spectrum ROM
image loaded into RAM, and the stub comes with it.

If you want to resume, use `SNAP7`. If you need to resume *somewhere else*, you
will have to put the same trampoline in a page of your own — or arrange that
only `HMPR` has to change, and use `&005C`.

---

## What the snapshot code assumes, and what that means for you

The three ports `SNAP7` restores come from `SNPRT0`, `SNPRT1` and `SNPRT2`
(`&4106`–`&4108`), and **nothing on the NMI path writes them**. They are
written in one place only — `&5FCE`–`&5FDA`, where `LOAD` enters Spectrum
mode — and `SNPRT2` is given a starting value by MasterBASIC's installer at
`&7675`.

That places the whole facility: it is built around the **Spectrum emulation**.
The menu forces page 4 (the Spectrum's RAM) into the window; a "48K snapshot" is
`&C000` bytes from `&8000` in it — three pages, stepped through the window; the
resume path goes through the Spectrum page. Your routine is called with the same
assumptions, whatever the machine was really doing when the button was pressed.

For a routine that displays or saves and then returns, none of that matters. For
one that resumes, it does: `SNAP7` is only meaningful when Spectrum mode was
entered through `CALL MODE 0` or a snapshot load.

---

## What to put behind the two keys

Both keys reach the same vector and are distinguished by one `BIT`, so the
natural shape is a pair: something that looks, and something that acts.

**A monitor.** `1` shows the frozen registers — they are lying at `&7F7C` in
the page already at `&4000`, in a known order — with a memory dump around `PC`.
`5` steps to the next page or the next screenful. Nothing needs to be saved and
`RET` puts you back in the menu.

**A cheat finder.** `1` copies the Spectrum's 48K somewhere for comparison; `5`
compares the current 48K against that copy and lists the addresses that changed.
Two presses either side of losing a life is the whole workflow, and it needs no
disk access at all.

**A better save.** `1` writes the *whole* machine rather than the 48K the menu's
key 4 manages — the other pages as well, through the DOS's own file hooks, which
are sitting at `&4000` while you run. `5` writes just the screen, in the mode
the machine is actually in rather than as a Spectrum `SCREEN$`.

**A poke-and-go.** `1` applies a table of patches — infinite lives, a starting
level — and returns to the menu; `5` applies them and jumps straight to `SNAP7`,
so one press patches and resumes.

**A serial dump.** `1` sends the frozen 48K out of the serial port to a host, `5`
reads a block back in. With interrupts already off and the machine stopped, the
timing is as good as it will ever be.

Whatever you choose, `1` returning to the menu and `5` resuming through `SNAP7`
is a good default division: it means one key is always safe to press twice and
the other always gets you out.

---

## A skeleton

```asm
; Assembled for &8000, in a page of its own.  POKE DVAR 26,<page>
; and DPOKE DVAR 27,&8000 to install it.

            ORG  &8000

NMIENT:     LD   (SPSAVE),SP
            LD   SP,MYSTACK           ; the DOS's stack has ~60 bytes left

            BIT  4,E                  ; E still holds the 1-to-5 row
            JR   Z,KEY5               ; bit clear = "5" was down

KEY1:       CALL LOOK                 ; whatever key 1 does
            LD   SP,(SPSAVE)
            RET                       ; back to the menu

KEY5:       CALL ACT                  ; whatever key 5 does
            JP   &5457                ; SNAP7: resume, at any stack depth

SPSAVE:     DEFW 0
            DEFS 64
MYSTACK:
```

Two things to hold on to. `LMPR` must be as you found it whenever you `RET` —
the DOS is at `&4000` and that is where the `RET` goes. And `&5457` is only
`SNAP7` while this build of MasterDOS is in memory; if you care about other
versions, read the address out of the DOS page rather than assembling it in.
