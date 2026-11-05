#!/usr/bin/env python3
import os,subprocess,json
from pathlib import Path
os.chdir(Path(__file__).resolve().parents[1])
base=dict(os.environ,CPU='68000',AMIGA_MODEL='A500',CHIP_KB='512',FAST_KB='0',SLOW_KB='1536',FIELDS='100',BOOT_HUNK='0xcf8210',WHD_ARGS='CUSTOM1=0 CUSTOM2=1 CUSTOM3=1 CUSTOM4=0 CUSTOM5=23')
for skip,traffic in ((2000,0),(4000,0),(6000,0),(2000,1)):
 out=Path('tmp/phase7/accepted-moving-'+('traffic' if traffic else str(skip)));out.mkdir(parents=True,exist_ok=True)
 print('START',out.name,flush=True)
 with (out/'run.log').open('w') as log:subprocess.run(['bash','tools/fixed_window.sh',str(out)],env=dict(base,SKIP_FIELDS=str(skip),WHD_ARGS=f'CUSTOM1={traffic} CUSTOM2=1 CUSTOM3=1 CUSTOM4=0 CUSTOM5=23'),stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
 with (out/'acceptance.log').open('w') as log:
  for tool in ('phase6_units','check_phase6','phase7_tables','buffer_audit','phase7_cost','phase6_latch_audit'):
   args=['python3','tools/'+tool+'.py',str(out)]
   if tool=='phase6_units':args.append(str(out/'slave.slave.lst'))
   subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,check=True)
 assert json.loads((out/'buffer-audit.json').read_text())['display_writes']==0
 cost=json.loads((out/'phase7-cost.json').read_text());assert cost['helper_percent']<=3.0,cost
 print('PASS',out.name,cost['helper_percent'],flush=True)
normal=str(Path('tmp/build/release/GrandPrixCircuit.Slave').resolve())
for name,c2,cpu,chip,fast,slow,model in [('a500-off',0,'68000',512,0,1536,'A500'),('a500-on',1,'68000',512,0,1536,'A500'),('a1200-on',1,'68EC020',2048,4096,0,'A1200')]:
 env=dict(os.environ,OUT_ROOT='tmp/phase7',CELL=name,SECOND_RACE=str(c2),CUSTOM2_VALUE=str(c2),SLAVE=normal,WARP='1',DETERMINISTIC='1',JOY0='none',JOY1='none',CPU=cpu,CHIP_KB=str(chip),FAST_KB=str(fast),SLOW_KB=str(slow),AMIGA_MODEL=model,WHD_ARGS='CUSTOM2='+str(c2))
 print('START normal',name,flush=True)
 subprocess.run(['python3','tools/phase5_lifecycle.py'],env=env,check=True,timeout=600)
