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

 run(s,ROUTE[ROUTE.index('t:n1'):])
 from flight_profile import window
 window(s,lambda n:s.fields(n))
 h0=int.from_bytes(s.read(arena+sym('RT_HUNKS'),4),'big')
 s.cmd(f'break *{h0+0x5c04:#x}')
 s.cmd('continue');s.cmd('delete')
 assert int.from_bytes(s.read(h6+0x3ba4,2),'big')>0
 assert s.read(h6+0x3b96,2)==b'\0\x02'
 print('damage write',s.read(h6+0x3b96,2).hex(),flush=True)
 rows=[]
 s.cmd(f'break *{h0+0x5c04:#x}')
 for n in range(40):
  s.cmd('continue')
  a=s.read(arena,sym('RT_ARENA_SIZE'));p=s.read(h6+0x3b88,86)
  val=lambda key,off,n=2,sgn=False:int.from_bytes(a[sym(key)+off:sym(key)+off+n],'big',signed=sgn)
  raw=(-(((p[53]+p[26])&255)*256+val('RT_ENDPOINT',20,4)*256//1360))&65535
  actual=val('RT_CAMERA',6)
  rows.append(dict(field=val('RT_RECORD',0,4),worlds=val('RT_SCHEDULER',36,4),height=int.from_bytes(p[28:30],'big'),damage=p[14:16].hex(),raw=raw,camera=actual,offset=(actual-raw+32768)%65536-32768,impulse=val('RT_IMPULSES',sym('SI_CACHE')+4,2,True),stamp=val('RT_IMPULSES',sym('SI_FIELD'),4)))
 s.cmd('delete')
 (s.out/'damage-yaw.json').write_text(json.dumps(rows,indent=2))
 print(json.dumps(rows),flush=True)
 assert any(r['offset'] for r in rows)
 s.shot('end.png')
finally:s.quit()
