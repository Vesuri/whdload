from pathlib import Path
import os,subprocess,sys
r=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,str(r/'tools/run_h4_checks.py'),'frames-timing'],check=True)
for mode,tag in [('profile','candidate'),('census','census')]:
 print('Starting ordinary trace validation',mode,flush=True)
 env=dict(os.environ,H4_BUILD=str(r/'tmp/build/render-h4'),C1_VARIANT='h4-'+tag,RENDER_CAPTURE=mode,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache')
 with (r/f'tmp/h4-{mode}-ordinary.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/capture_h4_profile.py'),'a1200-fast'],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
for script,args in [('analyze_render_profile.py',[str(r/'tmp/step5/c4-q03-render-profile-a1200-fast-h4-candidate')]),('analyze_h3_waits.py',[str(r/'tmp/step5/c4-q03-render-profile-a1200-fast-h4-candidate')]),('analyze_h3_calls.py',[str(r/'tmp/step5/c4-q03-render-profile-a1200-fast-h4-candidate')]),('analyze_h4_text.py',[str(r/'tmp/step5/c4-q03-render-profile-a1200-fast-h4-candidate')]),('audit_h4_census.py',[]),('audit_h4_dma.py',[])]:
 subprocess.run([sys.executable,str(r/'tools'/script),*args],check=True)
for option in ['0','1']:
 print('Starting legacy comparison CUSTOM1='+option,flush=True)
 with (r/f'tmp/h4-legacy-c{option}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/test_h4_legacy.py')],env=dict(os.environ,RELEASE_CUSTOM1=option,RELEASE_PROFILES='a500,a500-fast,a1200,a1200-fast'),stdout=f,stderr=subprocess.STDOUT,check=True)
 print('Passed legacy option',option,flush=True)
with (r/'tmp/h4-fault.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/test_h4_fault.py'),'a1200-fast'],stdout=f,stderr=subprocess.STDOUT,check=True)
print('Passed signature failure',flush=True)
