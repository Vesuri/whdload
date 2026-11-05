import sys,json,os
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 for name,lo,hi in [('avoidance',0x8d400,0x8d642)]:
  (s.out/(name+'.txt')).write_text(s.cmd(f'disassemble {lo:#x},{hi:#x}'))
 (s.out/'provenance.json').write_text(json.dumps(provenance(os.environ['SLAVE'],s),indent=2))
finally:s.quit()
