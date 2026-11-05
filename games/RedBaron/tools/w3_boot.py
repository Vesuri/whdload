#!/usr/bin/env python3
"""Boot W3 using the already-validated CPU configurations."""
import argparse,json,os,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('machine',choices=['a500','020','030']);p.add_argument('mask',type=int);p.add_argument('out',type=Path);p.add_argument('--twins',action='store_true');a=p.parse_args()
ref=Path('tmp/prof')/('w2-combined-030-0-r2' if a.machine=='030' else f'w2-combined-{a.machine}-0')
m=json.loads((ref/'entry.json').read_text())
base=Path.cwd()/'tmp/run/default/.run/fsuae';pid=Path('tmp/run/default/.run/fsuae.pid')
if pid.exists():
 result=subprocess.run(['ps','-p',pid.read_text().strip(),'-o','command='],capture_output=True,text=True)
 if result.returncode==0: assert f'--base_dir={base}' in result.stdout
assert not (a.out/'entry.json').exists()
env=dict(os.environ,MallocScribble='1',CPU=m['cpu'],CHIP_KB=m['chip_kb'],FAST_KB=m['fast_kb'],EXTRA_ARGS=m['extra_args'],AMIGA_MODEL='A1200' if a.machine=='020' else 'A500',WHD_ARGS=f'CUSTOM2={a.mask} CUSTOM5={49664 if a.twins else 512}'+(' MMU' if a.machine=='030' else ''))
env.pop('BOOT_BREAK',None)
calibration=Path('tmp/prof')/('w3-div-twin-a500-r2' if a.machine=='a500' else f'w3-div-twin-{a.machine}')/'entry.json'
if calibration.exists():
 old=json.loads(calibration.read_text());assert old['slave_sha256']=='bad57261d0593f51eb42c79dde6e53a9d15c0154d52d0831ec8edfc8f825469a'
 env['BOOT_BREAK']=hex(old['entry']['game_anchor'])
if a.machine=='020':env['KICKSTART']=os.environ['KICKSTART_A1200']
subprocess.run([sys.executable,'tools/reach_flight.py','--no-shot','--out',str(a.out)],env=env,check=True)
m=json.loads((a.out/'entry.json').read_text());assert m['slave_sha256']=='bad57261d0593f51eb42c79dde6e53a9d15c0154d52d0831ec8edfc8f825469a'
if a.twins:subprocess.run([sys.executable,'tools/w3_twin_check.py',str(a.out)],check=True)
