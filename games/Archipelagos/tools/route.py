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
    stones         collapse every stone of archipelago 1 (tools/play.py)
    obelisk        then destroy the Obelisk
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

# Program offsets (docs/internals.md): SPS 627's, or SPS 628's when VARIANT is
# ArchipelagosNTSC (set it for boot.sh and the tools alike). An address is body() + offset:
# the body is at $201C in chip memory, or in fast memory on a 68020+ with ExpMem; the slave
# leaves the address of the body that runs in the ST header's reserved long at $2012.
US = os.environ.get('VARIANT') == 'ArchipelagosNTSC'
CHIP_BODY = 0x201c
TITLE_LOOP = 0x1174c if US else 0x11504   # the title polls a key byte
ARCH_LOOP = 0x104f2 if US else 0x10468    # the archipelago screen asks for a key
GAME_LOOP = 0x11aa0 if US else 0x117ea    # the in-game loop; its first pass follows the
                                          # archipelago's opening tune
VARS = 0x3a4 if US else 0                 # SPS 628's variables are $3A4 above SPS 627's
_BODY = None

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


def peek(addr, n):
    vals = []
    for line in req('gdb', f'x/{n}xb {addr:#x}').splitlines():
        if ':' in line:
            vals += [int(v, 16) for v in line.split(':', 1)[1].split()]
    return bytes(vals[:n])


def body():
    """The running body's address, from $2012; runs fields until the slave has set it."""
    global _BODY
    if _BODY is None:
        old = 0
        for _ in range(200):
            # The body's first instruction is a jmp to offset $8D2A, which the relocation
            # points at the body that runs. A slave before 2.0b's fast memory leaves $2012
            # as the file has it (0): then the body is the chip one.
            if peek(CHIP_BODY, 2) == b'\x4e\xf9':
                v = int.from_bytes(peek(CHIP_BODY + 2, 4), 'big') - 0x8d2a
                mark = int.from_bytes(peek(0x2012, 4), 'big')
                if mark == v and v:
                    break
                if mark == 0 and v == CHIP_BODY:
                    old += 1
                    if old > 2:
                        break
            req('gdb', 'monitor fields 5')
        else:
            sys.exit('no body address after 1000 fields')
        _BODY = v
    return _BODY


def fast():
    return body() != CHIP_BODY


def addr(off):
    return body() + off


def until(off):
    """Run to body offset off."""
    a = addr(off)
    out = req('until', hex(a), timeout=int(os.environ.get('UNTIL_TIMEOUT', '180')))
    if 'Breakpoint' not in out:
        sys.exit(f'until {off:#x} ({a:#x}): {out}')


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
        elif w[0] in ('stones', 'obelisk'):
            import play
            getattr(play, w[0])()
        elif w[0] == 'shot':
            req('shot', str(ROOT / f'tmp/shots/{w[1]}.png'))
        elif w[0] == 'gdb':
            print(req('gdb', s[4:]), end='')
        else:
            sys.exit(f'unknown step {s!r}')


if __name__ == '__main__':
    run(sys.argv[1:])
