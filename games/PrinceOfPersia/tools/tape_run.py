#!/usr/bin/env python3
"""Play a VERIFY input tape: tape_run.py OUT TAPE STEP... [then fields]

Boots the VERIFY slave with CUSTOM4=TAPE (no host input), runs to the start of each gameplay
STEP and saves sSTEP.png (the last published frame). A final +N runs N more fields and saves end.png.
"""
import os,sys
os.environ.setdefault('SLAVE',os.path.join(os.path.dirname(os.path.abspath(__file__)),'../tmp/build/verify/PrinceOfPersia.Slave'))
from pop import Session
from verify import Verify
def play(out,tape,steps,env=None):
    s=Session(out,dict(WHD_ARGS=f'CUSTOM4={tape}',**(env or {})))
    try:
        v=Verify(s)
        while True:            # until the slave is loaded; the title's first poll comes later
            s.fields(25)
            try:v.addr('verify_block');break
            except RuntimeError:pass
        for st in steps:
            if st.startswith('+'):s.fields(int(st[1:]));s.shot('end.png');continue
            v.until_step(int(st));s.shot(f's{int(st):04d}.png')
        return s,v
    finally:s.quit()
if __name__=='__main__':play(sys.argv[1],int(sys.argv[2]),sys.argv[3:])
