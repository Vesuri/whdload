import sys,json,hashlib
from harness_a import *
s=Session(sys.argv[1]);rows=[]
try:
 route(s);s.input('JOY2_UP',1);s.cmd('break *0xb076e')
 for i in range(64):
  s.cmd('continue',timeout=60);f=field(s);ptr=rd(s,0x404);buf=read_bytes(s,ptr,33600);(s.out/f'frame-{i:03}.bin').write_bytes(buf)
  rows.append(dict(index=i,field=f,buffer=hex(ptr),sha256=hashlib.sha256(buf).hexdigest(),dma=rd(s,0xdff002,2)))
 (s.out/'frames.json').write_text(json.dumps(rows,indent=2))
finally:s.quit()
