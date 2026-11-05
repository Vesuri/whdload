"""Sample rank immediately after its native store, preserving field-timed inputs."""
import sys,json,os
from harness_a import *
from rank_audit_c import snapshot
s=Session(sys.argv[1])
try:
 route(s)
 tape=json.loads((ROOT/'tools/fixtures/lap.json').read_text())
 for target,event,value in tape['events']:
  if target>1140: break
  advance(s,target);s.input(event,value)
 advance(s,1150)
 s.cmd('break *0x8936c')
 rows=[]
 for _ in range(100):
  s.cmd('continue',timeout=60)
  row=snapshot(s);row['cursor']=rd(s,0xa5d50);rows.append(row)
  if row['cursor']>=1202:break
 else:raise RuntimeError('rank trace exceeded bounds')
 result=dict(rows=rows,provenance=provenance(os.environ['SLAVE'],s))
 (s.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print('rows',len(rows),'mismatches',sum(r['rank_audit']['displayed']!=r['rank_audit']['reconstructed'] for r in rows),flush=True)
finally:s.quit()
