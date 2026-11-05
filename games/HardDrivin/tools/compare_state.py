#!/usr/bin/env python3
"""Port of TFH's full-hunk comparison, with dynamic regions and strict file lengths.
Compare one sampling domain at a time. Relocation acceptance is opt-in, restricted
to even-aligned longwords pointing into the same named game hunk at the same offset.
It is address normalization, not proof that scalar values cannot resemble pointers.
"""
import argparse,json,struct
from pathlib import Path

def relocated(x,y,i,ma,mb):
 if i%2 or i+4>min(len(x),len(y)):return False
 u,v=struct.unpack_from('>I',x,i)[0],struct.unpack_from('>I',y,i)[0]
 other={r['name']:r for r in mb['layout']['regions']}
 for a in ma['layout']['regions']:
  b=other[a['name']]
  if 0<=u-a['base']<a['size'] and u-a['base']==v-b['base'] and a['size']==b['size']:return True
 return False

def differences(x,y,ma,mb,normalize=False):
 if len(x)!=len(y):raise ValueError('snapshot lengths differ')
 out=[];i=0
 while i<len(x):
  if x[i]==y[i]:i+=1;continue
  if normalize:
   for j in range(max(0,i-3),i+1):
    if relocated(x,y,j,ma,mb) and x[j:i]==y[j:i]:i=j+4;break
   else:out.append(i);i+=1
  else:out.append(i);i+=1
 return out

def compare(a,b,mode,normalize=False):
 ma,mb=[json.loads((d/'metadata.json').read_text()) for d in (a,b)]
 assert [(r['name'],r['size']) for r in ma['snapshot_regions']]==[(r['name'],r['size']) for r in mb['snapshot_regions']],'snapshot schemas differ'
 names=sorted(p.name for p in (a/mode).glob('*.bin'))
 assert names and names==sorted(p.name for p in (b/mode).glob('*.bin')),'different snapshot sets'
 raw=same=0;first=None
 for name in names:
  x,y=[(d/mode/name).read_bytes() for d in (a,b)]
  assert len(x)==ma['snapshot_size'] and len(y)==mb['snapshot_size'],'truncated snapshot'
  raw+=x==y;diff=[] if x==y else differences(x,y,ma,mb,normalize)
  if not diff:same+=1
  elif first is None:first=dict(snapshot=name,count=len(diff),data_a4_offsets=[i-0x7ffe for i in diff[:20]])
 return dict(domain=mode,snapshots=len(names),raw_equal=raw,equal=same,relocation_allowed=normalize,first_difference=first)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('a',type=Path);p.add_argument('b',type=Path);p.add_argument('--domain',choices=['vbl','physics'],default='vbl');p.add_argument('--relocate',action='store_true');a=p.parse_args()
 result=compare(a.a,a.b,a.domain,a.relocate);print(json.dumps(result,indent=2));raise SystemExit(0 if result['equal']==result['snapshots'] else 1)
if __name__=='__main__':main()
