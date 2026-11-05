"""Read-only observations of the installed enhanced flight loop."""
import os,sys,re,json,struct,hashlib
from pathlib import Path
from gunship import Session,machine
from route import run
from flight_profile import ROUTE
from amitools.binfmt.BinFmt import BinFmt
root=Path(__file__).resolve().parents[1]
slave=Path(os.environ['SLAVE']);blob=bytes(BinFmt().load_image(str(slave)).get_segments()[0].get_data())
listing=slave.with_suffix(slave.suffix+'.lst').read_text(encoding='latin1')
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
marker=b'Enhanced framerate: flight timing failed';off=blob.index(marker)
s=Session(sys.argv[1],dict(NTSC=os.environ.get('NTSC','0'),EXTRA_ARGS=machine().get('EXTRA_ARGS','')+' --video_driver=null',WHD_ARGS='CUSTOM1=1 CUSTOM2=12345'))
try:
 expected=hashlib.sha256(slave.read_bytes()).hexdigest()
 assert hashlib.sha256((s.run/'dh1/Gunship.slave').read_bytes()).hexdigest()==expected
 (s.out/'provenance.json').write_text(json.dumps(dict(slave_sha256=expected,listing_sha256=hashlib.sha256(listing.encode('latin1')).hexdigest(),machine=os.environ.get('MACHINE')),indent=2))
 run(s,ROUTE)
 mem=s.read(0x200000,0x800000);hits=[];i=0
 while True:
  i=mem.find(marker,i)
  if i<0:break
  candidate=0x200000+i-off
  ptr=int.from_bytes(s.read(candidate+sym('timing_runtime_arena'),4),'big')
  if 0x200000<=ptr<0xa00000 and ptr%2==0 and s.read(ptr+sym('RT_READY'),4)==bytes.fromhex('00000001'):hits.append((candidate,ptr))
  i+=len(marker)
 assert len(hits)==1,hits
 base,arena=hits[0]
 (s.out/'fast.bin').write_bytes(mem)
 (s.out/'arena.bin').write_bytes(s.read(arena,sym('RT_ARENA_SIZE')))
 (s.out/'addresses.json').write_text(json.dumps(dict(base=base,arena=arena)))
 def snapshot():
  data=s.read(arena,sym('RT_ARENA_SIZE'))
  def w(name,offset=0):return int.from_bytes(data[sym('RT_'+name)+offset:sym('RT_'+name)+offset+2],'big')
  def l(name,offset=0):return int.from_bytes(data[sym('RT_'+name)+offset:sym('RT_'+name)+offset+4],'big')
  status=int.from_bytes(s.read(base+sym('timing_flight_status'),4),'big',signed=True)
  setup=int.from_bytes(s.read(base+sym('timing_runtime_status'),4),'big',signed=True)
  s.cmd('maintenance flush register-cache')
  h6=int.from_bytes(data[sym('RT_HUNKS')+24:sym('RT_HUNKS')+28],'big')
  player=s.read(h6+0x3b88,0x56)
  return dict(player=player.hex(),phase=w('CLOCK',20),rate=w('CLOCK',22),last_field=l('CLOCK'),published_field=l('HISTORY',16),flight=status,setup=setup,ready=l('READY'),owner=w('CAPTURE_OWNER'),batch=w('BATCH'),steps=l('SCHEDULER',32),worlds=l('SCHEDULER',36),clock_fields=l('CLOCK',4),clock_ticks=l('CLOCK',8),history_lost=l('HISTORY',8),history_discarded=l('HISTORY',12),scheduler_fault=w('SCHEDULER',22),consumer=w('CONSUMER',60),pc=s.regs())
 rows=[snapshot()];print(rows[-1],flush=True)
 if rows[-1]['flight']!=0:raise AssertionError(rows[-1])
 if os.environ.get('TAKEOFF')=='1':
  for i in range(10):s.tap('f1',hold=4,after=6)
  s.fields(100)
 if os.environ.get('PROFILE')=='1':
  from amigaxdev.callprofile import Reduction
  from layout import locate
  (s.out/'layout.json').write_text(json.dumps(locate(mem)))
  red=Reduction()
  for j in range(4):
   trace=s.out/f'trace-{j}.bin';s.profile(25,trace);red.feed(trace);trace.unlink()
  red.save(s.out/'profile.pkl.gz')
 if os.environ.get('STEER')=='1':
  for event in ('JOY2_LEFT','JOY2_RIGHT','JOY2_UP','JOY2_DOWN'):
   s.cmd(f'monitor input {event} 1');s.fields(80);s.cmd(f'monitor input {event} 0');s.fields(20)
 for i in range(int(os.environ.get('RUN_SAMPLES','5'))):
  s.fields(100);rows.append(snapshot());print(rows[-1],flush=True)
  assert rows[-1]['flight']>=0 and rows[-1]['setup']==0,rows[-1]
 (s.out/'registers.txt').write_text(s.regs('d0 d1 d2 d3 d4 d5 d6 d7 a0 a1 a2 a3 a4 a5 a6 a7 pc sr'))
 (s.out/'low.bin').write_bytes(s.read(0,0x200000))
 (s.out/'final-fast.bin').write_bytes(s.read(0x200000,0x800000))
 s.shot('end.png')
 (s.out/'result.json').write_text(json.dumps(dict(base=base,arena=arena,rows=rows),indent=2)+'\n')
 assert rows[-1]['steps']>rows[0]['steps'] and rows[-1]['worlds']>rows[0]['worlds'],rows
 s.shot('end.png')
 print('PASS installed loop advances',flush=True)
finally:s.quit()
