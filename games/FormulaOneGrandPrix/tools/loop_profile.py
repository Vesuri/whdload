#!/usr/bin/env python3
"""Count A2 call sites from a raw profile plus its same-run fast RAM dump.
Usage: loop_profile.py TRACE FAST_DUMP; writes TRACE.counts.json and endpoint PNGs.
All inputs and outputs must stay in tmp/.
"""
import hashlib
import json
from pathlib import Path
import sys
from slave_inputs import ROOT, verify
from race_profile import StackReduction, barto, game_hunks, image, locate

SITES = {
    'entry_draw': 0x3c652, 'entry_pacer': 0x3c65e,
    'live_head': 0x3c8f6, 'live_update': 0x3c98e,
    'live_draw': 0x3c9ba, 'live_pacer': 0x3c9d2,
    'replay_head': 0x3cc40, 'replay_update': 0x3ccc6,
    'replay_draw': 0x3cce8, 'replay_pacer': 0x3cd06,
}

def report(trace, fast):
    verify()
    trace, fast = Path(trace).resolve(), Path(fast).resolve()
    if not all(p.is_relative_to(ROOT/'tmp') for p in (trace, fast)):
        raise ValueError('captures must stay in tmp/')
    t = barto.load(str(trace))
    t.chip = image(t.chip, fast.read_bytes(), t.slow)
    bases = locate(t.chip, game_hunks())
    red = StackReduction()
    red.feed(t)
    result = dict(fields=len(t.fields), hunk_bases=bases,
                  trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),
                  fast_sha256=hashlib.sha256(fast.read_bytes()).hexdigest(),
                  counts={name: red.counts[bases[0][0]+off] for name, off in SITES.items()})
    trace.with_suffix('.counts.json').write_text(json.dumps(result, indent=2)+'\n')
    trace.with_suffix('.first.png').write_bytes(t.fields[0].shot)
    trace.with_suffix('.last.png').write_bytes(t.fields[-1].shot)
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    report(*sys.argv[1:])
