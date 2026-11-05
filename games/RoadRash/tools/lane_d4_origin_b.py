import os,sys,json,re
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 for t,k,v in json.loads((ROOT/'tools/fixtures/lap.json').read_text())['events']:
  if t>1200:break
  advance(s,t);s.input(k,v)
 advance(s,1200)
 sites=[0x8747e,0x875c8,0x87658,0x87698,0x87730,0x87736,0x87742,0x87748,0x87298,0x8da5c]
 for pc in sites:s.cmd(f'break *{pc:#x}')
 rows=[]
 for _ in range(70):
  s.cmd('continue',timeout=60);regs=s.cmd('info registers pc d4 a1')
  v={k:int(x,16) for k,x in re.findall(r'\b(pc|d4|a1)\s+0x([0-9a-fA-F]+)',regs)}
  rows.append(dict(field=field(s),cursor=rd(s,0xa5d50),**v))
  if rows[-1]['field']>=1220:break
 (s.out/'result.json').write_text(json.dumps(dict(rows=rows,provenance=provenance(os.environ['SLAVE'],s)),indent=2));print([(hex(r['pc']),r['field'],r['d4']&65535) for r in rows],flush=True)
finally:s.quit()
