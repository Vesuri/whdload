#!/usr/bin/env python3
"""Memory snapshots at gameplay steps: snap.py OUT TAPE CUSTOM5 STEP...

Boots the VERIFY slave on tape TAPE with CUSTOM5 options and, at the start of each STEP,
saves OUT/STEP.chip (SNAP_AT=verify_wait_stopped: at its frame-wait exit instead) (0-$80000) and OUT/STEP.game (the relocated image, original $1000-$47800)."""
import os,struct,sys
from pathlib import Path
os.environ.setdefault('SLAVE',os.path.join(os.path.dirname(os.path.abspath(__file__)),'../tmp/build/verify/PrinceOfPersia.Slave'))
from pop import Session
from verify import Verify
IMAGE=0x46800
out=Path(sys.argv[1]);tape,opt=sys.argv[2:4]
s=Session(out,dict(WHD_ARGS=f'CUSTOM4={tape} CUSTOM5={opt}'))
try:
    v=Verify(s)
    while True:
        s.fields(25)
        try:v.addr('verify_block');break
        except RuntimeError:pass
    rb=struct.unpack('>I',s.read(v.live(v.sym['_reloc_base']),4))[0]
    (out/'reloc_base').write_text(hex(rb))
    for st in sys.argv[4:]:
        v.until_step(int(st),os.environ.get('SNAP_AT','verify_stopped'))
        (out/f'{st}.chip').write_bytes(s.read(0,0x80000));(out/f'{st}.game').write_bytes(s.read(rb,IMAGE))
        print('step',st,flush=True)
finally:s.quit()
