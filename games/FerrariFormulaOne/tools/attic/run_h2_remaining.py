from pathlib import Path
import os,subprocess,sys
r=Path(__file__).resolve().parents[1]
for group in ['profiles','scenes','accelerated','controls','user-config']:
 subprocess.run([sys.executable,str(r/'tools/run_h2_checks.py'),group],check=True)
for option in ['0','1']:
 print('Starting CUSTOM2=0 legacy gate, CUSTOM1='+option,flush=True)
 with (r/f'tmp/h2-legacy-c{option}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/test_h2_legacy.py')],env=dict(os.environ,RELEASE_CUSTOM1=option,RELEASE_PROFILES='a500,a500-fast,a1200,a1200-fast' if option=='0' else 'a1200-fast'),stdout=f,stderr=subprocess.STDOUT,check=True)
 print('Passed legacy option',option,flush=True)
print('Starting signature-failure check',flush=True)
with (r/'tmp/h2-fault.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/test_h2_fault.py'),'a1200-fast'],stdout=f,stderr=subprocess.STDOUT,check=True)
print('Passed signature failure',flush=True)
