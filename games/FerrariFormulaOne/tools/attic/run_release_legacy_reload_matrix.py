from pathlib import Path
import subprocess,sys,os,json
r=Path(__file__).resolve().parents[1];rows=[]
for profile in ('a500','a500-fast','a1200','a1200-fast'):
 for option in (0,1):
  name=f'c4-q03-release-legacy-live-{profile}-custom1-{option}';out=r/'tmp/step5'/name;env=dict(os.environ,C1_VARIANT=f'custom1-{option}',RELEASE_WHD_ARGS=f'CUSTOM1={option} CUSTOM2=0 ConfigDelay=0')
  evidence=out/'result.json'
  if evidence.exists() and json.loads(evidence.read_text()).get('native_original_reference_exact'):
   rows.append(dict(profile=profile,custom1=option,passed=True,evidence=str(evidence.relative_to(r))));print('Already passed',name,flush=True);continue
  print('RUN',name,flush=True)
  with (r/'tmp/step5'/f'{name}.log').open('w') as f:result=subprocess.run([sys.executable,str(r/'tools/run_release_legacy_reload.py'),profile],env=env,stdout=f,stderr=subprocess.STDOUT)
  evidence=out/'result.json';data=json.loads(evidence.read_text()) if evidence.exists() else {};passed=result.returncode==0 and data.get('status')=='passed' and data.get('reload_patch_words_exact')==1005
  rows.append(dict(profile=profile,custom1=option,passed=passed,evidence=str(evidence.relative_to(r))))
  (r/'manifest/release-disabled-reloads.json').write_text(json.dumps(dict(status='passed' if len(rows)==8 and all(x['passed'] for x in rows) else 'in-progress',results=rows),indent=2)+'\n')
  print('DONE',name,passed,flush=True)
  if not passed:raise SystemExit(1)
