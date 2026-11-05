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
 effective=s.run/'dh1/Gunship.slave'
 expected=hashlib.sha256(slave.read_bytes()).hexdigest()
 assert hashlib.sha256(effective.read_bytes()).hexdigest()==expected
 (s.out/'provenance.json').write_text(json.dumps(dict(slave_sha256=expected,listing_sha256=hashlib.sha256(listing.encode('latin1')).hexdigest(),machine=os.environ.get('MACHINE'),ntsc=os.environ.get('NTSC','0')),indent=2))
 route=ROUTE[:ROUTE.index('t:n1')];assert route[-1]=='f:800';run(s,route[:-1]+['f:600'])
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

 h6=int.from_bytes(s.read(arena+sym('RT_HUNKS')+24,4),'big')
 h2=int.from_bytes(s.read(arena+sym('RT_HUNKS')+8,4),'big')

 # Synchronize host-injected controls to the native producer's field epoch.
 initial=s.read(arena,sym('RT_ARENA_SIZE'))
 last,total=struct.unpack_from('>II',initial,sym('RT_CLOCK'));epoch=last-total
 events=[(240,'key 5 1'),(244,'key 5 0'),(260,'key 41 1'),(264,'key 41 0'),(300,'input JOY2_FIRE_BUTTON 1'),(304,'input JOY2_FIRE_BUTTON 0'),(320,'input JOY2_FIRE_BUTTON 1'),(324,'input JOY2_FIRE_BUTTON 0')]
 observations=[]
 for field,command in events:
  s.cmd(f'break *{base+sym("timing_live_field"):#x}')
  s.cmd(f'condition $bpnum *(unsigned int*){h2+0x1c:#x} >= {epoch+field}')
  s.cmd('continue',timeout=600);s.cmd('delete')
  actual=int.from_bytes(s.read(h2+0x1c,4),'big')-epoch
  assert actual==field,(actual,field)
  (s.out/f'input-{field}-arena.bin').write_bytes(s.read(arena,sym('RT_ARENA_SIZE')))
  s.cmd('monitor '+command)
  observations.append(dict(field=field,command=command))
  print('input',field,command,flush=True)
 (s.out/'input-events.json').write_text(json.dumps(dict(epoch=epoch,events=observations),indent=2))

 s.cmd(f'break *{base+sym("world_weapons_step"):#x}')
 s.cmd('continue',timeout=600);s.cmd('delete')
 (s.out/'before-weapons-arena.bin').write_bytes(s.read(arena,sym('RT_ARENA_SIZE')))
 checkpoint=base+sym('scheduler_world_done')
 s.cmd(f'break *{checkpoint:#x}')
 s.cmd(f'condition $bpnum *(unsigned int*){arena+sym("RT_SCHEDULER")+36:#x} >= 19')
 for i in range(3):
  s.cmd('continue',timeout=600)
  d=s.out/f'world-{20+i}';d.mkdir(exist_ok=True)
  a=s.read(arena,sym('RT_ARENA_SIZE'));(d/'arena.bin').write_bytes(a)
  hunks=struct.unpack_from('>9I',a,sym('RT_HUNKS'))
  for n in (0,2,4,5,6):
   length=int.from_bytes(s.read(hunks[n]-8,4),'big')-8
   assert 0<length<1000000,(n,length)
   (d/f'h{n}.bin').write_bytes(s.read(hunks[n],length))
  data=(d/'h6.bin').read_bytes()
  for name,offset,length in [('mission',0x45c8,0xac),('alive',0x45e2,256)]:
   ptr=int.from_bytes(data[offset:offset+4],'big');(d/(name+'.bin')).write_bytes(s.read(ptr,length))
  (d/'fast.bin').write_bytes(s.read(0x200000,0x800000))
  worlds=struct.unpack_from('>I',a,sym('RT_SCHEDULER')+36)[0]
  assert worlds==19+i,worlds
  print('captured completed native world',worlds+1,flush=True)
 s.cmd('delete')
 s.shot('end.png')
finally:s.quit()
