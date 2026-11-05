#!/usr/bin/env python3
"""Capture fixed steady (step 8) and bank (step 24) VERIFY windows sequentially."""
import argparse,json,subprocess,sys
from pathlib import Path
import step_log
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
for name,step,chunks in [('steady',8,[100,50]),('bank',24,[100])]:
 step_log.advance(step)
 for i,n in enumerate(chunks):
  path=a.out/f'{name}-{i}'
  subprocess.run([sys.executable,'tools/capture_current.py','--out',str(path),'--fields',str(n)],check=True)
 print(name,step_log.collect()['records'][-1]['step'],flush=True)
