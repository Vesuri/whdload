#!/usr/bin/env python3
"""tools/framecmp.py A B [--by tick|frame] [--lines FIRST-LAST]: compares two `frames` files (tools/vroom.py)
frame by frame, matched by tick (default) or by frame number: how many matched frames are
equal, and for each differing one the planes and lines that differ (a line is 40 bytes of
one plane: plane = index / 200, line = index % 200). --lines compares only those screen lines
(in every plane): lines 175-199, the cockpit's bottom, differ between two runs of the same
build on the a1200-040.)"""
import sys


def load(path, key):
    out = {}
    for line in open(path):
        f = line.split()
        if len(f) > 2:
            out[int(f[1 if key == 'tick' else 0])] = f[2:]
    return out


def main(argv):
    key = argv[argv.index('--by') + 1] if '--by' in argv else 'tick'
    a, b = load(argv[0], key), load(argv[1], key)
    first, last = (map(int, argv[argv.index('--lines') + 1].split('-')) if '--lines' in argv
                   else (0, 199))
    common = sorted(set(a) & set(b))
    bad = []
    for k in common:
        diff = [i for i, (x, y) in enumerate(zip(a[k], b[k]))
                if x != y and first <= i % 200 <= last]
        if diff:
            planes = sorted({i // 200 for i in diff})
            lines = sorted({i % 200 for i in diff})
            bad.append(f'{key} {k}: planes {planes} lines {lines[0]}-{lines[-1]} ({len(diff)} plane lines)')
    print(f'{len(common)} frames matched by {key}, {len(common) - len(bad)} equal'
          f' (lines {first}-{last})')
    for x in bad[:30]:
        print('  ' + x)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
