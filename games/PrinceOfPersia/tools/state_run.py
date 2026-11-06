#!/usr/bin/env python3
"""A4 faithfulness hashes from the harness: state_run.py OUT TAPE CUSTOM5 LAST_STEP

Boots the VERIFY slave on tape TAPE and stops at the frame-wait exit of every gameplay step
up to LAST_STEP, with emulated time stopped, so the game can't tell. There it hashes:
  state:  chip $1000-$80000 and the image's data parts, minus EXCLUDE below
  pixels: the 40000-byte frame in $49d1c, which the VBL has just shown
OUT/hashes.json maps step -> [state, pixels]; OUT/verify.bin is the VERIFY block at the end.
CUSTOM5 bits: 1 work delay, 2 delay after publishing, 4 sabotage (one blit at step 150),
8 no time pin (B7: sounds end in real time)."""
import hashlib,json,os,struct,sys
from pathlib import Path
os.environ.setdefault('SLAVE',os.path.join(os.path.dirname(os.path.abspath(__file__)),'../tmp/build/verify/PrinceOfPersia.Slave'))
from pop import Session
from verify import Verify
IMAGE=0x46800
# (start, end, why); chip addresses, or 'g' for original image addresses.
EXCLUDE=[('chip',0x0,0x1000,'stack'),
         ('chip',0x1a22,0x1a24,'SR saved by g:$05410 (interrupts off)'),
         ('chip',0x46e66,0x46f42,'MIDI player and its tracks (real time)'),
         ('chip',0x46f4e,0x470ce,'MIDI synth voices (run by the VBL) and channel programs (real time)'),
         ('chip',0x47420,0x47440,'sound (real time)'),
         ('chip',0x49d10,0x49d20,'VBL countdown, display swap'),
         ('chip',0x49dc0,0x49e40,'sound driver channel records (real time)'),
         ('chip',0x53c2e,0x674ae,'the two display buffers (pixel hash)'),
         ('g',0x5320,0x1f7d0,'code (patched by optimisations)'),
         ('g',0x7080,0x70c0,'sound channel table (real time)')]
def state_hash(chip,image):
    c=bytearray(chip);g=bytearray(image)
    for kind,a,b,_ in EXCLUDE:
        if kind=='chip':c[a:b]=bytes(b-a)
        else:g[a-0x1000:b-0x1000]=bytes(b-a)
    return hashlib.sha1(bytes(c)+bytes(g)).hexdigest()[:16]
if __name__=='__main__':
    out=Path(sys.argv[1]);tape,opt,last=sys.argv[2],sys.argv[3],int(sys.argv[4])
    s=Session(out,dict(WHD_ARGS=f'CUSTOM4={tape} CUSTOM5={opt}'));v=Verify(s);res={}
    try:
        while True:
            s.fields(25)
            try:v.addr('verify_block');break
            except RuntimeError:pass
        rb=struct.unpack('>I',s.read(v.live(v.sym['_reloc_base']),4))[0]
        for st in range(max(1,v.long('verify_steps')+1),last+1):
            v.until_step(st,'verify_wait_stopped')
            chip=s.read(0,0x80000);img=s.read(rb,IMAGE);buf=struct.unpack_from('>I',chip,0x49d1c)[0]
            res[st]=[state_hash(chip,img),hashlib.sha1(chip[buf:buf+40000]).hexdigest()[:16]]
            if st%25==0: print(f'{out}: step {st}',flush=True)
        (out/'verify.bin').write_bytes(v.dump())
    finally:s.quit()
    (out/'hashes.json').write_text(json.dumps(res)+'\n')
