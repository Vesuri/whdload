import re,sys,json,struct,os
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s);s.input('JOY2_UP',1);advance(s,400)
 base=rd(s,0x8b488) if rd(s,0x8b486,2)==0x4ef9 else 0x8b486
 actor=int(os.environ.get('RR_NPC_ACTOR','0xa61e0'),0)
 s.cmd(f'break *{base+0x8b930-0x8b486:#x}');s.cmd(f'condition 1 $a1 == {actor:#x}');rows=[]
 for _ in range(100):
  s.cmd('continue',timeout=60);regs=s.cmd('info registers d0 a1');v={k:int(x,16) for k,x in re.findall(r'\b(d0|a1)\s+0x([0-9a-fA-F]+)',regs)};assert v['a1']==actor
  a=read_bytes(s,v['a1'],128);displacement=struct.unpack_from('>I',a,0x26)[0];heading=struct.unpack_from('>h',a,8)[0];motion=v['d0']&65535;motion-=65536 if motion&32768 else 0
  rows.append(dict(field=field(s),cursor=rd(s,0xa5d50),position=struct.unpack_from('>I',a,4)[0],speed=struct.unpack_from('>H',a,0x12)[0],heading=heading,displacement=displacement,motion=motion,lateral=struct.unpack_from('>h',a)[0],flags=a[0x68:0x6a].hex(),unskidded=((displacement>>8)*heading)>>8))
  if rows[-1]['cursor']>=460:break
 else:raise RuntimeError('trace limit')
 (s.out/'result.json').write_text(json.dumps(dict(actor=hex(actor),rows=rows,provenance=provenance(os.environ['SLAVE'],s)),indent=2)+'\n');print('rows',len(rows),'zero positive',sum(r['heading']>0 and r['motion']==0 for r in rows),flush=True)
finally:s.quit()
