import sys
from harness_a import *
from drive import barto
s=Session(sys.argv[1])
try:
 route(s);s.input('JOY2_UP',1);advance(s,450)
 p=s.out/'fields.bin';s.cmd(f'monitor profile 50 "" "{p}"',timeout=120)
 trace=barto.load(str(p))
 for i,f in enumerate(trace.fields):(s.out/f'frame-{i:02d}.png').write_bytes(f.shot)
 p.unlink()
finally:s.quit()
