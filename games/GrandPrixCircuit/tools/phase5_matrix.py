#!/usr/bin/env python3
import os,subprocess,json,time
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=root/'tmp/phase5';out.mkdir(exist_ok=True)
env0=dict(os.environ,SKIP_FIELDS='300',FIELDS='1000',SWAP_ONLY='1')
models={'a500':dict(CPU='68000',AMIGA_MODEL='A500',CHIP_KB='512',FAST_KB='0',SLOW_KB='1536',KICKSTART=str(Path.home()/'.local/share/amiga/Kickstarts/kick40063.A600'),EXTRA_ARGS=''), 'a1200':dict(CPU='68EC020',AMIGA_MODEL='A1200',CHIP_KB='2048',FAST_KB='4096',SLOW_KB='0',KICKSTART=str(Path.home()/'.local/share/amiga/Kickstarts/kick40068.A1200'),EXTRA_ARGS=''), '68030':dict(CPU='68030',AMIGA_MODEL='A1200',CHIP_KB='2048',FAST_KB='4096',SLOW_KB='0',KICKSTART=str(Path.home()/'.local/share/amiga/Kickstarts/kick40068.A1200'),EXTRA_ARGS='--uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency=25000000 --uae_cpu_cycle_exact=true')}
arms={'original':(0,2),'fixed':(0,0),'enhanced':(1,0)}
def run(name,m,arm,trace=False):
 c2,c4=arms[arm];env=dict(env0,**models[m],WHD_ARGS=f'CUSTOM1=0 CUSTOM2={c2} CUSTOM3=1 CUSTOM4={c4} CUSTOM5=1')
 if trace:env.update(FIELDS='100',SWAP_ONLY='0')
 with (out/(name+'.log')).open('w') as log:
  print('START',name,flush=True)
  subprocess.run([str(root/'tools/fixed_window.sh'),'tmp/phase5/'+name],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
 print('DONE',name,flush=True)
for m,arm in [('a1200','original'),('a1200','fixed'),('a1200','enhanced'),('a500','fixed'),('a500','enhanced')]:run('trace-'+m+'-'+arm,m,arm,True)
for m in models:
 for arm in arms:
  for boot in (1,2):run(f'{m}-{arm}-{boot}',m,arm)
print('COMPLETE',flush=True)
