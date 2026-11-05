"""Read native opponent attack selection before interpreting its timing."""
import sys
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 for start,end,name in [(0x89d20,0x89e76,'pose-loop')]:
  (s.out/(name+'.txt')).write_text(s.cmd(f'disassemble {start:#x},{end:#x}'))
finally:s.quit()
