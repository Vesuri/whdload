import json,struct
from pathlib import Path
root=Path(__file__).resolve().parents[1]
g=(root/'tmp/game/GrandPrixCircuit_v1.0_0008/GrandPrixCircuit/data/GrandPrixCircuit').read_bytes();a4=0xe5bc+32766
def w(off):return struct.unpack_from('>H',g,a4+off)[0]
main=[w(-31280+i*2) for i in range(41)];mirror=[(((y-72)&65535)>>1)+9 for y in main[:21]]
count=0;allmax={}
for name,y,offs,step in [('main',main,(-612,-772,-692),-1),('mirror',mirror,(-972,-1198,-1044),1)]:
 for i in range(2,len(y)-1):
  for off in offs:
   lo,hi=w(off+y[i]*2),w(off+y[i+step]*2)
   assert -32768<=hi-lo<=32767
   values=[lo+(hi-lo)*f//256 for f in range(257)]
   assert values[0]==lo and values[-1]==hi
   assert all(min(lo,hi)<=v<=max(lo,hi) for v in values)
   count+=len(values)
# Centred roadside object at the first moving main boundary. Compare the
# horizontal shoulder offset over every representable camera fraction.
y0,y1=main[2],main[1]
old=[sum(w(off+(y0+(y1-y0)*f//256)*2) for off in (-772,-692)) for f in range(256)]
new=[sum(w(off+y0*2)+(w(off+y1*2)-w(off+y0*2))*f//256 for off in (-772,-692)) for f in range(256)]
result=dict(coefficient_vectors=count,all_endpoints_and_bounds='pass',near_centred_roadside_max_step_old=max(abs(b-a) for a,b in zip(old,old[1:])),near_centred_roadside_max_step_new=max(abs(b-a) for a,b in zip(new,new[1:])),scope='One-Q8-unit camera increments; coefficient model, not measured displayed frames or all-world-coordinate motion.')
(root/'tmp/phase8/projection-model.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
