import json,struct,subprocess,math,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'tmp/prof'
def word(b,x,fmt='h'):return struct.unpack_from('>'+fmt,b,0x7ffe+x-0x10000)[0]
def read(name,k):
 p=P/name;m=json.loads((p/'metadata.json').read_text());sz=m['snapshot_size'];b=subprocess.check_output(['zstd','-qdc',str(p/(k+'.bin.zst'))]);return m,[b[i:i+sz] for i in range(0,len(b),sz)]
def core(b):return b[0x18f4:0x1950] # a4+$98f6..$9951, positions and car dynamics
names=['a500','a500-slow','020','040'];result={};data={}
for n in names:
 m,bs=read('s3-coupling-'+n,'physics_out');_,ins=read('s3-coupling-'+n,'physics_in');_,controls=read('s3-coupling-'+n,'controls_in');data[n]=bs
 fields=[e['field'] for e in m['events'] if e['kind']=='physics_out'];dist=0;mphsum=0;moving=0
 for a,b in zip(ins,bs):
  if word(b,0x992c)>10 and not word(b,0x9606,'B') and not word(b,0x9605,'B'):
   dist+=math.dist([word(a,x,'i') for x in [0x98fc,0x9900,0x9904]],[word(b,x,'i') for x in [0x98fc,0x9900,0x9904]])/8;mphsum+=word(b,0x992c);moving+=1
 result[n]=dict(steps=len(bs),first_fields=fields[:15],end_pose_long=[word(bs[-1],x,'i') for x in [0x98fc,0x9900,0x9904]],end_mph=word(bs[-1],0x992c),mean_world_units_per_mph_step=dist/mphsum if mphsum else 0,moving_samples=moving,first_inputs=[dict(buttons=word(b,0x95f6),x=word(b,0x95fa)) for b in controls[:15]],first_physics_inputs=[word(b,0x95fa) for b in ins[:15]])
for n in names[1:]:
 a=data['a500'];b=data[n];i=next((i for i,(x,y) in enumerate(zip(a,b)) if core(x)!=core(y)),None);result[n]['first_car_dynamics_difference_step_0based']=i
 if i is not None:result[n]['first_differing_bytes']=[hex(j-0x7ffe+0x10000) for j in range(0x18f4,0x1950) if a[i][j]!=b[i][j]]
(P/'step3-coupling.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
