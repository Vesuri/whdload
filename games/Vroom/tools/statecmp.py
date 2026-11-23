#!/usr/bin/env python3
"""Compare two `statelog` files frame by frame: the first frame whose state block differs,
and the addresses (long words) that differ there.

    python3 tools/statecmp.py A.txt B.txt [--skip ADDR,...]

--skip leaves out long words (hex addresses) known to differ for a reason, such as values a
render-only frame writes. Exit status 0 when the common frames agree."""
import argparse
import sys


def load(path):
    """The long words' addresses (from the header's ranges) and the rows."""
    base, rows = None, []
    for line in open(path):
        if line.startswith('#'):
            base = []
            for r in line.split()[5:]:
                if r.startswith('$') and '-' in r:
                    lo, hi = (int(v.lstrip('$'), 16) for v in r.split('-'))
                    base += range(lo, hi + 1, 4)
            continue
        frame, field, clock, block = line.split()
        rows.append((int(frame), int(field), int(clock), block))
    return base, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a')
    ap.add_argument('b')
    ap.add_argument('--skip', default='')
    ap.add_argument('--align', type=int, default=0, metavar='N',
                    help='first shift B by up to N rows to where its first row matches')
    args = ap.parse_args()
    skip = {int(x, 16) for x in args.skip.split(',') if x}
    base, a = load(args.a)
    base_b, b = load(args.b)
    if base != base_b:
        sys.exit('the logs cover different blocks')
    def same(ra, rb):
        return all(ra[3][8 * w:8 * w + 8] == rb[3][8 * w:8 * w + 8]
                   for w in range(len(ra[3]) // 8) if base[w] not in skip)
    if args.align:
        shift = next((k for k in range(-args.align, args.align + 1)
                      if -len(a) < k < len(b) and same(a[max(0, -k)], b[max(0, k)])),
                     None)
        if shift is None:
            sys.exit(f'no row of B within {args.align} matches the first of A')
        a, b = a[max(0, -shift):], b[max(0, shift):]
        print(f'B shifted by {shift}')
    n = min(len(a), len(b))
    for i in range(n):
        da, db = a[i][3], b[i][3]
        diff = [w for w in range(len(da) // 8)
                if da[8 * w:8 * w + 8] != db[8 * w:8 * w + 8] and base[w] not in skip]
        if diff:
            print(f'frame {i} differs (fields {a[i][1]} / {b[i][1]}): ' + ' '.join(
                f'${base[w]:X} {da[8 * w:8 * w + 8]}/{db[8 * w:8 * w + 8]}'
                for w in diff[:12]) + (' ...' if len(diff) > 12 else ''))
            sys.exit(1)
    print(f'{n} frames agree ({len(a)} and {len(b)} logged)')


if __name__ == '__main__':
    main()
