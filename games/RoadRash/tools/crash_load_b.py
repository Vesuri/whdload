import os,sys,json
from harness_a import *
from matrix_a import config
os.environ.update(config('030-50'));os.environ['SLAVE']=str(ROOT/'tmp/build/RoadRash.slave')
s=Session(sys.argv[1])
try:
    for i in range(119):
        s.input('JOY2_FIRE_BUTTON',1);s.cmd('monitor fields 4')
        s.input('JOY2_FIRE_BUTTON',0);s.cmd('monitor fields 14')
    s.cmd('break *0xb2a00');print(s.cmd('continue',timeout=60),flush=True)
    print(s.cmd('info registers'),flush=True);print(s.cmd('x/48hx 0xdff000'),flush=True)
    (s.out/'before.bin').write_bytes(read_bytes(s,0,0x100000))
    s.cmd('delete breakpoints');s.cmd('break *0xb2a04');print(s.cmd('continue',timeout=60),flush=True)
    print(s.cmd('info registers'),flush=True);print(s.cmd('x/48hx 0xdff000'),flush=True)
    (s.out/'after.bin').write_bytes(read_bytes(s,0,0x100000))
finally:s.quit()
