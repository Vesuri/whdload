#!/usr/bin/env python3
"""Final same-build frozen pixel oracles and nonzero projection edge poses."""
import os,subprocess
from pathlib import Path
os.chdir(Path(__file__).resolve().parents[1])
base=dict(os.environ,CPU='68000',AMIGA_MODEL='A500',CHIP_KB='512',FAST_KB='0',SLOW_KB='1536',FIELDS='8',SKIP_FIELDS='300',BOOT_HUNK='0xcf8210')
cases=[(f'zero-s{s}-{c}',s,0,c) for s in (0,3,5,7) for c in (0,1)]+[(f'fraction-s{s}-f{f}',s,f,1) for s,f in ((5,1),(5,128),(5,255),(3,128))]
for name,scene,fraction,c2 in cases:
 out=Path('tmp/phase7/accepted-'+name);out.mkdir(parents=True,exist_ok=True)
 c4=8+scene*32+fraction*256
 env=dict(base,WHD_ARGS=f'CUSTOM1=1 CUSTOM2={c2} CUSTOM3=1 CUSTOM4={c4} CUSTOM5=7')
 print('START',name,flush=True)
 with (out/'run.log').open('w') as log:subprocess.run(['bash','tools/fixed_window.sh',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=400)
 with (out/'acceptance.log').open('w') as log:
  for args in [['tools/phase6_units.py',str(out),str(out/'slave.slave.lst')],['tools/check_phase6.py',str(out)],['tools/buffer_audit.py',str(out)]]+([['tools/phase7_tables.py',str(out)]] if c2 else []):
   subprocess.run(['python3',*args],stdout=log,stderr=subprocess.STDOUT,check=True)
  if c2 and fraction==0:subprocess.run(['python3','tools/phase7_pixels.py',f'tmp/phase7/accepted-zero-s{scene}-0',str(out)],stdout=log,stderr=subprocess.STDOUT,check=True)
 print('PASS',name,flush=True)
