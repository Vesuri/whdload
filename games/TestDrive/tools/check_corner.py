#!/usr/bin/env python3
"""Compare native corner rows and exhaust the camera fraction at the near plane."""
import json,struct
from pathlib import Path
from corner_model import ROOT,model,l,u
out=ROOT/'tmp/corner-jump';report={'native':{},'exhaustive':[]}
for name,seg,lane,bank in [('corrected-left-bank-v3',202,180,5),('final-right-bank-v2',100,-180,-5),('final-hill-bank',230,180,5)]:
 folder=out/name;frames=sorted(folder.glob('frame-*.bin'));assert len(frames)==96,(name,len(frames))
 for p in frames:
  b=p.read_bytes();expected,rows=model(seg,u(b,-22338),lane,bank*65536,heights=True,data=b)
  actual=(l(b,-29844),l(b,-29848),u(b,-29852));assert expected==actual,(p,expected,actual)
  raw=p.with_name(p.name.replace('frame','rows')).read_bytes()
  for i,row in enumerate(rows):
   x,y,c,s,idx=struct.unpack_from('>iiiHH',raw,i*16)
   assert idx==i and (x,y,s,c)==row,(p,i,(x,y,s,c),row)
 report['native'][name]={'frames':len(frames),'rows_per_frame':40,'phases':len({u(p.read_bytes(),-22338) for p in frames}),'status':'PASS'}
print('Native rows passed',flush=True)
for seg,lane,bank,hills in [(202,0,0,False),(202,180,5,False),(100,-180,-5,False),(30,180,-5,False),(385,0,0,False),(230,180,5,True)]:
 arms={}
 for fixed in [False,True]:
  vals=[model(seg,f,lane,bank*65536,fix=fixed,heights=hills)[0][0] for f in range(65536)]
  jump,f=max((abs(b-a)/65536,i+1) for i,(a,b) in enumerate(zip(vals,vals[1:])))
  if fixed:assert jump<0.1,(seg,lane,bank,jump,f)
  arms['corrected' if fixed else 'previous']={'largest_adjacent_step_pixels':jump,'camera_fraction':f}
 report['exhaustive'].append(dict(segment=seg,lane=lane,bank=bank,hills=hills,phases=65536,**arms))
 print(report['exhaustive'][-1],flush=True)
report['status']='PASS';report['scope']='Native draw-only fixtures on A1200/68040 CACHE; no host memory writes; independent integer model. Adjacent 16.16 camera phases are not frame-rate measurements.'
(out/'geometry-regression.json').write_text(json.dumps(report,indent=2)+'\n')
