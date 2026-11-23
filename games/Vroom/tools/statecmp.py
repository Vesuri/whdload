#!/usr/bin/env python3
"""Compare two `statelog` files frame by frame: the first frame whose state block differs,
and the addresses (long words) that differ there.

    python3 tools/statecmp.py A.txt B.txt [--skip ADDR,...]

--skip leaves out long words (hex addresses) known to differ for a reason, such as values a
render-only frame writes. Exit status 0 when the common frames agree."""
import argparse
import sys


def load(path):
    base, rows = None, []
    for line in open(path):
        if line.startswith('#'):
            base = int(line.split('$')[1].split('-')[0], 16)
            continue
        frame, field, clock, block = line.split()
        rows.append((int(frame), int(field), int(clock), block))
    return base, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a')
    ap.add_argument('b')
    ap.add_argument('--skip', default='')
    args = ap.parse_args()
    skip = {int(x, 16) for x in args.skip.split(',') if x}
    base, a = load(args.a)
    base_b, b = load(args.b)
    if base != base_b:
        sys.exit('the logs cover different blocks')
    n = min(len(a), len(b))
    for i in range(n):
        da, db = a[i][3], b[i][3]
        diff = [base + 4 * w for w in range(len(da) // 8)
                if da[8 * w:8 * w + 8] != db[8 * w:8 * w + 8] and base + 4 * w not in skip]
        if diff:
            print(f'frame {i} differs (fields {a[i][1]} / {b[i][1]}): ' + ' '.join(
                f'${x:X} {da[(x - base) * 2:(x - base) * 2 + 8]}/{db[(x - base) * 2:(x - base) * 2 + 8]}'
                for x in diff[:12]) + (' ...' if len(diff) > 12 else ''))
            sys.exit(1)
    print(f'{n} frames agree ({len(a)} and {len(b)} logged)')


if __name__ == '__main__':
    main()
