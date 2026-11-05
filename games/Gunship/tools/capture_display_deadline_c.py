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
 h4=int.from_bytes(initial[sym('RT_HUNKS')+16:sym('RT_HUNKS')+20],'big')
 def crt():return int.from_bytes(s.read(h4+0x1c5,1),'big')
 rows=[]
 for index in range(2):
  s.fields(60)
  current=s.read(arena,sym('RT_ARENA_SIZE'));rate=word(current,'RT_CLOCK',22)
  deadline=long(current,'RT_CLOCK')+(4*rate-word(current,'RT_CLOCK',20)+2)//3
  s.cmd(f'break *{base+sym("timing_live_field"):#x}')
  s.cmd(f'condition $bpnum *(unsigned int*){h2+0x1c:#x} >= {deadline-1}')
  s.cmd('continue',timeout=600);s.cmd('delete')
  s.cmd(f'break *{base+sym("timing_runtime_boundary_run"):#x}')
  s.key('space',True);s.cmd('continue',timeout=600);s.cmd('delete');s.key('space',False)
  before,p0,f0=snap(f'{index}-suspended');c0=crt()
  assert word(before,'RT_BOUNDARY_RECORD',4)==0x40
  assert word(before,'RT_SCHEDULER',14)==1,(deadline,long(before,'RT_SCHEDULER',24),word(before,'RT_SCHEDULER',14))
  for n,off in [('RT_CAPTURE_OWNER',0),('RT_CLOCK',24),('RT_HISTORY',4),('RT_COMMANDS',6)]:assert word(before,n,off)==0
  assert word(before,'RT_BOUNDARY_PHASE')==1
  s.cmd(f'break *{base+sym("timing_runtime_boundary_finish"):#x}')
  s.cmd('continue',timeout=600);s.cmd('delete')
  marked,p1,f1=snap(f'{index}-marked');c1=crt()
  assert word(marked,'RT_BOUNDARY_PHASE')==4 and word(marked,'RT_BOUNDARY_RESULT')==0
  for off in [32,36]:assert long(marked,'RT_SCHEDULER',off)==long(before,'RT_SCHEDULER',off)
  assert p1[12:14]==p0[12:14]
  q=sym('RT_COMMANDS');head=word(marked,'RT_COMMANDS',2)&127
  assert int.from_bytes(marked[q+24+head*8+6:q+24+head*8+8],'big')==1
  s.cmd(f'break *{base+sym("timing_runtime_batch"):#x}')
  s.cmd('continue',timeout=600);s.cmd('delete')
  resumed,p2,f2=snap(f'{index}-resumed')
  for n,off in [('RT_CAPTURE_OWNER',0),('RT_CLOCK',24),('RT_HISTORY',4),('RT_COMMANDS',6)]:assert word(resumed,n,off)==1
  assert word(resumed,'RT_CLOCK',20)==word(resumed,'RT_PLAYER_CACHE')==0
  assert resumed[sym('RT_ENDPOINT'):sym('RT_ENDPOINT')+40]==bytes(40)
  assert long(resumed,'RT_CLOCK',16)==long(before,'RT_CLOCK',16)+1
  assert long(resumed,'RT_SCHEDULER',32)==long(before,'RT_SCHEDULER',32)+1
  assert long(resumed,'RT_SCHEDULER',36)==long(before,'RT_SCHEDULER',36)+word(before,'RT_SCHEDULER',14)
  assert long(resumed,'RT_BOUNDARY_ABORTS')==long(before,'RT_BOUNDARY_ABORTS')
  assert word(resumed,'RT_SCHEDULER',22)==0
  rows.append(dict(index=index,crt_before=c0,crt_after_native=c1,native_transition_fields=f1-f0,until_resume_fields=f2-f0,retained_field_completed_once=True,world_due=word(before,'RT_SCHEDULER',14),history_lost=long(resumed,'RT_HISTORY',8)))
 s.fields(120);after,p3,f3=snap('after')
 assert word(after,'RT_SCHEDULER',22)==0 and long(after,'RT_HISTORY',8)==0
 (s.out/'display-boundary-result.json').write_text(json.dumps(dict(transitions=rows,sampling_suspended_and_resumed=True,cache_and_fractions_reset=True),indent=2)+'\n');print(rows,flush=True)
finally:s.quit()
