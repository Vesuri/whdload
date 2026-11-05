"""Rejected debugger-write prototype; retained only as fixture design notes.

The shared Barto stub exposes reads, breakpoints and harness input, but does
not implement guest memory/register writes. Never use this as validation.
Replace its guest setup with compiled diagnostic hooks before running.
"""
raise RuntimeError("Unsupported debugger-write fixture: use a compiled guest probe")
import os,sys,re,json,struct,tempfile,time
from pathlib import Path
from gunship import Session
from route import run
from flight_profile import ROUTE
from layout import locate
root=Path(__file__).resolve().parents[1]
listing=(root/'tmp/c/visibility-live.lst').read_text(encoding='latin1')
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
s=Session(sys.argv[1],dict(AMIGA_SETUP='a1200-fast',EXTRA_ARGS='--video_driver=null',WHD_ARGS='CUSTOM1=1 CUSTOM2=12345'))
def write(a,b):
 fd,p=tempfile.mkstemp(prefix='gunship-vr-');os.close(fd)
 try:Path(p).write_bytes(b);s.cmd(f'restore {p} binary {a:#x}')
 finally:os.unlink(p)
def numreg(n):
 out=s.cmd(f'p/x ${n}');return int(re.search(r'= (0x[0-9a-f]+)',out)[1],16)
def call(a,regs={},end=None):
 stop=space+3072 if end is None else end
 s.cmd(f'set $sr = 0x2700')
 s.cmd(f'set $sp = {space+2048:#x}');write(space+2048,struct.pack('>I',stop))
 for r,v in regs.items():s.cmd(f'set ${r} = {v:#x}')
 s.cmd(f'set $pc = {a:#x}');s.cmd(f'tbreak *{stop:#x}')
 s.cmd('continue',timeout=600)
 assert numreg('pc')==stop, s.regs()
 return numreg('d0')
def wait():call(space+3080)
def bitmap():
 desc=int.from_bytes(s.read(h[6]+0x47c4,4),'big');b=s.read(desc,40)
 stride,rows=struct.unpack_from('>HH',b);depth=b[5]
 assert 1<=depth<=6 and 0<stride<=80 and 0<rows<=512,(hex(desc),b.hex())
 planes=[int.from_bytes(b[8+4*i:12+4*i],'big') for i in range(depth)]
 return dict(desc=desc,stride=stride,rows=rows,planes=planes),[s.read(p,stride*rows) for p in planes]
try:
 run(s,ROUTE);mem=s.read(0x200000,0x800000);h=locate(mem)['hunks']
 hits=[];pos=0
 while True:
  pos=mem.find(b'GSVR0001',pos)
  if pos<0:break
  base=0x200000+pos-sym('visibility_test_space')
  if base>=0x200008:
   sz=int.from_bytes(mem[base-0x200000-8:base-0x200000-4],'big')
   print('marker',hex(base),hex(0x200000+pos),hex(sz),flush=True)
   hits.append((base,0x200000+pos))
  pos+=8
 assert len(hits)==1,hits
 base,space=hits[0];vr=space+16;wt=space+320;camera=space+880;state=wt+sym('WT_STATE');target=h[0]+0xa99e
 print('loaded',dict(base=hex(base),space=hex(space),hunks=[hex(a) for a in h]),flush=True)
 # Stop at the original render entry before taking exclusive foreground ownership.
 s.cmd(f'tbreak *{h[0]+0x5c04:#x}');s.cmd('continue',timeout=600)
 assert numreg('pc')==h[0]+0x5c04
 s.cmd('set $sr = 0x2700')
 # Return sentinel and a blitter wait; branch targets encoded independently.
 write(space+3072,bytes.fromhex('4e7160fc4e714e71'))
 write(space+3080,bytes.fromhex('4a7900dff0020839000600dff00266f64e75'))
 wait()
 assert call(base+sym('visibility_raster_prepare'),{'a0':h[0],'a1':h[6],'a2':vr})==0
 assert call(base+sym('target_select_prepare'),{'a0':h[0],'a1':h[6],'a2':wt})==0
 lo=min(h);hi=max(h)+0x5000;assert not(lo<=space<hi)
 original=s.read(lo,hi-lo)
 results=[];nonempty=0
 for heading in range(0,256,32):
  write(lo,original)
  initial=bytearray(s.read(target,168));initial[2:4]=bytes(2)
  for i,o in enumerate((0,18,36,54,72)):struct.pack_into('>H',initial,8+i*2,o)
  write(target,initial);write(state,initial)
  xy=(0x7fff,0x7fff);height=512
  write(camera,struct.pack('>6H',*xy,height+24,(-heading*256)&65535,0,0))
  special=struct.pack('>3H',xy[0]+128,xy[1]+128,height+24)
  for off,v in zip([0x3be3,0x3c5d,0x3c63,0x3cdd,0x3ddd,0x3d5d],special):write(h[6]+off,bytes([v]))
  coords=struct.pack('>18H',*[xy[0]+(i-2)*128 for i in range(6)],*[xy[1]+(i-2)*128 for i in range(6)],*[height+32]*6)
  write(h[0]+0xc6a0,coords);write(h[0]+0xba08,b'\0\x3f')
  call(h[0]+0x84e2)
  before=s.read(lo,hi-lo);bm0,planes0=bitmap()
  call(base+sym('scene_state_build'),{'a0':camera,'a1':h[0]+0xc6a0,'a2':h[6],'a3':h[6]+0x3904})
  call(h[0]+0x5c04,end=h[0]+0x5c78);wait()
  candidates=s.read(target,168);count=int.from_bytes(candidates[2:4],'big');assert count<=5
  bm,planes=bitmap();pixels=[]
  for i in range(count):
   x=int.from_bytes(candidates[0x80+2*i:0x82+2*i],'big');y=int.from_bytes(candidates[0x8a+2*i:0x8c+2*i],'big')
   assert 0<=x<bm['stride']*8 and 0<=y<bm['rows'],(x,y,bm)
   px=sum(((p[y*bm['stride']+x//8]>>(7-x%8))&1)<<j for j,p in enumerate(planes))
   assert call(h[0]+0x825e,{'d0':x,'d1':y})==px
   pixels.append(px)
  write(lo,before)
  for p,b in zip(bm0['planes'],planes0):write(p,b)
  assert call(base+sym('visibility_raster_step'),{'a0':vr,'a1':wt,'a2':camera,'a3':h[0]+0xc6a0})==0
  got=s.read(state,168);assert got==candidates,('candidates',heading,got.hex(),candidates.hex())
  assert s.read(target,168)==initial
  assert s.read(wt+sym('WT_PIXELS'),6)==bytes(pixels)+bytes(6-count)
  bm2,planes2=bitmap();assert bm2==bm and planes2==planes,('bitmap',heading)
  row=dict(heading=heading,candidates=count,pixels=pixels,bitmap=bm)
  results.append(row);nonempty+=count>0;print('view',row,flush=True)
 assert nonempty,results
 (s.out/'result.json').write_text(json.dumps(dict(status='passed',views=results,nonempty=nonempty,scope='020 PAL real DMA native-prefix/extracted-prefix bitmap and sampled pixels'),indent=2)+'\n')
 print('PASS',len(results),nonempty,flush=True)
finally:s.quit()
