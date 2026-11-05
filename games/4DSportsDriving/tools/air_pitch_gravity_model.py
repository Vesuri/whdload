#!/usr/bin/env python3
"""Independently reconstruct fully extended airborne wheel axes from gravity."""
import json,struct,math
from pathlib import Path
p=Path('tmp/prof');result={}
def axis(v):return [-(v[8]+v[11]-v[2]-v[5]),v[7]+v[10]-v[1]-v[4]]
def angle(v):return math.atan2(v[0],v[1])*512/math.pi-256
for hz in (20,50):
 root=p/f'air-pitch{hz}';meta=json.loads((root/'anchor.json').read_text());mem=(root/'memory.bin').read_bytes();a=meta['data_base']+0x7ffe-meta['memory_base'];car=a-0x92e;priv=mem.index(b'4DA4PHYS')+12
 vel=list(struct.unpack_from('>4h',mem,car+0x4c));vf=[struct.unpack_from('>h',mem,priv+8+4*i)[0] for i in range(4)];pf=[struct.unpack_from('>h',mem,priv+10+4*i)[0] for i in range(4)]
 data=json.loads((root/'tilt-baseline.json').read_text())['records'];checks=[]
 for b,pr,po in zip(data['BUILT'],data['PITCH'],data['PITCH_OUT']):
  ds=[]
  for i,acc in enumerate((21,21,15,15)):
   if hz==20:vel[i]+=acc;ds.append(vel[i])
   else:
    step,pf[i]=divmod(10*vel[i]+2*vf[i]+7*acc+pf[i],25)
    dv,vf[i]=divmod(2*acc+vf[i],5);vel[i]+=dv;ds.append(step)
  if b[5:9]!=[384]*4:continue
  assert pr[1:10]==[16384,0,0,0,16384,0,0,0,16384],pr[1:10]
  old=axis(b[18:30]);actual=axis(pr[10:22]);predicted=[old[0],old[1]+ds[0]+ds[1]-ds[2]-ds[3]]
  assert actual==predicted,(hz,b[0],actual,predicted,ds)
  checks.append(dict(tick=b[0],old_pitch=b[3],new_pitch=po[1],old_axis=old,final_axis=actual,steps=ds,velocity=vel.copy(),velocity_fifths=vf.copy(),position_twentyfifths=pf.copy(),geometric_delta=angle(actual)-angle(old)))
 result[str(hz)]=dict(checked_axes=len(checks),rows=checks,scope='Every fully extended wheel-axis output is exactly explained by the original raw rebuilt axis plus the independently calculated differential gravity; no fitted parameters.')
(p/'air-pitch-gravity-model.json').write_text(json.dumps(result,indent=2)+'\n');print({hz:dict(calls=d['checked_axes'],first=d['rows'][0]['tick'],last=d['rows'][-1]['tick']) for hz,d in result.items()})
