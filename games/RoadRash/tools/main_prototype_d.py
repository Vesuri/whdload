import os,json,sys
from harness_a import *
s=Session(sys.argv[1]);base=None
try:
 for i in range(500):
  if rd(s,0x80000,2)==0x4ef9:
   candidate=rd(s,0x80002)
   if 0x200000<=candidate<0xa00000:base=candidate
  if base and rd(s,base+0x25916)==base+0x7040:break
  s.input('JOY2_FIRE_BUTTON',1);s.cmd('monitor fields 4',timeout=60);s.input('JOY2_FIRE_BUTTON',0);s.cmd('monitor fields 14',timeout=60)
 else:
  s.shot('failed.png');print(s.cmd('info registers'),flush=True);raise RuntimeError('no relocated race')
 print('relocated race',hex(base),'field',rd(s,base+0x25d4c),flush=True)
 s.shot('race.png');s.input('JOY2_UP',1);s.cmd('monitor fields 499',timeout=120);s.shot('after.png')
 (s.out/'main-live.bin').write_bytes(read_bytes(s,base,0x3c3ec))
 result=dict(base=hex(base),field=rd(s,base+0x25d4c),player_position=rd(s,base+0x25d64),hook=hex(rd(s,base+0x25916)),provenance=provenance(os.environ['SLAVE'],s));(s.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
finally:s.quit()
