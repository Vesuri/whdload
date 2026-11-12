#!/usr/bin/env python3
"""The world state per logic step, from tools/route.py's `hash` dumps (tmp/hash/NAME.*).

    python3 tools/statehash.py hashes NAME            one hash per logic step, with its field
    python3 tools/statehash.py diff A B [FLOW]        equal steps; the first difference, by
                                                     address, with its writers from a
                                                     tools/dataflow.py pickle; and whether
                                                     the shown screens are equal at each step

A dump holds base memory $0-$13000 at the start of every step's world step ($DA56, after
the draw and the frame end; in an Enhanced run the loop's logic head) and both screens; the
screen compared is the one the parity $11E67 shows. In an Enhanced run the variables that
live in the copy (route.py MOVED) are read from there and laid over their chip addresses. The hash leaves out (EXCLUDE):
- the code: every byte of a reached instruction (tools/codemap.py), which in Enhanced runs
  holds the slave's entry jumps and in every run the horizon plotter's self-modified slots;
- the field counter $11DEA and the pacing wait's last exit $11ECC (a field number), which
  tell when the step ran, not what it computed (the elapsed count $11ECE stays in);
- the illegal-instruction vector $10, which the VERIFY slave points at its chip trap;
- the swap parity $11E67, which picks the back buffer: the Enhanced loop swaps twice per
  logic frame, 1.2 once (the logical parity is kept apart and drives $11E36);
- the horizon plotter's colour cache $CA4E, which says what its self-modified code slots
  hold (both excluded as code); a staged frame leaves it at its own last colour;
- the copper lists $12300-$124AD, written by the level-3 handler every field (the palette
  copy) and the frame end (the screen swap).
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

EXCLUDE = [(0x10, 0x14), (0xCA4E, 0xCA50), (0x11DEA, 0x11DEE), (0x11ECC, 0x11ECE), (0x11E67, 0x11E68),
           (0x12300, 0x124AE)]
PARITY = 0x11E67
# Code pointers the copy relocates (codemap.POINTER_SLOTS): in an Enhanced run they hold copy
# addresses, which are compared as the chip addresses they stand for.
COPY = (0x5000, 0x13000)
POINTERS = [0x14, 0x6C, 0x8266, 0x826A, 0x826E]
_mask = None


def mask(size=0x13000):
    global _mask
    if _mask is None:
        import codemap
        code = codemap.build()
        m = np.ones(size, dtype=bool)
        for b in code.covered:
            if b < size:
                m[b] = False
        for lo, hi in EXCLUDE:
            m[lo:hi] = False
        _mask = m
    return _mask


def load(name):
    p = ROOT / 'tmp/hash' / name
    meta = json.loads(p.with_suffix('.json').read_text())
    raw = np.frombuffer(p.with_suffix('.bin').read_bytes(), dtype=np.uint8)
    fields = [int(x) for x in p.with_suffix('.fields').read_text().split()]
    size = sum(b - a for a, b in meta['state'])
    moved = sum(k for _, k in meta['moved'])
    scr = sum(b - a for a, b in meta.get('screens', []))
    step = size + moved + scr
    n = len(raw) // step
    steps = raw[:n * step].reshape(n, step)
    state = steps[:, :size].copy()
    screens = steps[:, size + moved:]
    off = size
    for a, k in meta['moved']:
        state[:, a:a + k] = steps[:, off:off + k]
        off += k
    d = meta.get('delta', 0)
    if d:
        for p in POINTERS:
            v = state[:, p:p + 4].astype(np.uint32)
            v = (v[:, 0] << 24) | (v[:, 1] << 16) | (v[:, 2] << 8) | v[:, 3]
            inc = (v >= COPY[0] + d) & (v < COPY[1] + d)
            v = np.where(inc, v - d, v)
            for i in range(4):
                state[:, p + i] = (v >> (24 - 8 * i)) & 0xff
    # The screen shown at the step: an odd parity shows $68000 (the first), even $78000.
    half = screens.shape[1] // 2
    odd = (state[:, PARITY] & 1).astype(bool)
    load.screens = np.where(odd[:, None], screens[:, :half], screens[:, half:]) if half else screens
    return state, fields[:n]


def hashes(state):
    m = mask(state.shape[1])
    return [hashlib.sha1(s[m].tobytes()).hexdigest()[:16] for s in state]


def ranges(addrs):
    out = []
    for a in addrs:
        if out and out[-1][1] == a:
            out[-1][1] = a + 1
        else:
            out.append([a, a + 1])
    return out


def main(argv):
    if argv[0] == 'hashes':
        state, fields = load(argv[1])
        for i, (h, f) in enumerate(zip(hashes(state), fields)):
            print(f'{i:4d} {f:8d} {h}')
    elif argv[0] == 'diff':
        a, fa = load(argv[1])
        sa = load.screens
        b, fb = load(argv[2])
        sb = load.screens
        if sa.shape[1] and sb.shape[1]:
            k = min(len(sa), len(sb))
            eq = [bool((sa[i] == sb[i]).all()) for i in range(k)]
            bad = [i for i, e in enumerate(eq) if not e]
            print(f'screens equal at {sum(eq)} of {k} steps' + (f'; first different at step {bad[0]}' if bad else ''))
        ha, hb = hashes(a), hashes(b)
        n = min(len(ha), len(hb))
        same = sum(x == y for x, y in zip(ha, hb))
        first = next((i for i in range(n) if ha[i] != hb[i]), None)
        print(f'{argv[1]}: {len(ha)} steps, {argv[2]}: {len(hb)} steps; equal hashes {same} of {n}')
        print(f'fields: {fa[0]}..{fa[-1]} and {fb[0]}..{fb[-1]}; step fields equal relative to the '
              f'first: {sum((x - fa[0]) == (y - fb[0]) for x, y in zip(fa, fb))} of {n}')
        if first is None:
            print('identical')
            return
        m = mask(a.shape[1])
        d = np.nonzero((a[first] != b[first]) & m)[0].tolist()
        print(f'first difference at step {first} (fields {fa[first]} / {fb[first]}): {len(d)} bytes')
        flow = None
        if len(argv) > 3:
            from dataflow import DataFlow, lab
            flow = DataFlow.load(argv[3]).bytes_of('W')
        for lo, hi in ranges(d)[:40]:
            w = ''
            if flow is not None:
                tops = set().union(*(flow.get(x, set()) for x in range(lo, hi)))
                w = '  written by ' + ', '.join(sorted(lab(t) for t in tops))
            print(f'  ${lo:05x}-${hi - 1:05x}  {a[first][lo:hi].tobytes().hex()[:32]} / '
                  f'{b[first][lo:hi].tobytes().hex()[:32]}{w}')


if __name__ == '__main__':
    main(sys.argv[1:])
