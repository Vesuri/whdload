import os,subprocess,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];os.chdir(root)
base=dict(os.environ,CPU='68EC020',AMIGA_MODEL='A1200',CHIP_KB='2048',FAST_KB='4096',SLOW_KB='0',KICKSTART=str(Path.home()/'.local/share/amiga/Kickstarts/kick40068.A1200'))
cases=[('020-zero-off',dict(WHD_ARGS='CUSTOM1=1 CUSTOM2=0 CUSTOM3=1 CUSTOM4=168 CUSTOM5=7',FIELDS='8',SKIP_FIELDS='300')),('020-zero-on',dict(WHD_ARGS='CUSTOM1=1 CUSTOM2=1 CUSTOM3=1 CUSTOM4=168 CUSTOM5=7',FIELDS='8',SKIP_FIELDS='300')),('020-fraction',dict(WHD_ARGS='CUSTOM1=1 CUSTOM2=1 CUSTOM3=1 CUSTOM4=32936 CUSTOM5=7',FIELDS='20',SKIP_FIELDS='300')),('020-moving',dict(WHD_ARGS='CUSTOM1=0 CUSTOM2=1 CUSTOM3=1 CUSTOM4=0 CUSTOM5=23',FIELDS='100',SKIP_FIELDS='2000')),('000-moving',dict(CPU='68000',AMIGA_MODEL='A500',CHIP_KB='512',FAST_KB='0',SLOW_KB='1536',KICKSTART=str(Path.home()/'.local/share/amiga/Kickstarts/kick40063.A600'),WHD_ARGS='CUSTOM1=0 CUSTOM2=1 CUSTOM3=1 CUSTOM4=0 CUSTOM5=23',FIELDS='100',SKIP_FIELDS='2000'))]
if os.environ.get("ONLY_CASE"):cases=[c for c in cases if c[0]==os.environ["ONLY_CASE"]]
for name,options in cases:
 cap=Path('tmp/phase8/beta2-'+name);cap.mkdir(exist_ok=True)
 print('START',name,flush=True)
 with (cap/'run.log').open('w') as log:subprocess.run(['bash','tools/fixed_window.sh',str(cap)],env=dict(base,**options),stdout=log,stderr=subprocess.STDOUT,check=True)
 with (cap/'audit.log').open('w') as log:
  commands=[['tools/phase6_units.py',str(cap),str(cap/'slave.slave.lst')],['tools/check_phase6.py',str(cap)],['tools/buffer_audit.py',str(cap)]]
  if 'off' not in name:
   commands += [['tools/phase7_tables.py',str(cap)]]
   if name.startswith('020'):commands += [['tools/phase8_projection_audit.py',str(cap)]]
  if name=='020-zero-on':commands += [['tools/phase7_pixels.py','tmp/phase8/beta2-020-zero-off',str(cap)]]
  if 'moving' in name:commands += [['tools/phase7_cost.py',str(cap)],['tools/phase6_latch_audit.py',str(cap)]]
  for command in commands:subprocess.run(['python3',*command],stdout=log,stderr=subprocess.STDOUT,check=True)
 assert json.loads((cap/'buffer-audit.json').read_text())['display_writes']==0
 if name=='000-moving':assert json.loads((cap/'phase7-cost.json').read_text())['helper_percent']<=3.0
 print('PASS',name,flush=True)
