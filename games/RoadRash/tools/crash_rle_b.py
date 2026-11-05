import json,os,sys
from harness_a import *
from matrix_a import config
os.environ.update(config('030-50'))
os.environ['SLAVE']=str(ROOT/'tmp/build/RoadRash.slave')
s=Session(sys.argv[1]);log=[]
try:
    pass
    for i in range(120):
        for state,n in ((1,4),(0,14)):
            s.input('JOY2_FIRE_BUTTON',state);reply=s.cmd(f'monitor fields {n}')
            s.cmd('maintenance flush register-cache');regs=s.cmd('info registers');log.append(dict(step=i,state=state,reply=reply,regs=regs))
            if 'Breakpoint' in reply or 'SIG' in reply:
                print(i,state,reply,regs,flush=True)
                (s.out/'stack.txt').write_text(s.cmd('x/80wx $sp'))
                (s.out/'chip.bin').write_bytes(read_bytes(s,0,0x100000))
                s.shot('exception.png');raise RuntimeError('captured stop')
        if i%20==0:print(i,regs.splitlines()[-1],flush=True)
    print(s.cmd('break *0xaef64 if ($d4 & 255)==128'),flush=True)
    print(s.cmd('continue',timeout=60),flush=True)
    print(s.cmd('info registers'),flush=True)
    (s.out/'stack.txt').write_text(s.cmd('x/40wx $sp'))
    (s.out/'chip.bin').write_bytes(read_bytes(s,0,0x100000))
finally:
    (s.out/'crash.json').write_text(json.dumps(log,indent=2));s.quit()
