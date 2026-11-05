import sys,json
from harness_a import *
s=Session(sys.argv[1]);rows=[]
try:
 s.cmd('monitor fields 999',timeout=60);s.input('JOY2_FIRE_BUTTON',1)
 s.cmd('break *0xa8788');s.cmd('continue',timeout=60);s.cmd('delete breakpoints')
 def state(stage):
  s.cmd('maintenance flush register-cache');pc=int(s.cmd('p/x $pc').split('=')[1],16)
  r=dict(stage=stage,pc=hex(pc),dma=hex(rd(s,0xdff002,2)),regs=s.cmd('info registers'));rows.append(r);print(stage,hex(pc),r['dma'],flush=True)
 state('before-init')
 (s.out/'low-before-init.bin').write_bytes(read_bytes(s,0,0x8000))
 s.cmd('break *0xadf82');s.cmd('continue',timeout=60);s.cmd('delete breakpoints');state('before-load')
 ret=rd(s,int(s.cmd('p/x $sp').split('=')[1],16));s.cmd(f'break *{ret:#x}');s.cmd('continue',timeout=60);s.cmd('delete breakpoints');state('after-load')
 (s.out/'states.json').write_text(json.dumps(rows,indent=2)+'\n')
finally:s.quit()
