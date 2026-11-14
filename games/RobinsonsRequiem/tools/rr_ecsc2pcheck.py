#!/usr/bin/env python3
"""The ECS chunky-to-planar conversion against START's: rr_ecsc2pcheck.py [CASES] [SEED]

Runs START's loop (hunk 2 +$1a5e to +$1b98, from tmp/game/RobinsonsRequiem/data-ecs/START,
hunk 2 loaded at address 0 so that its chunky modulo at +$46 resolves) and src/c2p000.s's
_c2p000 under Unicorn (68000) on the same random rectangles, chunky bytes and plane
contents, and compares the four planes byte for byte. Rectangles: widths of 16 to 320
pixels in 16-pixel steps, 1 to 100 rows, a left edge on 16 pixels, chunky strides of the
width up to 336 bytes, START's 40-byte plane rows; planes 0 and 2 each with its pair 16,000
bytes on. Exit status 1 on the first difference.
"""
import os
import random
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rr_c2pcheck import Machine, UC_CPU_M68K_M68000, hunk  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
START = ROOT / 'tmp/game/RobinsonsRequiem/data-ecs/START'
CODE_NEW, STACK = 0x700000, 0x7D0000
CHUNKY = 0x100000
P0, P2 = 0x200000, 0x300000
AREAS = [(P0, 0x10000), (P2, 0x10000)]
ROWLEN, BPL = 40, 16000
LOOP, END, MODC = 0x1a5e, 0x1b98, 0x46


def assemble():
    tmp = Path(tempfile.mkdtemp(dir=ROOT / 'tmp'))
    s, b = tmp / 'c2p.s', tmp / 'c2p.bin'
    s.write_text(f'\t\tORG\t${CODE_NEW:x}\n\t\tbra.w\tc2pentry\n_c2pmod\tdc.l\t${MODC:x}\n'
                 'c2pentry\tmovem.l\td0-a6,-(a7)\n\t\tbra\t_c2p000\n'
                 f'\t\tINCLUDE\t"{ROOT / "src/c2p000.s"}"\n')
    subprocess.run([os.environ.get('VASM', 'vasmm68k_mot'), '-m68000', '-devpac', '-Fbin',
                    '-quiet', '-o', str(b), str(s)], check=True)
    data = b.read_bytes()
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()
    return data


def main():
    cases = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    rnd = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    code, new = hunk(2, START), assemble()
    for n in range(cases):
        w = 16 * rnd.randrange(1, 21)
        x0 = 16 * rnd.randrange(0, (320 - w) // 16 + 1)
        rows = rnd.choice([1, 2, 100, rnd.randrange(1, 101)])
        y0 = rnd.randrange(0, 100 - rows + 1)
        stride = rnd.choice([320, 336, x0 + w + 2 * rnd.randrange(0, 9)])
        chunky = rnd.randbytes(stride * (rows + 2) + 64)
        planes = [rnd.randbytes(size) for _, size in AREAS]
        off = y0 * ROWLEN + x0 // 8
        regs = [rnd.getrandbits(32) for _ in range(16)]
        regs[6] = (regs[6] & 0xffff0000) | (w // 16 - 1)
        regs[7] = (regs[7] & 0xffff0000) | (rows - 1)
        regs[8] = CHUNKY + x0
        regs[9], regs[10] = P0 + off, P2 + off
        regs[14] = (regs[14] & 0xffff0000) | (ROWLEN - w // 8)
        regs[15] = STACK
        out = []
        for target, until in ((LOOP, END), (CODE_NEW, None)):
            m = Machine(UC_CPU_M68K_M68000)
            m.write(0, code)
            m.write(MODC, struct.pack('>h', stride - w))
            m.write(CODE_NEW, new)
            m.write(CHUNKY, chunky)
            for (a, _), data in zip(AREAS, planes):
                m.write(a, data)
            m.call(target, regs, until)
            out.append([m.read(a, size) for a, size in AREAS])
        if out[0] == planes:
            sys.exit(f'case {n}: the planes did not change')
        if out[0] != out[1]:
            for (a, _), x, y in zip(AREAS, *out):
                for i in range(len(x)):
                    if x[i] != y[i]:
                        print(f'case {n}: w {w} x0 {x0} rows {rows} y0 {y0} stride {stride}: '
                              f'first difference at {a + i:#x}: START {x[i]:02x}, '
                              f'new {y[i]:02x}')
                        sys.exit(1)
    print(f'{cases} cases identical')


if __name__ == '__main__':
    main()
