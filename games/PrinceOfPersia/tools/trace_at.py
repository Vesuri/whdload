#!/usr/bin/env python3
"""Raw traces at a tape step: trace_at.py OUT TAPE STEP FIELDS [CUSTOM5]

Boots the VERIFY slave on TAPE, runs to the start of gameplay STEP and keeps FIELDS fields of
raw `monitor profile` trace in OUT/tNNNNN.bin chunks of at most 10 fields (~5 MB per field;
delete them when done). OUT/meta.json has reloc_base and the chunk list.
"""
import json,os,struct,sys
from pathlib import Path
os.environ.setdefault('SLAVE',os.path.join(os.path.dirname(os.path.abspath(__file__)),'../tmp/build/verify/PrinceOfPersia.Slave'))
from pop import Session
from verify import Verify
if __name__=='__main__':
    out=Path(sys.argv[1]).resolve();tape,step,n=sys.argv[2],int(sys.argv[3]),int(sys.argv[4])
    opt=sys.argv[5] if len(sys.argv)>5 else '0'
    s=Session(out,dict(WHD_ARGS=f'CUSTOM4={tape} CUSTOM5={opt}'));v=Verify(s);meta=dict(chunks=[])
    try:
        while True:
            s.fields(25)
            try:v.addr('verify_block');break
            except RuntimeError:pass
        meta['reloc_base']=struct.unpack('>I',s.read(v.live(v.sym['_reloc_base']),4))[0]
        meta['slave_at']=v.live(0)
        v.until_step(step);i=0
        while i<n:
            k=min(10,n-i);p=out/f't{i:05d}.bin';s.profile(k,p);meta['chunks'].append([p.name,i,k]);i+=k
            print('traced',i,flush=True)
    finally:s.quit()
    (out/'meta.json').write_text(json.dumps(meta,indent=1)+'\n')
