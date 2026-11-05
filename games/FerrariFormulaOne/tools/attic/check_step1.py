#!/usr/bin/env python3
"""Require completed baseline cases and recognizable title, pit and shell captures."""
from pathlib import Path
import json,hashlib,subprocess,sys
from PIL import Image,ImageChops
root=Path(__file__).resolve().parents[1];p=root/'tmp/baseline'
subprocess.run([sys.executable,str(root/'tools/verify_inputs.py')],check=True)
subprocess.run([sys.executable,str(root/'tools/compare_baselines.py')],check=True,stdout=subprocess.DEVNULL)
ref=p/'release-c0-accepted-pit'
regions={'title-menu':(54,36,694,436),'tow-pits':(300,220,520,320),'quit-shell':(78,60,600,110)}
def crop(folder,label):return Image.open(folder/(label+'.png')).convert('RGB').crop(regions[label])
report={}
for kind in ('shipped','release'):
 for c in (0,1):
  folder=p/f'{kind}-c{c}-accepted-pit'
  r=json.loads((folder/'result.json').read_text())
  names=[e['name'] for e in r['events']]
  assert names==['race-entry','takeover','paused-before-resume','resumed','steered','accept-target','tow-pits','F10-native-decode','quit-shell'],names
  assert (folder/'capture.log').stat().st_size>1000
  # This is a visual checkpoint check, not a claim of equal gameplay trajectories.
  checks={label:ImageChops.difference(crop(ref,label),crop(folder,label)).getbbox() is None for label in regions}
  assert all(checks.values()),(folder,checks)
  # Native demo-exit bookkeeping, not a pose or velocity injection.
  b=(folder/'resumed.bin').read_bytes();assert b[0x1bee8:0x1beea]==b'\0\0'
  report[folder.name]={'completed':True,'visual_checks':checks,'demo_flag_cleared':True,'events':r['events']}
assert ImageChops.difference(crop(ref,'tow-pits'),Image.open(ref/'title-menu.png').convert('RGB').crop(regions['tow-pits'])).getbbox() is not None
manifest=json.loads((root/'manifest/baseline-build.json').read_text())
for kind in ('imported','release','verify'):
 b=(root/f'tmp/build/{kind}/FerrariFormulaOne.slave').read_bytes()
 assert hashlib.sha256(b).hexdigest()==manifest['builds'][kind]['sha256']
(root/'manifest/step1-validation.json').write_text(json.dumps({'checks':report,'normal_build_hashes_unchanged':True,'evidence_scope':'SPS/A500 emulator, diagnostic input consumers; no physical input or performance claim'},indent=2)+'\n')
print('PASS: four completed input cases, title/pit/shell checkpoints, input/state checks, loaded-code and controlled-race comparisons, source/input/build hashes')
