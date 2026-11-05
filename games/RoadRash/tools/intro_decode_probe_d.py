import sys,json,hashlib
from harness_a import *
s=Session(sys.argv[1])
try:
 for i in range(500):
  try:
   p=rd(s,0x8002);entry=rd(s,p+2) if rd(s,0x8000,2)==0x4ef9 and 0x200000<=p<0xa00000 else 0
  except (ValueError,IndexError):entry=0
  if entry-p==0xa68:break
  s.cmd('monitor fields 49')
 else:raise RuntimeError('intro not reached')
 s.cmd(f'break *{p+0xd4e:#x}')
 rows=[]
 for i in range(3):
  s.cmd('continue',timeout=60)
  row=dict(regs=s.cmd('info registers'),remaining=rd(s,p+0x86,2),index=rd(s,p+0x12),screen=hashlib.sha256(read_bytes(s,0x6b6e0,80000)).hexdigest(),copper=read_bytes(s,0x8904,0x164).hex())
  (s.out/f'screen-{i}.bin').write_bytes(read_bytes(s,0x6b6e0,80000));rows.append(row)
 (s.out/'decode.json').write_text(json.dumps(rows,indent=2))
finally:s.quit()
