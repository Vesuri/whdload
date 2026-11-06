#!/usr/bin/env python3
"""A3 timing baseline of a tape: timing_run.py OUT TAPE FIELDS [CUSTOM5] -> OUT/verify.bin (frame_log.py)."""
import os,sys
from pathlib import Path
os.environ.setdefault('SLAVE',os.path.join(os.path.dirname(os.path.abspath(__file__)),'../tmp/build/verify/PrinceOfPersia.Slave'))
from pop import Session
from verify import Verify
out=Path(sys.argv[1]);tape,n=sys.argv[2],int(sys.argv[3]);opt=sys.argv[4] if len(sys.argv)>4 else '0'
s=Session(out,dict(WHD_ARGS=f'CUSTOM4={tape} CUSTOM5={opt}'))
try:
    while n>0:k=min(500,n);s.fields(k);n-=k
    (out/'verify.bin').write_bytes(Verify(s).dump());s.shot('end.png')
finally:s.quit()
