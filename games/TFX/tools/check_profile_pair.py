#!/usr/bin/env python3
"""Strict observer on/off or cold-boot equivalence, with no state waiver."""
import json,sys,hashlib
from pathlib import Path
a,b=map(Path,sys.argv[1:3]);ca=json.loads((a/'counts.json').read_text());cb=json.loads((b/'counts.json').read_text())
for k in ['window','publications','events','inputs']:assert ca[k]==cb[k],k
for name in ['after.png']+[p.name for pattern in ['entry-hunk*.bin','start-hunk*.bin','end-hunk*.bin'] for p in a.glob(pattern)]:
 assert (a/name).read_bytes()==(b/name).read_bytes(),name
if (a/'profile.csv').exists() and (b/'profile.csv').exists():assert (a/'profile.csv').read_bytes()==(b/'profile.csv').read_bytes(),'profile'
print('PASS: exact events, inputs, image, game hunks and profile when present')
