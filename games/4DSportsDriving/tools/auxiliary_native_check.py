#!/usr/bin/env python3
"""Independently inspect actual native fragment updater acceptance snapshots."""
from pathlib import Path
import argparse,struct,json,re
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args();p=a.capture;b=(p/'memory.bin').read_bytes();i=b.index(b'4DAUXNAT');assert struct.unpack_from('>HHI',b,i+8)==(2,9,9)
s={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)$',(p/'slave.lst').read_text(encoding='latin1'),re.M)};base=i-s['sim_aux_native_marker'];data=lambda n:b[base+s[n]:base+s[n]+1120]
born=data('sim_aux_birth_native');normal=data('sim_aux_normal_native');two=data('sim_aux_expected_native');assert b[i+16:i+20]==b'AUN1' and b[base+s['sim_aux_reuse_neighbor']+8:base+s['sim_aux_reuse_neighbor']+12]==b'AUN2'
w=lambda d,o:struct.unpack_from('>H',d,o)[0];l=lambda d,o:struct.unpack_from('>I',d,o)[0]
assert sum(w(born,0x38e+2*k)!=0 for k in range(24))==24
for k in range(24):
 for off in (0,0xc0):
  q=off+4*k;assert (l(two,q)-l(born,q))&0xffffffff==2*(l(normal,q)-l(born,q))&0xffffffff
 assert l(two,0x60+4*k)==l(normal,0x60+4*k)
 assert w(two,0x3be+2*k)==w(normal,0x3be+2*k)
 for off in (0x2fe,0x32e):
  q=off+2*k;assert (w(two,q)-w(born,q))&65535==32 and (w(normal,q)-w(born,q))&65535==16
r=dict(native_cases=9,fragments=24,normal_vertical_matches_two_a2500_steps=True,normal_horizontal_and_rotation_half_a2500=True,a4000_five_steps_match_two_a2500=True,guards=True)
(p/'native-fragment-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
