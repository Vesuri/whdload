from pathlib import Path
import sys,subprocess,os,json
r=Path(__file__).resolve().parents[1]
for a in ['control','candidate']:
 b=r/('tmp/build/render-h11-sky-probe-grid-stable-frames'+('-control' if a=='control' else ''))
 env=dict(os.environ,H5_BUILD=str(b),DRIVE_MATCHED=str(b/'FerrariFormulaOne.slave'),DRIVE_SLAVE=str(b/'FerrariFormulaOne.slave'),C1_VARIANT='h11-sky-grid-'+a,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache')
 with (r/f'tmp/h11-sky-frames-{a}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/capture_h7_frames.py'),'040-40-bce'],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 print('captured',a,flush=True)
x=[json.loads((r/f'tmp/step5/c4-q03-h5-frame-production-040-40-bce-h11-sky-grid-{a}/result.json').read_text()) for a in ['control','candidate']]
print('FRAME EXACT',x[0]['frames']==x[1]['frames'],flush=True)
assert x[0]['frames']==x[1]['frames']
