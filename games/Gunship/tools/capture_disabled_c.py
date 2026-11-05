"""Live master-toggle off: native patch sites and no runtime allocation."""
import os,sys,re,json,hashlib,struct
from pathlib import Path
from gunship import Session,machine
from route import run
from flight_profile import ROUTE
from layout import locate
from amitools.binfmt.BinFmt import BinFmt
from amitools.binfmt.Relocate import Relocate
root=Path(__file__).resolve().parents[1]
slave=Path(os.environ['SLAVE']);listing=slave.with_suffix(slave.suffix+'.lst').read_text(encoding='latin1')
blob=bytes(BinFmt().load_image(str(slave)).get_segments()[0].get_data())
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+'$',listing,re.M)[1],16)
args=os.environ.get('OFF_ARGS','CUSTOM1=0')+' CUSTOM2=12345'
s=Session(sys.argv[1],dict(NTSC=os.environ.get('NTSC','0'),EXTRA_ARGS=machine().get('EXTRA_ARGS','')+' --video_driver=null',WHD_ARGS=args))
try:
 assert hashlib.sha256(slave.read_bytes()).digest()==hashlib.sha256((s.run/'dh1/Gunship.slave').read_bytes()).digest()
 route=ROUTE[:ROUTE.index('t:n1')];run(s,route)
 mem=s.read(0x200000,0x800000);h=locate(mem)['hunks']
 code=s.read(h[0],0xf0c8)
 assert code[0x826a:0x826c]==bytes.fromhex('4eb9')
 base=int.from_bytes(code[0x826c:0x8270],'big')-sym('avoid_af_game')
 marker=b'Enhanced framerate: flight timing failed'
 assert s.read(base+blob.index(marker),len(marker))==marker
 image=BinFmt().load_image(str(root/'tmp/game/Gunship/data/gamemule'))
 original=bytes(Relocate(image).relocate(h)[0])
 sites=[]
 source=root/'src'
 for file in source.glob('timing-live-*.i'):
  for kind,offset,extra in re.findall(r'^\s*PL_(PSS|PS|P)\s+\$([0-9a-fA-F]+),[^,\n]+(?:,(\d+))?',file.read_text(),re.M):
   off=int(offset,16);size=6+(int(extra) if extra else 0)
   sites.append((off,size,file.name))
 waits=[];pixels=[]
 for off in range(0,len(original)-24,2):
  if original[off:off+2] in [bytes.fromhex(x) for x in ['0828','0829','082e']] and original[off+2:off+8]==bytes.fromhex('0006000266f8'):waits.append((off,8,'blitter wait'))
  if original[off:off+6]==bytes.fromhex('48e73ec04eb9') and int.from_bytes(original[off+6:off+10],'big')==h[0]+off+0x2c:pixels.append((off+4,6,'pixel helper'))
 assert len(waits)==14 and len(pixels)==1
 sites+=waits+pixels
 def check(label):
  current=s.read(h[0],len(original));(s.out/(label+'-h0.bin')).write_bytes(current)
  assert all(current[off:off+size]==original[off:off+size] for off,size,_ in sites)
  values={n:int.from_bytes(s.read(base+sym(n),4),'big') for n in ['_custom1','timing_runtime_arena','timing_runtime_status','blitter_pixel_target']}
  assert not any(values.values()),values
  assert s.read(base+sym('timing_runtime_hunk_table'),36)==bytes(36)
  assert s.read(base+sym('blitter_sites'),56)==bytes(56)
  return int.from_bytes(s.read(h[6]+0x3b94,2),'big')
 before=check('before');s.fields(120);after=check('after');assert after>before
 report=dict(slave_sha256=hashlib.sha256(slave.read_bytes()).hexdigest(),whd_args=args,machine=os.environ.get('MACHINE'),ntsc=os.environ.get('NTSC','0'),native_tick_before=before,native_tick_after=after,patch_sites=len(sites),sites=sites,no_arena_or_timing_binding=True,native_instructions_unchanged=True,scope='Current diagnostic runtime, original 0658 game, master omitted/zero during normal native flight; not an enabled-path acceptance test.')
 (s.out/'disabled-result.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k!='sites'},flush=True)
finally:s.quit()
