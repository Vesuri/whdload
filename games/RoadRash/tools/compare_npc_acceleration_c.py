import json,struct
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'tmp'
names=['b-npc-acceleration-native','c-road-npc-acceleration-native']
addresses=['0xa61e0','0xa6260']
def decode(r,a):
 b=bytes.fromhex(r['actors'][a]);return dict(position=struct.unpack_from('>I',b,4)[0],speed=struct.unpack_from('>H',b,18)[0],acceleration=struct.unpack_from('>h',b,20)[0],flags=b[104:106].hex(),lateral=struct.unpack_from('>h',b)[0])
result={'runs':[],'comparisons':{}};maps=[]
for name in names:
 rows=json.loads((root/name/'result.json').read_text())['rows'];maps.append({r['cursor']:r for r in rows});run=dict(name=name,first_cursor=rows[0]['cursor'],last_cursor=rows[-1]['cursor'],rows=len(rows),actors={})
 for a in addresses:
  changes=[];prev=None;position_exceptions=[]
  for r in rows:
   x=decode(r,a)
   if prev:
    assert x['speed']==max(0,prev['speed']+prev['acceleration']*r['delta']),(name,a,r['cursor'])
    if x['position']!=prev['position']+x['speed']*r['delta']:position_exceptions.append(r['cursor'])
   if prev is None or x['acceleration']!=prev['acceleration']:changes.append(dict(cursor=r['cursor'],**x))
   prev=x
  run['actors'][a]=dict(speed_recurrences_passed=len(rows)-1,position_exceptions=position_exceptions,acceleration_changes=changes)
 result['runs'].append(run)
for a in addresses:
 pairs=[]
 for t in sorted(maps[0].keys()&maps[1].keys()):
  b,c=[decode(m[t],a) for m in maps];pairs.append(dict(cursor=t,b=b,c=c,position_difference=c['position']-b['position']))
 result['comparisons'][a]=dict(first=pairs[0],first_negative=next(r for r in pairs if r['position_difference']<0),last=pairs[-1])
(root/names[1]/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
for r in result['runs']:print(r['name'],r['rows'],{a:(v['speed_recurrences_passed'],v['position_exceptions']) for a,v in r['actors'].items()})
print(json.dumps(result['comparisons'],indent=2))
