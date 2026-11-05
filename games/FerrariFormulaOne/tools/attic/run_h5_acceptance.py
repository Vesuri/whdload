from pathlib import Path
import subprocess,sys
r=Path(__file__).resolve().parents[1]
for script,args in [('run_h5_oracles_ccr.py',[]),('run_h5_checks.py',['initial']),('run_h5_profile_pair.py',[]),('run_h5_checks.py',['scenes']),('run_h5_checks.py',['accelerated']),('run_h5_checks.py',['controls']),('run_h5_checks.py',['user-config']),('run_h5_final_checks.py',[])]:
 print('GROUP',script,args,flush=True)
 subprocess.run([sys.executable,str(r/'tools'/script),*args],check=True)
