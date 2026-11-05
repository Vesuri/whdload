"""Summarize retained stationary-traffic field snapshots (not a pixel oracle)."""
import json, struct, sys
from pathlib import Path
p=Path(sys.argv[1]); rows=[]
for f in sorted((p/'state').glob('[0-9]*.bin')):
 d=f.read_bytes(); a=32766
 w=lambda o:struct.unpack_from('>h',d,a+o)[0]
 l=lambda o:struct.unpack_from('>i',d,a+o)[0]
 player=l(-30016)*256+(w(-30012)&255)
 cam=l(-30010)*256+(w(-30006)&255)
 cars=[l(6+i*4)*256+(w(46+i*2)&255) for i in range(1,10)]
 latched=[l(-94+i*4)*256+(w(-54+i*2)&255) for i in range(1,10)]
 buckets=d[a-342:a-342+122]
 main=sorted(set(x//2 for x in buckets[40:] if x))
 mirror=sorted(set(x//2 for x in buckets[:40] if x))
 rows.append(dict(field=int(f.stem),player=player,camera=cam,speed=w(-29944),relative=[x-player for x in cars],latched_relative=[x-cam for x in latched],main_bucket_ids=main,mirror_bucket_ids=mirror))
assert rows
out=dict(samples=len(rows),player_positions=sorted(set(r['player'] for r in rows)),speed_range=[min(r['speed'] for r in rows),max(r['speed'] for r in rows)],rows=rows)
(p/'stationary-report.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='rows'}))
for r in rows[::max(1,len(rows)//15)]:print(r)
