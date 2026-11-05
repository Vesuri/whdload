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
 def sample():
  p=s.read(h[6]+0x3b88,0x56)
  return dict(field=lng(h[2]+0x1c),tick=int.from_bytes(p[12:14],'big'),buffer=int.from_bytes(s.read(h[6]+0x4bb0,2),'big'),player=p.hex())
 initial=sample();rows=[]
 def chunk(n):
  for _ in range(n//2):s.fields(1);rows.append(sample())
 window(s,chunk);s.shot('end.png')
 (s.out/'fast.bin').write_bytes(s.read(0x200000,0x800000))
 (s.out/'samples.json').write_text(json.dumps(dict(hunks=h,slave_base=sb,arena=arena,initial=initial,rows=rows)))
 span=rows[-1]['field']-initial['field'];ticks=(rows[-1]['tick']-initial['tick'])&65535;flips=sum(a['buffer']!=b['buffer'] for a,b in zip([initial]+rows,rows))
 result=dict(machine=os.environ.get('MACHINE'),custom1=custom,renderer=os.environ.get('CUSTOM4','0'),video='NTSC' if ntsc else 'PAL',fields=span,world_ticks=ticks,world_hz=ticks*rate/span,fps=flips*rate/span,slave=str(slave.name))
 (s.out/'result.json').write_text(json.dumps(result,indent=2));print(result,flush=True)
 print('ticks', (rows[-1]['tick']-initial['tick'])&65535,'fields',rows[-1]['field']-initial['field'],'flips',sum(a['buffer']!=b['buffer'] for a,b in zip([initial]+rows,rows)),flush=True)
finally:s.quit()
