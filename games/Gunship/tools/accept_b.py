#!/usr/bin/env python3
"""B acceptance: assembled tests, audited writes, native planes/palettes, flight smoke checks."""
from pathlib import Path
import hashlib,json,struct
from PIL import Image
root=Path(__file__).resolve().parents[1];r=root/'tmp/b'
# Each capture's emulator ran as its own common/run.sh instance (gunship.instance_for).
run=lambda name:root/'tmp/run'/('session-b-'+name)/'.run'
audit=json.loads((r/'cache-audit.json').read_text())
assert not audit['unmapped_writes'] and not audit['code_data_overlap'] and not audit['unreached_write_sites']
assert (audit['direct_write_sites'],audit['distinct_direct_targets'])==(267,138)
assert '180 total cases' in (r/'assembled-tests.txt').read_text()
assert '128 frame-hook' in (r/'frame-tests.txt').read_text()
def frame(name,tick):
 p=r/name/f'tick-{tick}';c=json.loads((p/'clocks.json').read_text());assert c['tick']==tick
 planes=(p/'planes.bin').read_bytes();assert len(planes)==40000
 h=(p/'h6.bin').read_bytes();slot=c.get('displayed_buffer',int.from_bytes(h[0x49ac:0x49b0],'big'));assert slot in (0,1)
 palette=h[0x484c+64*slot:0x488c+64*slot];assert len(palette)==64
 colours=struct.unpack('>32H',palette)
 indexed=Image.open(p/'indices.png');im=Image.new('RGB',indexed.size)
 im.putdata([tuple(((colours[v//8]>>n)&15)*17 for n in (8,4,0)) for v in indexed.get_flattened_data()]);im.save(p/'display.png')
 return planes+palette
reference=frame('graphics-020',100)
assert len(set(reference))>16
checks=[]
for name in ('graphics-020','graphics-040','graphics-060'):
 for tick in (100,110,120):
  assert frame(name,tick)==reference,(name,tick)
  checks.append((name,tick))
policy={}
for name in ('cache-020-cpu-buffer','cache-040-cpu-buffer','cache-060-cpu-buffer','cache-040-off-cpu-buffer'):
 for tick in (300,310,320):
  assert frame(name,tick)==reference,(name,tick)
  q=json.loads((r/name/f'tick-{tick}/cache-policy.json').read_text())['policy']
  policy[name]=q
  if name=='cache-040-off-cpu-buffer':assert q==0,(name,q)
  else:assert q&0x3f==0x3d and q&0x300==0x300,(name,hex(q))
  checks.append((name,tick))
 assert (run(name)/'dh1/Gunship.slave').read_bytes()==(root/'tmp/build/verify/Gunship.Slave').read_bytes()
 # Record actual MMU/cache/blitter options with each run, not a CPU label alone.
 log=(run(name)/'fsuae/Cache/Logs/fs-uae.log.txt').read_text(errors='replace')
 if name.startswith(('cache-040','cache-060')):
  assert 'enabled=1' in log
  assert 'Set option immediate_blits = "true"' in log
for name in ('smoke-000','smoke-060','combat-060'):
 result=json.loads((r/name/'result.json').read_text());assert result['end_vbl']-result['start_vbl']==500 and result['frames']>40
assert json.loads((r/'ntsc-060-live-pilot/accepted.json').read_text())['loops']==14
sources=Path(__file__).resolve().parents[1]/'src'
report=dict(status='pass',assembled_cases=180,frame_hook_cases=128,direct_write_sites=267,distinct_direct_targets=138,graphics_checks=checks,cache_policy={n:hex(v) for n,v in policy.items()},planes_palette_sha256=hashlib.sha256(reference).hexdigest(),source_hashes={n:hashlib.sha256((sources/n).read_bytes()).hexdigest() for n in ('GunshipHD.s','blitter.i','verify.i')},limitations=['German original unavailable; dispatch and rejection tested with fixtures','Full-MMU asynchronous-blitter emulator configuration reproduces pre-existing cockpit corruption; immediate blits used only for separate cache-functional checks','No real-hardware certification or game-time equivalence claim'])
(r/'acceptance.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
