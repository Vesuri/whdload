"""Paired production-frame observation; debugger reads only, real monitor input."""
from session_b import Session,machine
from route import run
from flight_profile import ROUTE
from amitools.binfmt.BinFmt import BinFmt
from pathlib import Path
import os,sys,re,json,hashlib,struct
slave=Path(os.environ['SLAVE']);blob=bytes(BinFmt().load_image(str(slave)).get_segments()[0].get_data())
syms={n:int(v,16) for v,n in re.findall(r'^([0-9A-F]{8}) (\w+)$',slave.with_suffix(slave.suffix+'.lst').read_text(encoding='latin1'),re.M)}
s=Session(sys.argv[1],dict(NTSC=os.environ.get('NTSC','0'),EXTRA_ARGS=machine().get('EXTRA_ARGS','')+' --video_driver=null',WHD_ARGS='CUSTOM1=1 CUSTOM4='+os.environ.get('CUSTOM4','0')))
try:
 run(s,ROUTE)
 for _ in range(10):s.tap('f1',hold=4,after=6)
 s.fields(250)
 mem=s.read(0x200000,0x800000);marker=b'Enhanced framerate: flight timing failed';off=blob.index(marker);hits=[];pos=0
 while True:
  pos=mem.find(marker,pos)
  if pos<0:break
  base=0x200000+pos-off;arena=int.from_bytes(s.read(base+syms['timing_runtime_arena'],4),'big')
  if 0x200000<=arena<0xa00000:hits.append((base,arena))
  pos+=len(marker)
 assert len(hits)==1,hits
 base,arena=hits[0];h=struct.unpack('>9I',s.read(arena+syms['RT_HUNKS'],36))
 def lng(a):return int.from_bytes(s.read(a,4),'big')
 def snap():
  return dict(field=lng(h[2]+0x1c),camera=s.read(arena+syms['RT_CAMERA'],12).hex(),player=s.read(h[6]+0x3b88,86).hex(),pending=int.from_bytes(s.read(base+syms['timing_display_pending'],2),'big'),history=s.read(arena+syms['RT_HISTORY'],20).hex())
 # Stop after presentation has selected this frame's camera, at native draw entry.
 draw=lng(arena+syms['RT_DRAW_ENTRY']);s.cmd(f'break *{draw:#x}');s.cmd('continue');s.cmd('delete')
 before=snap();s.cmd('monitor input JOY2_RIGHT '+os.environ.get('PULSE','1'))
 rows=[]
 for i in range(5):
  s.cmd(f'break *{base+syms["timing_runtime_draw"]:#x}');s.cmd('continue');s.cmd('delete')
  row=snap();planes=struct.unpack('>5I',s.read(base+syms['timing_display_planes'],20));pixels=b''.join(s.read(p,8000) for p in planes);(s.out/f'frame-{i}.bin').write_bytes(pixels);row['sha256']=hashlib.sha256(pixels).hexdigest();rows.append(row)
  # Advance through preparation to next actual native draw, keeping per-frame camera.
  s.cmd(f'break *{draw:#x}');s.cmd('continue');s.cmd('delete')
 s.cmd('monitor input JOY2_RIGHT 0');s.shot('end.png')
 result=dict(machine=os.environ.get('MACHINE'),ntsc=os.environ.get('NTSC','0'),pulse=os.environ.get('PULSE','1'),slave_sha256=hashlib.sha256(slave.read_bytes()).hexdigest(),before=before,rows=rows)
 (s.out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
finally:s.quit()
