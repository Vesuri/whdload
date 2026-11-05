import os,sys
from pathlib import Path
from drive import Session,to_race,rd
os.environ['SLAVE']=str(Path(__file__).resolve().parents[1]/'tmp/build/RoadRash-verify.slave')
s=Session(sys.argv[1])
try:
    to_race(s,100)
    print('find',s.cmd('find /b 0x200000,0xa00000,0x52,0x52,0x41,0x31,0x53,0x54,0x41,0x54'),flush=True)
    for command in ['monitor fields 1','monitor fields 2','monitor fields 3']:
        before=rd(s,0xa5d4c)
        print(command,s.cmd(command),before,rd(s,0xa5d4c),flush=True)
    s.shot('probe.png')
    print('after shot',rd(s,0xa5d4c),flush=True)
    print(s.cmd('x/40wx 0x909cc'),flush=True)
    print(s.cmd('monitor aprof start'),flush=True)
    print(s.cmd('monitor fields 9'),flush=True)
    print(s.cmd(f'monitor aprof stop {s.out}/aprof.txt'),flush=True)
finally:s.quit()
