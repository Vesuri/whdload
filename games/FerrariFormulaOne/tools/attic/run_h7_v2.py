from pathlib import Path
import subprocess,sys,json
r=Path(__file__).resolve().parents[1]
for script in ['build_h7_stable_frames.py','build_h7_ownership.py','build_h7_unload.py','build_h7_legacy.py']:
 print('BUILD',script,flush=True)
 with (r/f'tmp/v2-{script}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools'/script)],stdout=f,stderr=subprocess.STDOUT,check=True)
for script,args in [('run_h7_ownership.py',[]),('run_h7_checks.py',['smoke']),('run_h7_checks.py',['exact']),('run_h7_checks.py',['fps']),('run_h7_unload.py',[]),('run_h7_lifecycle.py',['candidate']),('run_h7_controls.py',[]),('run_h7_profiles.py',[])]:
 print('ACCEPTANCE GROUP',script,args,flush=True)
 subprocess.run([sys.executable,str(r/'tools'/script),*args],check=True)
print('ALL H7 V2 ACCEPTANCE GROUPS COMPLETED',flush=True)
