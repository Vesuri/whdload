#!/usr/bin/env python3
"""Check pinned archives, all pristine extracted files, and runtime dependencies."""
import hashlib,json,os,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
 known=set()
 for manifest in ['inputs.sha256','runtime-inputs.sha256']:
  for line in (ROOT/'manifest'/manifest).read_text().splitlines():
   digest,name=line.split('  ',1);known.add(digest);p=Path(os.path.expandvars(name))
   if not p.is_absolute():p=ROOT/p
   if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise RuntimeError(f'input changed: {p}')
 for key in ('FSUAE','WHDLOAD_BINARY','KICKSTART','KICKSTART_A1200','KICKSTART13','RTB','WORKBENCH_ADF','FSUAE_COMMON'):
  if os.environ.get(key):
   p=Path(shutil.which(os.environ[key]) or os.environ[key])
   if hashlib.sha256(p.read_bytes()).hexdigest() not in known:raise RuntimeError(f'unpinned runtime override: {key}={p}')
 for manifest,folder in [('TestDrive.files.json','tmp/game/TestDrive'),('TestDrive_v1.3_0089.files.json','tmp/game/TestDrive_v1.3_0089')]:
  for name,digest in json.loads((ROOT/'manifest'/manifest).read_text()).items():
   p=ROOT/folder/name
   if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise RuntimeError(f'pristine extraction changed: {p}')
if __name__=='__main__':
 check();print('Pinned archives, pristine extractions and runtime dependencies: OK')
