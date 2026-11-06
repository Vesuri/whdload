"""Pair timing only after full startup-state equality, never by chosen FPS."""
from pathlib import Path
import os,subprocess,json
r=Path(__file__).resolve().parents[1];out=r/'tmp/opt20';base=out/'delta-eight-off';env=dict(os.environ,END_FIELD='2002',MATCH_ALL='1')
subprocess.run(['python3',str(r/'tools/opt20_profile.py'),str(base)],env=dict(env,WORD_COPY_OFF='1'),check=True)
for trial in range(1,5):
 p=out/f'delta-eight-on-{trial}'
 result=subprocess.run(['python3',str(r/'tools/opt20_profile.py'),str(p)],env=dict(env,TEST_SEED=str(base)+'-seed',MATCH_ENTRY=str(base)))
 if result.returncode==0:
  (out/'delta-eight-timing-pair.json').write_text(json.dumps(dict(off=base.name,on=p.name,startup_rejections=trial-1),indent=2));break
 assert (p/'entry-match.json').exists() and not all(json.loads((p/'entry-match.json').read_text())),'Unexpected run failure'
else:raise RuntimeError('No matching startup state in four attempts; no accepted timing pair')
