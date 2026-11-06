#!/usr/bin/env python3
"""Run sequentially: the harness owns one emulator/debugger session."""
import os,sys,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];dev=root;out=Path(sys.argv[1]).resolve();private=dev/'tmp/step7-emulator/fs-uae/fs-uae'
def call(tool,name,*args,**env):
 e=dict(os.environ,FSUAE=str(private));e.update({k:str(v) for k,v in env.items()});subprocess.run([sys.executable,str(dev/'tools'/tool),str(out/name),*args],cwd=root,env=e,check=True)
call('step7_window.py','baseline-window',TEST_SEED=dev/'tmp/step8/baseline-window-seed')
call('step7_window.py','final-window')
call('step7_window.py','final-window-repeat',TEST_SEED=out/'final-window-seed')
call('step8_audit.py','final-audit-040')
scene=dev/'tmp/step8-emulator/fs-uae/fs-uae'
call('step8_scene.py','baseline-scene-latched',FSUAE=scene,SCENE_NOMMU=1,TEST_SEED=dev/'tmp/step8/baseline-window-seed')
call('step8_scene.py','final-scene-latched',FSUAE=scene,SCENE_NOMMU=1,TEST_SEED=out/'final-window-seed')
call('step8_audit.py','final-audit-original',CUSTOM4=30)
call('step8_regression.py','final-regression',FSUAE=Path.home()/'.local/share/amiga/fs-uae-arm/fs-uae')
subprocess.run([sys.executable,str(dev/'tools/check_step8.py'),str(out)],cwd=root,check=True)
