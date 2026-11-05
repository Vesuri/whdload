#!/usr/bin/env python3
"""Summarise Phase 4 publications and verify the fastest fresh-boot repeat."""
import hashlib, json
from pathlib import Path
root = Path(__file__).resolve().parents[1] / 'tmp/phase4'
expected = '7af8f2f025632252c316c1ef6aa0991b254165edc2fac2d6a14784d41b01d0ed'
rows = []
for name in ('68030-50-1', '68030-100-1', '68030-100-2'):
    run = root / name
    meta = json.loads((run / 'metadata.json').read_text())
    assert meta['slave_sha256'] == expected
    assert hashlib.sha256((run / 'slave.slave').read_bytes()).hexdigest() == expected
    assert meta['cacr'] == 0x2000 and meta['races'] == 1
    counts = json.loads((run / 'swaps.json').read_text())
    assert len(counts) == 1000
    first = next(i for i, n in enumerate(counts) if n)
    last = max(i for i, n in enumerate(counts) if n)
    intervals = sum(counts[first+1:last+1])
    rows.append(dict(run=name, intervals=intervals, fields=last-first,
                     fps=50*intervals/(last-first), cacr=meta['cacr']))
a, b = [root / n for n in ('68030-100-1', '68030-100-2')]
checks = {}
for name in ('swaps.json', 'before.bin', 'code.bin'):
    x, y = (a/name).read_bytes(), (b/name).read_bytes()
    checks[name] = dict(bytes=len(x), identical=x == y,
                        sha256=hashlib.sha256(x).hexdigest())
assert checks['swaps.json']['identical']
meta = json.loads((a/'metadata.json').read_text())
for name in ('before.bin', 'code.bin'):
    x, y = (a/name).read_bytes(), (b/name).read_bytes()
    offsets = [i for i, (v, w) in enumerate(zip(x, y)) if v != w]
    checks[name]['different_ram_offsets'] = offsets
    checks[name]['different_bytes'] = len(offsets)
    for label, address, size in (('game_code', meta['code_base'], 0xe544),
                                  ('allocated_game_data', meta['data_base'], 0x9364)):
        lo = address - meta['base']
        equal = x[lo:lo+size] == y[lo:lo+size]
        checks[name][label+'_identical'] = equal
        assert equal, (name, label)
    checks[name]['all_differences_below_game_code'] = all(i < meta['code_base']-meta['base'] for i in offsets)
    assert checks[name]['all_differences_below_game_code']
assert json.loads((a/'metadata.json').read_text()) == json.loads((b/'metadata.json').read_text())
result = dict(measurements=rows, repeat=checks, metadata_identical=True)
(root/'review.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
