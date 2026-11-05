#!/usr/bin/env python3
"""Native adapter ABI and sampled-payload tests against displaced instructions."""
import random,json
from unicorn_b import *
blob=bytes(BinFmt().load_image(str(build/'input/Gunship.Slave')).get_segments()[0].get_data())
listing=(build/'input/Gunship.lst').read_text(encoding='latin1')
def addr(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
c=CPU();c.put(base,blob)
c.put(4,struct.pack('>I',0x760000))
c.put(0x760000-120,bytes.fromhex('4e75'));c.put(0x760000-126,bytes.fromhex('4e75'))
M=addr('timing_input_marker');H=addr('timing_input_history');S=addr('timing_input_sample')
H0=0x400000;H2=0x500000;EV=0x600000;REF=0x700000;NATIVE=0x710000
c.put(M+8,struct.pack('>4I',H0,H2,H,S));c.put(M+40,struct.pack('>I',NATIVE))
rng=random.Random(13);cases=0
def state(flags):
 x={r:rng.randrange(0x1000000) for r in range(1,17)}
 x.update({8:0x8f000,17:0x2000|flags})
 return x
def run(entry,rs):
 c.rw(17,rs[17])
 for r,v in rs.items():
  if r!=17:c.rw(r,v)
 c.put(0x90000,bytes.fromhex('40f900730000'))
 c.call(entry,end=0x90006)
 out={r:c.rr(r) for r in range(1,18)}
 # Materialize flags before leaving uc_emu_start, which loses lazy NZVC.
 out[17]=int.from_bytes(c.get(0x730000,2),'big')
 return out

for flags in range(32):
 for dx,dy in [(0,0),(1,-1),(-32768,32767),(32767,-32768)]:
  REF=0x700000
  rs=state(flags);rs[1]=EV
  c.put(EV+10,struct.pack('>hh',dx,dy));c.put(M+28,struct.pack('>ii',900,-700))
  c.put(REF,bytes.fromhex('3228000a48414e75'))
  want=run(REF,rs);got=run(addr('timing_input_mouse'),rs)
  assert got==want,('mouse',flags,got,want)
  assert struct.unpack('>ii',c.get(M+28,8))==(900+dx,-700+dy)
  cases+=1
 for held,prev in [(0,0),(1,0),(2,0),(3,0),(3,1),(1,3),(0,3)]:
  REF=0x700100
  rs=state(flags)
  c.put(H2+16,struct.pack('>I',held));c.put(H0+0x4e2a,struct.pack('>H',prev))
  c.put(REF,bytes.fromhex('2a39')+struct.pack('>I',H2+16)+bytes.fromhex('4e75'))
  want=run(REF,rs);got=run(addr('timing_input_fire'),rs)
  assert got==want,('fire',flags,got,want)
  assert int.from_bytes(c.get(M+36,2),'big')==(held^prev)&held
  cases+=1
 for seq in (0,0xffffffff):
  REF=0x700200
  rs=state(flags);rs.update({1:EV,9:8,15:0x1234})
  c.put(M+24,struct.pack('>I',seq));c.put(REF,bytes.fromhex('3186080070564e75'))
  want=run(REF,rs);got=run(addr('timing_input_command'),rs)
  assert got==want,('command',flags,got,want)
  assert c.get(EV+8,2)==b'\x12\x34'
  assert int.from_bytes(c.get(M+24,4),'big')==(seq+1)&0xffffffff
  cases+=1
 # A native sampler fixture sets flags/registers; adapter must return them intact.
 c.put(NATIVE,bytes.fromhex('70ff72427c004e75'))
 rs=state(flags)
 c.put(H,struct.pack('>4H3I',0,0,1,0,0,0,55))
 c.put(H2+8,struct.pack('>3I',0xffffffff,1,3));c.put(H2+28,struct.pack('>I',56))
 c.put(H2+20,struct.pack('>II',123456,987654));c.put(H2+42,struct.pack('>hh',-123,456));c.put(H0+0xc8c,b'\x88')
 c.put(M+24,struct.pack('>IiiH',17,-12,32,2))
 want=run(NATIVE,rs);got=run(addr('timing_input_field'),rs)
 assert got==want,('field',flags,got,want)
 expected=struct.pack('>4IhhIHhhHII',56,0xffffffff,1,3,-123,456,17,0x88,-12,32,2,123456,987654)
 assert c.get(S,40)==expected and c.get(H+20,40)==expected
 assert c.get(H,2)==b'\0\1' and c.get(M+28,8)==bytes(8)
 cases+=1
# Delta truncation must fault and preserve unread slots, rather than publish.
for delta in (-32769,32768):
 for offset in (28,32):
  c.put(H,struct.pack('>4H3I',0,0,1,0,0,0,55));c.put(M+28,bytes(8));c.put(M+offset,struct.pack('>i',delta))
  old=c.get(H+20,5120);run(addr('timing_input_field'),state(0))
  assert c.get(H,2)==bytes(2) and c.get(H+6,2)==b'\0\1'
  assert c.get(H+8,4)==b'\0\0\0\1' and c.get(H+20,5120)==old
  cases+=1
# Diagnostic arm request is accepted only for the unused unmodified key 0x7f.
for key in (0x7f,0x17f):
 rs=state(0x1f);rs.update({1:EV,9:0,15:key})
 c.put(M+38,bytes(2));run(addr('timing_input_command'),rs)
 assert int.from_bytes(c.get(M+38,2),'big')==(key==0x7f)
 if key==0x7f:
  c.put(H,struct.pack('>4H3I',128,0,1,1,99,0,1))
  c.put(M+28,bytes(8));run(addr('timing_input_field'),state(0))
  assert struct.unpack('>4H3I',c.get(H,20))==(1,0,1,0,0,0,56)
  assert c.get(M+38,2)==bytes(2)
 cases+=1
# Master gate: off installs nothing, on reaches the validated patch list.
from amitools.binfmt.Relocate import Relocate
img=BinFmt().load_image(str(root/'tmp/game/Gunship/data/gamemule'))
addresses=[H0+i*0x20000 for i in range(len(img.get_segments()))]
original=bytes(Relocate(img).relocate(addresses)[0]);H2=addresses[2]
c.put(H0,original)
c.put(addr('verify_marker')+8,struct.pack('>9I',*addresses))
resload=0x740000
c.put(resload+0x64,bytes.fromhex('23c90075000023c8007500044e75'))
for enabled in (0,1):
 c.put(addr('_custom1'),struct.pack('>I',enabled));c.put(0x750000,bytes(8))
 before=c.get(H,5140);marker_before=c.get(M,44)
 rs=state(0);rs[3]=resload
 run(addr('timing_input_install'),rs)
 if enabled:
  assert c.get(0x750000,8)==struct.pack('>II',H0,addr('timing_input_patches'))
  assert c.get(H,20)==bytes(20)
 else:
  assert c.get(0x750000,8)==bytes(8)
  assert c.get(H,5140)==before and c.get(M,44)==marker_before
 assert c.get(H0,len(original))==original  # mock Patch only records arguments
 cases+=1
sb=addr('slv_base')
assert int.from_bytes(c.get(sb+12,2),'big')==17
config=sb+int.from_bytes(c.get(sb+50,2),'big')
assert c.get(config,len(b'C1:B:Enhanced framerate;\0'))==b'C1:B:Enhanced framerate;\0'
cases+=1
c.close();report=dict(cases=cases,scope='native input adapters: displaced-instruction ABI, field payload, signed delta overflow')
(root/'tmp/c/input-tests.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
