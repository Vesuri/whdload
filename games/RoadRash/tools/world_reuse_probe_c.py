import json,os,re,sys
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 tape=json.loads((ROOT/'tools/fixtures/c-attacks.json').read_text())
 for target,event,value in tape['events']:
  if target>1200:break
  advance(s,target);s.input(event,value)
 advance(s,1200)
 s.cmd('break *0x87486');s.cmd('condition 1 *(unsigned int*)0xa5d50 >= 1234')
 rows=[]
 for _ in range(10):
  s.cmd('continue',timeout=60)
  cursor=rd(s,0xa5d50)
  rows.append(dict(cursor=cursor,live=field(s),count=rd(s,0xa8734,2),offset=rd(s,0xa59fc,2),world_count=rd(s,0xa59fe,2),roadside=rd(s,0xa8092),state=read_bytes(s,0xa5900,0x2e40).hex()))
  if cursor>=1240:break
 else:raise RuntimeError('probe limit')
 (s.out/'result.json').write_text(json.dumps(dict(rows=rows,provenance=provenance(os.environ['SLAVE'],s)),indent=2))
 print('cursors',[r['cursor'] for r in rows],flush=True)
finally:s.quit()
