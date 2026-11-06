"""Three deliberate corruptions must be rejected by the profile report."""
from pathlib import Path
import subprocess,sys,tempfile,json,re
root=Path(__file__).resolve().parents[1];out=root/'tmp/step11';base=out/'baseline';results={}
for kind in ['wrong_frame_count','wrong_slave_anchor','missing_instruction_cost']:
 with tempfile.TemporaryDirectory() as t:
  d=Path(t)
  for f in base.iterdir():
   if f.is_file() and f.name!='step11-report.json':(d/f.name).symlink_to(f)
  listing=out/'baseline.lst'
  if kind=='wrong_frame_count':
   f=d/'counts.json';v=json.loads(f.read_text());f.unlink();v['publications']-=1;f.write_text(json.dumps(v))
  elif kind=='wrong_slave_anchor':
   s=listing.read_text(encoding='latin1');s=re.sub(r'^(do_swap_screen\s+00:)000023E2',r'\g<1>000023E4',s,flags=re.M);listing=d/'bad.lst';listing.write_text(s,encoding='latin1')
  else:
   f=d/'profile.csv';f.unlink()
   # Remove the largest instruction cost, independently of runtime addresses.
   original=(base/'profile.csv').read_text().splitlines();pcs=[(sum(map(int,x.split(',')[3:7])),i) for i,x in enumerate(original) if x.startswith('pc,')];original.pop(max(pcs)[1]);f.write_text('\n'.join(original)+'\n')
  r=subprocess.run([sys.executable,str(root/'tools/step11_report.py'),str(d),str(listing)],capture_output=True,text=True)
  results[kind]=dict(rejected=r.returncode!=0,error=r.stderr.splitlines()[-1] if r.stderr else '')
assert all(x['rejected'] for x in results.values()),results
(out/'report-negative-controls.json').write_text(json.dumps(results,indent=2));print(results)
