from session_b import Session,machine
from route import run
from flight_profile import ROUTE,window
from pathlib import Path
from amitools.binfmt.BinFmt import BinFmt
import os,sys,json,struct,re
custom=int(os.environ.get('CUSTOM1','1'));ntsc=os.environ.get('EDITION','NTSC')=='NTSC';rate=60 if ntsc else 50
env=dict(NTSC=str(int(ntsc)),EXTRA_ARGS=machine().get('EXTRA_ARGS','')+' --video_driver=null',WHD_ARGS=f'CUSTOM1={custom} CUSTOM4='+os.environ.get('CUSTOM4','0'))
if os.environ.get('MACHINE')=='a1200-040':env.update(DETERMINISTIC='0',AMIGA_SETUP='a1200-040',EXTRA_ARGS='--video_driver=null',WHD_ARGS=env['WHD_ARGS']+' CACHE')
s=Session(sys.argv[1],env)
try:
 root=Path(__file__).resolve().parents[1]
 (s.run/'dh1/data/Roster/Gunship_roster').write_bytes((root/'tmp/game/Gunship/data/Roster/Gunship_roster').read_bytes())
 run(s,ROUTE);s.shot('start.png')
 mem=s.read(0x200000,0x800000);(s.out/'start-fast.bin').write_bytes(mem)
 sig=bytes.fromhex('4cdf4cfc' if ntsc else '51cfffce');hits=[];pos=0
 while True:
  pos=mem.find(sig,pos)
  if pos<0:break
  off=pos-0x2f2a
  if off>=8 and int.from_bytes(mem[off-8:off-4],'big')==(61748 if ntsc else 61640)+8:hits.append(off+0x200000)
  pos+=1
 assert len(hits)==1,hits
 h=[];ptr=hits[0]
 for _ in range(9):h.append(ptr);ptr=int.from_bytes(s.read(ptr-4,4),'big')*4+4
 slave=Path(os.environ['SLAVE']);listing=slave.with_suffix(slave.suffix+'.lst').read_text(encoding='latin1');syms={n:int(v,16) for v,n in re.findall(r'^([0-9A-F]{8}) (\w+)$',listing,re.M)}
 blob=bytes(BinFmt().load_image(str(slave)).get_segments()[0].get_data());off=syms['timing_runtime_prepare'];pattern=blob[off:off+24];pos=mem.find(pattern);assert pos>=0
 sb=pos+0x200000-off
 def lng(a):return int.from_bytes(s.read(a,4),'big')
 print('status',lng(sb+syms['timing_runtime_status']), 'flight',lng(sb+syms['timing_flight_status']),flush=True)
 arena=lng(sb+syms['timing_runtime_arena']);print('arena',hex(arena),flush=True)
 def get(a,n):return int.from_bytes(s.read(a,n),'big')
 def sample():
  ptr=get(h[6]+0x40,4)+get(h[6]+0x44,4)*4
  idx=get(h[6]+0x49ac,4)
  return dict(timer=get(h[6]+0x4296,1),colour=get(ptr,2),normal=get(h[6]+0x484c+idx*64,2),active=get(sb+syms['timing_display_async'],2))
 before=sample();assert before['active']==1,before
 # Execute the game's own OR.B hit-timer store: debugger RAM writes do
 # not reach a dirty 040 cache line. Restore registers after this one store.
 insn=bytes.fromhex('8139')+struct.pack('>I',h[6]+0x4296)
 target=h[0]+s.read(h[0],0x10000).index(insn)
 s.cmd('maintenance flush register-cache')
 for reg in ('pc','d0','sr'):s.cmd(f'set $saved_{reg} = ${reg}')
 s.cmd('set $sr = 0x2700');s.cmd('set $d0 = 30');s.cmd(f'set $pc = {target:#x}');s.cmd('stepi')
 for reg in ('pc','d0','sr'):s.cmd(f'set ${reg} = $saved_{reg}')
 rows=[]
 for n in range(55):
  s.fields(1);rows.append(sample())
  if n==3:s.shot('flash.png')
 s.shot('restored.png')
 assert any(r['colour']!=r['normal'] for r in rows),rows
 assert rows[-1]['timer']==0 and rows[-1]['colour']==rows[-1]['normal'],rows[-1]
 (s.out/'damage-colour.json').write_text(json.dumps(dict(before=before,rows=rows),indent=2))
 print(dict(before=before,after=rows[-1],flash_seen=True),flush=True)
finally:s.quit()
