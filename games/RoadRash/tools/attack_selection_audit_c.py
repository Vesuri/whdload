"""Read native opponent attack selection before interpreting its timing."""
import sys
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 for start,end,name in [(0x90090,0x90820,'attack-selection'),(0x8d2c0,0x8d966,'ai-dispatch')]:
  (s.out/(name+'.txt')).write_text(s.cmd(f'disassemble {start:#x},{end:#x}'))
finally:s.quit()
