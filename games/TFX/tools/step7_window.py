#!/usr/bin/env python3
import sys,os
from pathlib import Path
from baseline_matrix import ROOT,run,observer,VARIANTS
out=Path(sys.argv[1]).resolve();os.chdir(ROOT)
v=dict(VARIANTS['newfpu'],extra_args='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true',expected_cpu=dict(cpu=68040,frequency=40000000,mmu=0,fpu=68040))
run('040',out,Path(os.environ['TEST_SEED']) if 'TEST_SEED' in os.environ else out.parent/(out.name+'-seed'),observer(v),v)
