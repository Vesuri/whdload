from pathlib import Path
import os,sys,subprocess,json
r=Path(__file__).resolve().parents[1]
def run(script,args,tag,extra={}):
 print('RUN',tag,flush=True)
 with (r/f'tmp/h9-{tag}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools'/script),*args],env=dict(os.environ,**extra),stdout=f,stderr=subprocess.STDOUT,check=True)
 print('PASS',tag,flush=True)
run('run_h9_checks.py',['tracecontrol'],'tracecontrol')
run('analyze_h9_trace.py',[str(r/'tmp/step5/hi25-profile-040-40-bce-h9-grid-control')],'control-analysis')
run('run_h9_checks.py',['exact'],'exact')
run('run_h7_live.py',['040-40'],'live',dict(H5_BUILD=str(r/'tmp/build/render-h9'),C1_VARIANT='h9-candidate'))
run('test_h9_fault.py',['a1200-fast'],'fault')
for option in ['0','1']:run('test_h9_legacy.py',[],'legacy-'+option,dict(RELEASE_CUSTOM1=option,RELEASE_PROFILES='a1200-fast'))
