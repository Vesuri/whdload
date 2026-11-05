#!/usr/bin/env python3
"""Byte-exact original/enhanced zero-fraction rows, scanlines and object queues."""
import argparse,json
from pathlib import Path
from subunit_geometry import A,validate,u

def compare(a,b):
 assert json.loads((a.parent/'capture.json').read_text())['slave_sha256']==json.loads((b.parent/'capture.json').read_text())['slave_sha256'],'different builds'
 for folder in [a,b]:
  for view in ['main','mirror']:
   raw=(folder/(view+'-00.bin')).read_bytes()
   assert all(u(raw,x)==0 for x in [-22338,-22370,-22362]+list(range(-29372,-29326,4))),'nonzero oracle input'
 validate(a,False,True);validate(b,True,True);result={}
 for view in ['main','mirror']:
  files=sorted(a.glob(view+'-[0-9][0-9].bin'));mismatch=[]
  assert len(files)==len(list(b.glob(view+'-[0-9][0-9].bin')))
  for f in files:
   old=f.read_bytes();new=(b/f.name).read_bytes()
   for lo,hi in [(-29852,-29830),(-29308,-29306),(-29208,-28808)]:
    if old[A+lo:A+hi]!=new[A+lo:A+hi]:mismatch.append((f.name,lo))
  for suffix in ['before','after']:
   old=(a/(view+'-'+suffix+'.bin')).read_bytes();new=(b/(view+'-'+suffix+'.bin')).read_bytes()
   for lo,hi in [(-29208,-28808),(-28798,-27196)]:
    if old[A+lo:A+hi]!=new[A+lo:A+hi]:mismatch.append((suffix,lo))
  result[view]=dict(rows=len(files),mismatches=mismatch)
 assert all(not x['mismatches'] for x in result.values()),result
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('original',type=Path);p.add_argument('enhanced',type=Path);a=p.parse_args();print(json.dumps(compare(a.original,a.enhanced),indent=2))
