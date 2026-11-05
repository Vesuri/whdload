"""Capture native player curve integration operands without changing game state."""
import re,sys,json,struct
from harness_a import *
s=Session(sys.argv[1])
try:
 initial=route(s);s.input('JOY2_UP',1);s.cmd('break *0x8babe');rows=[]
 for _ in range(700):
  s.cmd('continue',timeout=60)
  regs=s.cmd('info registers d6 a1');vals={k:int(v,16) for k,v in re.findall(r'\b(d6|a1)\s+0x([0-9a-fA-F]+)',regs)}
  assert vals['a1']==0xa5d60,regs
  b=read_bytes(s,0xa5d60,0x80);curve=vals['d6']&65535;curve=curve-65536 if curve&32768 else curve
  displacement=struct.unpack_from('>I',b,0x26)[0];center=struct.unpack_from('>h',b,0x36)[0]
  update=3*(((displacement>>8)*curve)>>8)
  if rows:assert center==rows[-1]['center']+rows[-1]['update'],(center,rows[-1])
  rows.append(dict(cursor=rd(s,0xa5d50),live=field(s),position=struct.unpack_from('>I',b,4)[0],speed=struct.unpack_from('>H',b,0x12)[0],delta=rd(s,0xa6f00,2),displacement=displacement,curve=curve,center=center,update=update))
  if rows[-1]['cursor']>=600:break
 else:raise RuntimeError('trace did not finish')
 result=dict(initial=initial,rows=rows,provenance=provenance(os.environ['SLAVE'],s));(s.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('verified road updates',len(rows),'last',rows[-1],flush=True)
finally:s.quit()
