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
 h0=int.from_bytes(initial[sym('RT_HUNKS'):sym('RT_HUNKS')+4],'big')
 tail=listing[listing.index('world_reserves_step:'):]
 terminal=int(re.search(r'^00:([0-9A-F]{8}).*tst.b \$18\(a5\)',tail,re.M)[1],16)
 s.cmd(f'break *{base+terminal:#x}')
 s.cmd(f'condition $bpnum *(unsigned short*){h6+0x3b88+12:#x} >= 192')
 s.cmd('continue',timeout=600);s.cmd('delete')
 a=s.read(arena,sym('RT_ARENA_SIZE'));player=s.read(h6+0x3b88,86)
 ticks=int.from_bytes(player[12:14],'big');assert ticks==192
 (s.out/'minute-arena.bin').write_bytes(a);(s.out/'minute-player.bin').write_bytes(player)
 field=int.from_bytes(s.read(h2+0x1c,4),'big')
 for offset in [sym('RT_CLOCK')+12,sym('RT_HISTORY')+12,sym('RT_COMMANDS')+16,sym('RT_COMMANDS')+20]:assert int.from_bytes(a[offset:offset+4],'big')==0
 # The guest fixture requests landing-result UI at tick 192 immediately
 # before this terminal-state read. It never changes the elapsed tick count.
 assert player[24]==player[82]==2
 s.cmd(f'break *{h0+0x5622:#x}')
 s.cmd('continue',timeout=600);s.cmd('delete')
 ended=s.read(h6+0x3b88,86);end_arena=s.read(arena,sym('RT_ARENA_SIZE'))
 (s.out/'ended-player.bin').write_bytes(ended);(s.out/'ended-arena.bin').write_bytes(end_arena)
 ticks=int.from_bytes(ended[12:14],'big');assert ticks>=192 and ended[24]==2
 result=dict(active_start=epoch,measured_field=field,measured_ticks=192,exit_ticks=ticks,expected_minutes=ticks//180,expected_seconds=ticks//3%60,diagnostic_guest_exit_bytes=[24,82],scope='Actual timed run followed by diagnostic landing-result request; not natural landing acceptance')
 (s.out/'clock-ui-result.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
 s.fields(360);s.shot('clock-result.png')
finally:s.quit()
