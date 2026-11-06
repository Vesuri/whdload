#!/usr/bin/env python3
"""Strict current-slave profile; unique seed for each changed build."""
import os,sys,shutil
from pathlib import Path
from baseline_matrix import ROOT,run,observer,VARIANTS
out=Path(sys.argv[1]).resolve();os.chdir(ROOT)
seed=Path(os.environ.get('TEST_SEED',str(out.parent/(out.name+'-seed'))))
v=dict(VARIANTS['newfpu'],extra_args='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true',expected_cpu=dict(cpu=68040,frequency=40000000,mmu=0,fpu=68040))
def capture(cmd,dump,bases,hs,out):
 def observed_dump(name,addr,size):
  if name=='start-hunk0.bin':cmd(f'monitor tfxstart {bases[0]}')
  if name=='end-hunk0.bin':cmd(f'monitor tfxsave {out}/profile.csv')
  return dump(name,addr,size)
 observer(v)(cmd,observed_dump,bases,hs,out)
 dump('chip.bin',0,0x200000);dump('fast.bin',0x40000000,0x2000000)
run('040',out,seed,capture,v)
shutil.copy(__file__,out/Path(__file__).name)
