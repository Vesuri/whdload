#!/usr/bin/env python3
"""Differential native command tests for field-owned targets and shared tail."""
import itertools,json,random
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88
listing=(root/'tmp/c/control-targets.lst').read_text()
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/control-targets.hunk')).get_segments()[0].get_data()))
owned=[0x4c,0x4d,0x4e,0x4f,0x50,0x5a,0x51,0x5b,0x52,0x5c,0x53,0x5d,0x38,0x39,0x3a]
keys=owned+[0x7f];keys += [k|0x800 for k in keys]
checks=0;rng=random.Random(4303)
def helper(name,key):
 expected={r:rng.randrange(0x1000000) for r in range(1,17) if r not in (8,9)};expected[1]=p
 for r,v in expected.items():c.rw(r,v)
 c.rw(8,0x8f000);c.rw(9,key);c.call(base+sym(name))
 assert all(c.rr(r)==v for r,v in expected.items()),name
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 return c.rr(9)
def compare(key,collective,yaw,speed):
 global checks
 b=bytearray(rng.randbytes(86));b[0x39]=collective;b[0x3f]=yaw&255;b[0x50]=speed&255
 c.put(p,b);c.rw(8,0x8f000);c.rw(6,p);c.rw(16,key);c.rw(17,0x2000);c.call(h[0]+0x4ed4)
 assert c.rr(18)==0x90000
 native=c.get(p,86);c.put(p,b)
 assert helper('control_target_command',key)==int(key in owned)
 assert helper('control_target_tail',key)==key
 assert c.get(p,86)==native,(key,collective,yaw,speed,native.hex(),c.get(p,86).hex())
 checks+=1
for args in itertools.product(keys,range(43),range(-4,5),[-128,-15,-1,0,1,15,127]):compare(*args)
# Full byte domains catch wrapping rather than assuming legal target ranges.
for v in range(256):
 for key in owned:compare(key,v,v,(v*73)&255)
# Every possible command word: unknown commands must leave all bytes unchanged.
for key in range(65536):
 b=rng.randbytes(86);c.put(p,b);result=helper('control_target_command',key)
 assert result==int(key in owned)
 if not result:assert c.get(p,86)==b
r=dict(native_differential_cases=checks,full_word_dispatch_cases=65536,scope='primary view/collective/yaw and shared ordinary-command tail; no native installation')
(root/'tmp/c/control-target-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
