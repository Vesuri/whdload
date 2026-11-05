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
c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/endpoint-player.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/endpoint-player.lst').read_text()
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
ANCHOR=0x380000;RESIDUES=0x390000;DISTRIBUTED=0x3a0000
def distribute(anchor,target,previous,n):
 current=bytearray(target)
 for off,width,_,_ in fields:current[off:off+width]=previous[off:off+width]
 c.put(ANCHOR,anchor);c.put(P,target);c.put(DISTRIBUTED,current)
 call('endpoint_motion_step',{1:RESIDUES,2:ANCHOR,3:P,4:DISTRIBUTED,9:n})
 return c.get(DISTRIBUTED,86)
report=json.loads((root/'tmp/c/moving-scene-comparison.json').read_text());results=[]
for ref in report['results']:
 rate=ref['rate'];config=ref['config'];name=ref['scenario']
 if name=='reversal':tape=[(1,1)]*3+[(-1,-1)]*3+[(0,0)]*4
 elif name=='pulse':tape=[(1,-1),(0,0),(-1,1),(0,0)]*2+[(0,0)]*2
 else:tape=[ast.literal_eval(name)]*10
 b=bytearray(86);struct.pack_into('>HH',b,0,0x7000,0x8000);struct.pack_into('>H',b,28,1024);b[16]=config;b[27]=128;b[57]=30;b[66]=28
 c.put(RESIDUES,bytes(40))
 values=[F(read(b,s)) for s in fields];lastinterval=0;history=[];matches=0;poses=[]
 for field in range(1,rate*10+1):
  interval=(field-1)*3//rate+1
  if interval!=lastinterval:
   anchor=bytes(b);start=[read(anchor,s) for s in fields];n=(interval*rate+2)//3-((interval-1)*rate+2)//3;lastinterval=interval
  x,y=tape[(field-1)//rate];delay=(rate+2)//3;previous=history[-delay] if len(history)>=delay else 0
  c.put(P,anchor);c.put(PACKET,struct.pack('>hhhhh',x,y,0,0,0))
  call('player_step_init',{1:SH,9:3,10:previous&0xffffffff})
  call('player_step_interval',{1:SH,2:P,3:STAGES,4:h[0]+0x7a44,5:PACKET,9:interval})
  target=c.get(P,86);assembled=distribute(anchor,target,b,n);b=bytearray(target)
  for i,spec in enumerate(fields):
   off,width,sgn,circ=spec;delta=read(target,spec)-start[i]
   if circ:delta=(delta+128)%256-128
   values[i]+=F(delta,n);value=math.floor(values[i]);b[off:off+width]=(value%(1<<(8*width))).to_bytes(width,'big')
  assert assembled==b,(name,config,rate,field)
  history.append(y)
  if field*3//rate>(field-1)*3//rate:
   expected=bytes.fromhex(ref['boundaries'][interval-1]['native'])
   assert b==expected,(name,config,rate,interval,b.hex(),expected.hex())
   matches+=1;poses.append(bytes(b))
 for off,v in zip([0x3be3,0x3c5d,0x3c63,0x3cdd,0x3ddd,0x3d5d],struct.pack('>HHH',*ref['object_xyz'])):c.put(h[6]+off,bytes([v]))
 c.put(h[6]+0x3ce3,b'\0');collisions=[]
 for pose,expected in zip(poses,ref['collisions']):
  c.put(WP,pose)
  for r,v in {1:WP,2:GEOM,3:h[0]+0xc6a0}.items():c.rw(r,v)
  c.rw(8,0x8f000);c.call(sym('world_scene_check'));hit=c.rr(9)
  assert hit==expected['native'],(name,config,rate,expected,hit)
  collisions.append(hit)
 results.append(dict(scenario=name,config=config,rate=rate,native_boundary_matches=matches,collision_matches=len(collisions)))
# Fresh mid-interval input must affect committed motion before the next tick.
rate=60;n=20;b=bytearray(86);struct.pack_into('>HH',b,0,0x7000,0x8000);struct.pack_into('>H',b,28,1024);b[27]=128;b[57]=30;b[66]=28
c.put(RESIDUES,bytes(40));anchor=bytes(b);start=[read(anchor,s) for s in fields];values=[F(x) for x in start];pulse=[]
for field in range(1,21):
 x=1 if 5<=field<=9 else 0;c.put(P,anchor);c.put(PACKET,struct.pack('>hhhhh',x,0,0,0,0));call('player_step_init',{1:SH,9:3,10:0});call('player_step_interval',{1:SH,2:P,3:STAGES,4:h[0]+0x7a44,5:PACKET,9:1});target=c.get(P,86);assembled=distribute(anchor,target,b,n);b=bytearray(assembled)
 for i,spec in enumerate(fields):
  delta=read(target,spec)-start[i]
  if spec[3]:delta=(delta+128)%256-128
  values[i]+=F(delta,n)
 assert F(read(assembled,fields[8]))+F(int.from_bytes(c.get(RESIDUES+32,4),'big'),1360)==values[8]
 pulse.append(float(values[8]))
assert pulse[4]!=pulse[3] and pulse[-1]!=0
print(dict(cases=len(results),native_boundary_matches=sum(x['native_boundary_matches'] for x in results),pulse_roll_by_field=pulse))
(root/'tmp/c/endpoint-motion-assembled.json').write_text(json.dumps(dict(results=results,pulse_roll_by_field=pulse),indent=2)+'\n')
c.close()
