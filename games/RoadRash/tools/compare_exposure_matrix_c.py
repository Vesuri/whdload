import json,struct
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'tmp/c-approved-exposure-matrix'
report=[]
for cell in sorted(p for p in root.iterdir() if p.is_dir()):
 if not all((cell/k/'result.json').exists() for k in ('b','c')):continue
 maps={}
 for kind in ('b','c'):
  rows=json.loads((cell/kind/'result.json').read_text())['rows'];exposure=0;vals={};previous=524288
  for r in rows:
   b=bytes.fromhex(r['actors']['0xa5d60']);flags=b[104]
   position=struct.unpack_from('>I',b,4)[0];displacement=struct.unpack_from('>I',b,38)[0]
   assert position-previous==displacement,(cell.name,kind,r['cursor'],'origin/increment')
   previous=position
   if flags&2:exposure+=r['delta']
   if exposure>400:break
   assert flags&0xbd==0,(cell.name,kind,r['cursor'],flags)
   vals[exposure]=dict(cursor=r['cursor'],live=r['live'],exposure=exposure,speed=struct.unpack_from('>H',b,18)[0],distance=struct.unpack_from('>I',b,4)[0]-524288)
  maps[kind]=vals
 common=sorted(set(maps['b'])&set(maps['c'])-{0})
 pairs=[dict(exposure=e,b=maps['b'][e],c=maps['c'][e],percent=(maps['c'][e]['distance']/maps['b'][e]['distance']-1)*100) for e in common]
 result=dict(cell=cell.name,endpoint=pairs[-1],maximum_early_absolute_percent=max(abs(r['percent']) for r in pairs),pairs=pairs)
 report.append(result)
(root/'comparison.json').write_text(json.dumps(dict(rule='Last common completed boundary at or before 400 applied throttle fields (8 seconds); all earlier common boundaries retained. Position origin 524288 verified by each completed displacement, including the first.',cells=report),indent=2)+'\n')
for r in report:print(r['cell'],r['endpoint'],'early max',r['maximum_early_absolute_percent'])
