#!/usr/bin/env python3
import sys,csv,json,re,bisect,collections
from pathlib import Path
import replay_flight
from amigaxdev.disasm import records
p=Path(sys.argv[1]);b=json.loads((p/'segments.json').read_text())[0];code=(p/'entry-hunk0.bin').read_bytes()
a=list(csv.reader((p/'profile.csv').open()));total=int(a[0][2])-int(a[0][1]);pcs={int(x[1]):list(map(int,x[2:])) for x in a if x[0]=='pc'}
starts={b}|{int(x[2]) for x in a if x[0]=='call' and b<=int(x[2])<b+len(code)}
for o in range(0,len(code)-3,2):
 if code[o:o+2] in [b'\x4e\x56',b'\x4e\x55']:starts.add(b+o)
starts=sorted(starts);totals=collections.Counter()
for pc,v in pcs.items():
 if b<=pc<b+len(code):totals[starts[bisect.bisect_right(starts,pc)-1]]+=sum(v[1:5])
for pc,c in totals.most_common(45):
 print(hex(pc-b),round(100*c/total,3))
 for off,raw,txt in list(records(str(p/'entry-hunk0.bin'),b,b,pc-b,min(pc-b+24,len(code)),'68040'))[:4]:print(' ',hex(off),txt)
(p/'region-costs.json').write_text(json.dumps({hex(k-b):v for k,v in totals.items()},indent=2))
