#!/usr/bin/env python3
"""Diagnose differences at observed SOFT stores in tick-aligned captures.
The trace map is incomplete: agreement is evidence, not full equivalence.
"""
import argparse,json,collections
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('a',type=Path);p.add_argument('b',type=Path);p.add_argument('map',type=Path)
p.add_argument('--shift-a',type=int,default=0);p.add_argument('--shift-b',type=int,default=0)
a=p.parse_args();ma=json.loads((a.a/'metadata.json').read_text());mb=json.loads((a.b/'metadata.json').read_text())
assert {n:hi-lo for n,(lo,hi) in ma['regions'].items()}=={n:hi-lo for n,(lo,hi) in mb['regions'].items()},'captured region sizes differ'
m=json.loads(a.map.read_text());g=m['game_base'];targets=collections.defaultdict(dict);missing=[]
for offset,item in m['writes'].items():
    address=g+int(offset)
    for byte in range(max(item['sizes'])):
        addr=address+byte
        for name,(lo,hi) in m.get('regions',ma['regions']).items():
            if lo<=addr<hi:
                if name in ma['regions']:targets[name][addr-lo]=item['pcs']
                else:missing.append(addr)
                break
        else:missing.append(addr)
n=min(ma['fields']-a.shift_a,mb['fields']-a.shift_b)
for name,offsets in targets.items():
    differences=collections.Counter()
    for i in range(n):
        suffix='' if name=='game' else '-'+name
        x=(a.a/f'{i+a.shift_a:04d}{suffix}.bin').read_bytes();y=(a.b/f'{i+a.shift_b:04d}{suffix}.bin').read_bytes()
        for off in offsets:
            if x[off]!=y[off]:differences[off]+=1
    print(f'{name}: {len(offsets)} observed SOFT-written bytes; {len(differences)} differing offsets in {n} ticks')
    for off,count in sorted(differences.items()):
        print(f'  {name}:{off:05x}: {count} ticks differ; writers '+','.join(f'game:{pc:05x}' for pc in offsets[off]))
print(f'{len(set(missing))} observed written bytes outside captured hunks')
