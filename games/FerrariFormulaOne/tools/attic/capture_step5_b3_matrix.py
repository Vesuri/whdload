from pathlib import Path
import os,subprocess,json,sys
r=Path(__file__).resolve().parents[1];profiles=json.loads((r/'manifest/step3-profiles.json').read_text())
for profile in ('a1200-fast','a1200'):
 for variant in ('verify','control-lean','lean'):
  build='step5-b3-native-control-lean-v4' if variant=='control-lean' else 'step5-b3-v4/'+variant
  name=f'{profile}-b3-v4-matrix-{variant}-fine'
  e=dict(os.environ,**profiles[profile],LEAN=str(int(variant in ('lean','control-lean'))),KICKSTART=os.environ['KICKSTART_A1200'],WHD_ARGS='CUSTOM1=1 CUSTOM2=1',SLAVE=str(r/f'tmp/build/{build}/fine.slave'))
  print('START',name,flush=True)
  subprocess.run([sys.executable,str(r/'tools/capture_step5_b3.py'),name],env=e,check=True)
