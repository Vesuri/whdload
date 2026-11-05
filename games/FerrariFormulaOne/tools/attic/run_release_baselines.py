from pathlib import Path
import os,sys,subprocess,json
from analyze_step3 import analyze
r=Path(__file__).resolve().parents[1];profiles=json.loads((r/'manifest/step3-profiles.json').read_text());results=[]
for profile in ('030-50','040-25','040-40','060-50'):
 for custom1 in (0,1):
  name=f'release-original-{profile}-custom1-{custom1}-clock-v2';out=r/'tmp/step3'/name
  env=dict(os.environ);env.update(profiles[profile]);env.update(KICKSTART=env['KICKSTART_A1200'],WHD_ARGS=f'CUSTOM1={custom1}',OBSERVE='census')
  if not (out/'result.json').exists() or json.loads((out/'result.json').read_text()).get('status')!='complete':
   print('RUN',name,flush=True)
   with (r/'tmp/step5'/f'{name}.log').open('w') as log:rc=subprocess.run([sys.executable,str(r/'tools/measure_release_baseline.py'),name],env=env,stdout=log,stderr=subprocess.STDOUT).returncode
   if rc:results.append(dict(name=name,status='failed'));continue
  a=analyze(out);report=json.loads((out/'result.json').read_text())
  before=(out/'anchor.bin').read_bytes();after=(out/'end.bin').read_bytes();clocks=[]
  for at in (0x226c0,0x226ca):
   x=before[at:at+10];y=after[at:at+10];assert x[:3]==y[:3]
   tick=lambda c:sum(v*w for v,w in zip(c[3:],(360000,36000,6000,600,100,10,1)))
   clocks.append((tick(y)-tick(x))/10)
  observed_seconds=1000*71051/3546895
  report['clock_seconds']=clocks;report['observed_seconds']=observed_seconds;report['calendar_speed_ratio']=clocks[0]/observed_seconds
  results.append(dict(name=name,status='passed',fps=a['presented_fps_count'],interval_fields=a['interval_fields'],metadata=report))
  (r/'manifest/release-original-observations.json').write_text(json.dumps(dict(scope='Unmodified original demo observations, calibrated observer; each arm starts after 125 native updates. These are not equal-state or equal-elapsed-workload speedup comparisons with the converted production path.',results=results),indent=2)+'\n')
  print(name,a['presented_fps_count'],flush=True)
