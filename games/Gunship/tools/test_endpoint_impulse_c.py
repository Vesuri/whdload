"""Experimental native-endpoint field distribution; not production assembly.
Recomputes a native whole-tick candidate from interval anchor and fresh input
on every field, distributes its delta, and retains fractional state. Explicitly
uses linear within-interval distribution instead of the old response substeps.
"""
from unicorn_b import *
from layout import locate
from fractions import Fraction as F
import json,math,ast
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];c=CPU();c.put(0x200000,mem)
c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/endpoint-impulse.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/endpoint-impulse.lst').read_text()
def sym(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
def call(name,args):
 for r,v in args.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(sym(name));assert c.rr(18)==0x90000 and c.rr(9)==0,(name,c.rr(9))
STAGES=0x310000;P=0x320000;SH=0x330000;PACKET=0x340000;GEOM=0x520000;WP=h[6]+0x3b88
call('motion_stages_prepare',{1:h[0],2:STAGES});call('scene_private_prepare',{1:h[0],2:h[6],3:GEOM})
c.put(h[0]+0xba08,bytes(2))
# Motion variables only; other candidate bytes are provisional derived outputs.
fields=[(0,2,False,False),(2,2,False,False),(28,2,False,False),(42,2,True,False),(27,1,False,False),(53,1,False,True),(61,1,False,True),(54,1,True,False),(55,1,True,False),(62,1,True,False)]
def read(b,spec):
 off,n,sgn,circ=spec;return int.from_bytes(b[off:off+n],'big',signed=sgn)
OWNER=0x3b0000;LIVE=0x3c0000;OWNER_SIZE=164
ANCHOR=0x380000;RESIDUES=0x390000;DISTRIBUTED=0x3a0000
def distribute(anchor,target,previous,n):
 current=bytearray(target)
 for off,width,_,_ in fields:current[off:off+width]=previous[off:off+width]
 c.put(ANCHOR,anchor);c.put(P,target);c.put(DISTRIBUTED,current)
 call('endpoint_motion_step',{1:RESIDUES,2:ANCHOR,3:P,4:DISTRIBUTED,9:n})
 return c.get(DISTRIBUTED,86)
import itertools
BASE_C=0x3d0000;IMP_C=0x3e0000;cases=steps=0
for rate,span in [(3,1),(50,17),(60,20)]:
 for config,ri,pi,hi in itertools.product([0,2],[-4,0,4],[-1,0,1],[-2,-1,0,1,2]):
  b=bytearray(86);struct.pack_into('>HH',b,0,0x7000,0x8000);struct.pack_into('>H',b,28,1024);struct.pack_into('>h',b,42,32)
  b[16]=config;b[27]=128;b[54]=[-12,0,20][cases%3]&255;b[55]=[-20,-16,16,20][cases%4]&255;b[57]=30;b[66]=28
  x=[-1,0,1][cases%3];y=[1,0,-1][cases%3]
  for dest,impulses in [(BASE_C,(0,0,0)),(IMP_C,(ri,pi,hi))]:
   c.put(P,b);c.put(PACKET,struct.pack('>hhhhh',x,y,*impulses));call('player_step_init',{1:SH,9:3,10:0})
   call('player_step_interval',{1:SH,2:P,3:STAGES,4:h[0]+0x7a44,5:PACKET,9:1});c.put(dest,c.get(P,86))
  c.put(LIVE,b);call('endpoint_player_init',{1:OWNER,9:rate,10:0});call('endpoint_player_begin',{1:OWNER,2:LIVE,9:span,10:1});c.put(PACKET,struct.pack('>hhhhh',x,y,0,0,0))
  for f in range(1,span+1):call('endpoint_player_step',{1:OWNER,2:LIVE,3:STAGES,4:h[0]+0x7a44,5:PACKET,9:f});steps+=1
  assert c.get(LIVE,86)==c.get(BASE_C,86)
  call('endpoint_impulse_apply',{1:OWNER,2:LIVE,3:BASE_C,4:IMP_C})
  assert c.get(LIVE,86)==c.get(IMP_C,86),(rate,config,ri,pi,hi)
  assert c.get(OWNER,40)==bytes(40);cases+=1
# Changed input: actual roll is nearer a limit than the last native preview.
for actual,rem,base_roll,target_roll,expected in [(19,816,12,16,20),(-20,544,-12,-16,-20)]:
 b=bytearray(c.get(BASE_C,86));b[55]=base_roll&255;c.put(BASE_C,b);b[55]=target_roll&255;c.put(IMP_C,b);b[55]=actual&255;c.put(LIVE,b);c.put(OWNER+32,struct.pack('>I',rem))
 call('endpoint_impulse_apply',{1:OWNER,2:LIVE,3:BASE_C,4:IMP_C})
 assert c.get(LIVE+55,1)==bytes([expected&255]) and c.get(OWNER+32,4)==bytes(4)
# Invalid interval or residue never changes authoritative candidates.
for kind in ['phase','span','residue']:
 c.put(OWNER+158,struct.pack('>HH',20,20));c.put(OWNER+36,bytes(4))
 if kind=='phase':c.put(OWNER+160,struct.pack('>H',19))
 if kind=='span':c.put(OWNER+158,struct.pack('>HH',18,18))
 if kind=='residue':c.put(OWNER+36,struct.pack('>I',1360))
 before=c.get(OWNER,164),c.get(LIVE,86)
 for r,v in {1:OWNER,2:LIVE,3:BASE_C,4:IMP_C}.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(sym('endpoint_impulse_apply'))
 assert c.rr(9)==0xffffffff and before==(c.get(OWNER,164),c.get(LIVE,86))
print(dict(native_endpoint_cases=cases,fields=steps,changed_input_roll_limits=2,atomic_rejections=3));c.close()
