#!/usr/bin/env python3
"""Audit native contact/reset block; intercept its external notification call."""
import itertools,json
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88
c=CPU();c.put(0x200000,mem)
# Notification itself is outside this fixture; preserve the real branch and stores.
c.put(h[0]+0xa150,bytes.fromhex('4e75'))
cases=[]
for previous_air,speed,vertical,roll,config,damage in itertools.product([0,255],[-128,-32,0,32,96,255],[-128,-32,-1,0,32,127],[-20,0,20],[0,1],[0,12]):
 b=bytearray(86)
 struct.pack_into('>h',b,0x2a,speed);struct.pack_into('>H',b,0xe,damage)
 b[0x10]=config;b[0x36]=7;b[0x37]=roll&255;b[0x3e]=vertical&255
 c.put(p,b);c.put(h[6]+0x42f6,b'\0');c.rw(8,0x8f000);c.rw(6,p);c.rw(11,previous_air);c.rw(17,0x2000)
 c.call(h[0]+0x95a0,end=h[0]+0x9636)
 assert c.rr(18)==h[0]+0x9636
 out=c.get(p,86)
 assert out[0x2a:0x2c]==b'\0\0' and all(out[x]==0 for x in [0x36,0x37,0x3e])
 changed=[i for i in range(86) if b[i]!=out[i]]
 assert set(changed)<=set([0x18,0x2a,0x2b,0x36,0x37,0x3e,0x52])
 cases.append(dict(previous_air=bool(previous_air),speed=speed,vertical=vertical,roll=roll,config=config,damage=damage,end=out[0x18],crash=out[0x52]))
r=dict(cases=len(cases),scope='native +095a0..+09636, altitude already zero; notification +0a150 stubbed',flight_end_cases=sum(x['end']!=0 for x in cases),crash_states=sorted(set(x['crash'] for x in cases)),fixtures=cases)
(root/'tmp/c/player-ground-audit.json').write_text(json.dumps(r,indent=2)+'\n');print({k:v for k,v in r.items() if k!='fixtures'});c.close()
