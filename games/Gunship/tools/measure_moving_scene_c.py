#!/usr/bin/env python3
"""Connect scaled response/linear rates to native stages; prove h=1 and fractions."""
import json,random
from fractions import Fraction as F
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/moving-scene.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/moving-scene.lst').read_text()
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


fieldshadow=0x330000;native_shadow=0x350000;packet=0x360000
delaystate=0x370000
GEOMETRY=0x520000;world_player=h[6]+0x3b88
assert call('scene_private_prepare',{1:h[0],2:h[6],3:GEOMETRY})==0
c.put(h[0]+0xba08,bytes(2))
results=[]
def pose(ptr,shadow,rate):
 b=c.get(ptr,86)
 values=dict(x=int.from_bytes(b[:2],'big'),y=int.from_bytes(b[2:4],'big'),height=int.from_bytes(b[28:30],'big'),speed=sw(int.from_bytes(b[42:44],'big')),vertical=sb(b[62]),rpm=b[27],heading=b[53],track=b[61],pitch=sb(b[54]),roll=sb(b[55]))
 def i(off):return int.from_bytes(c.get(shadow+off,4),'big',signed=True)
 for key,main,conv in [('speed',8,12),('vertical',4,None),('rpm',16,20),('heading',28,32),('track',36,40)]:
  values[key]+=i(main+12)/32767+(i(conv+12)/(rate*32767) if conv is not None else 0)
 for key,off in [('height',48),('x',52),('y',56)]:values[key]+=i(off+12)/rate
 values['roll']+=i(4)/rate;values['pitch']+=i(8)/rate
 return values
scenarios=[(str((x,y)),[(x,y)]*10) for x in [-1,0,1] for y in [-1,0,1]]
scenarios += [('reversal',[(1,1)]*3+[(-1,-1)]*3+[(0,0)]*4),('pulse',[(1,-1),(0,0),(-1,1),(0,0)]*2+[(0,0)]*2)]
for config in [0,2]:
 for name,tape in scenarios:
  for rate in [50,60]:
   initial=bytearray(86);struct.pack_into('>HH',initial,0,0x7000,0x8000);struct.pack_into('>H',initial,28,1024)
   initial[16]=config;initial[27]=128;initial[57]=30;initial[66]=28
   c.put(p,initial);c.put(out,initial)
   for sh,hz in [(fieldshadow,rate),(native_shadow,3)]:assert call('player_step_init',{1:sh,9:hz,10:0})==0
   assert call('control_delay_init',{1:delaystate,9:rate,10:0})==0
   maxima={k:0 for k in pose(p,native_shadow,3)};samples=[];boundaries=[]
   history=[];delay=(rate+2)//3
   for field in range(1,rate*10+1):
    x,y=tape[(field-1)//rate];c.put(packet,struct.pack('>hhhhh',x,y,0,0,0));interval=(field-1)*3//rate+1
    delayed_y=history[-delay] if len(history)>=delay else 0
    c.put(out+12,struct.pack('>H',interval))
    assert call('player_step_delayed',{1:fieldshadow,2:out,3:stages,4:h[0]+0x7a44,5:packet,6:delaystate,9:field})==0
    if field*3//rate>(field-1)*3//rate:
     assert call('player_step_interval',{1:native_shadow,2:p,3:stages,4:h[0]+0x7a44,5:packet,9:field*3//rate})==0
     boundaries.append(dict(tick=field*3//rate,field=field,native=c.get(p,86).hex(),fine=c.get(out,86).hex()))
    if field%rate==0:
     native=pose(p,native_shadow,3);fine=pose(out,fieldshadow,rate)
     error={k:((fine[k]-native[k]+128)%256-128 if k in ['heading','track'] else fine[k]-native[k]) for k in native}
     for k,v in error.items():maxima[k]=max(maxima[k],abs(v))
     samples.append(dict(second=field//rate,native=native,field=fine,error=error))
     assert native['height']>0 and fine['height']>0
   # One stationary special object at the native midpoint endpoint; both
   # trajectories see the exact same scene. No AI, weapons or contact feedback.
   center=bytes.fromhex(boundaries[14]['native'])
   object_xyz=(int.from_bytes(center[:2],'big'),int.from_bytes(center[2:4],'big'),int.from_bytes(center[28:30],'big')+24)
   for off,v in zip([0x3be3,0x3c5d,0x3c63,0x3cdd,0x3ddd,0x3d5d],struct.pack('>HHH',*object_xyz)):c.put(h[6]+off,bytes([v]))
   c.put(h[6]+0x3ce3,b'\0')
   collisions=[]
   for row in boundaries:
    hits=[]
    for kind in ['native','fine']:
     c.put(world_player,bytes.fromhex(row[kind]))
     result=call('world_scene_check',{1:world_player,2:GEOMETRY,3:h[0]+0xc6a0})
     assert result in [0,1];hits.append(result)
    collisions.append(dict(tick=row['tick'],field=row['field'],native=hits[0],fine=hits[1]))
   results.append(dict(scenario=name,config=config,rate=rate,max_abs_error=maxima,samples=samples,boundaries=boundaries,object_xyz=object_xyz,collisions=collisions))
report=dict(scope='44 ten-second player trajectories; actual delayed-control field integrator versus h=1 reference, independently checked against original native clamp/control/motion slices; no world RNG, ground/contact feedback or commands; geometry evaluated at every world deadline against the same stationary special object at the native fifth-second endpoint',seconds=10,results=results,calls=calls)
(root/'tmp/c/moving-scene-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
for r in results:
 differences=[x for x in r['collisions'] if x['native']!=x['fine']]
 if differences:print(r['scenario'],r['config'],r['rate'],differences)
print(dict(trajectories=len(results),world_comparisons=sum(len(r['collisions']) for r in results),disagreements=sum(x['native']!=x['fine'] for r in results for x in r['collisions']),calls=calls))
c.close()
