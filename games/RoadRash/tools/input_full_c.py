import sys,json,os
from harness_a import *
s=Session(sys.argv[1])
try:
 for attempt in range(500):
  try:hook=rd(s,0xa5916)
  except (ValueError,IndexError):hook=0
  if hook==0x87040:break
  s.input('JOY2_FIRE_BUTTON',1);s.cmd('monitor fields 4')
  s.input('JOY2_FIRE_BUTTON',0);s.cmd('monitor fields 14')
 else:raise RuntimeError('race not reached')
 s.cmd('monitor fields 199')
 s.shot('overflow.png')
 (s.out/'result.json').write_text(json.dumps(dict(provenance=provenance(os.environ['SLAVE'],s),registers=s.cmd('info registers pc sp')),indent=2))
finally:s.quit()
