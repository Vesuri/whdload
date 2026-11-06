#!/usr/bin/env python3
import csv,json,sys,collections
from pathlib import Path
p=Path(sys.argv[1]);b=json.loads((p/'segments.json').read_text())[0]
a=list(csv.reader((p/'profile.csv').open()));meta=list(map(int,a[0][1:]));print('META',meta)
pcs={int(x[1]):list(map(int,x[2:])) for x in a if x[0]=='pc'}
total=meta[1]-meta[0];summed=sum(sum(x[1:5]) for x in pcs.values());print('COVERAGE',summed,total,summed/total)
for pc,v in sorted(pcs.items(),key=lambda kv:-sum(kv[1][1:5]))[:40]:print(hex(pc),hex(pc-b),v[0],round(100*sum(v[1:5])/total,3),v[9:])
print('EXCEPTIONS',collections.Counter({k:sum(int(x[-1]) for x in a if x[0]=='exception' and x[2]==k) for k in {x[2] for x in a if x[0]=='exception'}}))
print('CACHE',sum(int(x[-1]) for x in a if x[0]=='cache'))
