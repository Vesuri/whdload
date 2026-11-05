from pathlib import Path
import os,subprocess,sys,json
r=Path(__file__).resolve().parents[1]
def run(script,*args,**env):
 tag=script.removesuffix('.py')+'-'+env.get('C1_VARIANT','candidate')
 print('Starting',tag,flush=True)
 with (r/'tmp/step5'/('r3b-v1-'+tag+'.log')).open('w') as f:
  subprocess.run([sys.executable,str(r/'tools'/script),*args],env=os.environ|env,stdout=f,stderr=subprocess.STDOUT,check=True)
images={}
for scene in ('ab','start_grid_center','heavy_v2'):
 for arm in ('baseline-render','candidate'):run(f'capture_step5_c4_rotate_r3b_{scene}_images.py','a500',C1_VARIANT=arm)
 paths=[Path(f'tmp/step5/c4-rotate-r3b-v1-cleanframe-{scene.replace("_","-")}-a500-{a}-images/result.json') for a in ('baseline-render','candidate')]
 a,b=[json.loads((r/p).read_text()) for p in paths]
 assert a['frames']==b['frames'] and len(a['frames'])==10 and a['error']==b['error']==0,scene
 images[scene]=dict(arms=[str(p) for p in paths],frames=a['frames'])
 (r/'manifest/step5-c4-rotate-r3b-images.json').write_text(json.dumps(dict(status='in-progress',workloads=images),indent=2)+'\n')
(r/'manifest/step5-c4-rotate-r3b-images.json').write_text(json.dumps(dict(status='passed',workloads=images),indent=2)+'\n')
for arm in ('baseline-render','candidate'):run('capture_step5_c4_acceptance_fps.py','a500',C1_VARIANT=arm,C4_ACCEPT_BUILD='step5-c4-rotate-r3b-v1-ab')
for scene in ('start_grid_center','heavy_v2'):
 for arm in ('baseline-render','candidate','native'):run(f'capture_step5_c4_rotate_r3b_{scene}.py','a500',C1_VARIANT=arm,C4_HEAVY_FRAMES='300')
run('capture_step5_c4_rotate_r3b_elapsed.py','a500')
run('capture_step5_c4_rotate_r3b_exit.py','a500')
run('test_step5_c4_rotate_r3b_default.py')
print('R3b acceptance captures complete',flush=True)
