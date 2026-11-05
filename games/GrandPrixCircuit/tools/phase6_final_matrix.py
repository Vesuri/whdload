#!/usr/bin/env python3
import os,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];os.chdir(root)
models={'a500':dict(CPU='68000',AMIGA_MODEL='A500',CHIP_KB='512',FAST_KB='0',SLOW_KB='1536',KICKSTART=str(Path.home()/'.local/share/amiga/Kickstarts/kick40063.A600'),EXTRA_ARGS=''),'a1200':dict(CPU='68EC020',AMIGA_MODEL='A1200',CHIP_KB='2048',FAST_KB='4096',SLOW_KB='0',KICKSTART=str(Path.home()/'.local/share/amiga/Kickstarts/kick40068.A1200'),EXTRA_ARGS=''),'68030':dict(CPU='68030',AMIGA_MODEL='A1200',CHIP_KB='2048',FAST_KB='4096',SLOW_KB='0',KICKSTART=str(Path.home()/'.local/share/amiga/Kickstarts/kick40068.A1200'),EXTRA_ARGS='--uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency=25000000 --uae_cpu_cycle_exact=true')}
def run(name,model,c2,c4,trace=False,c5=7,skip=None):
 out=Path('tmp/phase6')/name;assert not out.exists(),out
 env=os.environ|models[model]|dict(WHD_ARGS=f'CUSTOM1={int(trace)} CUSTOM2={c2} CUSTOM3=1 CUSTOM4={c4} CUSTOM5={c5}',SKIP_FIELDS=str(skip) if skip is not None else ('300' if trace else '0'),PHASE3_FIELDS='0' if trace else '720',FIELDS='100',STATE_STRIDE='1',EVENT_AUDIT='0',STOP_AT_LAP='0')
 print('START',name,flush=True)
 for attempt in range(3):
  try:
   subprocess.run(['bash','tools/fixed_window.sh',str(out)],env=env,check=True,timeout=600)
   break
  except subprocess.CalledProcessError:
   transcripts=[out/'state/gdb.txt',out/'dump-gdb.txt']
   if attempt==2 or not any(p.exists() and 'Invalid hex digit' in p.read_text() for p in transcripts):raise
   rejected=out.with_name(out.name+f'-transport-rejected-{attempt+1}')
   assert not rejected.exists(),rejected
   out.rename(rejected)
   print('REJECTED debugger transport; fresh boot retry:',str(rejected),flush=True)
 subprocess.run(['python3','tools/phase6_units.py',str(out),str(out/'slave.slave.lst')],check=True)
 subprocess.run(['python3','tools/check_phase6.py',str(out)],check=True)
 if trace:
  for script in ['phase6_step_cost.py','phase6_latch_audit.py','buffer_audit.py']:
   subprocess.run(['python3','tools/'+script,str(out)],check=True)
 print('DONE',name,flush=True)
for name,model,c2,c4 in [('core-a500-p6','a500',1,0),('core-030-p6','68030',1,4),('core-030-p2','68030',1,0)]:run(name,model,c2,c4)
for name,model,c2,c4 in [('cost-020-p6','a1200',1,4),('cost-020-p2','a1200',1,0),('cost-a500-p6','a500',1,0)]:run(name,model,c2,c4,True)
for name,event in [('overheat',1),('spin',3)]:run('cost-020-'+name,'a1200',1,0,True,7+256*event,160)
for model,c2 in [('a500',0),('a1200',1)]:
 name=model+('-on' if c2 else '-off');env=os.environ|models[model]|dict(CELL=name,SLAVE=str((root/'tmp/build/release/GrandPrixCircuit.Slave').resolve()),CUSTOM2_VALUE=str(c2),WHD_ARGS=f'CUSTOM2={c2}',DETERMINISTIC='1',JOY0='none',JOY1='none')
 print('START normal',name,flush=True)
 subprocess.run(['python3','tools/phase6_lifecycle.py'],env=env,check=True,timeout=600)
 subprocess.run(['python3','tools/check_phase6.py',str(Path('tmp/phase6')/('normal-'+name))],check=True)
 print('DONE normal',name,flush=True)
