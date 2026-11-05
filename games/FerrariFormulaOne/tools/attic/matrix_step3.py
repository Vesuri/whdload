#!/usr/bin/env python3
from pathlib import Path
import os,json,subprocess,sys
r=Path(__file__).resolve().parents[1]
ce='--uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_cycle_exact=true'
profiles={
 'a500':dict(CPU='68000',AMIGA_MODEL='A500',CHIP_KB='512',SLOW_KB='1536',FAST_KB='0'),
 'a500-fast':dict(CPU='68000',AMIGA_MODEL='A500',CHIP_KB='512',SLOW_KB='1536',FAST_KB='2048'),
 'a1200':dict(CPU='68EC020',AMIGA_MODEL='A1200',CHIP_KB='2048',SLOW_KB='0',FAST_KB='0'),
 'a1200-fast':dict(CPU='68EC020',AMIGA_MODEL='A1200',CHIP_KB='2048',SLOW_KB='0',FAST_KB='4096'),
 '030-50':dict(CPU='68030-NOMMU',AMIGA_MODEL='A1200',CHIP_KB='2048',SLOW_KB='0',FAST_KB='8192',EXTRA_ARGS=ce+' --uae_cpu_frequency=50000000'),
 '040-25':dict(CPU='68040-NOMMU',AMIGA_MODEL='A4000/040',CHIP_KB='2048',SLOW_KB='0',FAST_KB='8192',EXTRA_ARGS=ce+' --uae_cpu_frequency=25000000'),
 '040-40':dict(CPU='68040-NOMMU',AMIGA_MODEL='A4000/040',CHIP_KB='2048',SLOW_KB='0',FAST_KB='8192',EXTRA_ARGS=ce+' --uae_cpu_frequency=40000000'),
 '060-50':dict(CPU='68060-NOMMU',AMIGA_MODEL='A4000/040',CHIP_KB='2048',SLOW_KB='0',FAST_KB='8192',EXTRA_ARGS=ce+' --uae_cpu_frequency=50000000')}
(r/'manifest/step3-profiles.json').write_text(json.dumps(profiles,indent=2)+'\n')
for profile in (sys.argv[1:] or ['a500','a1200','a1200-fast']):
 for arm in (0,1):
  for rep in ('a','b'):
   name=f'{profile}-c{arm}-{rep}';p=r/'tmp/step3'/name
   if (p/'result.json').exists() and json.loads((p/'result.json').read_text()).get('status')=='complete':continue
   e=dict(os.environ,**profiles[profile],WHD_ARGS=f'CUSTOM1={arm}',FIELDS='1000',OBSERVE='survey' if profile in ('a500','a500-fast','a1200','a1200-fast') else 'census')
   if profile not in ('a500','a500-fast'):e['KICKSTART']=os.environ['KICKSTART_A1200']
   if profile in ('a1200','a1200-fast','030-50'):e['APROF']='1'
   else:e.pop('APROF',None)
   print('START',name,flush=True)
   try:subprocess.run([sys.executable,str(r/'tools/measure_step3.py'),name],env=e,check=True,timeout=280)
   except (subprocess.CalledProcessError,subprocess.TimeoutExpired) as ex:
    print('FAILED',name,ex,flush=True);break
   subprocess.run([sys.executable,str(r/'tools/analyze_step3.py'),name],check=True)
