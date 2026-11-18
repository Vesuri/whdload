#!/usr/bin/env python3
"""Routes through a running server (tools/boot.sh: warp, deterministic, JOY0=none).

    python3 tools/route.py STEPS...

A step is one of
    stop           stop the CPU; from then on the server leaves it stopped between commands
    f N            run N fields
    key RAW N      press raw key RAW (hex), hold it N fields, release it
    title          run to the title's key loop, then press space
    arch           run to the archipelago screen's key loop, then press space
    play           run to the first pass of the in-game loop: archipelago 1 takes input
    rmb N          hold the right mouse button N fields, release it (toggles pan mode)
    mouse DX DY N  N times: add DX, DY to the mouse counters, run one field
    shot NAME      screenshot to tmp/shots/NAME.png (traces one field)
    gdb TEXT...    one raw gdb command (the rest of the step)
Named routes (ROUTES below) expand in place.

The waits are breakpoints on game code (until), not field counts: the screens take
different numbers of fields on different machines. Each has a deadline (UNTIL_TIMEOUT
seconds, default 180); a missed one quits the server and fails.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = [sys.executable, str(ROOT / 'tools/archipelagos.py')]

# Program addresses: the program loads to $2000 and its body (offsets in docs/internals.md)
# starts at $201c, so address = offset + $201c.
TITLE_LOOP = 0x13520     # offset $11504: the title polls the key byte $10356 (and counts d0)
ARCH_LOOP = 0x12484      # offset $10468: the archipelago screen asks for a key (Space, Return)
GAME_LOOP = 0x13806      # offset $117ea: the in-game loop; its first pass follows the
                         # archipelago's opening tune, when the crosshair appears

# 'start': boot to archipelago 1 in play, stopped at the in-game loop's first pass.
ROUTES = {
    'start': ['stop', 'title', 'arch', 'play'],
}


def req(*words, timeout=600):
    try:
        p = subprocess.run(TOOL + list(words), capture_output=True, text=True, cwd=ROOT,
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess.run(TOOL + ['quit'], capture_output=True, cwd=ROOT)
        sys.exit(f'{" ".join(words)}: no reply in {timeout} s; server quit')
    if p.returncode or 'rror' in p.stdout:
        sys.exit(f'{" ".join(words)}: {p.stdout}{p.stderr}')
    return p.stdout


def until(addr):
    out = req('until', hex(addr), timeout=int(os.environ.get('UNTIL_TIMEOUT', '180')))
    if 'Breakpoint' not in out:
        sys.exit(f'until {addr:#x}: {out}')


def key(raw, fields):
    req('gdb', f'monitor key {raw} 1')
    req('gdb', f'monitor fields {fields}')
    req('gdb', f'monitor key {raw} 0')


def run(steps):
    for s in steps:
        if s in ROUTES:
            run(ROUTES[s])
            continue
        w = s.split()
        if w[0] == 'stop':
            req('stop')
        elif w[0] == 'f':
            req('gdb', f'monitor fields {w[1]}')
        elif w[0] == 'key':
            key(w[1], w[2])
        elif w[0] == 'title':
            until(TITLE_LOOP)
            key('40', 5)
        elif w[0] == 'arch':
            until(ARCH_LOOP)
            key('40', 5)
        elif w[0] == 'play':
            until(GAME_LOOP)
        elif w[0] == 'rmb':
            req('gdb', 'monitor input JOY1_2ND_BUTTON 1')
            req('gdb', f'monitor fields {w[1]}')
            req('gdb', 'monitor input JOY1_2ND_BUTTON 0')
        elif w[0] == 'mouse':
            for _ in range(int(w[3])):
                req('gdb', f'monitor mouse {w[1]} {w[2]}')
                req('gdb', 'monitor fields 1')
        elif w[0] == 'shot':
            req('shot', str(ROOT / f'tmp/shots/{w[1]}.png'))
        elif w[0] == 'gdb':
            print(req('gdb', s[4:]), end='')
        else:
            sys.exit(f'unknown step {s!r}')


if __name__ == '__main__':
    run(sys.argv[1:])
