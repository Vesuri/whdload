#!/usr/bin/env python3
"""Check explicit session closure and fresh scheduler entry from read-only probes.

Requires at least two closures and two subsequent gameplay entries. This is not
pause, pit-return, rescue, or arbitrary nonlocal-exit coverage.
"""
import argparse
import json
from pathlib import Path
import re

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('captures', type=Path, nargs='+')
a = p.parse_args()
for root in a.captures:
    cfg = json.loads((root/'configuration.json').read_text())
    assert re.search(r'\bCUSTOM5=12\b', cfg['WHD_ARGS']) and int(cfg['FIELDS']) in (1800,3600)
    pending = None
    closed = None
    awaiting = None
    closures = restarts = inactive = 0
    discarded_steps = discarded_phase = discarded_inputs = discarded_engine = 0
    for field, off, values in re.findall(r'^PDSESSION_EVENT (-?\d+) (0x[0-9a-f]+) (.+)$',
                                        (root/'swaps-gdb.txt').read_text(), re.M):
        off = int(off, 16)
        v = list(map(int, values.split()))
        assert len(v) == 23
        if off in (0x12f6a, 0x13cde):
            assert all(v[i] == 0 for i in (8,9,11,12,13,16,17,18,19,20,21,22)), ('Timed gameplay leaked into menu/pit',field,v)
        if off == 0xc2aa:
            assert pending is None
            pending = (off, v)
        elif off == 0xc2b0:
            assert pending is not None
            entry, before = pending
            assert entry == 0xc2aa
            expected = before[:8]
            if before[8]:
                expected[1] += 1
                expected[2] += before[12]
                expected[3] += before[11]
                expected[4] += ((before[17]-before[16]) & 4080)//16
                expected[6] += before[21]-before[22]
                expected[7] = before[10]
                closures += 1
                discarded_steps += before[12]
                discarded_phase += before[11]
                discarded_inputs += ((before[17]-before[16]) & 4080)//16
                discarded_engine += before[21]-before[22]
            # Key discard count is recorded but not independently probed here.
            expected[5] = v[5]
            assert v[:8] == expected, ('Incorrect session discard accounting', field, before, v)
            assert all(v[i] == 0 for i in (8,9,11,12,13,16,17,18,19,20,21,22)), ('Session still owns timed work',field,v)
            closed, pending = v[:8], None
        if closed is not None:
            if off == 0xca44:
                assert v[8] == 0 and v[:8] == closed, 'Scheduler restarted before gameplay entry'
                awaiting, closed = closed, None
            else:
                assert v[8] == 0 and v[:8] == closed, 'Menu/pit input changed closed session state'
                inactive += 1
        elif awaiting is not None and off == 0xccee:
            assert v[0] == awaiting[0]+1 and v[1:8] == awaiting[1:8]
            assert v[8] == v[9] == v[12] == v[13] == v[18] == 1
            assert v[11] == 0 and v[14] == v[10] and v[15] == v[14]+18, 'New session inherited menu time or old control deadline'
            assert v[16] == v[17] == 0, 'New session inherited queued input'
            assert all(v[i] == 0 for i in (19,20,21,22)), 'New session inherited engine presentation'
            restarts += 1
            awaiting = None
    assert pending is None, 'Capture stops inside an exit gate'
    assert closures >= 2 and restarts >= 2 and inactive, 'Insufficient native exit/reentry coverage'
    print(f'{root.name}: {closures} explicit closures, {restarts} fresh gameplay entries; {inactive} inactive probes')
    print(f'  Discarded {discarded_steps} assigned steps, {discarded_phase*5} ms allocator debt, {discarded_inputs} inputs, {discarded_engine} engine events at session boundaries')
