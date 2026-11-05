from pathlib import Path
import os,subprocess,sys
r=Path(__file__).resolve().parents[1]
def run(script,*args,**env):
 tag=script.removesuffix('.py')+'-'+env.get('C1_VARIANT',env.get('C1_FIXTURE','default'))+'-'+env.get('C1_VERIFY','0');print(tag,flush=True)
 with (r/'tmp/step5'/('r3c-'+tag+'.log')).open('w') as f:subprocess.run([sys.executable,str(r/'tools'/script),*args],env=os.environ|env,stdout=f,stderr=subprocess.STDOUT,check=True)
run('build_step5_c4_mul_r3c_ab.py',C1_VERIFY='1')
for scene in ('heavy_v2','start_grid_center','heavy_v2_images','start_grid_center_images'):run('build_step5_c4_mul_r3c_'+scene+'.py')
for fixture in ('images','exit'):run('build_step5_c4_mul_r3c_lifecycle.py',C1_FIXTURE=fixture)
run('build_step5_c4_mul_r3c_default.py')
for arm in ('baseline-render','candidate'):run('capture_step5_c4_mul_r3c_states.py','a500',C1_VARIANT=arm)
run('analyze_step5_c4_mul_r3c_states.py','a500','baseline-render','candidate')
for arm in ('baseline-render','candidate'):
 name=f'c4-mul-r3c-v1-fullloop-a500-{arm}'
 run('capture_step5_c4_mul_r3c_fullloop.py','a500',C1_VARIANT=arm,FIELDS='100')
 for script,args in [('analyze_step5_profile.py',()),('percar_step5_profile.py',('0','0')),('classify_step5_profile.py',('0','0')),('audit_step5_c4_heavy_profile.py',()),('archive_profile_traces.py',())]:run(script,name,*args)
print('preflight passed',flush=True)
