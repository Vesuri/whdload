import sys,json,re
from harness_a import *
s=Session(sys.argv[1]); rows=[]
try:
 route(s)
 for site in [0xb4da4,0xb4dc4,0xb4de4,0xb4e02,0xb4e22,0xb4e40,0xb4e60,0xb4e7e]:
  s.cmd(f'tbreak *{site:#x}');s.cmd('continue',timeout=120)
  regs=s.cmd('info registers');rows.append(dict(site=hex(site),registers=regs,custom=s.cmd('monitor custom')))
 (s.out/'dials.json').write_text(json.dumps(rows,indent=2))
finally:s.quit()
