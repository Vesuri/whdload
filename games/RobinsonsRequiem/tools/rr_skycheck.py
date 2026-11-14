#!/usr/bin/env python3
"""The sky copy against START's: rr_skycheck.py [ecs] [CASES] [SEED]

The AGA game: runs START's row loop (hunk 1 +$e262 to +$e292, from tmp/game/
RobinsonsRequiemAGA/data-aga/START, hunk 1 loaded at address 0 so that its own variables
resolve) and src/sky030.s's _skyrows under Unicorn (68020) on the same random rows,
segments, strides and bytes, and compares the view and the registers the code after +$e292
can see: all but d3, which it sets (+$e2d8) or restores (+$e2e4) before reading, and a7.
Sources on any alignment, odd row lengths included.

`ecs`: the ECS game's loop (hunk 1 +$c8b8 to +$c8e8, data-ecs/START) against
src/sky000.s on a 68000: sources, row lengths, the view and its modulo even, as the
68000's word moves need; d3 is not compared either (set at +$c92e before it is read).
Exit status 1 on the first difference.
"""
import os
import random
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rr_c2pcheck import (ROOT, START, Machine, UC_CPU_M68K_M68000,  # noqa: E402
                         UC_CPU_M68K_M68020, hunk, STACK)

CODE_NEW = 0x700000
SKY, VIEW = 0x200000, 0x400000
SKY_SIZE, VIEW_SIZE = 0x100000, 0x100000
GAMES = {
    'aga': dict(start=START, loop=0xe262, end=0xe292, width=0xedfe, src='sky030.s',
                cpu=UC_CPU_M68K_M68020, opt='-m68020', even=False),
    'ecs': dict(start=ROOT / 'tmp/game/RobinsonsRequiem/data-ecs/START', loop=0xc8b8,
                end=0xc8e8, width=0xd454, src='sky000.s', cpu=UC_CPU_M68K_M68000,
                opt='-m68000', even=True),
}


def assemble(game):
    tmp = Path(tempfile.mkdtemp(dir=ROOT / 'tmp'))
    s, b = tmp / 'sky.s', tmp / 'sky.bin'
    s.write_text(f'\t\tORG\t${CODE_NEW:x}\n\t\tbra.w\t_skyrows\n_hunk1\tdc.l\t0\n'
                 f'\t\tINCLUDE\t"{ROOT / "src" / game["src"]}"\n')
    subprocess.run([os.environ.get('VASM', 'vasmm68k_mot'), game['opt'], '-devpac', '-Fbin',
                    '-quiet', '-o', str(b), str(s)], check=True)
    data = b.read_bytes()
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()
    return data


def main():
    args = sys.argv[1:]
    game = GAMES['ecs' if args[:1] == ['ecs'] else 'aga']
    args = args[1:] if args[:1] == ['ecs'] else args
    cases = int(args[0]) if args else 1000
    rnd = random.Random(int(args[1]) if len(args) > 1 else 1)
    code, new = hunk(1, game['start']), assemble(game)
    ev = 2 if game['even'] else 1
    sky = rnd.randbytes(SKY_SIZE)
    for n in range(cases):
        width = rnd.choice([rnd.randrange(0, 700), 320, 256, 2, 1, 0])
        d0 = rnd.choice([-1, 0, rnd.randrange(-1, width // 2 + 2)])
        row = ev * rnd.choice([rnd.randrange(1, 1200 // ev), 2 * rnd.randrange(1, 600 // ev),
                               640 // ev])
        rows = rnd.randrange(1, 120)
        mod = ev * rnd.randrange(0, 80 // ev)
        src = SKY + 0x40000 + ev * rnd.randrange(0, 64 // ev)
        dst = VIEW + ev * rnd.randrange(0, 64 // ev)
        regs = [rnd.getrandbits(32) for _ in range(16)]
        regs[0] = (regs[0] & 0xffff0000) | (d0 & 0xffff)
        regs[1] = (regs[1] & 0xffff0000) | row
        regs[5] = (regs[5] & 0xffff0000) | mod
        regs[7] = (regs[7] & 0xffff0000) | (rows - 1)
        regs[8] = regs[12] = src
        regs[9] = dst
        regs[15] = STACK
        view = rnd.randbytes(VIEW_SIZE)
        out = []
        for target in (game['loop'], CODE_NEW):
            m = Machine(game['cpu'])
            m.write(0, code)
            m.write(game['width'], struct.pack('>H', width))
            m.write(CODE_NEW, new)
            m.write(SKY, sky)
            m.write(VIEW, view)
            if target == game['loop']:
                m.call(target, regs, until=game['end'])
            else:
                m.call(CODE_NEW, regs)
            r = m.regs()
            keep = [r[i] for i in range(15) if i != 3]
            out.append((m.read(VIEW, VIEW_SIZE), keep))
        if out[0][0] == view:
            if width // 2 - d0 - 1 > 0 or d0 >= 0:
                sys.exit(f'case {n}: the view did not change')
        if out[0] != out[1]:
            what = 'the view' if out[0][0] != out[1][0] else \
                f'registers START {[hex(x) for x in out[0][1]]}, new {[hex(x) for x in out[1][1]]}'
            print(f'case {n}: width {width} d0 {d0} row {row} rows {rows} mod {mod} '
                  f'src {src:#x} dst {dst:#x}: {what}')
            sys.exit(1)
    print(f'{cases} cases identical')


if __name__ == '__main__':
    main()
