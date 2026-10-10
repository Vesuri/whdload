#!/usr/bin/env python3
"""Reject player catch-up debt created by a blocking same-session pit visit.

Use --report-only to inspect a known failing capture. This checks the player
allocator boundary, not opponent cadence, repairs, or complete mode/input state.
"""
import argparse
import json
from pathlib import Path
import re

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('capture', type=Path)
p.add_argument('--report-only', action='store_true')
a = p.parse_args()
root = a.capture
cfg = json.loads((root/'configuration.json').read_text())
assert re.search(r'\bCUSTOM5=13\b', cfg['WHD_ARGS'])
log = (root/'swaps-gdb.txt').read_text()
assert re.search(r'^PDEVENT \d+ 0xc7d2$',log,re.M), 'No accepted native rescue'
last_frame = None
pit = returned = first_frame = None
reports = []
entry_offset=0xce1e if re.search(r'^PDSESSION_EVENT -?\d+ 0xce1e ',log,re.M) else 0x103a2
for field, off, values in re.findall(r'^PDSESSION_EVENT (-?\d+) (0x[0-9a-f]+) (.+)$',log,re.M):
    field, off = int(field), int(off,16)
    v = list(map(int,values.split()))
    assert len(v) == 23
    if off == 0xca44:
        if returned is not None:
            first_frame = field
        last_frame = field
    elif off == entry_offset:
        assert pit is None and last_frame is not None
        assert v[13] == 1, 'Pit entry was not inside an active world update'
        pit = (field, last_frame, v)
    elif off == 0xcedc and pit is not None and returned is None:
        returned = field
    elif off == 0xccee and first_frame is not None:
        entry, frame_before, before = pit
        outside_fields = entry-frame_before + first_frame-returned
        assert outside_fields >= 0
        # Up to two field boundaries of observation/sampling uncertainty. A
        # genuine pre-existing backlog is allowed; pit duration is not.
        allowed_units = before[11] + 4*(outside_fields+2)
        allocated_units = 4*v[9] + v[11]
        report = dict(pit_entry_field=entry, world_return_field=returned,
                      pit_ms=20*(returned-entry), first_frame_field=first_frame,
                      first_batch_steps=v[9], retained_debt_ms=5*v[11],
                      assigned_plus_retained_ms=5*allocated_units,
                      outside_pit_allowance_ms=5*allowed_units,
                      passed=allocated_units<=allowed_units)
        reports.append(report)
        pit = returned = first_frame = None
assert reports and pit is None, 'No complete pit-return allocator observation'
print(json.dumps(dict(capture=root.name, visits=reports),indent=2))
if not a.report_only:
    assert all(r['passed'] for r in reports), 'Pit time became player movement backlog'
