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
 route=ROUTE[:ROUTE.index('t:n1')];assert route[-1]=='f:800';run(s,route[:-1]+['f:500'])
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
 # The 68000 can reach the menu-route stop before activation. A zeroed
 # inactive clock is not an epoch; synchronize at the first active batch.
 if int.from_bytes(initial[sym('RT_CLOCK')+24:sym('RT_CLOCK')+26],'big')!=1:
  s.cmd(f'break *{base+sym("timing_runtime_batch"):#x}')
  s.cmd('continue',timeout=600);s.cmd('delete')
  initial=s.read(arena,sym('RT_ARENA_SIZE'))
 assert int.from_bytes(initial[sym('RT_CLOCK')+24:sym('RT_CLOCK')+26],'big')==1
 assert int.from_bytes(initial[sym('RT_CAPTURE_OWNER'):sym('RT_CAPTURE_OWNER')+2],'big')==1
 assert int.from_bytes(initial[sym('RT_CLOCK')+12:sym('RT_CLOCK')+16],'big')==0
 last,total=struct.unpack_from('>II',initial,sym('RT_CLOCK'));epoch=last-total
 (s.out/'active-epoch-arena.bin').write_bytes(initial)

 def snap(name):
  a=s.read(arena,sym('RT_ARENA_SIZE'));(s.out/(name+'-arena.bin')).write_bytes(a)
  player=s.read(h6+0x3b88,86);(s.out/(name+'-player.bin')).write_bytes(player)
  return a,player,int.from_bytes(s.read(h2+0x1c,4),'big')
 def word(a,n,off=0):return int.from_bytes(a[sym(n)+off:sym(n)+off+2],'big')
 def long(a,n,off=0):return int.from_bytes(a[sym(n)+off:sym(n)+off+4],'big')
 # Stop at native boundary entry after runtime sampling has been suspended.
 s.fields(100)
 s.cmd(f'break *{base+sym("timing_runtime_boundary_run"):#x}')
 s.key('tab',True);s.cmd('continue',timeout=600);s.cmd('delete');s.key('tab',False)
 before,p0,f0=snap('suspended')
 assert word(before,'RT_CAPTURE_OWNER')==word(before,'RT_CLOCK',24)==word(before,'RT_HISTORY',4)==0
 s.fields(120)
 paused,p1,f1=snap('paused')
 assert f1-f0>=120
 assert p1==p0 # All 86 player bytes remain frozen, not only the clock.
 for n,off,width in [('RT_CLOCK',4,12),('RT_SCHEDULER',32,8),('RT_HISTORY',0,4)]:
  q=sym(n)+off;assert before[q:q+width]==paused[q:q+width],(n,off)
 assert word(paused,'RT_CAPTURE_OWNER')==word(paused,'RT_CLOCK',24)==0
 # First batch entry is after activation but before consuming new fields.
 s.cmd(f'break *{base+sym("timing_runtime_batch"):#x}')
 s.key('n1',True);s.cmd('continue',timeout=600);s.cmd('delete');s.key('n1',False)
 resumed,p2,f2=snap('resumed')
 assert word(resumed,'RT_CAPTURE_OWNER')==word(resumed,'RT_CLOCK',24)==1
 assert word(resumed,'RT_CLOCK',20)==0
 assert word(resumed,'RT_PLAYER_CACHE')==0
 assert resumed[sym('RT_ENDPOINT'):sym('RT_ENDPOINT')+40]==bytes(40)
 assert long(resumed,'RT_CLOCK')>=f1
 assert long(resumed,'RT_CLOCK',12)==long(before,'RT_CLOCK',12)+word(before,'RT_CLOCK',20)
 s.fields(120)
 after,p3,f3=snap('after')
 assert long(after,'RT_SCHEDULER',36)>long(resumed,'RT_SCHEDULER',36)
 assert long(after,'RT_CLOCK',12)==long(resumed,'RT_CLOCK',12)
 assert word(after,'RT_SCHEDULER',22)==0
 result=dict(paused_native_fields=f1-f0,player_clock_frozen=True,queue_and_world_frozen=True,cache_and_fractions_reset=True,resume_rebases=long(resumed,'RT_CLOCK',16)-long(before,'RT_CLOCK',16),worlds_after_resume=long(after,'RT_SCHEDULER',36)-long(resumed,'RT_SCHEDULER',36),discarded_phase_units=long(after,'RT_CLOCK',12))
 (s.out/'pause-result.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
finally:s.quit()
