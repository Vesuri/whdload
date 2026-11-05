import json,sys,struct
from pathlib import Path
from machine_profiles import banks
left,right=map(Path,sys.argv[1:3]);result={}
fields={'pose':(-0x6710,12),'angles':(-0x66bc,12),'speed':(-0x66d4,2),'gear':(-0x66ca,2),'clocks':(-0x6870,12),'crash':(-0x69fa,1),'replay':(-0x5229,1)}
rows=[]
for p in [left,right]:
 m=json.loads((p/'metadata.json').read_text());a4=m['layout']['a4'];memory=[(b,(p/('before-'+n+'.bin')).read_bytes()) for n,b,z in banks(m['configuration'])]
 def rd(addr,n):return next(b[addr-a:addr-a+n] for a,b in memory if a<=addr and addr+n<=a+len(b))
 rows.append({k:rd(a4+off,n).hex() for k,(off,n) in fields.items()})
r=dict(captures=[left.name,right.name],domain='B capture start after the same 3999-field wait; selected globals only',values=rows,different=[k for k in fields if rows[0][k]!=rows[1][k]],equal_scene_proven=False)
(right/'scene-start-comparison.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
