#!/usr/bin/env python3
"""Final raw-input full laps, with retained transport failures and strict checks."""
import os,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];os.chdir(root)
for period,c4 in [('p6',4),('p2',0)]:
 out=Path('tmp/phase6')/('lap-final-'+period)
 assert not out.exists(),out
 env=os.environ|dict(AMIGA_MODEL='A1200',CPU='68EC020',CHIP_KB='2048',FAST_KB='4096',SLOW_KB='0',KICKSTART=str(Path.home()/'.local/share/amiga/Kickstarts/kick40068.A1200'),EXTRA_ARGS='',WHD_ARGS=f'CUSTOM1=0 CUSTOM2=1 CUSTOM3=1 CUSTOM4={c4} CUSTOM5=23',SKIP_FIELDS='0',PHASE3_FIELDS='10000',LAP_ONLY='1',BOOT_HUNK='0x5791d8',EVENT_AUDIT='0')
 print('START',out,flush=True)
 for attempt in range(3):
  try:
   subprocess.run(['bash','tools/fixed_window.sh',str(out)],env=env,check=True,timeout=900)
   break
  except subprocess.CalledProcessError:
   if attempt==2 or not any(p.exists() and 'Invalid hex digit' in p.read_text() for p in [out/'dump-gdb.txt',out/'state/gdb.txt']):raise
   rejected=out.with_name(out.name+f'-transport-rejected-{attempt+1}')
   assert not rejected.exists();out.rename(rejected)
   print('REJECTED debugger transport; fresh boot retry:',rejected,flush=True)
 for script,args in [('phase6_units.py',[str(out),str(out/'slave.slave.lst')]),('check_phase6.py',[str(out)])]:
  subprocess.run(['python3','tools/'+script,*args],check=True)
 print('DONE',out,flush=True)
subprocess.run(['python3','tools/phase6_lap_report.py','tmp/phase6/lap-final-p6','tmp/phase6/lap-final-p2'],check=True)
with open('tmp/phase6/lap-final-native-oracle.txt','w') as log:
 subprocess.run(['python3','tools/phase6_compare.py','tmp/phase6/pilot-record-v2','tmp/phase6/lap-final-p6','--assert-core','--match-native-fields','--output','tmp/phase6/lap-final-native-oracle.json'],stdout=log,check=True)
print('Full laps and native-period oracle PASS',flush=True)
