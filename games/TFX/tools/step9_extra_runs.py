import os,sys,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=root/'tmp/step9';backend=str(root/'tmp/step9-emulator/fs-uae/fs-uae')
for script,name,opts in [('test_native_modes.py','modes',{}),('step9_scene.py','controlled-off',{'CUSTOM5':'1','SCENE_NOMMU':'1'}),('step9_scene.py','controlled-on',{'CUSTOM5':'0','SCENE_NOMMU':'1'})]:
 with (out/(name+'.log')).open('w') as f:r=subprocess.run([sys.executable,str(root/'tools'/script),str(out/name)],env=dict(os.environ,FSUAE=backend,**opts),stdout=f,stderr=subprocess.STDOUT)
 print(name,'exit',r.returncode,flush=True)
