#!/usr/bin/env python3
"""Memory at chosen steps of a VERIFY tape: dump_run.py OUT TAPE CUSTOM5 STEP...

Stops at the frame-wait exit of each STEP (as state_run.py) and saves OUT/sNNNN.chip (chip
$0-$80000) and OUT/sNNNN.img (the game image from reloc_base, original numbering from $1000).
Compare two runs with mem_diff.py."""
import os,struct,sys
from pathlib import Path
os.environ.setdefault('SLAVE',os.path.join(os.path.dirname(os.path.abspath(__file__)),'../tmp/build/verify/PrinceOfPersia.Slave'))
from pop import Session
from verify import Verify
from state_run import IMAGE
if __name__=='__main__':
    out=Path(sys.argv[1]);tape,opt=sys.argv[2],sys.argv[3];steps=[int(x) for x in sys.argv[4:]]
    s=Session(out,dict(WHD_ARGS=f'CUSTOM4={tape} CUSTOM5={opt}'));v=Verify(s)
    try:
        while True:
            s.fields(25)
            try:v.addr('verify_block');break
            except RuntimeError:pass
        rb=struct.unpack('>I',s.read(v.live(v.sym['_reloc_base']),4))[0]
        for st in steps:
            v.until_step(st,'verify_wait_stopped')
            (out/f's{st:04d}.chip').write_bytes(s.read(0,0x80000));(out/f's{st:04d}.img').write_bytes(s.read(rb,IMAGE))
    finally:s.quit()
