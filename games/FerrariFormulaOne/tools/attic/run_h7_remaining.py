from pathlib import Path
import subprocess,sys
r=Path(__file__).resolve().parents[1]
for script,args in [('run_h7_remaining_correctness.py',[]),('run_h7_checks.py',['fps']),('run_h7_unload.py',[]),('run_h7_lifecycle.py',['candidate']),('run_h7_controls.py',[]),('run_h7_profiles.py',[])]:
 print('ACCEPTANCE GROUP',script,args,flush=True)
 subprocess.run([sys.executable,str(r/'tools'/script),*args],check=True)
print('ALL H7 ACCEPTANCE GROUPS COMPLETED',flush=True)
