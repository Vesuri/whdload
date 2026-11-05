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
 events=[(240,'key 5 1'),(244,'key 5 0'),(300,'input JOY2_FIRE_BUTTON 1'),(304,'input JOY2_FIRE_BUTTON 0'),(320,'input JOY2_FIRE_BUTTON 1'),(324,'input JOY2_FIRE_BUTTON 0')]
 rate=int.from_bytes(initial[sym('RT_CLOCK')+22:sym('RT_CLOCK')+24],'big')
 assert rate in (50,60)
 events=[(round(field*rate/50),command) for field,command in events]
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

 h0=int.from_bytes(initial[sym('RT_HUNKS'):sym('RT_HUNKS')+4],'big')
 def word(a,n,off=0):return int.from_bytes(a[sym(n)+off:sym(n)+off+2],'big')
 def long(a,n,off=0):return int.from_bytes(a[sym(n)+off:sym(n)+off+4],'big')
 def snapshot(tag):
  a=s.read(arena,sym('RT_ARENA_SIZE'));actors=s.read(h0+0xc6a0,0xc2);player=s.read(h6+0x3b88,86)
  timers=s.read(h6+0x4296,1)+s.read(h6+0x42f6,2);masks=s.read(h0+0xba08,8)
  for name,data in [('arena',a),('actors',actors),('player',player),('timers',timers),('masks',masks)]:(s.out/f'{tag}-{name}.bin').write_bytes(data)
  return a,actors,player,timers,masks
 s.cmd(f'break *{base+sym("scheduler_world_done"):#x}')
 s.cmd(f'condition $bpnum *(unsigned int*){arena+sym("RT_SCHEDULER")+36:#x} >= 23')
 s.cmd('continue',timeout=600);s.cmd('delete')
 s.cmd(f'break *{base+sym("timing_runtime_boundary_run"):#x}')
 s.key('tab',True);s.cmd('continue',timeout=600);s.cmd('delete');s.key('tab',False)
 before=snapshot('suspended');a=before[0]
 assert before[1][0x3b]==8 and before[1][0x35]>0
 assert word(a,'RT_CAPTURE_OWNER')==word(a,'RT_CLOCK',24)==0
 s.fields(120);paused=snapshot('paused')
 assert before[1:]==paused[1:]
 for name,width in [('RT_ACTOR_PRESENT',sym('AC_SIZE')),('RT_RELEASE_PRESENT',sym('AC_SIZE')),('RT_ACTOR_GENERATIONS',sym('AG_SIZE'))]:
  off=sym(name);assert a[off:off+width]==paused[0][off:off+width]
 for off in [32,36]:assert long(a,'RT_SCHEDULER',off)==long(paused[0],'RT_SCHEDULER',off)
 s.cmd(f'break *{base+sym("timing_runtime_batch"):#x}')
 s.key('n1',True);s.cmd('continue',timeout=600);s.cmd('delete');s.key('n1',False)
 resumed=snapshot('resumed');r=resumed[0];c=sym('RT_ACTOR_PRESENT')
 assert word(r,'RT_CAPTURE_OWNER')==1 and word(r,'RT_CLOCK',20)==0
 assert word(r,'RT_PLAYER_CACHE')==0 and word(r,'RT_RELEASE_PRESENT',sym('AC_VALID'))==0
 assert word(r,'RT_ACTOR_PRESENT',sym('AC_VALID'))==1
 assert word(r,'RT_ACTOR_PRESENT',sym('AC_PHASE'))==0
 assert long(r,'RT_ACTOR_PRESENT',sym('AC_TICK'))==long(r,'RT_CLOCK',8)
 assert r[c+sym('AC_CURRENT'):c+sym('AC_CURRENT')+36]==resumed[1][:36]
 assert r[c+sym('AC_GENERATIONS'):c+sym('AC_GENERATIONS')+sym('AG_SIZE')]==r[sym('RT_ACTOR_GENERATIONS'):sym('RT_ACTOR_GENERATIONS')+sym('AG_SIZE')]
 first=long(r,'RT_SCHEDULER',36)+1
 s.cmd(f'break *{base+sym("scheduler_world_done"):#x}')
 for w in range(first,66):
  s.cmd('continue',timeout=600)
  a=s.read(arena,sym('RT_ARENA_SIZE'));assert long(a,'RT_SCHEDULER',36)==w-1
  assert word(a,'RT_SCHEDULER',22)==0 and long(a,'RT_HISTORY',8)==0
  assert long(a,'RT_CLOCK',12)==long(r,'RT_CLOCK',12)
  length=int.from_bytes(s.read(h0-8,4),'big')-8;h=s.read(h0,length)
  assert h[0xc6d5]==max(64-w,0),(w,h[0xc6d5])
  d=s.out/f'world-{w}';d.mkdir();(d/'arena.bin').write_bytes(a);(d/'h0.bin').write_bytes(h)
 s.cmd('delete')
 result=dict(paused_emulator_fields=120,rocket_lifetime_before_pause=before[1][0x35],full_actor_block_frozen=True,player_timers_masks_frozen=True,prediction_caches_frozen_while_paused=True,resume_prediction_recaptured_at_phase_zero=True,release_cache_invalid=True,resumed_world_first=first,rocket_release_world=64,post_resume_clock_discard=0)
 (s.out/'actor-pause-result.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
finally:s.quit()
