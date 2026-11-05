import os,sys,subprocess
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();tag=sys.argv[1];out=root/f'tmp/graphics-menu-{tag}';out.mkdir(exist_ok=True)
env=config('040-mmu' if tag=='mmu-cache' else '040-25');env.update(FSUAE=str(root/'tmp/b-gdb-passive-emulator/fs-uae'),SLAVE=str(root/'tmp/graphics-dma-build/RoadRash.slave'),WHD_ARGS='Cache CUSTOM2=1',DEBUG_PORT=sys.argv[2])
if tag=='mmu-cache':env['EXTRA_ARGS']='--uae_cpu_data_cache=true --uae_uaeboard=full'
if tag=='nocache':env['WHD_ARGS']='NoCache CUSTOM2=1'
if tag=='reference':env['WHD_ARGS']='Cache CUSTOM2=0'
try:
 with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/graphics_reference.py' if tag=='reference' else 'tools/graphics_probe.py',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
finally:cleanup(out)
print(tag,p.returncode,flush=True)
