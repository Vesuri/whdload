"""Bounded retry only for rejected pre-timing startup states."""
import os,sys,subprocess,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];prefix=sys.argv[1];ref=Path(sys.argv[2]).resolve()
for i in range(2,5):
 out=root/'tmp/opt20'/f'{prefix}-{i}'
 result=subprocess.run(['python3',str(root/'tools/opt20_balanced_profile.py'),str(out)],env=dict(os.environ,TEST_SEED=str(ref)+'-seed',MATCH_ENTRY=str(ref)))
 if result.returncode==0:
  (root/'tmp/opt20'/f'{prefix}-accepted.json').write_text(json.dumps(dict(off=ref.name,on=out.name),indent=2));break
 assert (out/'entry-match.json').exists() and not all(json.loads((out/'entry-match.json').read_text())),'Unexpected failure'
else:raise RuntimeError('No matching startup state after bounded retries')
