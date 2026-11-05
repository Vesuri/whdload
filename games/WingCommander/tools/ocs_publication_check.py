#!/usr/bin/env python3
"""Execute OCS ownership adapter and native publication; beam/OS are explicit stubs."""
import argparse
import json
from pathlib import Path
from ocs_display_check import Native, CODE, DATA, PLANES, OTHER, long, word, STACK
from ocs_c2p import assemble
from ocs_memory_build import NATIVE
from ocs_reconstruct import ROOT, new_output, require

MODULE=0x180000

def check(out, mutation=None):
    source=(ROOT/'src/ocs_publication.s').read_text()
    if mutation:source=source.replace(*mutation)
    text='\n'.join(f'{key} equ ${CODE+off:x}' for key,off in NATIVE.items())+'\n'+source
    blob,sy=assemble(out,'publication',text)
    results=[]
    for clock in (0,0xfffffffe,0xffffffff):
      for index in (0,1):
       for mode in ('idle','future','locked','copper-locked','early','late','overrun','ready'):
        c=Native(ROOT/'tmp/game/WingCommander/data/Wing.english')
        try:
            c.setup(320,16,bytes([0x12])*5120)
            c.write(MODULE,blob)
            def put(n,v,size=4):c.write(MODULE+sy[n],v.to_bytes(size,'big'))
            def get(n,size=4):return c.get(MODULE+sy[n],size)
            c.write(CODE+0x33442,b'\x4e\xf9'+long(MODULE+sy['ocs_publish_queue']))
            c.write(CODE+0x342c0,b'\x4e\xf9'+long(MODULE+sy['ocs_publish_irq']))
            c.write(CODE+0x3352c,long(CODE+0x331b8))
            gfx=0x9000;c.write(CODE+0x33518,long(gfx))
            for i,pointer in enumerate((0x1a000,0x1b000)):
                st=0x184000+i*32;c.write(st+4,long(pointer));c.write(CODE+0x3360c+i*4,long(st))
            c.write(CODE+0x33a6c,word(-1));c.write(DATA+0x77ae,word(-1))
            c.write(CODE+0x331d8,word(index));c.write(DATA+0x77fe,long(clock))
            put('ocs_game_a4',DATA+0x7ffe)
            c.run(0x32e06,registers={5:0x12345678}) # actual completion queues, never publishes immediately
            require(get('ocs_pending',2)==1 and get('ocs_pending_index',2)==index,'completion not queued')
            require(get('ocs_target_field')==(clock+1)&0xffffffff,'wrong forecast field')
            require(not c.mmio_events,'publication before blank')
            if mode=='idle':put('ocs_pending',0,2)
            c.write(DATA+0x77fe,long(clock-1 if mode=='future' else clock))
            if mode=='locked':c.write(DATA+0x77ae,word(0))
            if mode=='copper-locked':c.write(CODE+0x33a6c,word(0))
            beams=iter([0,15,16,20] if mode=='early' else [33] if mode=='late' else [16,41] if mode=='overrun' else [16,20])
            def beam():c.reg(9,next(beams));c.return_call()
            c.intercept(MODULE+sy['ocs_publish_beam'],beam)
            regs={r:0x12340000+r for r in range(1,17) if r!=8}
            c.run(0x342a2,registers=regs)
            require(c.reg(9)==0 and c.reg(1)==0xdff000,'native VBL return ABI')
            require(all(c.reg(r)==v for r,v in regs.items() if r not in (1,9)),'VBL register damage')
            require(c.reg(8)==STACK+4,'VBL stack damage')
            success=mode in ('early','ready')
            require(get('ocs_pending',2)==(0 if success or mode=='idle' else 1),'premature buffer release')
            jumps=[x for x in c.mmio_events if x[0]==0x8a]
            require(bool(jumps)==success,'unsafe Copper restart')
            if success:
                require(get('ocs_front')==(PLANES,OTHER)[index],'wrong displayed owner')
                require(get('ocs_display_field')==(clock+1)&0xffffffff,'wrong actual display field')
                require(c.get(0xdff084,4)==(0x1a000,0x1b000)[index],'wrong native Copper selection')
            results.append((clock,index,mode))
        finally:c.close()
    for entry,args in [('ocs_publish_rotate',b''),('ocs_publish_clear',word(0)),
                       ('ocs_publish_pixel',word(5)+word(4)+word(2)),('ocs_publish_close',b'')]:
        c=Native(ROOT/'tmp/game/WingCommander/data/Wing.english')
        try:
            c.setup(320,16,bytes([0x12])*5120);c.write(MODULE,blob)
            c.write(MODULE+sy['ocs_pending'],word(1));polls=[];retired=[]
            def retire():retired.append(True);c.return_call()
            def poll():
                polls.append(True)
                if len(polls)==3:c.write(MODULE+sy['ocs_pending'],word(0))
            c.intercept(CODE+0x32990,retire)
            c.intercept(MODULE+sy['ocs_publish_wait']+6,poll)
            c.intercept(CODE+0x33872,lambda:c.return_call())
            c.run(MODULE-CODE+sy[entry],args)
            require(len(polls)==3,'pending wait bypassed')
            require(entry=='ocs_publish_rotate' or retired,'native completion wait bypassed')
            require(c.reg(8)==STACK+4,'task wrapper stack damage')
            results.append(entry)
        finally:c.close()
    return results


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args()
    out=new_output(a.output);out.mkdir(parents=True)
    cases=check(out)
    rejected=[]
    for n,mutation in enumerate((('        bhi.s   .late','        nop\n        nop'),
                                ('        bpl.w   .done','        nop\n        nop'),
                                ('        bmi.w   .done','        nop\n        nop'),
                                ('move.w  #1,(a1)','clr.w   (a1)'),
                                ('        bne.s   .wait','        nop'),
                                ('        jsr     OCS_WAIT','        nop'))):
        d=out/f'negative-{n}';d.mkdir()
        try:check(d,mutation)
        except (ValueError,StopIteration):rejected.append(n)
        else:raise ValueError('ownership defect survived')
    (out/'report.json').write_text(json.dumps(dict(passed=True,cases=cases,rejected=rejected),indent=2)+'\n')
    print(len(cases),'publication cases;',len(rejected),'defects rejected')

if __name__=='__main__':main()
