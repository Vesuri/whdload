import os,sys,subprocess,json
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae')
for kind in ['candidate']:
 build=root/f'tmp/f-scenes-final-{kind}-build';out=root/f'tmp/f-scenes-final-{kind}'
 env=dict(os.environ,RR_BUILD_OUT=str(build),VERIFY_DEFINES='-DC_SIMULATION -DVERIFY_C_SEED_RNG -DVERIFY_FRAME_PERIOD=4'+(' -DVERIFY_E_CONTROL' if kind=='reference' else ''))
 subprocess.run(['bash','tools/build.sh'],env=env,check=True,stdout=subprocess.DEVNULL)
 env=config('040-25');env.update(SLAVE=str(build/'RoadRash-verify.slave'),DEBUG_PORT='27832',WHD_ARGS='CUSTOM2=1');out.mkdir()
 try:
  with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/invoke_e.py','tools/scenes_e.py',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
 finally:cleanup(out)
 print(kind,p.returncode,flush=True);assert not p.returncode
x=json.loads((root/'tmp/e-scenes-v2-candidate/scenes.json').read_text());y=json.loads((root/'tmp/f-scenes-final-candidate/scenes.json').read_text());assert x==y,[(a,b) for a,b in zip(x,y) if a!=b];print('All scenes exact:',len(x),flush=True)
