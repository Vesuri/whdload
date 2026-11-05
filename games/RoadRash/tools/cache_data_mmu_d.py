import os,subprocess,sys
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae')
for i,cell in enumerate(['040-mmu','060-mmu']):
 env=config(cell);env.update(SLAVE=str(root/'tmp/d-native-decrunch-build/RoadRash-verify.slave'),DEBUG_PORT=str(27360+i));env['WHD_ARGS']+=' CUSTOM2=1';env['EXTRA_ARGS']=env['EXTRA_ARGS'].replace('data_cache=false','data_cache=true')
 dest=root/'tmp'/('d-cache-data-enabled-'+cell);dest.mkdir()
 try:
  with (dest/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/cache_mmu_policy_c.py',str(dest)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
  print(cell,p.returncode,flush=True)
 except subprocess.TimeoutExpired:print(cell,'timeout',flush=True)
 finally:cleanup(dest)
