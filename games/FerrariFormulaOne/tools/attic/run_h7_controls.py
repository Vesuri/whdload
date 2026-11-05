from pathlib import Path
import os,sys,json,subprocess
r=Path(__file__).resolve().parents[1];b=r/'tmp/build/render-h7'
launch=json.loads((r/'tmp/step5/c4-q03-controls-a1200-fast-fixed-040-mmu-32m-controls/result.json').read_text());over={k:launch['launch'][k] for k in ['CPU','AMIGA_MODEL','CHIP_KB','SLOW_KB','FAST_KB']};over['EXTRA_ARGS']=launch['extra_args'];over['DRIVE_Z3_KB']='32768'
for script,tag,extra in [('test_drive_controls.py','controls',{'DRIVE_CLUTCH':'1'}),('run_h5_manual.py','manual',{}),('test_drive_controls.py','040-mmu-32m',{'DRIVE_CLUTCH':'1','RELEASE_FSUAE':str(r/'tmp/step5-frame-observer-build/fs-uae'),'RELEASE_PROFILE_OVERRIDES':json.dumps(over)})]:
 print('CONTROLS',tag,flush=True)
 env=dict(os.environ,H5_BUILD=str(b),DRIVE_SLAVE=str(b/'FerrariFormulaOne.slave'),C1_VARIANT='h7-'+tag,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache');env.update(extra)
 with (r/f'tmp/h7-{tag}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools'/script),'a1200-fast'],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
for option in ['0','1']:
 print('LEGACY',option,flush=True)
 with (r/f'tmp/h7-legacy-c{option}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/test_h7_legacy.py')],env=dict(os.environ,RELEASE_CUSTOM1=option,RELEASE_PROFILES='a500,a500-fast,a1200,a1200-fast'),stdout=f,stderr=subprocess.STDOUT,check=True)
