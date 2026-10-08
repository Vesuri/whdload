#!/usr/bin/env python3
"""Which of BH's state follows T: compare three STATE_ONLY dumps of the same flight.

  python3 tools/tscale_compare.py A_DIR B_DIR C_DIR [BASE]

A: the normal step divisor T at flight frame N; B: T x 2 (make tscale TSCALE=2) at frame 2N,
the same game time if every per-step quantity goes through T; C: normal T at frame 2N, the
same number of steps as B. Prints the bh-data words that differ, as signed words (and the
long they start, if even-aligned with its neighbour), classified:
  time    B is nearer A than C: the quantity advances by game time (T-scaled)
  steps   B is nearer C: it advances per step, whatever T is
  other   neither (diverged, or the same in A and C but changed in B)
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from compare_state import data

base = int(sys.argv[4], 0) if len(sys.argv) > 4 else 0x200000
A, B, C = (data(d, base) for d in sys.argv[1:4])
n = min(len(A), len(B), len(C))


def w(m, o):
    v = int.from_bytes(m[o:o + 2], 'big')
    return v - 65536 if v >= 32768 else v


def l(m, o):
    v = int.from_bytes(m[o:o + 4], 'big')
    return v - (1 << 32) if v >= 1 << 31 else v


counts = {'time': 0, 'steps': 0, 'other': 0}
rows = []
for o in range(0, n - 1, 2):
    a, b, c = w(A, o), w(B, o), w(C, o)
    if a == b == c:
        continue
    if a == c:
        k = 'other'
    elif abs(b - a) < abs(b - c):
        k = 'time'
    elif abs(b - c) < abs(b - a):
        k = 'steps'
    else:
        k = 'other'
    counts[k] += 1
    rows.append((o, k, a, b, c))
print(f'bh-data: {n} bytes; differing words: ' + ', '.join(f'{k} {v}' for k, v in counts.items()))
for o, k, a, b, c in rows:
    # a4 = data hunk + $7FFE: the offset the code uses
    lng = f'  long {l(A, o)} {l(B, o)} {l(C, o)}' if o + 4 <= n else ''
    print(f'{o - 0x7ffe:+7d}(a4) {k:5s}  A {a:6d}  B {b:6d}  C {c:6d}{lng}')
