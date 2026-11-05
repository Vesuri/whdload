import os,sys,subprocess
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();tag=sys.argv[1];out=root/f'tmp/loading-graphics-{tag}';out.mkdir()
env=config('040-mmu' if tag=='mmu-fixed' else '040-25');env.update(FSUAE=str(root/'tmp/b-gdb-passive-emulator/fs-uae'),SLAVE=str(root/'tmp/loading-dma-build/RoadRash.slave'),WHD_ARGS='Cache CUSTOM2='+('0' if tag.startswith('original') else '1'),DEBUG_PORT=sys.argv[2])
if tag=='mmu-fixed':env['EXTRA_ARGS']='--uae_cpu_data_cache=true --uae_uaeboard=full'
try:
 with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/loading_graphics_probe.py',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
finally:cleanup(out)
print(tag,p.returncode)
