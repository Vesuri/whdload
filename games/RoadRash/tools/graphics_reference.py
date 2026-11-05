import sys
from harness_a import *
s=Session(sys.argv[1])
try:
 for i in range(1500):
  try:ready=rd(s,0x4f2)==2224 and rd(s,0x81e6e,2)==0x41f9
  except (ValueError,IndexError):ready=False
  if ready:break
  s.input('JOY2_FIRE_BUTTON',int(i%4==0));s.cmd('monitor fields 4')
 else:raise RuntimeError('menu not reached')
 s.input('JOY2_FIRE_BUTTON',0);s.cmd('monitor fields 399');s.shot('menu.png')
 route(s);s.shot('race.png')
finally:s.quit()
