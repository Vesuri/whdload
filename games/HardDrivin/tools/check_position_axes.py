import sys,json,re
from pathlib import Path
def trunc(n,d):return abs(n)//d*(-1 if n<0 else 1)
for name in sys.argv[1:]:
 out=Path('tmp/prof')/name;pending={};counts={k:0 for k in ['X','Y','Z']};nonzero=dict(counts)
 for tag,values in re.findall(r'^(YPIN|YPOUT|ZPIN|ZPOUT|PIN|POUT) ([-0-9 ]+)$',(out/'events.log').read_text(),re.M):
  axis=tag[0] if tag[0] in 'YZ' else 'X';r=list(map(int,values.split()))
  if tag.endswith('PIN'):
   assert axis not in pending;pending[axis]=r;continue
  before=pending.pop(axis);f,pos,v,u,ic,qold,prev,fine,n=before[:9];qnew=r[5]
  combined=(8*((8+n)*v-(8-n)*u)+ic)*512+((8+n)*qnew-(8-n)*prev)//16+fine
  delta=trunc(combined,65536);carry=combined-delta*65536
  assert (r[1],r[4],r[7])==(pos+delta,0,carry),(axis,before,r,pos+delta,carry)
  counts[axis]+=1;nonzero[axis]+=delta!=0
 assert not pending and all(counts.values())
 result=dict(passed=True,axis_updates=counts,nonzero_displacements=nonzero)
 (out/'position-axes-check.json').write_text(json.dumps(result,indent=2)+'\n');print(name,result)
