#!/usr/bin/env python3
"""FR3: read FF1FastRenderStats ('FR3S' block) from every memory dump in the
given result directories, latest dump last.   fr3_stats.py DIR [DIR...]"""
import json, struct, sys
from pathlib import Path
F = ['installs', 'active', 'reject_cpu', 'reject_layout', 'alloc_fail', 'seeds', 'releases', 'publishes',
     'free_before', 'largest_before', 'min_free_after', 'block_bytes']


def scan(p):
    d = p.read_bytes(); out = []; at = 0
    while True:
        at = d.find(b'FR3S', at)
        if at < 0:
            return out
        if at % 2 == 0 and at + 4 + 4 * len(F) <= len(d):
            v = struct.unpack_from('>%dI' % len(F), d, at + 4)
            if v[0] < 1000 and v[11] in (0, 125760):
                out.append(dict(zip(F, v)))
        at += 4


res = {}
for d in sys.argv[1:]:
    rows = []
    for p in sorted(Path(d).glob('*.bin'), key=lambda p: p.stat().st_mtime):
        for s in scan(p):
            rows.append(dict(dump=p.name, **s))
    res[d] = rows
    last = rows[-1] if rows else None
    print(d, len(rows), 'dumps with stats; last:', last)
