from pathlib import Path
import os,subprocess,sys
r=Path(__file__).resolve().parents[1]
for mode,tag in [('profile','candidate'),('census','census')]:
 print('Starting ordinary trace validation',mode,flush=True)
 env=dict(os.environ,H3_BUILD=str(r/'tmp/build/render-h3'),C1_VARIANT='h3-'+tag,RENDER_CAPTURE=mode,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache')
 with (r/f'tmp/h3-{mode}-ordinary.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/capture_h3_profile.py'),'a1200-fast'],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
for script,args in [('analyze_render_profile.py',[str(r/'tmp/step5/c4-q03-render-profile-a1200-fast-h3-candidate')]),('audit_h3_census.py',[]),('audit_h3_dma.py',[])]:
 subprocess.run([sys.executable,str(r/'tools'/script),*args],check=True)
for option in ['0','1']:
 print('Starting legacy comparison CUSTOM1='+option,flush=True)
 with (r/f'tmp/h3-legacy-c{option}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/test_h3_legacy.py')],env=dict(os.environ,RELEASE_CUSTOM1=option,RELEASE_PROFILES='a500,a500-fast,a1200,a1200-fast'),stdout=f,stderr=subprocess.STDOUT,check=True)
 print('Passed legacy option',option,flush=True)
with (r/'tmp/h3-fault.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/test_h3_fault.py'),'a1200-fast'],stdout=f,stderr=subprocess.STDOUT,check=True)
print('Passed signature failure',flush=True)
