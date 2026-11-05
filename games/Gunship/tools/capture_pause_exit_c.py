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
 d1_check=os.environ.get('CHECK_D1')=='1'
 if d1_check:
  saved_blit=int.from_bytes(s.read(base+sym('timing_blitter_intena'),2),'big')
  flight_intena=int.from_bytes(s.read(0xdff01c,2),'big')
  assert flight_intena&0x40==0,(saved_blit,flight_intena)
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
 # Escape takes the native nonlocal exit out of pause. Observe its return
 # to original flight cleanup, rather than allowing a new runtime epoch.
 h0=int.from_bytes(before[sym('RT_HUNKS'):sym('RT_HUNKS')+4],'big')
 s.cmd(f'break *{h0+0x5622:#x}')
 s.key('esc',True);s.cmd('continue',timeout=600);s.cmd('delete');s.key('esc',False)
 exited,p2,f2=snap('exited')
 assert int.from_bytes(s.read(base+sym('timing_flight_status'),4),'big')==4
 assert p2[24]==128
 for n,off in [('RT_CAPTURE_OWNER',0),('RT_CLOCK',24),('RT_HISTORY',4),('RT_COMMANDS',6)]:assert word(exited,n,off)==0,(n,off)
 assert word(exited,'RT_BATCH')==4 and word(exited,'RT_BOUNDARY_PHASE')==5
 assert long(exited,'RT_BOUNDARY_ABORTS')==long(before,'RT_BOUNDARY_ABORTS')+1
 for off in [32,36]:assert long(exited,'RT_SCHEDULER',off)==long(before,'RT_SCHEDULER',off)
 assert long(exited,'RT_CLOCK',16)==long(before,'RT_CLOCK',16)
 assert long(exited,'RT_CLOCK',12)==long(before,'RT_CLOCK',12)
 assert word(exited,'RT_SCHEDULER',12)==word(exited,'RT_SCHEDULER',14)==0
 assert word(exited,'RT_COMMANDS')==word(exited,'RT_COMMANDS',2)==word(exited,'RT_COMMANDS',4)
 if d1_check:
  s.cmd(f'break *{h0+0x5628:#x}')
  s.cmd('continue',timeout=600);s.cmd('delete')
  released_intena=int.from_bytes(s.read(0xdff01c,2),'big')
  assert released_intena&0x40==saved_blit,(saved_blit,released_intena)
  (s.out/'blitter-ownership.json').write_text(json.dumps(dict(saved_blit=saved_blit,flight_intena=flight_intena,released_intena=released_intena)))
 s.fields(120)
 # Native flight hunks may be released/reused during cleanup. Observe only
 # the slave-owned arena; elapsed cleanup time is the monitor's field count.
 after=s.read(arena,sym('RT_ARENA_SIZE'))
 (s.out/'cleanup-after-arena.bin').write_bytes(after)
 for n,off in [('RT_CAPTURE_OWNER',0),('RT_CLOCK',24),('RT_HISTORY',4),('RT_COMMANDS',6)]:assert word(after,n,off)==0
 for n,off in [('RT_SCHEDULER',32),('RT_SCHEDULER',36),('RT_BOUNDARY_ABORTS',0),('RT_CLOCK',16)]:assert long(after,n,off)==long(exited,n,off)
 result=dict(paused_native_fields=f1-f0,all_player_bytes_frozen=True,returned_to_native_cleanup=True,exit_status=4,aborted_fields=long(exited,'RT_BOUNDARY_ABORTS')-long(before,'RT_BOUNDARY_ABORTS'),completed_extra_fields=long(exited,'RT_SCHEDULER',32)-long(before,'RT_SCHEDULER',32),completed_extra_worlds=long(exited,'RT_SCHEDULER',36)-long(before,'RT_SCHEDULER',36),epoch_unchanged=True,producers_stay_off_after_cleanup=True,cleanup_monitor_fields=120)
 (s.out/'pause-exit-result.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
finally:s.quit()
