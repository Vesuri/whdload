import os,sys,re,json
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 for target,event,value in json.loads((ROOT/'tools/fixtures/lap.json').read_text())['events']:
  if target>1200:break
  advance(s,target);s.input(event,value)
 advance(s,1200)
 entry=rd(s,0x8da5e) if rd(s,0x8da5c,2)==0x4ef9 else 0x8da5c
 s.cmd(f'break *{entry:#x}')
 rows=[]
 for _ in range(60):
  s.cmd('continue',timeout=60);regs=s.cmd('info registers d4 a1')
  v={k:int(x,16) for k,x in re.findall(r'\b(d4|a1)\s+0x([0-9a-fA-F]+)',regs)}
  rows.append(dict(field=field(s),cursor=rd(s,0xa5d50),delta=rd(s,0xa6f00,2),d4=v['d4'],actor=hex(v['a1']),record=read_bytes(s,v['a1'],128).hex()))
  if rows[-1]['cursor']>=1220:break
 (s.out/'result.json').write_text(json.dumps(dict(rows=rows,provenance=provenance(os.environ['SLAVE'],s)),indent=2))
 print('lane D4',sorted(set(r['d4']&65535 for r in rows)),'cursors',rows[0]['cursor'],rows[-1]['cursor'],flush=True)
finally:s.quit()
