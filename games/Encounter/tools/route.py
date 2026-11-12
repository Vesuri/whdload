#!/usr/bin/env python3
"""The level-1 benchmark route, driven through a running server (tools/encounter.py serve).

The server must have been started with BOOT_BREAK=0xD7E2 (the game's entry, stopped before it
runs) and WARP=1 DETERMINISTIC=1 JOY0=none, so every step lands on the same field:

    BOOT_BREAK=0xD7E2 SETUP=a1200-030 WARP=1 WINDOW=none JOY0=none DETERMINISTIC=1 \
        python3 tools/encounter.py serve &
    python3 tools/route.py STEPS...

A step is one of
    f N            run N fields
    +EVENT / -EVENT press / release an input event (JOY2_FIRE_BUTTON, JOY2_RIGHT, ...)
    shot NAME      screenshot to tmp/shots/NAME.png (traces one field)
    sheet N K NAME K screenshots N fields apart, one contact sheet tmp/shots/NAME.png
    prof N BIN     cycle-exact trace of N fields (needs a CPU without MMU)
    pass ADDR N    run until the Nth execution of ADDR (a breakpoint with an ignore count; the
                   next `f N` then runs N + 1 fields, the first one partial)
    hash N NAME    stop at the world step's start ($DA56: one logic step) N times and dump
                   the state each time to tmp/hash/NAME.bin (tools/statehash.py compares
                   runs); with the Enhanced main loop at its logic head (the page's PG_HASH),
                   where the state is 1.2's at $DA56
    stack          the Enhanced VERIFY slave's stack depth (its guard fill)
    gdb TEXT...    one raw gdb command (the rest of the step, quoted)
Named routes (ROUTES below) expand in place.

Game addresses in steps are chip addresses. With Enhanced framerate on, the game runs from its
copy in the ExpMem: the slave leaves a `jmp` to the copy's entry at $D7E2, and addresses in the
copied range are moved to the copy (copy_delta()).
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = [sys.executable, str(ROOT / 'tools/encounter.py')]

ENTRY = 0xD7E2
LOOP = 0xDA30            # main loop head: bsr $DF94 (the draw); one pass is one logic step
WORLD = 0xDA56           # the world step's start, after the draw and the frame end (the hash)
COPY = (0x5000, 0x13000)  # the range the Enhanced slave copies (src/relocs.i)
# The state dumped per logic step: base memory below the screens. In the Enhanced copy the
# variables PC-relative code reads live in the copy (MOVED, chip address and length).
STATE = [(0x0, 0x13000)]
# The two screens (four planes, 40 x 200 each): at the loop head both hold finished frames.
SCREENS = [(0x68000, 0x6FD00), (0x78000, 0x7FD00)]
MOVED = [(0xC526, 2), (0xCA4E, 2)]
# The ExpMem's page (src/EncounterHD.s EXP_PAGE, PG_*): the VERIFY trap loop, the stack guard;
# the Enhanced main loop's logic head and the addresses of its marks (the screen swap, the
# end of the field wait).
EXP_PAGE, PG_TRAPLOOP, PG_GUARD, PG_STACKTOP, GUARD = 0xE000, 0x104, 0x400, 0x1000, 0x5A5A5A5A
PG_HASH, PG_MSWAP, PG_MGO, PG_PREW, PG_PREWE, PG_PRECLR, PG_STAGE, PG_CLEAR = 0x108, 0x0, 0x4, 0x8, 0xC, 0x24, 0x28, 0x2C
_delta = None

# 'start': fire on the title screen starts level 1. The title loop ($DCFC) calls the RNG once
# per pass (one pass per field) until fire, which seeds the level; its setup takes a different
# number of fields on each machine, so fire is pressed on the 60th pass of $DD24 (the loop's
# field wait), not at a field count, and every machine and build gets the same level.
# 'aim': 25 fields into level 1, 8 fields of right turn (the heading at $11EB4 turns per field,
# the same on every machine), then fire held: the enemy appears ahead about 80 fields later and
# the stream of shots destroys it (traced on a1200-030 without its MMU: fields 140-200 of
# tools/bench.py's window).
# 'demo': no input; the title times out into the attract demo, whose setup ends at $D9B4
# (move.w #1,$11E06, the demo flag), and the demo plays recorded input through the same main
# loop.
ROUTES = {
    'start': ['pass 0xDD24 60', '+JOY2_FIRE_BUTTON', 'f 10', '-JOY2_FIRE_BUTTON'],
    'aim': ['f 25', '+JOY2_RIGHT', 'f 8', '-JOY2_RIGHT', '+JOY2_FIRE_BUTTON'],
    'demo': ['pass 0xD9B4 1'],
}


def req(*words):
    out = subprocess.run(TOOL + list(words), capture_output=True, text=True, cwd=ROOT).stdout
    if 'rror' in out:
        sys.exit(f'{" ".join(words)}: {out}')
    return out


def word(addr, size='w'):
    out = req('gdb', f'x/1x{size} {addr:#x}')
    return int(out.split(':')[1].split()[0], 16)


def copy_delta():
    """0, or the offset of the game's copy when the Enhanced slave runs it from the ExpMem:
    the slave writes `jmp copy` over the entry $D7E2 (read before the game clears it)."""
    global _delta
    if _delta is None:
        _delta = 0
        if word(ENTRY, 'h') == 0x4EF9:
            _delta = word(ENTRY + 2) - ENTRY
    return _delta


def page():
    """The ExpMem's page, or None with the code in chip."""
    d = copy_delta()
    return d + COPY[0] + EXP_PAGE if d else None


def eloop():
    """With the Enhanced main loop (the copy's $DA30 jumps to the slave's): the logic head
    and the marks, {'hash', 'swap', 'go', 'preclr', 'stage', 'clear'} and the clear-ahead's wait for the beam
    ('prew': first and last + 2); otherwise None."""
    d = copy_delta()
    if not d or word(LOOP + d, 'h') != 0x4EF9:
        return None
    p = page()
    return {'hash': p + PG_HASH, 'swap': word(p + PG_MSWAP), 'go': word(p + PG_MGO),
            'prew': (word(p + PG_PREW), word(p + PG_PREWE)), 'preclr': word(p + PG_PRECLR),
            'stage': word(p + PG_STAGE), 'clear': word(p + PG_CLEAR)}


def game(addr):
    a = int(addr, 0)
    return a + copy_delta() if COPY[0] <= a < COPY[1] else a


def hash_run(n, name):
    out = ROOT / 'tmp/hash' / name
    out.parent.mkdir(parents=True, exist_ok=True)
    d = copy_delta()
    rngs = list(STATE) + ([(a + d, a + d + k) for a, k in MOVED] if d else []) + SCREENS
    trap = [hex(page() + PG_TRAPLOOP)] if d else []
    el = eloop()
    head = el['hash'] if el else game(hex(WORLD))
    reply = req('hash', str(n), hex(head), str(out), ','.join(f'{a:x}-{b:x}' for a, b in rngs), *trap)
    meta = {'steps': n, 'delta': d, 'state': STATE, 'moved': MOVED if d else [], 'screens': SCREENS}
    out.with_suffix('.json').write_text(json.dumps(meta) + '\n')
    print(reply, end='')


def stack():
    """The deepest the Enhanced stack went: the VERIFY slave fills its page with GUARD."""
    d = copy_delta()
    if not d:
        return 'code in chip'
    page = d + COPY[0] + EXP_PAGE
    out = req('gdb', f'x/{(PG_STACKTOP - PG_GUARD) // 4}xw {page + PG_GUARD:#x}')
    words = [int(w, 16) for line in out.splitlines() for w in line.split(':')[1].split()]
    low = next((i for i, w in enumerate(words) if w != GUARD), len(words))
    used = (len(words) - low) * 4
    return f'stack: {used} bytes used of {PG_STACKTOP - PG_GUARD} (guard intact below)'


def sheet(n, k, name):
    from PIL import Image
    names = []
    for i in range(k):
        req('gdb', f'monitor fields {n}')
        p = ROOT / f'tmp/shots/{name}-{i:02d}.png'
        req('shot', str(p))
        names.append(p)
    ims = [Image.open(p).crop((60, 20, 700, 400)) for p in names]
    w, h = ims[0].size
    cols = 4
    m = Image.new('RGB', (w * cols, h * ((k + cols - 1) // cols)))
    for i, im in enumerate(ims):
        m.paste(im, ((i % cols) * w, (i // cols) * h))
    m = m.resize((m.width // 2, m.height // 2))
    m.save(ROOT / f'tmp/shots/{name}.png')
    for p in names:
        p.unlink()


def run(steps):
    for s in steps:
        if s in ROUTES:
            run(ROUTES[s])
            continue
        w = s.split()
        if w[0] == 'f':
            req('gdb', f'monitor fields {w[1]}')
        elif w[0][0] in '+-':
            req('gdb', f'monitor input {w[0][1:]} {1 if w[0][0] == "+" else 0}')
        elif w[0] == 'shot':
            req('shot', str(ROOT / f'tmp/shots/{w[1]}.png'))
        elif w[0] == 'sheet':
            sheet(int(w[1]), int(w[2]), w[3])
        elif w[0] == 'prof':
            print(req('profile', w[1], str(ROOT / w[2])), end='')
        elif w[0] == 'hash':
            hash_run(int(w[1]), w[2])
        elif w[0] == 'stack':
            print(stack())
        elif w[0] == 'pass':
            req('gdb', f'break *{game(w[1]):#x}')
            if int(w[2]) > 1:
                req('gdb', f'ignore $bpnum {int(w[2]) - 1}')
            req('gdb', 'continue')
            req('gdb', 'delete')
        elif w[0] == 'gdb':
            print(req('gdb', s[4:]), end='')
        else:
            sys.exit(f'unknown step {s!r}')


if __name__ == '__main__':
    run(sys.argv[1:])
