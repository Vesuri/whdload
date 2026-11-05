#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,subprocess,sys
r=Path(__file__).resolve().parents[1];d=r/'tmp/step2'
subprocess.run([sys.executable,str(r/'tools/compare_step2.py')],check=True)
a=json.loads((d/'verified-demo-a/display.json').read_text());b=json.loads((d/'verified-demo-b/display.json').read_text());assert a==b and len(a)==32
changes=[y['field'] for x,y in zip(a,a[1:]) if x['first_dma']!=y['first_dma']]
pixels=[y['field'] for x,y in zip(a,a[1:]) if x['game_pixels_sha256']!=y['game_pixels_sha256']]
assert changes and all(i in pixels for i in changes)
m=json.loads((r/'manifest/step2-overlays.json').read_text());assert {x['header'] for x in m['groups']}=={0,0x22f30,0x30a30}
checks={}
for name in ('verified-demo-a','verified-demo-b','slow-demo'):
 v=json.loads((d/name/'result.json').read_text());assert v['profile_metadata_restored'] and v['warp_before']=='warp=1' and v['warp_after']=='warp=0' and v['before']['updates']==125 and v['after']['fields']-v['before']['fields']==32
 checks[name]={'settling_fields':v['before']['fields']-v['warp_switch_fields'],'before':v['before'],'after':v['after']}
paths=[r.parent.parent/'Games/FerrariFormulaOne_WHD.s',r/'tmp/build/release/FerrariFormulaOne.slave',d/'emulator-build/fs-uae',r/'tools/step2-emulator.patch']
for n in checks:paths += [d/n/f for f in ('verify.slave','verify.s','anchor.bin','display.json','launch.json','result.json')]
hashes={str(p.relative_to(r.parent.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
assert hashes['Games/FerrariFormulaOne_WHD.s']=='88995624ab0cc80974109bfede29ff6aa7434cf9901933b1961cf87eda851761'
assert hashes['tmp/dev/tmp/build/release/FerrariFormulaOne.slave']=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
o={'status':'complete','scope':'SPS 0481, A500 PAL, automatic no-input demo; preparation only, not performance measurement','two_fresh_boots_dma_and_pixels_equal':True,'visible_bank_change_fields':changes,'pixel_change_fields':pixels,'captures':checks,'state_checks':json.loads((r/'manifest/step2-state-checks.json').read_text()),'sha256':hashes,'limits':['Calibrated SPS/A500 addresses; other layouts require resolution','Full time model remains step 4','Interactive coverage deferred at user direction','Pixels can change without bank exchange; count DMA exchanges for presentation','Diagnostic overhead unsuitable for final FPS claims']}
(r/'manifest/step2-validation.json').write_text(json.dumps(o,indent=2)+'\n');print('Step 2 demo checks PASS; DMA presentations:',changes,'; image changes:',pixels)
