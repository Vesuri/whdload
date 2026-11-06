"""Final build verification. Record failed replay gates without hiding other checks."""
import os,sys,subprocess,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];dev=root;out=Path(sys.argv[1]).resolve();private=dev/'tmp/step9-emulator/fs-uae/fs-uae';results={}
def call(tool,name,*args,**extra):
 e=dict(os.environ,FSUAE=str(private));e.update({k:str(v) for k,v in extra.items()})
 r=subprocess.run([sys.executable,str(dev/'tools'/tool),str(out/name),*args],env=e,cwd=root)
 results[name]=r.returncode;out.mkdir(exist_ok=True,parents=True);(out/'run-status.json').write_text(json.dumps(results,indent=2));return r.returncode
call('step10_scene.py','scene',SCENE_NOMMU=1)
call('step10_scene.py','original-scene',SCENE_NOMMU=1,CUSTOM4=22)
for c4,label in [(18,'default'),(50,'uncapped'),(82,'oneframe')]:
 call('step10_profile.py',label+'-profile',CUSTOM4=c4)
 call('step10_profile.py',label+'-repeat',CUSTOM4=c4,TEST_SEED=out/(label+'-profile-seed'))
call('test_frame_options.py','options')
call('test_render_fills.py','fills',SELECTED_ONLY=1)
call('step8_regression.py','regression',FSUAE=Path.home()/'.local/share/amiga/fs-uae-arm/fs-uae')
for cpu,c4 in [('040',114),('040',118),('030',114),('060',114)]:call('audit_step10_options.py',f'gate-{cpu}-{c4}',cpu,str(c4))
print('Final statuses',results,flush=True)
