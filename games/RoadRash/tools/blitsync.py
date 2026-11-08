#!/usr/bin/env python3
"""Summarise a blitter-sync observer log (tools/patches/fsuae-blitsync.patch).

  python3 tools/blitsync.py LOG [MAIN_BASE]

One line per blit start PC and channel (D, A/B/C source write, R for register writes),
with the accessing PCs. PCs inside the main image are shown as main-hunk offsets; its
native base is $80000 on the harness machines (MAIN_BASE, hex, changes it). ROM PCs are
dropped. The log keeps the first access per (PC, blit, channel), so counts are sites,
not occurrences.
"""
import collections
import sys

MAIN_SIZE = 0x3c3ec


def main(path, base):
    def name(a):
        a = int(a, 16)
        return f'main+{a - base:05x}' if base <= a < base + MAIN_SIZE else f'{a:08x}'
    by = collections.defaultdict(lambda: dict(n=0, live=0, frames=[], pcs=collections.Counter(), info=None))
    for line in open(path):
        d = dict(kv.split('=', 1) for kv in line.split() if '=' in kv)
        access = line.split()[3]
        if d['pc'].startswith('00f') or d['blitpc'].startswith('00f'):
            continue
        b = by[(name(d['blitpc']), d['ch'])]
        b['n'] += 1
        b['live'] += int(d['live'])
        b['frames'].append(int(d['frame']))
        b['pcs'][f"{name(d['pc'])} {access}"] += 1
        b['info'] = b['info'] or f"con0={d['con0']} size={d['size']} range={d['range']}"
    for (blit, ch), b in sorted(by.items(), key=lambda x: min(x[1]['frames'])):
        print(f"{blit} {ch}: {b['n']} sites, {b['live']} live, frames {min(b['frames'])}-{max(b['frames'])}; {b['info']}")
        print('    by ' + ', '.join(p for p, _ in b['pcs'].most_common(6)))


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x80000)
