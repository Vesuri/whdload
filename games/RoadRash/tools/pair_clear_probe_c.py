import sys,re,json,struct
from harness_a import *
s=Session(sys.argv[1]);rows=[]
try:
 route(s);s.input('JOY2_UP',1);advance(s,int(os.environ.get("RR_PROBE_START","1000")))
 listing=Path(os.environ['RR_LISTING']).read_text(encoding='latin1')
 def sym(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
 base=rd(s,0x87480)-sym('step_main');entry=base+sym('step_pair_clear');s.cmd(f'break *{entry:#x}')
 def regs():return {k:int(v,16) for k,v in re.findall(r'\b(d[0-7]|a[0-6]|sp|sr|pc)\s+0x([0-9a-fA-F]+)',s.cmd('info registers'))}
 for _ in range(256):
  s.cmd('continue',timeout=60);before=regs();assert before['pc']==entry
  addresses=sorted({before['a1']+0x68,before['a1']+0x69,before['a2']+0x69})
  raw={a:read_bytes(s,a,1)[0] for a in addresses};expected=dict(raw)
  for a,bit in [(before['a1']+0x68,4),(before['a1']+0x69,7),(before['a2']+0x69,7)]:
   z=not(expected[a]&(1<<bit));expected[a]&=255^(1<<bit)
  expected_ccr=(before['sr']&31&~4)|(4 if z else 0)
  ret=rd(s,before['sp']);s.cmd('disable 1');s.cmd(f'tbreak *{ret:#x}');s.cmd('continue',timeout=60);after=regs();assert after['pc']==ret
  for k in [f'd{i}' for i in range(8)]+[f'a{i}' for i in range(7)]:assert before[k]==after[k],k
  assert after['sr']&31==expected_ccr,(before,after,expected_ccr)
  assert after['sp']==before['sp']+4
  for a,value in expected.items():assert read_bytes(s,a,1)[0]==value
  rows.append(dict(cursor=rd(s,0xa5d50),before=raw,after=expected,ccr=expected_ccr))
  s.cmd('enable 1')
 (s.out/'probe.json').write_text(json.dumps(dict(calls=len(rows),rows=rows,provenance=provenance(os.environ['SLAVE'],s)),indent=2)+'\n');print('validated live calls',len(rows),flush=True)
finally:s.quit()
