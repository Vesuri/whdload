from pathlib import Path
import subprocess,sys
r=Path(__file__).resolve().parents[1]
for script,args in [('run_h4_profile_pair.py',[]),('run_h4_checks.py',['scenes']),('run_h4_checks.py',['accelerated']),('run_h4_checks.py',['controls']),('run_h4_checks.py',['user-config']),('run_h4_final_checks.py',[])]:
 print('GROUP',script,args,flush=True)
 subprocess.run([sys.executable,str(r/'tools'/script),*args],check=True)
