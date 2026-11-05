from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parents[1];out={'status':'passed','scope':'Same grid fixture and native clear phase; 12 traced fields per arm. Immutable one-word preset, both installed native hook operands checked live. 030 trace uses 68EC030; this is not real hardware timing. Diagnostic CPU helper lacks final production CCR/extent guards, so final acceptance uses separate production runs.','profiles':{}}
for profile in ['030-50-trace-bce','040-40-bce','060-50-bce']:
 row={}
 for arm in ['control','candidate']:
  p=r/f'tmp/step5/hi25-profile-{profile}-h10-micro-{arm}';x=json.loads((p/'result.json').read_text());a=json.loads((p/'hi25-analysis.json').read_text());c=json.loads((p/'h8-calls.json').read_text());assert x['status']=='passed' and len(x['verified_hooks'])==2 and a['complete_draws']>0
  row[arm]={'result':str((p/'result.json').relative_to(r)),'sha256':hashlib.sha256((p/'result.json').read_bytes()).hexdigest(),'slave_sha256':x['slave_sha256'],'complete_draws':a['complete_draws'],'post_wait_ms':a['mean_after_wait_ms'],'background':next(v for k,v in c['calls'].items() if k.startswith('$6b050')),'trace':json.loads((p/'h9-trace-hash.json').read_text())}
 row['post_wait_saved_ms']=row['control']['post_wait_ms']-row['candidate']['post_wait_ms'];assert row['post_wait_saved_ms']>0;out['profiles'][profile]=row
(r/'manifest/render-h10-microbench.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
