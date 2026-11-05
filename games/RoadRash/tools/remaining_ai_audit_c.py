"""Read native opponent attack selection before interpreting its timing."""
import sys
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 for start,end,name in [(0x8db0a,0x8dd66,'remaining-ai'),(0xb3e00,0xb3f50,'blit-hotspot')]:
  (s.out/(name+'.txt')).write_text(s.cmd(f'disassemble {start:#x},{end:#x}'))
finally:s.quit()
