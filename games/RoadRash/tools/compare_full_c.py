import sys,json,collections
from pathlib import Path
a,b=map(Path,sys.argv[1:3]);x=json.loads((a/'race.json').read_text());y=json.loads((b/'race.json').read_text())
assert (a/'hashes.bin').read_bytes()==(b/'hashes.bin').read_bytes()
assert x['events']==y['events']
assert all(x[k]==y[k] for k in ['capture','finish','finish_time','end_time','published'])
u=(a/'snapshot.bin').read_bytes();v=(b/'snapshot.bin').read_bytes()
ranges=[(0xa5d60,0x1180),(0xa5d50,16),(0xa5d1e,4),(0xa5d22,4),(0xa7220,8),(0xa59f4,2)]
for addr,n in ranges:assert u[addr-0xa5900:addr-0xa5900+n]==v[addr-0xa5900:addr-0xa5900+n],hex(addr)
for d in [x,y]:assert d['next_race']['capture'][2]==0
result=dict(hashes=x['published'],events=len(x['events']),equal_terminal_ranges=[dict(address=hex(a),size=n) for a,n in ranges],finish=x['finish'],finish_time=y['finish_time'],end_time=y['end_time'],restart=y['next_race']['capture'])
(b/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
