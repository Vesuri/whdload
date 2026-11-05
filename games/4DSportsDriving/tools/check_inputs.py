#!/usr/bin/env python3
"""Check the retained archive and every pristine extracted file."""
from pathlib import Path
import hashlib, json
root = Path(__file__).resolve().parents[1]
stem = '4DSportsDriving_v1.2_1461'
archive = root / 'tmp/archives' / (stem + '.lha')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == archive.with_suffix('.lha.sha256').read_text().split()[0]
base = root / 'tmp/game' / stem
expected = json.loads(archive.with_suffix('.files.json').read_text())
actual = {str(p.relative_to(base)): sha(p) for p in base.rglob('*') if p.is_file()}
assert actual == expected, 'Pristine inputs changed'
print(f'Archive and all {len(actual)} pristine files verified')
