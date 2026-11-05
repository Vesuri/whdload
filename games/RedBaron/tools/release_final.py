import os,subprocess,sys,json
from pathlib import Path
for mode,mask in [('developer',0),('normal',1)]:
 out=Path('tmp/prof/completion-f3-disabled-'+mode)
 if out.exists():
  result=json.loads((out/'disabled-check.json').read_text())
  assert result['build_mode']==mode and result['custom2']==mask
  assert set(result['domains'])=={'sim','sound'}
  print('RETAIN PASSED DISABLED',mode,flush=True)
  continue
 env=dict(os.environ,BENCH_DEVELOPER='1' if mode=='developer' else '0',BENCH_BATCH_KEYS='1')
 print('START DISABLED',mode,flush=True)
 with Path(str(out)+'.driver.log').open('w') as log:
  subprocess.run([sys.executable,'-B','tools/release_disabled_case.py','020',str(mask),str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 print('PASSED DISABLED',mode,flush=True)
hashes=set()
for machine in ('a500','020','030','030-nommu','040','060'):
 out=Path('tmp/prof/completion-f-'+machine+'-1')
 if out.exists():raise SystemExit('Refuse overwrite '+str(out))
 env=dict(os.environ,BENCH_DEVELOPER='0',BENCH_OMIT_CUSTOM2='1',BENCH_BATCH_KEYS='1',BENCH_EVENT_ONLY='1',BENCH_OPENING_ONLY='0')
 print('START FINAL',machine,flush=True)
 with Path(str(out)+'.driver.log').open('w') as log:
  subprocess.run([sys.executable,'-B','tools/completion_matrix_case.py',machine,'0',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 data=json.loads((out/'event.json').read_text());hashes.add(data['slave_sha256']);assert len(hashes)==1
 assert 'CUSTOM2=' not in data['environment']['WHD_ARGS']
 assert b'C2:L:Faster rendering:On,Off;' in (out/'slave.slave').read_bytes()
 for path in out.glob('locate-*.bin'):path.unlink()
 print('PASSED FINAL',machine,data['fps'],flush=True)
print('FINAL MATRIX COMPLETE',hashes,flush=True)
