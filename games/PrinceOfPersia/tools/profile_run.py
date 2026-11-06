#!/usr/bin/env python3
"""Profile a scripted route: profile_run.py OUT STEP...

Route steps as in route.py, plus P:N = trace N fields (in chunks of <=100). Each chunk goes
through AmigaXDev's amigaxdev.callprofile and is deleted; OUT keeps profile.pkl.gz (the
reduction), meta.json, slow.bin/chip.bin (first chunk's memory, for disassembly) and the
chunk-start screenshots. Frame-wait start/end are marks; the STOP blitter waits are tallied.
With the VERIFY slave (SLAVE=...) OUT also gets verify.bin, the block and its frame log
(tools/frame_log.py); WHD_ARGS=CUSTOM4=n in the environment selects a tape.
"""
import json,struct,sys
from pathlib import Path
from pop import Session,SLAVE,symbols
from verify import Verify
from route import run as route_run
from amigaxdev import barto
from amigaxdev.callprofile import Reduction
SYM=symbols();RELOC_BASE_OFF,RESLOAD_OFF=SYM['_reloc_base'],SYM['_resload']
FRAME_WAIT,FRAME_WAIT_END=0x1bd46,0x1bd5a       # game addresses (original numbering)
STOPS=(0x53be,0x53c8,0x53ee,0x53f8)              # STOP #$2000 after starting a blit

def find_reloc_base(t):
    code=SLAVE.read_bytes()[0x20:];probe=code[0x200:0x240]
    for mem,base in ((t.slow,0xc00000),(t.chip,0)):
        i=mem.find(probe)
        while i>=0:
            s=i-0x200
            if s>=0 and struct.unpack_from('>I',mem,s+RESLOAD_OFF)[0]:
                return struct.unpack_from('>I',mem,s+RELOC_BASE_OFF)[0],base+s
            i=mem.find(probe,i+1)
    raise RuntimeError('live slave not found')

if __name__=='__main__':
    out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
    s=Session(out,{});tmp=out/'chunk.bin';red=None;meta=dict(chunks=[])
    try:
        steps=[]
        for st in sys.argv[2:]:
            if not st.startswith('P:'):steps.append(st);continue
            if steps:route_run(s,steps);steps=[]
            n=int(st[2:])
            while n>0:
                k=min(100,n);start=s.field;s.profile(k,tmp);t=barto.load(str(tmp))
                if red is None:
                    rb,sl=find_reloc_base(t);g=lambda o:rb+o-0x1000
                    meta.update(reloc_base=rb,slave_at=sl)
                    if 'verify_wait' in SYM:   # the VERIFY slave replaces the frame wait
                        marks={'wait':sl+SYM['verify_wait'],'wait_end':sl+SYM['verify_wait_end'],'poll':sl+SYM['verify_poll']}
                    else:marks={'wait':g(FRAME_WAIT),'wait_end':g(FRAME_WAIT_END)}
                    red=Reduction(marks=marks,tally=[g(o) for o in STOPS])
                    (out/'slow.bin').write_bytes(t.slow);(out/'chip.bin').write_bytes(t.chip)
                red.feed(t);(out/f'c{start:05d}.png').write_bytes(t.fields[0].shot)
                del t;tmp.unlink();meta['chunks'].append((start,k));n-=k
                print('traced',start,k,flush=True)
        if steps:route_run(s,steps)
        if 'verify_block' in SYM:(out/'verify.bin').write_bytes(Verify(s).dump())
    finally:
        s.quit()
        if tmp.exists():tmp.unlink()
    red.save(out/'profile.pkl.gz');(out/'meta.json').write_text(json.dumps(meta,indent=1)+'\n')
    print('reloc_base',hex(meta['reloc_base']),'slave',hex(meta['slave_at']),'fields',len(red.fields))
