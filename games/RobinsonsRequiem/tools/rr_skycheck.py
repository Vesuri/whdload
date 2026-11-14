#!/usr/bin/env python3
"""The AGA sky copy against START's: rr_skycheck.py [CASES] [SEED]

Runs START's row loop (hunk 1 +$e262 to +$e292, from tmp/game/RobinsonsRequiemAGA/data-aga/
START, hunk 1 loaded at address 0 so that its own variables resolve) and src/sky030.s's
_skyrows under Unicorn (68020) on the same random rows, segments, strides and bytes, and
compares the view and the registers the code after +$e292 can see: all but d3, which it
sets (+$e2d8) or restores (+$e2e4) before reading, and a7. Sources on any alignment, odd row lengths included.
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
from rr_c2pcheck import ROOT, Machine, hunk, STACK  # noqa: E402

CODE_NEW = 0x700000
SKY, VIEW = 0x200000, 0x400000
SKY_SIZE, VIEW_SIZE = 0x100000, 0x100000
LOOP, END, WIDTH = 0xe262, 0xe292, 0xedfe


def assemble():
    tmp = Path(tempfile.mkdtemp(dir=ROOT / 'tmp'))
    s, b = tmp / 'sky.s', tmp / 'sky.bin'
    s.write_text(f'\t\tORG\t${CODE_NEW:x}\n\t\tbra.w\t_skyrows\n_hunk1\tdc.l\t0\n'
                 f'\t\tINCLUDE\t"{ROOT / "src/sky030.s"}"\n')
    subprocess.run([os.environ.get('VASM', 'vasmm68k_mot'), '-m68020', '-devpac', '-Fbin',
                    '-quiet', '-o', str(b), str(s)], check=True)
    data = b.read_bytes()
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()
    return data


def main():
    cases = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    rnd = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    code, new = hunk(1), assemble()
    sky = rnd.randbytes(SKY_SIZE)
    for n in range(cases):
        width = rnd.choice([rnd.randrange(0, 700), 320, 256, 2, 1, 0])
        d0 = rnd.choice([-1, 0, rnd.randrange(-1, width // 2 + 2)])
        row = rnd.choice([rnd.randrange(1, 1200), 2 * rnd.randrange(1, 600), 640])
        rows = rnd.randrange(1, 120)
        mod = rnd.randrange(0, 80)
        src = SKY + 0x40000 + rnd.randrange(0, 64)
        dst = VIEW + rnd.randrange(0, 64)
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
        for target in (LOOP, CODE_NEW):
            m = Machine()
            m.write(0, code)
            m.write(WIDTH, struct.pack('>H', width))
            m.write(CODE_NEW, new)
            m.write(SKY, sky)
            m.write(VIEW, view)
            if target == LOOP:
                m.call(LOOP, regs, until=END)
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
