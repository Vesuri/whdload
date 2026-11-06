"""Sequential final checks; only one project debugger session at a time."""
import os,sys,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=False)
def call(tool,dest,allow_failure=False,**extra):
 env=dict(os.environ,**extra)
 with (out/(dest+'.log')).open('w') as f:subprocess.run([sys.executable,str(root/'tools'/tool),str(out/dest)],env=env,stdout=f,stderr=subprocess.STDOUT,check=not allow_failure)
 print(dest,'complete',flush=True)
backend=str(root/'tmp/step9-emulator/fs-uae/fs-uae')
call('step9_profile.py','profile',FSUAE=backend)
call('step9_profile.py','profile-repeat',FSUAE=backend,TEST_SEED=str(out/'profile-seed'))
call('step8_scene.py','baseline-scene',FSUAE=backend,SCENE_NOMMU='1',TEST_SEED=str(root/'tmp/step8/final-window-seed'))
call('step8_scene.py','native-scene',FSUAE=backend,SCENE_NOMMU='1',TEST_SEED=str(out/'profile-seed'))
call('step8_regression.py','regression',allow_failure=True,FSUAE=os.path.expanduser('~/.local/share/amiga/fs-uae-arm/fs-uae'))

call('test_native_modes.py','modes',FSUAE=backend)
call('test_native_math.py','math-tests',FSUAE=backend)
subprocess.run([sys.executable,str(root/'tools/check_native_math.py'),str(out/'math-tests/results.json')],check=True)
call('step9_scene.py','controlled-off',FSUAE=backend,SCENE_NOMMU='1',CUSTOM5='1')
call('step9_scene.py','controlled-on',FSUAE=backend,SCENE_NOMMU='1',CUSTOM5='0')
print('All fixtures captured. Inspect regression/summary.json: failed raw/image gates are not waived.',flush=True)
