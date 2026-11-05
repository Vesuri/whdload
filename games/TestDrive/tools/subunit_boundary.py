#!/usr/bin/env python3
"""Match the same road segments across a native 0xffff -> next-segment 0 crossing."""
import argparse,json
from pathlib import Path
from subunit_geometry import validate,l,u

def check(before,after):
 assert json.loads((before.parent/'capture.json').read_text())['slave_sha256']==json.loads((after.parent/'capture.json').read_text())['slave_sha256'],'different builds'
 validate(before);validate(after);result={}
 for view in ['main','mirror']:
  rows=[]
  for folder in [before,after]:
   paths=sorted(folder.glob(view+'-[0-9][0-9].bin'));b=paths[0].read_bytes()
   rows.append([(l(f.read_bytes(),-29844)>>16,l(f.read_bytes(),-29848)>>16,u(f.read_bytes(),-29852)) for f in paths])
  a,z=rows;pairs=list(zip(a[1:],z)) if view=='main' else list(zip(a,z[1:]))
  assert len(pairs)>=10
  first=(sorted(before.glob(view+'-[0-9][0-9].bin'))[0]).read_bytes();last=(sorted(after.glob(view+'-[0-9][0-9].bin'))[0]).read_bytes()
  assert u(first,-22338)==65535 and l(last,-22340)==(l(first,-22340)&~65535)+65536
  assert l(first,-22372)==l(last,-22372),'held lateral input required'
  maximum=[max(abs(x[i]-y[i]) for x,y in pairs) for i in range(3)]
  assert maximum[0]<=1 and maximum[1]<=1 and maximum[2]<=1,(view,maximum)
  result[view]=dict(matched_segments=len(pairs),max_x_pixels=maximum[0],max_y_pixels=maximum[1],max_scale_units=maximum[2])
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('before',type=Path);p.add_argument('after',type=Path);a=p.parse_args();print(json.dumps(check(a.before,a.after),indent=2))
