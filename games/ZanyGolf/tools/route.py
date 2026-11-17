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
    title          run until the title takes input (state 3, drawing), then press 1 until
                   the game leaves it (state 4), at most 10 tries 60 fields apart
    play           click until the pause screen (state 5; the hole's intro, then about 400
                   fields of loading with interrupts off), then click until play (state 4,
                   drawing); at most 5 and 10 clicks
    mouse DX DY N  N times: add DX, DY to the mouse counters, run one field
    shot NAME      screenshot to tmp/shots/NAME.png (traces one field)
    prof N BIN     cycle-exact trace of N fields (needs a CPU without MMU)
    track N NAME   the ball and the clock every field for N fields, to tmp/shots/NAME.txt
                   (tools/zanygolf.py track)
    frametrack N NAME
                   the clock and the objects at each of N frames, to tmp/shots/NAME.txt
                   (tools/zanygolf.py frametrack; not on MMU cores)
    press, release hold or release the left mouse button
    gdb TEXT...    one raw gdb command (the rest of the step)
Named routes (ROUTES below) expand in place.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = [sys.executable, str(ROOT / 'tools/zanygolf.py')]

# 'hole1': the credits and title, 1 for one player, the hole's intro, a click, the hole's
# loading, the pause screen, a click: hole 1 in play, the pointer at rest. The credits take
# about 1350 NTSC fields on a1200-030 and 2200 on a500, so the route waits for the game's
# state instead of counting fields.
# 'putt' (from 'hole1'): press the button, drag the pointer 48 right and 36 down in 12
# fields, hold it still for 30 fields so the game samples where it ended, release. The ball
# rolls up and left, bounces off the wall and stops after 44 frames on every machine. The
# game's per-frame timers (friction every fifth frame) run from the hole's start, so their
# phase at the release depends on the frames drawn before it: to compare paths frame by
# frame across machines, change the hold until the phases agree (internals.md, "Game time").
ROUTES = {
    'hole1': ['stop', 'title', 'play', 'f 120'],
    'putt': ['press', 'f 10', 'mouse 4 3 12', 'f 30', 'release'],
}

# Program addresses (FILE1 at $10000). The state byte is 3 at the title, 4 in the hole's
# intro and in play, 5 in the pause screen; the drawing flag is 1 while the main loop draws
# frames (the title draws too, the pause screen does not).
STATE = 0x10ea8
DRAWING = 0x10ea0


def until(test, tries, fields=50):
    for _ in range(tries):
        if test():
            return True
        req('gdb', f'monitor fields {fields}')
    return test()


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
        elif w[0] in ('press', 'release'):
            req('gdb', f'monitor input JOY1_FIRE_BUTTON {int(w[0] == "press")}')
        elif w[0] == 'track':
            print(req('track', w[1], str(ROOT / f'tmp/shots/{w[2]}.txt')), end='')
        elif w[0] == 'title':
            if not until(lambda: peek(STATE, 'b') == 3 and peek(DRAWING, 'b') == 1, 80):
                sys.exit('title: not reached in 4000 fields')
            for _ in range(10):
                req('gdb', 'monitor fields 60')
                run(['key 01 5'])
                req('gdb', 'monitor fields 60')
                if peek(STATE, 'b') == 4:
                    break
            else:
                sys.exit('title: still there after 10 presses of 1')
        elif w[0] == 'frametrack':
            print(req('frametrack', w[1], str(ROOT / f'tmp/shots/{w[2]}.txt')), end='')
        elif w[0] == 'play':
            for _ in range(5):
                run(['click 5'])
                if until(lambda: peek(STATE, 'b') == 5, 16):
                    break
            else:
                sys.exit('play: no pause screen after 5 clicks')
            for _ in range(10):
                run(['click 5', 'f 60'])
                if peek(STATE, 'b') == 4 and peek(DRAWING, 'b') == 1:
                    break
            else:
                sys.exit('play: still paused after 10 clicks')
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
