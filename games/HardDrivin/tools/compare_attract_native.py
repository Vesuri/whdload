import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('names',nargs='+');a=p.parse_args();root=Path(__file__).resolve().parents[1]/'tmp/prof';ref=json.loads((root/'s4-attract-original/poses.json').read_text())
for name in a.names:
 out=root/name;poses=json.loads((out/'poses.json').read_text());result=json.loads((out/'results.json').read_text());ages=[int(line.split()[3]) for line in (out/'events.log').read_text().splitlines() if line.startswith('POSE ')]
 checked=0;errors=[]
 for i,(pose,age) in enumerate(zip(poses,ages)):
  if result['native']:j=i
  else:
   if age%8 or age//8>=len(ref):continue
   j=age//8
  expected=ref[j];actual={k:pose[k] for k in ['route','geometry']}
  if actual!={k:expected[k] for k in actual}:errors.append([i,age,actual,expected])
  if result['native'] and pose['scroll']!=expected['scroll']:errors.append([i,'scroll'])
  checked+=1
 r=dict(passed=not errors,checked_native_grid_poses=checked,forced_native=result['native'],errors=errors[:3]);(out/'native-grid-equivalence.json').write_text(json.dumps(r,indent=2)+'\n');print(name,r);assert checked and not errors
