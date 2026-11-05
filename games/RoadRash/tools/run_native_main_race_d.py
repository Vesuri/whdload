from pathlib import Path
import os,sys,subprocess,json
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae')
for i,kind in enumerate(['reference','public']):
 out=root/f'tmp/d-native-main-race-{kind}';out.mkdir();env=config('a500-1m');env.update(FAST_KB='8192',SLAVE=str(root/f'tmp/d-native-main-{kind}-build/RoadRash-verify.slave'),DEBUG_PORT=str(27558+i),WHD_ARGS='CUSTOM2=1',EXTRA_ARGS='--uae_cpu_speed=max --uae_cpu_cycle_exact=false --uae_cpu_memory_cycle_exact=false --uae_blitter_cycle_exact=false')
 try:
  with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/native_main_race_d.py',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600)
 finally:cleanup(out)
 print(kind,p.returncode,flush=True);assert not p.returncode
r=[json.loads((root/f'tmp/d-native-main-race-{k}/race.json').read_text()) for k in ['reference','public']];assert r[0]==r[1];print('Native full race and restart equal',len(r[0]['points']),flush=True)
