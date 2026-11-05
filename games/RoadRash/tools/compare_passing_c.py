import json,struct
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'tmp'
def decode(r):
 out=dict(cursor=r['cursor'],live=r['live'],delta=r['delta'],actors={})
 for a,h in r['actors'].items():
  raw=bytes.fromhex(h)
  out['actors'][a]=dict(position=struct.unpack_from('>I',raw,4)[0],speed=struct.unpack_from('>H',raw,18)[0],acceleration=struct.unpack_from('>h',raw,20)[0],lateral=struct.unpack_from('>h',raw,0)[0],road=struct.unpack_from('>h',raw,54)[0],flags=raw[104:106].hex(),crash=struct.unpack_from('>b',raw,110)[0],displacement=struct.unpack_from('>I',raw,38)[0])
 out['gap']=out['actors']['0xa6260']['position']-out['actors']['0xa5d60']['position'];return out
b=[decode(r) for r in json.loads((root/'b-road-passing-boundaries/result.json').read_text())['rows']]
c=[decode(r) for r in json.loads((root/'c-road-passing-boundaries/result.json').read_text())['rows']]
bm={r['cursor']:r for r in b};cm={r['cursor']:r for r in c};pairs=[]
for t in sorted(bm.keys()&cm.keys()):
 x=bm[t];y=cm[t];pairs.append(dict(cursor=t,b=x,c=y,position_difference={a:y['actors'][a]['position']-x['actors'][a]['position'] for a in x['actors']}))
result=dict(common=pairs,b_first_pass=next((r for r in b if r['gap']<0),None),c_first_pass=next((r for r in c if r['gap']<0),None))
(root/'c-road-passing-boundaries/comparison.json').write_text(json.dumps(result,indent=2)+'\n')
for r in pairs:print(r['cursor'],'gap',r['b']['gap'],r['c']['gap'],'position differences',r['position_difference'],'speed B/C',[(a,r['b']['actors'][a]['speed'],r['c']['actors'][a]['speed']) for a in r['b']['actors']])
for k in ['b_first_pass','c_first_pass']:print(k,result[k]['cursor'] if result[k] else None)
