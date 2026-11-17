#!/usr/bin/env python3
"""Routes through a running server (python3 tools/zanygolf.py serve, warp, deterministic,
JOY0=none).

    python3 tools/route.py STEPS...

A step is one of
    stop           stop the CPU; from then on the server leaves it stopped between commands
                   (a server resumes the CPU after a command when it was running before,
                   and in warp hundreds of fields then pass between two commands)
    f N            run N fields
    key RAW N      press raw key RAW (hex), hold it N fields, release it
    click N        hold the left mouse button N fields, release it
    play           click until the game publishes frames (out of the pause screen), at most
                   10 tries 60 fields apart
    mouse DX DY N  N times: add DX, DY to the mouse counters, run one field
    shot NAME      screenshot to tmp/shots/NAME.png (traces one field)
    prof N BIN     cycle-exact trace of N fields (needs a CPU without MMU)
    gdb TEXT...    one raw gdb command (the rest of the step)
Named routes (ROUTES below) expand in place.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = [sys.executable, str(ROOT / 'tools/zanygolf.py')]

# 'hole1': the credits and title (about 1350 NTSC fields on a1200-030), 1 for one player,
# the pause screen, a click: hole 1 in play, the pointer at rest.
ROUTES = {
    'hole1': ['stop', 'f 1500', 'key 01 5', 'f 360', 'play', 'f 120'],
}

# The low word of BPL4PT in the copper list: the renderer flips its bit 15 at every frame
# it shows (program offset $14a8). It stays put in the pause screen.
PLANE4 = 0x12326


def playing():
    """True when frames are being shown: the plane pointer changes within 40 fields."""
    first = peek(PLANE4, 'h')
    for _ in range(20):
        req('gdb', 'monitor fields 2')
        if peek(PLANE4, 'h') != first:
            return True
    return False


def req(*words):
    p = subprocess.run(TOOL + list(words), capture_output=True, text=True, cwd=ROOT)
    if p.returncode or 'rror' in p.stdout:
        sys.exit(f'{" ".join(words)}: {p.stdout}{p.stderr}')
    return p.stdout


def peek(addr, size='w'):
    out = req('gdb', f'x/{size}x {addr:#x}')
    return int(out.split(':')[1].split()[0], 16)


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
            req('gdb', f'monitor key {w[1]} 1')
            req('gdb', f'monitor fields {w[2]}')
            req('gdb', f'monitor key {w[1]} 0')
        elif w[0] == 'click':
            req('gdb', 'monitor input JOY1_FIRE_BUTTON 1')
            req('gdb', f'monitor fields {w[1]}')
            req('gdb', 'monitor input JOY1_FIRE_BUTTON 0')
        elif w[0] == 'play':
            for _ in range(10):
                req('gdb', 'monitor input JOY1_FIRE_BUTTON 1')
                req('gdb', 'monitor fields 5')
                req('gdb', 'monitor input JOY1_FIRE_BUTTON 0')
                if playing():
                    break
                req('gdb', 'monitor fields 60')
            else:
                sys.exit('play: still no frames after 10 clicks')
        elif w[0] == 'mouse':
            for _ in range(int(w[3])):
                req('gdb', f'monitor mouse {w[1]} {w[2]}')
                req('gdb', 'monitor fields 1')
        elif w[0] == 'shot':
            req('shot', str(ROOT / f'tmp/shots/{w[1]}.png'))
        elif w[0] == 'prof':
            print(req('profile', w[1], str(ROOT / w[2])), end='')
        elif w[0] == 'gdb':
            print(req('gdb', s[4:]), end='')
        else:
            sys.exit(f'unknown step {s!r}')


if __name__ == '__main__':
    run(sys.argv[1:])
