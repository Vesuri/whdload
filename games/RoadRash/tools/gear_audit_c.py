import sys,json,os
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 for name,lo,hi in [('motion',0x8b486,0x8b610),('acceleration',0x8e166,0x8e2d6),('gear',0x8da5c,0x8db0a)]:
  (s.out/(name+'.txt')).write_text(s.cmd(f'disassemble {lo:#x},{hi:#x}'))
 (s.out/'provenance.json').write_text(json.dumps(provenance(os.environ['SLAVE'],s),indent=2))
finally:s.quit()
