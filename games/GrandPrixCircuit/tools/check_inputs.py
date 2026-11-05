#!/usr/bin/env python3
"""Every file of the pristine installed game (tmp/game/GrandPrixCircuit_v1.0_0008, from make
unpack) against manifest/GrandPrixCircuit_v1.0_0008.files.json: membership and SHA-256."""
import hashlib,json
from pathlib import Path
r=Path(__file__).resolve().parents[1]; stem='GrandPrixCircuit_v1.0_0008'
m=json.loads((r/f'manifest/{stem}.files.json').read_text()); root=r/f'tmp/game/{stem}'
a={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
assert a==m,'pristine file membership or hashes changed'
print(f'{len(m)} pristine files: all manifest hashes unchanged')
