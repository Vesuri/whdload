#!/usr/bin/env python3
"""Capture native displayed bitplanes at completed swaps at matched ticks."""
import json,struct,sys,os,hashlib,re
from pathlib import Path
if os.environ.get('B_MMU'):
 from session_b import Session
else:
 from session_a import Session
from route import run
from flight_profile import ROUTE
from verify_run import marker,save_snapshot
from PIL import Image
out=Path(sys.argv[1]);s=Session(out,dict(AMIGA_SETUP=os.environ['MACHINE'],EXTRA_ARGS=os.environ.get('B_EXTRA',''),DETERMINISTIC='0',WINDOW='none') if os.environ.get('B_MMU') else None)
if os.environ.get('CACHE_VIEW'):s.cmd('monitor memory cache',timeout=15)
try:
 # Unpowered stationary player: match simulation ticks without field-timed engine input.
 route=list(ROUTE);route=route[:route.index('t:n1')]
 if os.environ.get('B_EARLY'):route[-1]='f:100'
 run(s,route)
 M=marker(s.read(0x200000,0x800000));(out/'layout.json').write_text(json.dumps(M,indent=2))
 checkpoint=int.from_bytes(s.read(M['address']+76,4),'big') if os.environ.get('B_REGS') else M['hunks'][0]+0x44ca
 s.cmd(f'break *{checkpoint:#x}')
 for tick in ([int(x) for x in os.environ['B_TICKS'].split(',')] if os.environ.get('B_TICKS') else (100,110,120)):
  condition=f'($d0 & 0xffff) >= {tick}' if os.environ.get('B_REGS') else f"*(unsigned short*){M['hunks'][6]+0x3b94:#x} >= {tick}"
  s.cmd('condition $bpnum '+condition)
  s.cmd('continue',timeout=600)
  p=out/f'tick-{tick}';p.mkdir(exist_ok=True)
  if os.environ.get('B_REGS'):(p/'cache-policy.json').write_text(json.dumps(dict(policy=int.from_bytes(s.read(M['address']+72,4),'big'))))
  if os.environ.get('B_REGS'):
   h6=M['hunks'][6];blob=s.read(h6,int.from_bytes(s.read(h6-8,4),'big')-8);(p/'h6.bin').write_bytes(blob)
   cpu_d0=int(re.search(r'= (0x[0-9a-fA-F]+)',s.cmd('p/x $d0'))[1],16)
   clocks=dict(tick=cpu_d0&65535,displayed_buffer=(cpu_d0>>16)^1,ram_tick=int.from_bytes(blob[0x3b94:0x3b96],'big'),vbl=int.from_bytes(s.read(M['hunks'][2]+0x1c,4),'big'))
  else:clocks=save_snapshot(s,M,p)
  assert clocks['tick']==tick,clocks
  screen=int.from_bytes(s.read(M['hunks'][6]+0x47b0,4),'big')
  if os.environ.get('B_REGS'):
   bitmaps=int.from_bytes(s.read(M['hunks'][0]+0xba2,4),'big')
   assert clocks['displayed_buffer'] in (0,1)
   bm=s.read(bitmaps+40*clocks['displayed_buffer'],40)
  else:bm=s.read(screen+184,40)
  row,height=struct.unpack_from('>HH',bm);depth=bm[5]
  assert (row,height,depth)==(40,200,5),(row,height,depth)
  planes=[s.read(int.from_bytes(bm[8+i*4:12+i*4],'big'),row*height) for i in range(depth)]
  (p/'planes.bin').write_bytes(b''.join(planes))
  pixels=bytes(sum(((planes[k][i//8]>>(7-i%8))&1)<<k for k in range(depth)) for i in range(row*height*8))
  Image.frombytes('L',(row*8,height),bytes(x*8 for x in pixels)).save(p/'indices.png')
  (p/'clocks.json').write_text(json.dumps(clocks))
  print(tick,clocks,hashlib.sha256(b''.join(planes)).hexdigest(),flush=True)
 s.cmd('delete');s.shot('end.png')
finally:s.quit()
