#!/usr/bin/env python3
"""Step 5: observe the frozen baseline with a private NOMMU cost observer."""
import os,sys,json,shutil
from pathlib import Path
from baseline_matrix import observer,VARIANTS,ROOT,run
out=Path(sys.argv[1]).resolve(); os.chdir(ROOT); seed=ROOT/'tmp/step4-matrix/seed-newfpu'
v=dict(VARIANTS['newfpu'],extra_args='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true',expected_cpu=dict(cpu=68040,frequency=40000000,mmu=0,fpu=68040))
if '--strict-fpu' in sys.argv:
 v['extra_args']+=' --uae_fpu_no_unimplemented=true'
 seed=ROOT/'tmp/step5/seed-strict'
def capture(cmd,dump,bases,hs,out):
 started=False
 def observed_dump(name,addr,size):
  nonlocal started
  if name=='start-hunk0.bin':
   cmd(f'monitor tfxstart {bases[0]}');started=True
  if name=='end-hunk0.bin':
   assert started;cmd(f'monitor tfxsave {out}/profile.csv')
  return dump(name,addr,size)
 observer(v)(cmd,observed_dump,bases,hs,out)
 dump('chip.bin',0,0x200000)
 dump('fast.bin',0x40000000,0x2000000)
run('040',out,seed,capture,v)
for f in ['profile_flight.py','baseline_matrix.py','install_profile_observer.py']:shutil.copy(ROOT/'tools'/f,out/f)
