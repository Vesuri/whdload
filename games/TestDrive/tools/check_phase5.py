#!/usr/bin/env python3
"""Evidence-based acceptance for the phase-5 model; no emulator or guest writes."""
import json,hashlib
from pathlib import Path
from harness import ROOT,sha
from timing_map import decode
P=ROOT/'tmp/phase5'
def load(p,frames=False):
 fs=sorted(p.glob('[0-9][0-9][0-9][0-9].bin'));assert fs
 ss=[]
 for f in fs:
  s=decode(f.read_bytes())
  if frames:
   b=(p/('frame-'+f.name)).read_bytes();assert len(b)==62
   for n,o in [('count',-36),('sum',-44),('period',-16),('deadline',-12)]:s[n]=int.from_bytes(b[52+o:56+o],'big',signed=True)
  ss.append(s)
 assert all(b['vbl']==a['vbl']+1 for a,b in zip(ss,ss[1:]))
 return ss
def changes(s,n):return [(i,x[n]) for i,x in enumerate(s) if i==0 or x[n]!=s[i-1][n]]
report={};short={};long={}
for preset in ['a500','a1200']:
 short[preset]=s=load(P/(preset+'-frames/states'),True);long[preset]=z=load(P/(preset+'-fields/states'))
 assert len(s)==201 and len(z)==1800
 assert all(x['period']==5 for x in s)
 assert all(x['deadline']-s[0]['vbl']==i//5*5 for i,x in enumerate(s))
 assert s[125]['count']-s[65]['count']==12 and s[125]['vbl']-s[65]['vbl']==60
 assert s[0]['count']==1 and s[0]['sum']==0
 assert all(x['count']==1 for x in s[:65])
 assert changes(s,'gear')[1]==(65,1)
 c=json.loads((P/('events-'+preset+'/crash/result.json')).read_text())
 assert c['penalty']==240 and c['wait_count_change']==0 and c['wait_speed_sum_change']==0 and c['recovery_chances']==4
 r=load(P/('events-'+preset+'/radar/states'),True);assert len(r)==1501
 assert r[-1]['count']-r[0]['count']==300
 assert all(x['chances']==4 and x['event']==0 for x in r)
 st=changes(r,'police_stop');assert [x[1] for x in st]==[0]+list(range(1,31))+[0]
 assert all(st[i+1][0]-st[i][0]==5 for i in range(1,30))
 first,last=st[1][0],st[-1][0]
 assert all(x['speed']==0 for x in r[first:last])
 report[preset]=dict(fields=len(z),period=5,clutch=changes(s,'clutch'),gear=changes(z,'gear'),rng_changes=len(changes(z,'rng'))-1,rng_first=changes(z,'rng')[1][0],clock_count_delta=12,clock_field_delta=60,crash_animation_fields=c['animation_fields'],crash_stop_to_ack_fields=c['stop_to_ack_fields'],crash_penalty=c['penalty'],radar_stop_first=first,radar_stop_30=st[-2][0],radar_clear=last,radar_vehicle_hold_fields=last-first,radar_count_delta=r[-1]['count']-r[0]['count'])
a,b=short['a500'],short['a1200']
assert next(i for i in range(201) if a[i]['speed']!=b[i]['speed'])==85
assert all(a[i]['count']==b[i]['count'] for i in range(201))
assert report['a500']['crash_animation_fields']!=report['a1200']['crash_animation_fields']
expected={'root':[0x230,0x4450,0x46aa],'overlay3':[0x162,0x1de,0x252,0x2c8,0xb28],'overlay4':[0x1294,0x130c,0x1eee,0x1f00,0x1f10,0x1f76]}
for n,sites in expected.items():
 data=(ROOT/'tmp/phase2'/(n+'.bin')).read_bytes()
 assert [i for i in range(0,len(data)-3,2) if data[i:i+4]==bytes.fromhex('4eac8146')]==sites
assert sha(ROOT/'tmp/build/release/TestDrive.Slave')=='ca765222b4257e060e684b80581ed45506d8167c98c016c6d088ad066d6750d4'
assert sha(ROOT/'tmp/phase5/a500-fields/slave.slave')=='d1b3a400a7a20bb7d78ee9745b815351fee6373f552a536b311076df6046fb07'
late=json.loads((P/'late-contexts.json').read_text())
assert late['a500']['counts']['h4:1eee']==9 and late['a1200']['counts']['h4:1eee']==17
assert late['a1200']['counts']['h4:1294']==1
report['rng_call_sites']={n:[hex(i) for i in v] for n,v in expected.items()}
report['result']='PASS';(P/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
