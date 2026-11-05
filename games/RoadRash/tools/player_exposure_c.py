import json,struct
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'tmp'
runs={}
for name in ['b-npc-acceleration-native','c-road-npc-acceleration-native']:
 source=json.loads((root/name/'result.json').read_text())['rows'];rows=[];exposure=0
 for r in source:
  if r['cursor']>500:break
  b=bytes.fromhex(r['actors']['0xa5d60']);flags=b[104]
  assert flags&0xbd==0
  if flags&2:exposure+=r['delta']
  rows.append(dict(cursor=r['cursor'],delta=r['delta'],exposure=exposure,speed=struct.unpack_from('>H',b,18)[0],gear=struct.unpack_from('>H',b,24)[0],acceleration=struct.unpack_from('>h',b,20)[0],position=struct.unpack_from('>I',b,4)[0]))
 runs[name]=rows
b,c=runs.values();cm={r['cursor']:r for r in c};ce={r['exposure']:r for r in c};pairs=[]
for r in b:
 if r['cursor'] not in cm or r['exposure'] not in ce:continue
 now=cm[r['cursor']];equal=ce[r['exposure']]
 pairs.append(dict(cursor=r['cursor'],b=r,c=now,c_equal_exposure=equal,same_cursor_speed_difference=now['speed']-r['speed'],equal_exposure_speed_difference=equal['speed']-r['speed'],same_cursor_position_difference=now['position']-r['position'],equal_exposure_position_difference=equal['position']-r['position']))
result=dict(scope='Player, normal riding before cursor 500; equal exposure is causal analysis, not a substitute for the live-field gate.',runs=runs,comparisons=pairs)
(root/'c-road-npc-acceleration-native/player-exposure.json').write_text(json.dumps(result,indent=2)+'\n')
for r in pairs:
 if r['cursor'] in [102,258,262,318,322,326,498]:print(json.dumps(r))
