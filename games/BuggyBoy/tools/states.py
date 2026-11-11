#!/usr/bin/env python3
"""Per-frame snapshots of the game's state block, through a running server stopped in a race.

    python3 tools/states.py N OUT.npy [LO HI]

Breaks at the swap (program offset $2672, once per frame), N times, and dumps the program's
runtime range LO..HI (default the state block $9C60-$A170 at base $400, given as program
offsets $9860-$9D70) at each stop; saves an (N, HI-LO) uint8 array and prints the field
counter ($6AD8) per frame.
"""
import os
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import route  # noqa: E402

SWAP_ENTRY = 0x2672
FIELDS = 0x66D8


def main(argv):
    n, out = int(argv[0]), ROOT / argv[1]
    lo, hi = (int(argv[2], 16), int(argv[3], 16)) if len(argv) > 3 else (0x9860, 0x9D70)
    prog = route.prog_base()
    route.req('gdb', f'break *{prog + SWAP_ENTRY:#x}')
    rows, fields = [], []
    tmp = Path(tempfile.mkdtemp(dir=ROOT / 'tmp'))
    try:
        for i in range(n):
            route.req('gdb', 'continue')
            f = tmp / 's.bin'
            route.req('gdb', f'dump binary memory {os.path.relpath(f, ROOT)} {prog + lo:#x} {prog + hi:#x}')
            rows.append(np.frombuffer(f.read_bytes(), np.uint8))
            fields.append(route.peek(prog + FIELDS) >> 16)
    finally:
        route.req('gdb', 'delete')
        for p in tmp.iterdir():
            p.unlink()
        tmp.rmdir()
    np.save(out, np.array(rows))
    np.save(str(out).replace('.npy', '-fields.npy'), np.array(fields))
    print(' '.join(str((b - a) & 0xffff) for a, b in zip(fields, fields[1:])))


if __name__ == '__main__':
    main(sys.argv[1:])
