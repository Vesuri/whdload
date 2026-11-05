"""Read-only observations of the installed enhanced flight loop."""
import os,sys,re,json,struct
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
 run(s,ROUTE)
 mem=s.read(0x200000,0x800000);hits=[];i=0
 while True:
  i=mem.find(marker,i)
  if i<0:break
  candidate=0x200000+i-off
  ptr=int.from_bytes(s.read(candidate+sym('timing_runtime_arena'),4),'big')
  if 0x200000<=ptr<0xa00000:hits.append((candidate,ptr))
  i+=len(marker)
 assert len(hits)==1,hits
 base,arena=hits[0]
 (s.out/'fast.bin').write_bytes(mem)
 (s.out/'arena.bin').write_bytes(s.read(arena,sym('RT_ARENA_SIZE')))
 (s.out/'addresses.json').write_text(json.dumps(dict(base=base,arena=arena)))
 h2=int.from_bytes(s.read(arena+sym('RT_HUNKS')+8,4),'big')
 def field():return int.from_bytes(s.read(h2+0x1c,4),'big')
 def capture(tag):
  (s.out/(tag+'-frames.bin')).write_bytes(s.read(base+sym('frame_probe_data'),16+512*48))
  (s.out/(tag+'-arena.bin')).write_bytes(s.read(arena,sym('RT_ARENA_SIZE')))
 for i in range(10):s.tap('f1',hold=4,after=6)
 s.fields(250);capture('before')
 events=[]
 for i,event in enumerate(['JOY2_LEFT','JOY2_RIGHT']*4):
  before=field();s.cmd(f'monitor input {event} {0 if os.environ.get("NO_PULSE")=="1" else 1}');s.fields(6)
  release=field();s.cmd(f'monitor input {event} 0');s.fields(40)
  events.append(dict(event=event,before=before,release=release,after=field()))
  capture(f'pulse-{i}')
  print(events[-1],flush=True)
 capture('after');s.shot('end.png')
 (s.out/'events.json').write_text(json.dumps(events,indent=2)+'\n')
 print('frame probe captured',flush=True)
finally:s.quit()
