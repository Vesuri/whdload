import sys,json,hashlib
from harness_a import *
s=Session(sys.argv[1]);rows=[]
try:
 route(s);s.input('JOY2_UP',1)
 for i in range(8):
  for site in [0xafd68,0xafd6c,0xafd70,0xb076e]:
   s.cmd(f'tbreak *{site:#x}');s.cmd('continue',timeout=60);f=field(s);ptr=rd(s,0x404 if site==0xb076e else 0x408);buf=read_bytes(s,ptr,33600);(s.out/f'frame-{i:03}-{site:x}.bin').write_bytes(buf)
   rows.append(dict(index=i,site=hex(site),field=f,buffer=hex(ptr),sha256=hashlib.sha256(buf).hexdigest(),dma=rd(s,0xdff002,2)))
 (s.out/'frames.json').write_text(json.dumps(rows,indent=2))
finally:s.quit()
