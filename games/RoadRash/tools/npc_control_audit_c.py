"""Read native opponent attack selection before interpreting its timing."""
import sys
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 for start,end,name in [(0x8b486,0x8b700,'movement-entry'),(0x8dd66,0x8e2d6,'control-update')]:
  (s.out/(name+'.txt')).write_text(s.cmd(f'disassemble {start:#x},{end:#x}'))
finally:s.quit()
