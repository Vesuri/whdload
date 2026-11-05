"""Record completed native/C steps under the same live-field throttle input."""
import sys,json,struct
from harness_a import *
s=Session(sys.argv[1])
try:
 initial=route(s);s.input('JOY2_UP',1)
 isc=rd(s,0x8747e,2)==0x4ef9
 if isc:
  main=rd(s,0x87480);data=read_bytes(s,main,1024);off=data.find(b'RRCSTEP1');assert off>=0
  base=main+off;end=rd(s,0x875b8);code=read_bytes(s,end,base-end)
  rts=code.rfind(bytes.fromhex('4e75'));assert rts>=0 and len(code)-rts<=4
  bp=end+rts
 else:bp=0x875b6
 s.cmd(f'break *{bp:#x}')
 rows=[]
 for i in range(700):
  s.cmd('continue',timeout=60)
  b=read_bytes(s,0xa5d4c,0x94)
  rows.append(dict(live=struct.unpack_from('>I',b)[0],cursor=struct.unpack_from('>I',b,4)[0],position=struct.unpack_from('>I',b,0x18)[0],speed=struct.unpack_from('>H',b,0x26)[0],delta=rd(s,0xa6f00,2),acceleration=struct.unpack_from('>h',b,0x28)[0],gear=struct.unpack_from('>H',b,0x2c)[0],lateral=struct.unpack_from('>h',b,0x14)[0],height=struct.unpack_from('>h',b,0x16)[0],flags=struct.unpack_from('>H',b,0x7c)[0],crash=struct.unpack_from('>b',b,0x82)[0],road_center=struct.unpack_from('>h',b,0x4a)[0],road_fraction=struct.unpack_from('>h',b,0x4c)[0],displacement=struct.unpack_from('>I',b,0x3a)[0]))
  if rows[-1]['live']>=600:break
 else:raise RuntimeError('did not reach 600')
 result=dict(initial=initial,c_path=isc,breakpoint=hex(bp),rows=rows,provenance=provenance(os.environ['SLAVE'],s))
 (s.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(dict(c_path=isc,count=len(rows),first=rows[0],last=rows[-1])),flush=True)
finally:s.quit()
