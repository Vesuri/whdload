#!/usr/bin/env python3
from pathlib import Path
import json,sys,hashlib
sys.path.insert(0,str(Path(__file__).parent))
from compare_step2 import state,compare
r=Path(__file__).resolve().parents[1];d=r/'tmp/step3';profiles=json.loads((r/'manifest/step3-profiles.json').read_text());checks={}
for name in ('a500','a500-fast','a1200','a1200-fast'):
 arms={}
 for arm in (0,1):
  a=d/f'{name}-c{arm}-a';b=d/f'{name}-c{arm}-b'
  if not (a/'analysis.json').exists() or not (b/'analysis.json').exists():arms[str(arm)]={'status':'unavailable'};continue
  x=json.loads((a/'analysis.json').read_text());y=json.loads((b/'analysis.json').read_text())
  assert x['fields']==y['fields']==1000
  z={'status':'complete','same_anchor':(a/'anchor.bin').read_bytes()==(b/'anchor.bin').read_bytes(),'same_end':(a/'end.bin').read_bytes()==(b/'end.bin').read_bytes(),'same_presentations':x['bank_changes']==y['bank_changes'],'same_cycle_calibration':x['cycle_values']==y['cycle_values'],'fps_a':x['presented_fps_count'],'fps_b':y['presented_fps_count']}
  assert z['same_anchor'] and z['same_end'] and z['same_presentations'] and z['same_cycle_calibration'],(name,arm,z)
  arms[str(arm)]=z
 if all(arms[str(i)]['status']=='complete' for i in (0,1)):
  arms['matched_update125_c0_c1_mismatches']=compare(state((d/f'{name}-c0-a/anchor.bin').read_bytes()),state((d/f'{name}-c1-a/anchor.bin').read_bytes()))
 checks[name]=arms
out={'profiles':checks,'source_sha256':hashlib.sha256((r.parent.parent/'Games/FerrariFormulaOne_WHD.s').read_bytes()).hexdigest(),'release_sha256':hashlib.sha256((r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes()).hexdigest()}
assert out['source_sha256']=='88995624ab0cc80974109bfede29ff6aa7434cf9901933b1961cf87eda851761'
assert out['release_sha256']=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
(r/'manifest/step3-checks.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(checks,indent=2))
