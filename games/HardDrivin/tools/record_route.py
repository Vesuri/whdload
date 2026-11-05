"""Explore using ONLY native input variables; save field-indexed inputs for freezing."""
import sys,json,math,struct,time,os
from pathlib import Path
from capture_demo import ROOT,command
out=ROOT/'tmp/prof'/sys.argv[2];sig=(out/'code.bin').read_bytes().hex();rel=out.relative_to(ROOT)
base=0xd0ee16;a4=0xd15f16;state=json.loads((out/'layout.json').read_text())['state']
chip=(ROOT/'tmp/prof/drive-calibration-2/current-chip.bin').read_bytes()
def node(p):
 v=struct.unpack_from('>6H3hH',chip,p)
 return [(v[j]+v[j+3])/2 for j in range(3)]
route=[node(0x1dc94+i*20) for i in range(3,22)]
# Keep the right-hand lane clear of the oncoming car on the initial straight.
for r in route:r[2]=24940
mode=sys.argv[1] if len(sys.argv)>1 else 'straight'
if mode=='stunt':
 route=[node(0x1dc94+i*20) for i in range(3,12)]+[node(0x1e860+i*20) for i in range(27)]
 for r in route[:9]:r[2]=24940
 for i,r in enumerate(route[9:]):
  angle=struct.unpack_from('>h',chip,0x1e860+i*20+12)[0]*2*math.pi/1440
  r[0]+=50*math.cos(angle);r[2]-=50*math.sin(angle)
records=[];samples=[];idx=0;previous=None
command('gdb delete')
command('gdb break *0xcfb5a8')
for k in range(625):
 command('gdb set $hd_k=0\nwhile $hd_k < 16\ncontinue\nset $hd_k=$hd_k+1\nend')
 command(f'gdb dump binary memory {rel}/live.bin 0xd0ee16 0xd16016')
 command(f'gdb dump binary memory {rel}/tape-state.bin {state:#x} {state+20:#x}')
 b=(out/'live.bin').read_bytes();t=(out/'tape-state.bin').read_bytes();field=struct.unpack_from('>I',t,4)[0]
 def read(o,fmt):return struct.unpack_from('>'+fmt,b,0x7100+o)[0]
 x,y,z=[read(o,'H') for o in [-0x670a,-0x6708,-0x6706]];heading=read(-0x66b6,'h');speed=read(-0x66d4,'h');crash=read(-0x69fa,'B');replay=read(-0x5229,'B')
 nearest=min((range(len(route)) if k==0 else range(max(0,idx-1),min(len(route),idx+5))),key=lambda i:(route[i][0]-x)**2+(route[i][2]-z)**2)
 idx=max(idx,nearest)
 target=min(len(route)-1,idx+2)
 dx,dz=route[target][0]-x,route[target][2]-z
 desired=math.atan2(dx,dz)*1440/(2*math.pi)
 error=(desired-heading+720)%1440-720
 limit=min(12,max(1,int(1100/(abs(read(-0x66d8,'h'))+1))))
 steer=max(-limit,min(limit,round(error*.4)))
 mx=320+20*steer;buttons=4
 if mode=='stunt' and 6<=idx<=16: buttons=5 if speed>48 else (4 if speed<42 else 0)
 if idx==len(route)-1:buttons=0;mx=320
 payload=struct.pack('>HHH',mx,200,buttons).hex()
 if payload != previous:
  command(f'poke {state+12:#x} {payload} {sig} 0xcfb1d0')
  previous=payload
 records.append([field+1,mx,200,buttons,0]);samples.append(dict(field=field,pose=[x,y,z],heading=heading,speed=speed,crash=crash,replay=replay,route_index=idx,steer=mx))
 (out/f'{os.environ.get("RECORDER_LABEL",mode)}-recording.json').write_text(json.dumps(dict(records=records,samples=samples),indent=2))
 if k%25==0 or crash or replay:print(samples[-1],flush=True)
 if k%100==0:command(f'shot {out}/{mode}-{field:05d}.png')
 if idx==len(route)-1 or crash or replay:
  print('STOP condition',flush=True);break
command('gdb delete')
