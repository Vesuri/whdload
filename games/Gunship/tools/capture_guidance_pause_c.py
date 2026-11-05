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
  guide=s.read(h0+0xa44d,3);(s.out/f'{tag}-guidance.bin').write_bytes(guide)
  return a,actors,player,timers,masks,guide
 s.cmd(f'break *{base+sym("timing_runtime_boundary_run"):#x}')
 s.key('tab',True);s.cmd('continue',timeout=600);s.cmd('delete');s.key('tab',False)
 before=snapshot('suspended');a=before[0]
 assert before[1][0x3b]==8 and before[1][0x35]>0
 assert before[4][6:8]==b'\0\5' and 0<before[5][0]<=30 and before[5][1]==1
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
 assert resumed[5]==before[5]
 counter=resumed[5][0];initial_counter=counter;rows=[]
 s.cmd(f'break *{base+sym("scheduler_player_done"):#x}')
 for field in range(1,40):
  s.cmd('continue',timeout=600)
  a=s.read(arena,sym('RT_ARENA_SIZE'));guide=s.read(h0+0xa44d,3);slot=int.from_bytes(s.read(h0+0xba0e,2),'big')
  counter=255 if counter==31 else counter+1
  assert guide[0]==counter,(field,guide.hex(),counter)
  assert slot==(65535 if counter==255 else 5)
  assert guide[1]==(0 if counter==255 else 1)
  assert long(a,'RT_CLOCK',4)==long(r,'RT_CLOCK',4)+field
  assert word(a,'RT_SCHEDULER',22)==0 and long(a,'RT_HISTORY',8)==0
  rows.append(dict(delivered_fields=field,counter=counter,slot=slot))
  if counter==255:break
 else:raise AssertionError('guidance never released')
 assert len(rows)==32-initial_counter
 s.cmd('delete');released=snapshot('released')
 mask_before=int.from_bytes(released[4][:2],'big')
 ammo_before=s.read(h6+0x155a,1)[0]
 s.cmd(f'break *{base+sym("scheduler_world_done"):#x}')
 s.cmd('monitor input JOY2_FIRE_BUTTON 1')
 # The key may arrive after this delivered field's cutoff; allow the next
 # complete world after the first observed deadline, without skipping input.
 captures=[]
 for unused in range(2):
  s.cmd('continue',timeout=600)
  a=s.read(arena,sym('RT_ARENA_SIZE'));mask=int.from_bytes(s.read(h0+0xba08,2),'big');ammo=s.read(h6+0x155a,1)[0]
  captures.append(dict(world=long(a,'RT_CLOCK',8),mask=mask,ammo=ammo))
  if mask&~mask_before:break
 s.cmd('monitor input JOY2_FIRE_BUTTON 0');s.cmd('delete')
 assert mask&~mask_before and ammo==ammo_before-1,(captures,mask_before,ammo_before)
 result=dict(paused_emulator_fields=120,guidance_frozen=True,initial_counter=initial_counter,remaining_consumed_fields=len(rows),release_trace=rows,next_launch=captures,ammo_before=ammo_before,ammo_after=ammo,scope='Guided-slot launch exclusion and release, not a generic reload timer.')
 (s.out/'guidance-pause-result.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
finally:s.quit()

