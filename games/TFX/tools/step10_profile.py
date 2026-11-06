"""Strict profiling with optional pre-window restore of selected original fill entries."""
import os,sys,struct,shutil
from pathlib import Path
from baseline_matrix import ROOT,run,observer,VARIANTS
out=Path(sys.argv[1]).resolve();os.chdir(ROOT)
v=dict(VARIANTS['newfpu'],custom4=int(os.environ.get('CUSTOM4','18')),extra_args='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true',expected_cpu=dict(cpu=68040,frequency=40000000,mmu=0,fpu=68040))
def capture(cmd,dump,bases,hs,out):
 for name in os.environ.get('RESTORE_FILLS','').split(','):
  if not name:continue
  offset={'normal':0x6c4f2,'gouraud':0x4f840,'texture':0x4f9f8}[name];data=hs[0]['bytes'][offset:offset+6]
  if name=='normal':data=data[:2]+struct.pack('>I',bases[0]+0x6c4c0)
  cmd(f'monitor tfxmem {bases[0]+offset:x} {data.hex()}');assert dump(name+'-restored.bin',bases[0]+offset,6)==data
 def observed_dump(name,addr,size):
  if name=='start-hunk0.bin':cmd(f'monitor tfxstart {bases[0]}')
  if name=='end-hunk0.bin':cmd(f'monitor tfxsave {out}/profile.csv')
  return dump(name,addr,size)
 observer(v)(cmd,observed_dump,bases,hs,out)
 dump('chip.bin',0,0x200000);dump('fast.bin',0x40000000,0x2000000)
run('040',out,Path(os.environ.get('TEST_SEED',str(out)+'-seed')),capture,v)
shutil.copy(__file__,out/Path(__file__).name)
