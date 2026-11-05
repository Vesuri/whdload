#!/usr/bin/env python3
"""Connect scaled response/linear rates to native stages; prove h=1 and fractions."""
import json,random
from fractions import Fraction as F
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/kinematics-step.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/kinematics-step.lst').read_text()
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
whole=0x300000;stages=0x310000;p=0x320000;out=0x320100;terms=0x320200;state=0x320300;rng=random.Random(9636);calls=0
trunc=lambda n,d:-(abs(n)//d) if n<0 else n//d
signed=lambda n:n-2**32 if n&2**31 else n
sb=lambda n:(n&255)-256 if n&128 else n&255
sw=lambda n:(n&65535)-65536 if n&32768 else n&65535
def call(name,ptrs):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update(ptrs)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(base+sym(name));calls+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 for r,v in regs.items():
  if r==9 or r==10 and name=='fraction_add_rate':continue
  assert c.rr(r)==v,(name,r)
 return c.rr(9)
def long(off):return struct.unpack('>i',c.get(state+off,4))[0]
def qvalue(off,rate,conversion=None):return F(long(off),32767)+(F(long(conversion),rate*32767) if conversion else 0)
assert call('motion_preview_prepare',{1:h[0],2:whole})==0
assert call('motion_stages_prepare',{1:h[0],2:stages})==0
fixtures=json.loads((root/'tmp/c/player-motion-fixtures.json').read_text())


fieldshadow=0x330000
scenarios=[('level',0,0,26,0,28,0,0),('climb',0,0,34,0,28,0,0),('descent',0,0,18,0,28,0,0),('forward',12,0,30,0,28,0,0),('bank',8,16,30,0,28,0,0),('yaw',0,0,26,2,28,0,0),('wind',0,0,26,0,28,3,-2),('coast',8,0,26,0,0,0,0)]
results=[]
def pose(ptr,shadow=None,rate=None):
 b=c.get(ptr,86)
 values=dict(x=int.from_bytes(b[:2],'big'),y=int.from_bytes(b[2:4],'big'),height=int.from_bytes(b[28:30],'big'),speed=sw(int.from_bytes(b[42:44],'big')),vertical=sb(b[62]),rpm=b[27],heading=b[53],track=b[61])
 if shadow is not None:
  def i(off):return int.from_bytes(c.get(shadow+off,4),'big',signed=True)
  for key,main,conv in [('speed',8,12),('vertical',4,None),('rpm',16,20),('heading',28,32),('track',36,40)]:
   values[key]+=i(main)/32767+(i(conv)/(rate*32767) if conv is not None else 0)
  for key,off in [('height',48),('x',52),('y',56)]:values[key]+=i(off)/rate
 return values

initial=bytearray(86);struct.pack_into('>HH',initial,0,0x7000,0x8000);struct.pack_into('>H',initial,28,1024)
initial[16]=2;initial[27]=128;initial[57]=26;initial[66]=28
c.put(p,initial);c.put(out,initial);assert call('kinematics_init',{1:fieldshadow,9:60})==0
trace=[]
for field in range(1,121):
 interval=(field-1)*3//60+1;c.put(out+12,struct.pack('>H',interval))
 before=pose(out,fieldshadow,60)
 c.put(0x350000,c.get(out,86));c.put(terms,bytes(12))
 for stage in [0,1]:assert call('motion_stage',{1:0x350000,2:stages,3:terms,9:stage})==0
 target=int.from_bytes(c.get(terms+2,2),'big',signed=True)
 assert call('kinematics_step',{1:fieldshadow,2:out,3:stages,4:h[0]+0x7a44,9:0})==0
 row=dict(field=field,tick=interval,before=before,target=target,after=pose(out,fieldshadow,60),integer_height=int.from_bytes(c.get(out+28,2),'big'),integer_vertical=sb(c.get(out+62,1)[0]))
 if field%20==0:
  c.put(p+12,struct.pack('>H',field//20));call('motion_preview',{1:p,2:0x340000,3:whole,9:0});c.put(p,c.get(0x340000,86));row['native']=pose(p)
 trace.append(row)
(root/'tmp/c/height-feedback-trace.json').write_text(json.dumps(trace,indent=2)+'\n')
previous=None
for row in trace:
 key=(row['target'],row['integer_height'],row['integer_vertical'])
 if key!=previous or 'native' in row:print(row)
 previous=key
c.close()
