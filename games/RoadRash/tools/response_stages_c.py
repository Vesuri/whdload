import os,sys,json,re
from harness_a import *
s=Session(sys.argv[1]);rows=[];inject=int(os.environ.get("RR_INJECT","300"))
try:
 route(s);s.input('JOY2_UP',1);advance(s,inject)
 listing=Path(os.environ['RR_LISTING']).read_text(encoding='latin1')
 def symbol(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
 base=rd(s,0x87480)-symbol('step_main')
 initial=dict(field=field(s),cursor=rd(s,0xa5d50),pc=s.cmd('info registers pc'))
 s.input('JOY2_RIGHT',1)
 sites=[0x875b6,0x875c8,0x8a8ec,0x87736,0x8773c,0x871dc]
 for i,a in enumerate(sites,1):
  s.cmd(f'break *{a:#x}')
  if a==0x8a8ec:s.cmd(f'condition {i} $a1 == 0xa5d60')
 for _ in range(250):
  s.cmd('continue',timeout=60);regs=s.cmd('info registers pc d1 a1');v={k:int(x,16) for k,x in re.findall(r'\b(pc|d1|a1)\s+0x([0-9a-fA-F]+)',regs)}
  assert v['pc'] in sites
  rows.append(dict(pc=hex(v['pc']),live=field(s),cursor=rd(s,0xa5d50),input=read_bytes(s,0xa598c,1)[0],heading=rd(s,0xa5d6c,2),predicted_heading=v['d1']&65535,pose_busy=read_bytes(s,base+symbol('step_pose_busy'),1)[0],horizon=rd(s,base+symbol('step_pose_render_fields'),2),history=read_bytes(s,base+symbol('step_pose_headings'),10).hex(),front=hex(rd(s,0x404))))
  if rows[-1]['live']>=inject+20:break
 else:raise RuntimeError('stage trace overflow')
 (s.out/'result.json').write_text(json.dumps(dict(initial=initial,rows=rows,provenance=provenance(os.environ['SLAVE'],s)),indent=2)+'\n');print('stage records',len(rows),flush=True)
finally:s.quit()
