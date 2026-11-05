from pathlib import Path
import sys,subprocess,os
r=Path(__file__).resolve().parents[1]
e=dict(os.environ,EXCLUDE_PACING='1',DROP_UPDATES='1',MAX_UPDATES='18')
for name in sys.argv[1:]:
 for tool,args in [('analyze_step5_profile.py',[]),('percar_step5_profile.py',['0','0']),('classify_step5_profile.py',['0','0'])]:
  with (r/'tmp/step5'/name/(tool+'.log')).open('w') as out:
   subprocess.run([sys.executable,str(r/'tools'/tool),name]+args,env=e,stdout=out,check=True)
 subprocess.run([sys.executable,str(r/'tools/audit_step5_c1_profile.py'),name],check=True)
