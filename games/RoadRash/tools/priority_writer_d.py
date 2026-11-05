import json,sys
from harness_a import *
s=Session(sys.argv[1]);rows=[]
try:
 s.cmd('monitor fields 999',timeout=60)
 s.input('JOY2_FIRE_BUTTON',1)
 s.cmd('break *0xa8788')
 print(s.cmd('continue',timeout=60),flush=True)
 s.cmd('delete breakpoints');s.cmd('maintenance packet Z2,dff096,2')
 for i in range(80):
  r=s.cmd('continue',timeout=30);s.cmd('maintenance flush register-cache');regs=s.cmd('info registers');pc=int(s.cmd('p/x $pc').split('=')[1],16)
  row=dict(index=i,reply=r,pc=hex(pc),registers=regs,dmaconr=hex(rd(s,0xdff002,2)),near=s.cmd(f'x/12hx {max(0,pc-16):#x}'));rows.append(row)
  print(i,hex(pc),row['dmaconr'],flush=True)
  if rd(s,0xdff002,2)&0x400:break
 (s.out/'writes.json').write_text(json.dumps(rows,indent=2)+'\n')
finally:s.quit()
