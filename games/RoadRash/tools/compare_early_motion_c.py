import json,struct
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'tmp'
names=['b-early-motion-native','c-road-early-motion-native']
data=[json.loads((root/n/'result.json').read_text()) for n in names]
def actor(row,address):
 b=bytes.fromhex(row['actors'][address])
 return dict(position=struct.unpack_from('>I',b,4)[0],speed=struct.unpack_from('>H',b,18)[0],acceleration=struct.unpack_from('>h',b,20)[0])
release=[next(r for r in d['rows'] if r['kind']=='release' and not r['active']) for d in data]
assert release[0]['cursor']==release[1]['cursor']==41
assert release[0]['actors']==release[1]['actors']
checks=[];maps=[]
for name,d,rel in zip(names,data,release):
 rows=[r for r in d['rows'] if r['kind']=='motion' and r['active'] and r['cursor']<=100]
 previous=rel
 for r in rows:
  for address in ['0xa61e0','0xa6260']:
   p=actor(previous,address);a=actor(r,address)
   assert a['acceleration']==39
   assert a['speed']==p['speed']+p['acceleration']*r['delta'],(name,r['cursor'],'speed')
   assert a['position']==p['position']+a['speed']*r['delta'],(name,r['cursor'],'position')
  previous=r
 checks.append(dict(run=name,checked_motion_rows=len(rows),first_active_cursor=rows[0]['cursor'],last_cursor=rows[-1]['cursor'],applied_delta=sum(r['delta'] for r in rows)))
 maps.append({r['cursor']:r for r in rows})
pairs=[]
for t in sorted(maps[0].keys()&maps[1].keys()):
 b,c=[actor(m[t],'0xa61e0') for m in maps]
 pairs.append(dict(cursor=t,b=b,c=c,position_difference=c['position']-b['position'],speed_difference=c['speed']-b['speed']))
result=dict(release_cursor=41,release_actors_identical=True,release_live_fields=[r['live'] for r in release],checks=checks,common=pairs,scope='Post-motion/pre-pose boundaries; no throttle; two NPCs, through cursor 100. B cursor 102 excluded.')
(root/names[1]/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
