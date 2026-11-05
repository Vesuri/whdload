import os,subprocess,sys,json
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae')
for label,slave in [('before',root/'tmp/release-3.0b-visual-final/RoadRash.slave'),('after',root/'src/RoadRash.slave')]:
 out=root/f'tmp/merge-replay-{label}';out.mkdir()
 env=config('040-25');env.update(SLAVE=str(slave),WHD_ARGS='Cache CUSTOM2=1',DEBUG_PORT='24411');env['EXTRA_ARGS']+=' --uae_cpu_data_cache=true'
 try:
  with (out/'run.log').open('w') as log:
   p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/replay_a.py',str(out),'--normal','--sample-step','20'],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
 finally:cleanup(out)
 print(label,p.returncode,flush=True)
 assert p.returncode==0
