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
 h0=int.from_bytes(s.read(arena+sym('RT_HUNKS'),4),'big')
 h4=int.from_bytes(s.read(arena+sym('RT_HUNKS')+16,4),'big')
 s.cmd(f'break *{h0+0x46de:#x}')
 s.cmd(f'break *{base+sym("timing_live_field"):#x}')
 s.cmd(f'condition $bpnum *(unsigned int*){h2+0x1c:#x} >= {epoch+300}')
 log=[]
 for j in range(20):
  s.cmd('continue',timeout=600)
  s.cmd('maintenance flush register-cache')
  regs=s.regs('pc a7 a5');log.append(regs+'\n'+s.cmd('x/4wx $a7')+'\nfield='+str(int.from_bytes(s.read(h2+0x1c,4),'big')-epoch)+' mode='+s.read(h4+0x1c4,3).hex())
  if f'{h0+0x46de:x}' not in regs.lower():break
 (s.out/'crt-calls.txt').write_text('\n'.join(log))
 print('\n'.join(log),flush=True)

finally:s.quit()
