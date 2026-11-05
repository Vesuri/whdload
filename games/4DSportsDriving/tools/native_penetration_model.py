#!/usr/bin/env python3
"""Reproduce native penetration transforms, redirection, push and impact flags."""
import json,struct
from pathlib import Path
p=Path('tmp/prof')
raw=Path('tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/stunts').read_bytes()
data=0x3a1dc+0x7ffe
angles=raw[data-0x386c:data-0x386c+257]
sines=struct.unpack_from('>257h',raw,data-0x376a)
def atan_native(x,y):
 octant=(4 if x<0 else 0)+(2 if y<0 else 0);x,y=abs(x),abs(y)
 if x==y:
  if not x:return 0
  angle=128
 else:
  if x>y:x,y=y,x;octant+=1
  quotient=(x<<16)//y;angle=angles[(quotient>>8)+((quotient>>7)&1)]
 return (angle,256-angle,512-angle,256+angle,-angle,angle-256,angle-512,-256-angle)[octant]
def sine(a):
 a&=1023
 return sines[a] if a<=256 else sines[512-a] if a<=512 else -sines[a-512] if a<=768 else -sines[1024-a]
def length2(x,y):
 a=abs(atan_native(x,y))
 if a>=256:a=512-a
 return (abs(y)<<14)//sine(a+256) if a<=128 else (abs(x)<<14)//sine(a)
def length3(v):return length2(v[1],length2(v[0],v[2]))
def word(x):return (x+32768)%65536-32768
def trunc(x,d):return (abs(x)//abs(d))*(1 if x*d>=0 else -1)
def vec(r,prefix):return [r[prefix+'_'+a] for a in 'xyz']
def rotate(v,m):return [word(sum(v[j]*m[3*j+i] for j in range(3))//16384) for i in range(3)]
def classify(r):
 old,new=r['old_plane_y'],r['new_plane_y'];deep=not r['plane_flags'] and old<-12 and new<-12
 if deep and new<=-24:return 'retry_flat'
 if new==0:return 'backoff64'
 if old>0 and new<0:return 'crossing'
 return 'full_tangent'
def plane(r,v):
 d=[word(word(x>>6)-o) for x,o in zip(v,vec(r,'origin'))]
 return d[1] if r['plane']<4 else word(trunc(sum(x*n for x,n in zip(d,vec(r,'normal'))),8192))
report={}
for name in ('penetration-release20-source','penetration-landing20'):
 rows=json.loads((p/name/'penetration.json').read_text())['rows'];groups={}
 for r in rows:groups.setdefault((r['tick'],r['wheel']),{})[r['stage']]=r
 refs=json.loads((p/'first-release20/takeoff-plane.json').read_text())['rows'];refs={(r['tick'],r['wheel']):r for r in refs if r['event']=='SELECT'};results=[]
 for key,stages in groups.items():
  entry=stages['ENTER'];r=stages['ROTATED'];query=stages['REQUERY'];resolved=stages['RESOLVED'];done=stages['DONE'];m=[r[f'matrix{i}'] for i in range(9)];inverse=[m[3*j+i] for i in range(3) for j in range(3)]
  if 'origin_x' not in r:
   ref=refs[key];assert vec(entry,'new')==vec(ref,'world')
   r=dict(r)
   for a in 'xyz':r['origin_'+a]=word(ref['base_'+a]+ref['node_'+a]);r['normal_'+a]=ref['normal_'+a]
  old=vec(r,'old');new=vec(r,'new');origin=vec(r,'origin')
  for prefix,v in [('old_plane',old),('new_plane',new)]:
   local=[word(word(x>>6)-o) for x,o in zip(v,origin)]
   assert rotate(local,inverse)==vec(r,prefix),(name,key,prefix,rotate(local,inverse),vec(r,prefix))
  assert plane(r,new)==entry['clearance']
  branch=classify(r);assert branch in ('full_tangent','crossing'),(key,branch)
  if branch=='full_tangent':projected=r['distance'];straight=[0,0,0]
  else:
   ov=vec(r,'old_plane');nv=vec(r,'new_plane')
   ov=[ov[0],ov[2],word(-ov[1])];nv=[nv[0],nv[2],word(-nv[1])]
   numerator=word(-ov[2]);denominator=word(nv[2]-ov[2])
   if denominator<0:numerator=(numerator&65535)>>1;denominator=(denominator&65535)>>1
   assert denominator>0
   intersection=[word(ov[i]+trunc(word(nv[i]-ov[i])*numerator,denominator)) for i in (0,1)]+[0]
   assert intersection==vec(query,'correction')
   penetration_vector=[word((b-a)*64) for a,b in zip(intersection,nv)]
   projected=length3(penetration_vector)
   total=word(r['velocity']+r['distance']);rest=word(total-projected)
   assert total>0 and (total,rest)==(query['ratio_total'],query['ratio_rest'])
   straight=[word(trunc((b-a)*rest,total)) for a,b in zip(old,new)]
  tangent=rotate([0,0,projected],m)
  assert tangent==vec(query,'resolved'),(name,key,tangent,vec(query,'resolved'))
  expected=[a+b+c for a,b,c in zip(old,straight,tangent)]
  assert expected==vec(query,'new'),(name,key,expected,vec(query,'new'))
  push=[0,0,0]
  if 'PUSH_VECTOR' in stages:
   event=stages['PUSH_VECTOR'];assert event['clearance']<0
   push=rotate([0,word(-event['clearance']*64),0],m)
   assert push==vec(event,'correction')
  final=[a+b for a,b in zip(expected,push)];assert final==vec(resolved,'new')==vec(done,'new')
  assert done['velocity']==0
  if 'impact_flags' in r:
   expected_flags=r['impact_flags'] | (32 if r['velocity']>250 else 0)
   assert done['impact_flags']==expected_flags
  results.append(dict(tick=key[0],wheel=key[1],branch=branch,entry_clearance=entry['clearance'],old_plane_y=r['old_plane_y'],new_plane_y=r['new_plane_y'],whole_distance=r['distance'],projected_distance=projected,straight=straight,tangent=tangent,push=push,final=final,final_recomputed_clearance=plane(r,final),reported_clearance_at_done=done['clearance'],velocity_reset_verified=True))
 report[name]=results
result=dict(captures=report,scope='Exact independent Q14 transforms, signed-word/truncating arithmetic, native table-based intersection length/ratio, movement split, tangent vector, residual push and velocity/observed impact verification on12 native20 contacts. Straight steering direction here; retry-flat, backoff64, hard-crash, changing steering/heading and general terrain cases remain unaudited. Not a fractional-time solver. Final stored BC0 is deliberately not assumed to equal re-evaluated clearance after the push.')
(p/'native-penetration-model.json').write_text(json.dumps(result,indent=2)+'\n')
for name,rows in report.items():
 print(name,len(rows),{b:sum(r['branch']==b for r in rows) for b in ('full_tangent','crossing')})
 for r in rows:
  if r['wheel'] in (0,2):print(r)
