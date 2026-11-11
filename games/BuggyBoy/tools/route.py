#!/usr/bin/env python3
"""Routes through a running server (tools/boot.sh, stopped at the game entry $400).

    tools/boot.sh && python3 tools/route.py STEPS...

A step is one of
    f N            run N fields
    +EVENT / -EVENT press / release an input event (JOY2_FIRE_BUTTON, JOY2_UP, ...)
    shot NAME      screenshot to tmp/shots/NAME.png (traces one field)
    sheet N K NAME K screenshots N fields apart, one contact sheet tmp/shots/NAME.png
    prof N BIN     cycle-exact trace of N fields (needs a CPU without MMU)
    pass ADDR N    run until the Nth execution of ADDR (a breakpoint with an ignore count);
                   +OFF is a program offset (hex)
    gdb TEXT...    one raw gdb command (the rest of the step, quoted)
Named routes (ROUTES below) expand in place.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = [sys.executable, str(ROOT / 'tools/buggyboy.py')]

# 'race': title -> course select (fire), Offroad (fire), then the race loop's first pass
# (program offset $158, after the start sequence), joystick up held from there, and 100 fields to get moving.
ROUTES = {
    'race': ['f 150', '+JOY2_FIRE_BUTTON', 'f 10', '-JOY2_FIRE_BUTTON', 'f 150',
             '+JOY2_FIRE_BUTTON', 'f 25', '-JOY2_FIRE_BUTTON', 'pass +158 1', '+JOY2_UP', 'f 100'],
}


def req(*words):
    out = subprocess.run(TOOL + list(words), capture_output=True, text=True, cwd=ROOT).stdout
    if 'rror' in out:
        sys.exit(f'{" ".join(words)}: {out}')
    return out


def peek(addr):
    """One longword of emulated memory."""
    out = req('gdb', f'x/wx {addr:#x}')
    return int(out.split(':')[1].split()[0], 16)


def prog_base():
    """The program's base (its offset 0; $400 in the shipped slave), from the level-3 vector
    $6C, which the game points at its handler at program offset $4DAC."""
    return peek(0x6C) - 0x4DAC


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
            # '+OFF' is a program offset (the base read at this step), else an address.
            a = prog_base() + int(w[1][1:], 16) if w[1][0] == '+' else int(w[1], 0)
            req('gdb', f'break *{a:#x}')
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
