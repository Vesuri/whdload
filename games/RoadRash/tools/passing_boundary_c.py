import sys,json,os,struct
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 for target,event,value in json.loads((ROOT/'tools/fixtures/lap.json').read_text())['events']:
  if target>1100:break
  advance(s,target);s.input(event,value)
 isc=rd(s,0x8747e,2)==0x4ef9
 if isc:
  main=rd(s,0x87480);data=read_bytes(s,main,1024);off=data.find(b'RRCSTEP1');assert off>=0
  base=main+off;end=rd(s,0x875b8);code=read_bytes(s,end,base-end)
  rts=code.rfind(bytes.fromhex('4e75'));assert rts>=0 and len(code)-rts<=4
  bp=end+rts
 else:bp=0x875b6
 s.cmd(f'break *{bp:#x}')
 rows=[]
 for _ in range(90):
  s.cmd('continue',timeout=60)
  row=dict(live=field(s),cursor=rd(s,0xa5d50),delta=rd(s,0xa6f00,2),rank=read_bytes(s,0xa59f4,2).hex(),actors={})
  for a in [0xa5d60,0xa61e0,0xa6260]:row['actors'][hex(a)]=read_bytes(s,a,128).hex()
  rows.append(row)
  if row['cursor']>=1138:break
 else:raise RuntimeError('boundary limit')
 result=dict(rows=rows,breakpoint=hex(bp),provenance=provenance(os.environ['SLAVE'],s))
 (s.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('boundaries',len(rows),rows[0]['cursor'],rows[-1]['cursor'],flush=True)
finally:s.quit()
