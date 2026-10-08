#!/usr/bin/env python3
"""Compare BH's data hunk between two state dumps taken at the same frame number.

  python3 tools/compare_state.py A_DIR B_DIR [BASE]

Each directory holds code.bin (the dump at BASE, default the 8 MB fast RAM at $200000) and
chip.bin from fixed_window.sh STATE_ONLY=1 (memory at the c2p entry of frame SKIP_FRAMES+1).
Prints the differing bh-data offsets grouped into runs. For the coupling test: two runs whose
frames take different numbers of fields (a slowed renderer) but the same input. If the game
steps once per frame, only per-field state (the VBL sound sequencer) may differ.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from bh_report import regions


def data(d, base):
    code, chip = open(f'{d}/code.bin', 'rb').read(), open(f'{d}/chip.bin', 'rb').read()
    os.environ['SLAVE'] = f'{d}/slave.slave'
    r = {n: (lo, hi) for lo, hi, n, o in regions(code, base, chip)}
    lo, hi = r['bh-data']
    mem, mbase = (chip, 0) if lo < len(chip) else (code, base)
    return mem[lo - mbase:hi - mbase]



if __name__ == '__main__':
    base = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0x200000
    a, b = data(sys.argv[1], base), data(sys.argv[2], base)
    diff = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
    print(f'bh-data: {len(a)} bytes, {len(diff)} differ')
    runs, start = [], None
    for i, o in enumerate(diff):
        if start is None: start = o
        if i + 1 == len(diff) or diff[i + 1] > o + 4:
            runs.append((start, o)); start = None
    for s, e in runs[:60]:
        # a4 = data hunk + $7FFE: print the a4 offset the code uses
        print(f'  bh-data:{s:05x}..{e:05x} ({s - 0x7ffe:+d}(a4))  {a[s:e + 1].hex()[:32]}  {b[s:e + 1].hex()[:32]}')
