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
 start=s.read(base+sym('landing_initial_player'),86)
 (s.out/'initial-player.bin').write_bytes(start)
 assert start[24]==start[82]==0 and int.from_bytes(start[28:30],'big')==1
 assert int.from_bytes(start[12:14],'big')==0
 # Let the native ground/periodic code decide when the flight ends.
 h0=long(initial,'RT_HUNKS')
 s.cmd(f'break *{arena+sym("RT_CLEANUP"):#x}')
 s.cmd('continue',timeout=600)
 before,p0,f0=snap('native-cleanup-entry')
 tick=int.from_bytes(p0[12:14],'big')
 assert tick % 16 == 0 and tick > 0
 if os.environ.get('CRASH')=='1':
  assert p0[24]==1 and p0[82]==0
  assert start[62]==128 and int.from_bytes(start[14:16],'big')==12
 else:
  assert p0[24]==p0[82]==2
 assert int.from_bytes(p0[28:30],'big') == 0
 assert p0[27] < 32 and p0[66]&12 == 0
 assert word(before,'RT_CAPTURE_OWNER') == 1
 s.cmd(f'break *{h0+0x5622:#x}')
 s.cmd('continue',timeout=600);s.cmd('delete')
 exited,p1,f1=snap('returned-native-flight')
 assert int.from_bytes(s.read(base+sym('timing_flight_status'),4),'big')==4
 assert p1[12:14]==p0[12:14] and p1[24]==p0[24]
 assert long(exited,'RT_SCHEDULER',32)==long(before,'RT_SCHEDULER',32)
 assert long(exited,'RT_SCHEDULER',36)==long(before,'RT_SCHEDULER',36)+1
 assert long(exited,'RT_SCHEDULER',36)==tick
 assert word(exited,'RT_CONSUMER',60)==6 and word(exited,'RT_BATCH')==4
 assert exited[sym('RT_ENDPOINT'):sym('RT_ENDPOINT')+sym('EP_SIZE')]==bytes(sym('EP_SIZE'))
 for n,o in [('RT_PLAYER_CACHE',sym('PC_VALID')),('RT_ACTOR_PRESENT',sym('AC_VALID')),('RT_RELEASE_PRESENT',sym('AC_VALID')),('RT_SCRIPT_PRESENT',sym('SPC_VALID'))]:assert word(exited,n,o)==0
 assert word(exited,'RT_SCHEDULER',12)==word(exited,'RT_SCHEDULER',14)==0
 for n,off in [('RT_CAPTURE_OWNER',0),('RT_CLOCK',24),('RT_HISTORY',4),('RT_COMMANDS',6)]:assert word(exited,n,off)==0
 s.fields(120)
 after=s.read(arena,sym('RT_ARENA_SIZE'));(s.out/'cleanup-after-arena.bin').write_bytes(after)
 for n,off in [('RT_CAPTURE_OWNER',0),('RT_CLOCK',24),('RT_HISTORY',4),('RT_COMMANDS',6)]:assert word(after,n,off)==0
 for n,off in [('RT_SCHEDULER',32),('RT_SCHEDULER',36),('RT_CLOCK',16)]:assert long(after,n,off)==long(exited,n,off)
 result=dict(exit_tick=tick,native_landing_result=p0[82],native_exit_reason=p0[24],exit_status=4,ending_world_acknowledged_once=True,no_extra_player_field=True,producers_off=True,cleanup_monitor_fields=120,scope='Controlled initial descent, optionally failed engines; native ground classification and periodic flight end. Not natural mission landing or weapon-induced death.')
 (s.out/'landing-exit-result.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
 s.fields(600);s.shot('first-result.png')
 s.tap('space');s.fields(400);s.shot('postflight-choices.png')
 # Native menu resets the pointer to its upper-left position. The second
 # observed choice is "Take off again immediately" at this relative move.
 s.mouse(20,120);s.click()
 s.cmd(f'break *{base+sym("timing_runtime_prepare"):#x}')
 s.cmd('continue',timeout=600);s.cmd('delete')
 old=s.read(arena,sym('RT_ARENA_SIZE'));(s.out/'before-reload-arena.bin').write_bytes(old)
 assert word(old,'RT_CAPTURE_OWNER')==0 and long(old,'RT_SCHEDULER',36)==16
 s.cmd(f'break *{base+sym("timing_runtime_batch"):#x}')
 s.cmd('continue',timeout=600);s.cmd('delete')
 active=s.read(arena,sym('RT_ARENA_SIZE'))
 h0=long(active,'RT_HUNKS');h2=long(active,'RT_HUNKS',8);h6=long(active,'RT_HUNKS',24)
 active,player,native=snap('second-active')
 assert word(active,'RT_CAPTURE_OWNER')==word(active,'RT_CLOCK',24)==1
 assert long(active,'RT_SCHEDULER',32)==long(active,'RT_SCHEDULER',36)==0
 assert long(active,'RT_CLOCK',4)==long(active,'RT_CLOCK',8)==0
 assert word(active,'RT_CLOCK',20)==0 and long(active,'RT_CLOCK',16)==1
 assert int.from_bytes(player[12:14],'big')==16 and player[24]==player[82]==0
 assert word(active,'RT_PLAYER_CACHE')==0
 s.cmd(f'break *{base+sym("scheduler_world_done"):#x}')
 s.cmd(f'condition $bpnum *(unsigned int*){arena+sym("RT_SCHEDULER")+36:#x} >= 4')
 s.cmd('continue',timeout=600);s.cmd('delete')
 running,player,_=snap('second-world-5')
 assert int.from_bytes(player[12:14],'big')==21
 assert long(running,'RT_SCHEDULER',36)==4
 assert word(running,'RT_SCHEDULER',22)==0
 assert long(running,'RT_HISTORY',8)==long(running,'RT_HISTORY',12)==0
 assert long(running,'RT_CLOCK',12)==0 and long(running,'RT_CLOCK',16)==1
 s.cmd(f'break *{h0+0x5622:#x}')
 s.cmd('continue',timeout=600);s.cmd('delete')
 ended,player,_=snap('second-ended')
 assert int.from_bytes(player[12:14],'big')==32 and player[24]==2
 assert long(ended,'RT_SCHEDULER',36)==16
 assert word(ended,'RT_CAPTURE_OWNER')==word(ended,'RT_CLOCK',24)==0
 assert word(ended,'RT_PLAYER_CACHE')==0
 assert ended[sym('RT_ENDPOINT'):sym('RT_ENDPOINT')+sym('EP_SIZE')]==bytes(sym('EP_SIZE'))
 result=dict(native_reload_observed=True,same_arena_reprepared=True,second_initial_tick=16,second_world_observed=21,second_exit_tick=32,second_exit_reason=2,active_sample_without_loss_or_discard=True,terminal_unread_records_discarded=long(ended,'RT_HISTORY',12),fresh_epoch=True,terminal_history_cleared=True,scope='Native immediate-takeoff menu, controlled landing initialization on both flights; not a new mission or all rearm/repair routes.')
 (s.out/'reentry-result.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
finally:s.quit()
