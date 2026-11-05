import json,struct,sys
from pathlib import Path
sys.path.insert(0,'tools')
import display_ownership,check_disabled,hook_ranges
out=Path(sys.argv[1]);m=json.loads((out/'entry.json').read_text());sim=m['entry']['sim'];chunk=out/('dma' if (out/'dma').exists() else 'chunk0');before=json.loads((chunk/'before.json').read_text());h3=before['h3']
memories=[]
for p in chunk.glob('memory-*.bin'):memories.append((int(p.stem.split('-')[1],16),p.read_bytes()))
def read(at,n):
 for base,b in memories:
  if base<=at and at+n<=base+len(b):return b[at-base:at-base+n]
 raise ValueError(hex(at))
buffers=struct.unpack('>2I',read(h3+0x9d66,8))
r=display_ownership.analyse(chunk/'trace.bin',sim,list(buffers))
(out/'display.json').write_text(json.dumps(r,indent=2)+'\n')
print(out.name,dict(observable=r['observable'],writes=r['framebuffer_writes'],conflicts=len(r['active_display_conflicts']),later=r['conflicts_fetched_later']))
import re,subprocess
mask=int(re.search(r'CUSTOM2=(\d+)',m['whd_args'])[1])
listing=(out/'slave.lst').read_text(encoding='latin1')
def label(n):return int(re.search('^'+n+r'\s+00:([0-9a-fA-F]+)',listing,re.M)[1],16)
slave=m['entry']['game_anchor']-label('tape_game_anchor')
if mask & 128:
 assert read(sim+0x2fd2c,10)==struct.pack('>HIHH',0x4eb9,slave+label('fill_setup'),0x4e71,0x4e71)
 assert read(sim+0x2fd8a,8)==bytes.fromhex('2141005431430058'), 'Pixel twin must be off for timings'
if mask & 256: assert read(sim+0xb06,2)==bytes.fromhex('7001')
if mask & 512:
 assert read(sim+0xb08,8)==struct.pack('>HIH',0x4eb9,slave+label('pace_flight'),0x4e71)
 assert read(sim+0x2d34e,6)==struct.pack('>HI',0x4eb9,slave+label('pace_vbl'))
driver=None
for _,raw in memories:
 at=raw.find(b'RBSLOAD1')
 if at>=0:driver=struct.unpack_from('>I',raw,at+16)[0]
assert driver
for domain,original,base in [('sim','sim',sim),('sound','amigasnd.drv',driver)]:
 args=[sys.executable,'tools/check_disabled.py',f'tmp/game/RedBaron/data/{original}','--domain',domain,'--base',str(base),'--custom2',str(mask)]
 for path in sorted(chunk.glob('memory-*.bin')):args+=['--memory',str(int(path.stem.split('-')[1],16))+':'+str(path)]
 subprocess.run(args,check=True)
(out/'hook-audit.json').write_text(json.dumps(dict(disabled_domains=['sim','sound'],selected_match=bool(mask),pixel_twin_disabled=True,sha256=m['slave_sha256']),indent=2)+'\n')
