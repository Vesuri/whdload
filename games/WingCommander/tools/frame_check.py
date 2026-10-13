#!/usr/bin/env python3
"""A1 gate: check a --frame-stats capture against the read-only observer.

The observer logs every publication (E:3378e) with the game's VBL count and the
emulated cycle clock. Per field, the number of recorded pictures must equal the
number of observed publications, and the recorder's beam-line time over the
window must agree with the observer's elapsed cycles within one field.
"""
import argparse
import json
from collections import Counter
from pathlib import Path
from frame_report import records


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    meta = json.loads((a.run/'result.json').read_text())
    hz, lines, ev = records(a.run/'framestats.bin')
    layout_pc = int((a.run/'observer.cfg').read_text().split()[3], 16)  # E:3378e
    pubs = []
    for line in (a.run/'events.txt').read_text().splitlines():
        if line.startswith('#'):
            continue
        q = line.split()
        if int(q[0], 16) == layout_pc:
            # pc field hsync cycles vpos maxvpos baseclock unit d0..a7 clock ...
            pubs.append(dict(clock=int(q[24]), cycles=int(q[3]), vpos=int(q[4]), baseclock=int(q[6])))
    pairs = [((f0, f+1, t)) for (e0, f0, _), (e, f, t) in zip(ev, ev[1:]) if e0 == 15 and e == 6]
    shown = [(f, t) for _, f, t in pairs]
    # Publication between the two samples straddling a field edge is ambiguous.
    ambiguous = {f for f0, f, _ in pairs if f0+1 != f}
    if len(shown) < 100 or len(pubs) < 100:
        raise ValueError('too few pictures')
    # Recorder fields are relative to an unrecorded start. One-field pictures
    # make nearby offsets alike; score each over the whole sequence.
    observed = Counter(q['clock']+1 for q in pubs)
    recorded = Counter(f for f, _ in shown)
    candidates = {c-f for f in list(recorded)[:50] for c in observed}
    votes, offset = max((sum(min(n, observed[f+offset]) for f, n in recorded.items()), offset) for offset in candidates)
    mismatched = sorted(f for f, n in recorded.items() if observed[f+offset] != n)
    first, last = shown[0], shown[-1]
    cyc = {q['clock']+1: q for q in pubs}
    unit = pubs[0]['baseclock']*64
    observer_s = (cyc[last[0]+offset]['cycles']-cyc[first[0]+offset]['cycles'])/unit
    recorder_s = (last[1]-first[1])*records.line_ms/1000
    result = dict(run=a.run.name, pictures=len(shown), fields=len(recorded), mismatched_fields=mismatched,
                  offset=offset, matched_pictures=votes, observer_seconds=observer_s, recorder_seconds=recorder_s,
                  time_difference_ms=(recorder_s-observer_s)*1000,
                  ambiguous_pictures=sorted(ambiguous),
                  passed=all(any(abs(m-f) <= 1 for f in ambiguous) for m in mismatched) and abs(recorder_s-observer_s)*1000 <= 1000/hz)
    a.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
