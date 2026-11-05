from pathlib import Path
import os,subprocess,sys
r=Path(__file__).resolve().parents[1]
env=dict(os.environ,H5_BUILD=str(r/'tmp/build/render-h5-oracle-owned'),C1_VARIANT='owned',RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache')
print('Starting already-owned pixel/CCR oracle',flush=True)
with (r/'tmp/h5-oracle-owned.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/test_h5_oracle.py'),'a1200-fast'],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
for mode,tag in [('profile','candidate'),('census','census')]:
 print('Starting ordinary trace validation',mode,flush=True)
 env=dict(os.environ,H5_BUILD=str(r/'tmp/build/render-h5'),C1_VARIANT='h5-'+tag,RENDER_CAPTURE=mode,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache')
 with (r/f'tmp/h5-{mode}-ordinary.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/capture_h5_profile.py'),'a1200-fast'],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
for script,args in [('analyze_render_profile.py',[str(r/'tmp/step5/c4-q03-render-profile-a1200-fast-h5-candidate')]),('analyze_h3_waits.py',[str(r/'tmp/step5/c4-q03-render-profile-a1200-fast-h5-candidate')]),('analyze_h3_calls.py',[str(r/'tmp/step5/c4-q03-render-profile-a1200-fast-h5-candidate')]),('analyze_h5_text.py',[str(r/'tmp/step5/c4-q03-render-profile-a1200-fast-h5-candidate')]),('audit_h5_census.py',[]),('audit_h5_dma.py',[])]:
 subprocess.run([sys.executable,str(r/'tools'/script),*args],check=True)
for tag in ['candidate','matched-candidate']:
 path=r/f'tmp/step5/c4-q03-render-profile-a1200-fast-h5-{tag}'
 for script in ['analyze_h5_bitmap.py','audit_h5_cpu_display.py','audit_h5_irq.py']:
  subprocess.run([sys.executable,str(r/'tools'/script),str(path)],check=True)
for option in ['0','1']:
 print('Starting legacy comparison CUSTOM1='+option,flush=True)
 with (r/f'tmp/h5-legacy-c{option}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/test_h5_legacy.py')],env=dict(os.environ,RELEASE_CUSTOM1=option,RELEASE_PROFILES='a500,a500-fast,a1200,a1200-fast'),stdout=f,stderr=subprocess.STDOUT,check=True)
 print('Passed legacy option',option,flush=True)
with (r/'tmp/h5-fault.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/test_h5_fault.py'),'a1200-fast'],stdout=f,stderr=subprocess.STDOUT,check=True)
print('Passed signature failure',flush=True)
