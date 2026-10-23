#!/usr/bin/env python3
"""Cost per frame of each routine under the drawing calls, from a route profile.

  python3 tools/render_profile.py PROFILE_DIR [ROOT ...]     ROOT: Disk.1 offset, e.g. 577be

Reads route_profile.py's profile.pkl.gz and route.json. Call stacks are normalised to
Disk.1 offsets: copies in expansion memory (M1, S3; tools/relocation.py) count as their
chip originals, so a routine reached through its entry jump and one called from inside a
copy are the same routine. For each root (default: the drawing and publication calls of a
frame) it prints the inclusive cycles per published frame and a tree of its callees
(inclusive, then self), down to MIN_SHARE (default 1%) of the root. SLAVE_LST= names slave
offsets from a vasm listing (`vasm ... -L FILE`). Cycles are the traced CPU's clocks.

The reducer also pushes a frame where execution resumes after an exception, which never
pops; such frames are dropped, so interrupt time counts towards the interrupted routine
(as in beam-timed measurements).
"""
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev.callprofile import Reduction
from relocation import Map
from route_profile import DISK_DELTA, IMAGE, IMAGE_END

# Frame work in the main loop (docs/internals.md: P1 and the frame budget).
ROOTS = ['577be', '5765e', '5410e', '5afaa', '593a6', '5e840', '5e458']
FIELD = {'68020': 283_751, '68000': 141_876}   # CPU clocks per PAL field


def main():
    d = sys.argv[1]
    roots = ['D1:' + r.lower().lstrip('$') for r in (sys.argv[2:] or ROOTS)]
    min_share = float(os.environ.get('MIN_SHARE', '0.01'))
    meta = json.load(open(os.path.join(d, 'route.json')))
    red = Reduction.load(os.path.join(d, 'profile.pkl.gz'))
    reloc = Map(int(meta.get('expmem', '0'), 16))
    slave = int(meta['slave_base'], 16) if meta.get('slave_base') else None
    names = {}
    if os.environ.get('SLAVE_LST'):
        text = open(os.environ['SLAVE_LST'], encoding='latin1').read()
        names = {int(a, 16): n for a, n in re.findall(r'^([0-9A-F]{8}) (_\w+)$', text, re.M)}

    def label(fr):
        if isinstance(fr, str):
            return fr
        pc = reloc.to_chip(fr)
        if IMAGE <= pc < IMAGE_END:
            return f'D1:{pc + DISK_DELTA:05x}'
        if slave is not None and slave <= pc < slave + 0x10000:
            off = pc - slave
            return f'slave:{names[off]}' if off in names else f'slave:{off:04x}'
        return f'{pc:06x}'

    stacks = collections.Counter()
    for st, c in red.stacks.items():
        out = []
        for fr in st:
            if isinstance(fr, tuple):
                continue
            lab = label(fr)
            if not out or out[-1] != lab:
                out.append(lab)
        stacks[tuple(out)] += c
    frames = sum(1 for name, _, _ in red.events if name == 'frame')
    field = FIELD.get(meta['machine']['cpu_model'], FIELD['68020'])
    total = red.total()
    print(f'{meta["setup"]}, {meta["whd_args"]}: {total / len(red.fields):,.0f} cycles per field, '
          f'{frames} published frames ({len(red.fields) / max(frames, 1):.2f} fields each)')
    print(f'Per frame: cycles (fields of {field:,} cycles); inclusive, self.')

    for r in roots:
        # A root's cost is the sum over its outermost occurrences, wherever it was called from.
        callers = collections.Counter()
        for st, c in stacks.items():
            if r in st:
                callers[st[:st.index(r) + 1]] += c
        if not callers:
            print(f'\n{r}: not reached')
            continue
        top = sum(callers.values())
        print(f'\n{r}: {top / max(frames, 1):,.0f} cycles per frame '
              f'({top / max(frames, 1) / field:.2f} field), {100 * top / total:.1f}% of all cycles; '
              f'from {len(callers)} call paths')
        merged = collections.Counter()
        for st, c in stacks.items():
            if r in st:
                merged[st[st.index(r):]] += c
        walk_stacks(merged, r, top, frames, field, min_share, int(os.environ.get('DEPTH', '4')))


def walk_stacks(stacks, root, top, frames, field, min_share, depth):
    def node(path):
        n = len(path)
        incl = self_c = 0
        kids = collections.Counter()
        for st, c in stacks.items():
            if st[:n] == path:
                incl += c
                if len(st) > n:
                    kids[st[n]] += c
                else:
                    self_c += c
        return incl, self_c, kids

    def walk(path, ind, depth):
        incl, self_c, kids = node(path)
        pf = incl / max(frames, 1)
        print(f'{"  " * ind}{path[-1]:24} {pf:10,.0f} ({pf / field:4.2f})  self '
              f'{self_c / max(frames, 1):9,.0f}  {100 * incl / top:5.1f}%')
        if depth:
            for k, c in kids.most_common():
                if c / top >= min_share:
                    walk(path + (k,), ind + 1, depth - 1)
    walk((root,), 1, depth)


if __name__ == '__main__':
    main()
