import os,subprocess,json
from pathlib import Path
os.chdir(Path(__file__).resolve().parents[1])
cases=[('zero-off',dict(WHD_ARGS='CUSTOM1=1 CUSTOM2=0 CUSTOM3=1 CUSTOM4=168 CUSTOM5=7',FIELDS='8',SKIP_FIELDS='300')),('moving',dict(WHD_ARGS='CUSTOM2=1 CUSTOM3=1 CUSTOM5=7',FIELDS='100',SKIP_FIELDS='2000')),('fraction',dict(WHD_ARGS='CUSTOM1=1 CUSTOM2=1 CUSTOM3=1 CUSTOM4=32936 CUSTOM5=7',FIELDS='20',SKIP_FIELDS='300'))]
for name,options in cases:
 cap=Path('tmp/phase8/followup-'+name);cap.mkdir(exist_ok=True)
 print('START',name,flush=True)
 with (cap/'run.log').open('w') as log:
  subprocess.run(['bash','tools/fixed_window.sh',str(cap)],env=dict(os.environ,**options),stdout=log,stderr=subprocess.STDOUT,check=True)
 with (cap/'audit.log').open('w') as log:
  for command in [['tools/phase6_units.py',str(cap),str(cap/'slave.slave.lst')],['tools/check_phase6.py',str(cap)],['tools/buffer_audit.py',str(cap)]]:
   subprocess.run(['python3',*command],stdout=log,stderr=subprocess.STDOUT,check=True)
  if name=='zero-off':subprocess.run(['python3','tools/phase7_pixels.py',str(cap),'tmp/phase8/followup-zero-on'],stdout=log,stderr=subprocess.STDOUT,check=True)
  else:
   subprocess.run(['python3','tools/phase7_tables.py',str(cap)],stdout=log,stderr=subprocess.STDOUT,check=True)
   subprocess.run(['python3','tools/phase7_cost.py',str(cap)],stdout=log,stderr=subprocess.STDOUT,check=True)
 print('PASS',name,flush=True)
