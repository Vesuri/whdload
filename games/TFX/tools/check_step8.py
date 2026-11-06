#!/usr/bin/env python3
"""Validate final step-8 evidence without turning clock/state mismatches into passes."""
import json,sys,struct,subprocess,hashlib
from pathlib import Path
import map_symbols as m
from PIL import Image
root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else m.ROOT/'tmp/step8';r={}
subprocess.run([sys.executable,str(m.ROOT/'tools/check_chip_relocs.py')],check=True)
base=root/'baseline-scene-latched';candidate=root/'final-scene-latched'
r['controlled_screenshots']={f.name:f.read_bytes()==(candidate/f.name).read_bytes() for f in sorted(base.glob('swap-*.png'))}
assert len(r['controlled_screenshots'])==5 and all(r['controlled_screenshots'].values())
for d in [base,candidate]:
 for image in d.glob('swap-*.png'):
  im=Image.open(image).convert('RGB');assert im.getbbox() and im.getcolors(64) is None
 assert (d/'swap-001.png').read_bytes()!=(d/'swap-030.png').read_bytes()
for d in [base,candidate]:
 steps=json.loads((d/'controlled-time.json').read_text());assert steps['swaps']==57 and steps['delta']==5
 assert [p['swap'] for p in json.loads((d/'publications.json').read_text())]==list(range(1,58))
subprocess.run([sys.executable,str(m.ROOT/'tools/check_chip_dma.py'),str(candidate)],check=True)
ns=m.load(m.GAME/'tfx.020');a=root/'final-audit-040';audit=json.loads((a/'audit.json').read_text());assert audit['split']
code=(a/'hunk0.bin').read_bytes();n=0
# Also prove CPU-only objects were NOT relocated into the DMA block.
for o in ns[0]['relocs'][1]:
 old=struct.unpack_from('>I',ns[0]['data'],o)[0]
 if 0x24d4<=old<0x27e0 or 0x4330<=old<0x4938:
  assert struct.unpack_from('>I',code,o)[0]==audit['bases'][1]+old;n+=1
r['cpu_only_code_operands_in_fast']=n;assert n==156
r['dma_code_operands']=sum(x['source']==0 for x in audit['relocations']);assert r['dma_code_operands']==50
assert all(x['equal'] for x in audit['relocations'] if x['source']==0)
mutations=[x for x in audit['relocations'] if not x['equal']];assert {x['offset'] for x in mutations}=={'0xfcb0','0xfcc0','0x27d6'}
r['expected_live_data_pointer_changes']=mutations
assert not json.loads((root/'final-audit-original/audit.json').read_text())['split']
r['windows']={name:json.loads((root/name/'counts.json').read_text())['publications'] for name in ['baseline-window','final-window','final-window-repeat']}
assert r['windows']['final-window']==r['windows']['final-window-repeat']
a,b=root/'final-window',root/'final-window-repeat'
r['repeat_window_events_equal']=json.loads((a/'counts.json').read_text())['events']==json.loads((b/'counts.json').read_text())['events']
r['repeat_window_image_equal']=(a/'after.png').read_bytes()==(b/'after.png').read_bytes()
r['repeat_window_hunks_equal']=[(a/f'end-hunk{i}.bin').read_bytes()==(b/f'end-hunk{i}.bin').read_bytes() for i in range(3)]
r['uncontrolled_before_after_image_equal']=(root/'baseline-window/after.png').read_bytes()==(a/'after.png').read_bytes()
r['regression']=json.loads((root/'final-regression/summary.json').read_text())
assert all(x['screenshots_identical'] for x in r['regression'].values())
# State results are evidence, not an acceptance condition silently weakened here.
r['all_regression_raw_state_equal']=all(x['raw_identical'] for x in r['regression'].values())
assert (m.ROOT/'tmp/build/release/TFX.Slave').read_bytes()==(a/'slave.slave').read_bytes()
(root/'validation.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
