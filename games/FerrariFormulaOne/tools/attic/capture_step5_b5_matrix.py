from pathlib import Path
import os,sys,json,subprocess
r=Path(__file__).resolve().parents[1];profiles=json.loads((r/'manifest/step3-profiles.json').read_text())
for profile in ('a1200-fast','a1200'):
 for variant in ('verify','lean'):
  e=dict(os.environ,**profiles[profile],KICKSTART=os.environ['KICKSTART_A1200'],SLAVE=str(r/f'tmp/build/step5-b5-v5-compact/{variant}/fine.slave'),WHD_ARGS='CUSTOM1=1 CUSTOM2=1',LEAN='1' if variant=='lean' else '0')
  subprocess.run([sys.executable,str(r/'tools/capture_step5_b5.py'),f'{profile}-b5-v5-matrix-{variant}-fine'],env=e,check=True)
