import json,hashlib,subprocess
from pathlib import Path
from capture_demo import ROOT,sha
from machine_profiles import PROFILES
from check_disabled import check
P=ROOT/'tmp/prof'
base=json.loads((P/'step2-baselines.json').read_text());assert len(base)==7
validated=[]
for profile in PROFILES:
 for w in ['attract','A','B']:
  d=P/('s2-a500-attract-analysis' if profile=='a500' and w=='attract' else f's2-profile-{profile}-{w}')
  r=json.loads((d/'window-metrics.json').read_text());assert r['fields']==(1000 if w=='attract' else 500)
  assert abs(r['seconds']-r['fields']*142102/7093790)<1e-9
  assert r['instruction_timing_supported']==(PROFILES[profile][-1]=='trace')
  if profile=='a500' and w=='attract':
   assert r['swaps']==base[profile]['attract']['swaps']
  else:
   assert (d/'trace.bin.zst').exists() and (d/'trace.sha256').exists()
   assert check(d,['VERIFY_ATTRACT' if w=='attract' else 'VERIFY_DRIVE'])['passed']
   assert r['independent_swaps'] is not None
  if r['instruction_timing_supported']:
   assert .999<=r['coverage']<=1.001
   if profile=='a1200-020' and w in ['B','attract']:
    repeat=json.loads((d/'repeatability.json').read_text());assert repeat['all_instruction_dma_screenshot_cycle_fingerprints_identical'] and repeat['all_memory_snapshots_identical']
  r['blitter_dma_recording_supported']=PROFILES[profile][-1]=='trace'
  if not r['blitter_dma_recording_supported']:
   assert 'blitter_cycle_exact=false' in (d/'emulator.uae').read_text()
   note='Effective blitter_cycle_exact=false: absent blitter DMA records are unavailable activity, not zero blitter use.'
   if note not in r['limitations']:r['limitations'].append(note)
  (d/'window-metrics.json').write_text(json.dumps(r,indent=2)+'\n')
  validated.append(dict(profile=profile,window=w,fields=r['fields'],instruction_timing=r['instruction_timing_supported'],blitter_slots=r['blitter_dma_recording_supported']))
 for kind in ['attract1','attract2','drive']:
  d=P/f's2-{profile}-{kind}';m=json.loads((d/'placement.json').read_text());assert all(m[k]['bank']=='chip' for k in ['edge_left','edge_right','front','back'])
  assert check(d,['VERIFY_DRIVE' if kind=='drive' else 'VERIFY_ATTRACT'])['passed']
 c=P/f's2-cache-{profile}'/'cache.json';assert c.exists()
for cpu in ['68040','68060']:
 d=json.loads((P/f's2-mmu-{cpu}'/'functional.json').read_text());assert d['swaps']>0 and d['disabled_ranges_pass'] and not d['timing_valid']
for k,v in [('normal','HardDrivin.Slave'),('attract','HardDrivin-verify.slave'),('drive','HardDrivin-drive.slave')]:assert (ROOT/f'tmp/build/s2-final-{k}.slave').read_bytes()==(ROOT/'tmp/build'/v).read_bytes()
assert json.loads((P/'step2-ceiling-validation.json').read_text())['layout_identical']
(P/'step2-validation.json').write_text(json.dumps(dict(profiles=7,samples=validated,normal_existing_fixture_binaries_unchanged=True,all_disabled_ranges_pass=True,mmu_functional_pass=True,ceiling_validation_pass=True),indent=2)+'\n')
print('Validated seven baselines, 21 samples, cache/MMU/ceiling evidence and unchanged normal fixtures.')
