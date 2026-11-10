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
    gdb TEXT...    one raw gdb command (the rest of the step, quoted)
Named routes (ROUTES below) expand in place.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = [sys.executable, str(ROOT / 'tools/encounter.py')]

# 'start': fire on the title screen starts level 1. The title loop ($DCFC) calls the RNG once
# per pass (one pass per field) until fire, which seeds the level; its setup takes a different
# number of fields on each machine, so fire is pressed on the 60th pass of $DD24 (the loop's
# field wait), not at a field count, and every machine and build gets the same level.
# 'aim': 25 fields into level 1, 8 fields of right turn (the heading at $11EB4 turns per field,
# the same on every machine), then fire held: the enemy appears ahead about 80 fields later and
# the stream of shots destroys it (traced on a1200-030 without its MMU: fields 140-200 of
# tools/bench.py's window).
ROUTES = {
    'start': ['pass 0xDD24 60', '+JOY2_FIRE_BUTTON', 'f 10', '-JOY2_FIRE_BUTTON'],
    'aim': ['f 25', '+JOY2_RIGHT', 'f 8', '-JOY2_RIGHT', '+JOY2_FIRE_BUTTON'],
}


def req(*words):
    out = subprocess.run(TOOL + list(words), capture_output=True, text=True, cwd=ROOT).stdout
    if 'rror' in out:
        sys.exit(f'{" ".join(words)}: {out}')
    return out


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
        elif w[0] == 'pass':
            req('gdb', f'break *{w[1]}')
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
