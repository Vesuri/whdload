#!/usr/bin/env python3
"""Compare the A4 hashes of two state_run.py runs by gameplay step: hash_cmp.py RUN_A RUN_B

Prints the steps compared, the first differing ones, and a digest of each run for recording
baselines. Exits 1 if any step differs."""
import hashlib,json,sys
from pathlib import Path
def load(p):return {int(k):v for k,v in json.loads((Path(p)/'hashes.json').read_text()).items()}
def digest(d,steps):return hashlib.sha256(''.join(''.join(d[s]) for s in steps).encode()).hexdigest()[:12]
a,b=(load(p) for p in sys.argv[1:3])
common=sorted(set(a)&set(b));bad=[]
for st in common:
    d=[k for i,k in enumerate(('state','pixels')) if a[st][i]!=b[st][i]]
    if d:bad.append((st,d))
print(f'steps {common[0]}..{common[-1]}: {len(common)} compared, {len(bad)} differ',
      ('first: '+', '.join(f'{s} {"/".join(d)}' for s,d in bad[:8])) if bad else '')
print('digests:',' '.join(f'{p}={digest(d,common)}' for p,d in zip(sys.argv[1:3],(a,b))))
sys.exit(1 if bad else 0)
