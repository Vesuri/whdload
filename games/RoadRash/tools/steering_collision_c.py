import sys,json,re,struct
from harness_a import *
s=Session(sys.argv[1])
try:
 initial=route(s)
 tape=json.loads((ROOT/'tools/fixtures/lap.json').read_text())
 for f,event,v in tape['events']:
  if f>1200:break
  advance(s,f);s.input(event,v)
 advance(s,1200)
 base=rd(s,0x8b488) if rd(s,0x8b486,2)==0x4ef9 else 0x8b486
 sites={base+a-0x8b486:a for a in [0x8c266,0x8c310,0x8c36c]}
 for pc in [0x87040]+list(sites):s.cmd(f'break *{pc:#x}')
 rows=[]
 for _ in range(1000):
  s.cmd('continue',timeout=60)
  regs=s.cmd('info registers pc d0 a1 a2');r={k:int(v,16) for k,v in re.findall(r'\b(pc|d0|a1|a2)\s+0x([0-9a-fA-F]+)',regs)}
  f=field(s)
  if r['pc'] in sites:
   rows.append(dict(field=f,site=hex(sites[r['pc']]),registers=r,player=read_bytes(s,0xa5d60,128).hex(),steering=rd(s,0xa7262,2)))
  if f>=1325:break
 else:raise RuntimeError('trace limit')
 (s.out/'result.json').write_text(json.dumps(dict(rows=rows,provenance=provenance(os.environ['SLAVE'],s)),indent=2)+'\n');print('steering collision writes',len(rows),[(r['field'],r['site'],hex(r['registers']['a2'])) for r in rows],flush=True)
finally:s.quit()
