import sys,json
from harness_a import *
s=Session(sys.argv[1])
try:
 for i in range(300):
  try:p=rd(s,0x88)
  except (ValueError,IndexError):p=0
  if p==0x4734 or (0x200000<=p<0xa00000 and rd(s,p)==0x46fc2700):break
  s.cmd('monitor fields 19')
 else:raise RuntimeError('loader not reached')
 base=p-0x4734
 print('loader',hex(p),flush=True)
 s.cmd(f'tbreak *{base+0x4a1c:#x}')
 for i in range(1000):
  s.input('JOY2_FIRE_BUTTON',int(i%4==0))
  s.cmd('monitor fields 4')
  pc=int(s.cmd('info registers pc').split()[1],16)
  if pc==base+0x4a1c:break
 else:raise RuntimeError('loading animation breakpoint not reached')
 s.input('JOY2_FIRE_BUTTON',0)
 ptr=rd(s,0x6cf2);assert 0x6cf0<ptr<0x73b0,hex(ptr)
 assert rd(s,base+0x4906)==0x6cf0
 assert rd(s,base+0x4a84)==0x6cf2
 s.shot('loading.png')
 (s.out/'pointer.json').write_text(json.dumps(dict(pixel=hex(ptr),loader_delta=hex(base))))
 route(s);s.shot('race.png')
finally:s.quit()
