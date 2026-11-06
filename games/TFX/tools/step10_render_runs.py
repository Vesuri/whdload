"""Sequential renderer validation: one owned emulator/debugger at a time."""
import os,sys,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];dev=root;out=Path(sys.argv[1]).resolve()
private=dev/'tmp/step9-emulator/fs-uae/fs-uae'
def call(tool,name,**extra):
 e=dict(os.environ,FSUAE=str(private));e.update({k:str(v) for k,v in extra.items()})
 subprocess.run([sys.executable,str(dev/'tools'/tool),str(out/name)],env=e,cwd=root,check=True)
call('step10_scene.py','baseline-scene',SCENE_NOMMU=1,TEST_SEED=dev/'tmp/step10/baseline-seed')
call('step10_scene.py','fills-scene',SCENE_NOMMU=1)
call('step10_scene.py','original-scene',SCENE_NOMMU=1,CUSTOM4=22)
call('step9_profile.py','fills-profile')
call('step9_profile.py','fills-profile-repeat',TEST_SEED=out/'fills-profile-seed')
