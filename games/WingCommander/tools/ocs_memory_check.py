#!/usr/bin/env python3
"""Execute C4 allocation/rollback with native registry and surface routines.
Exec allocation services are modelled; this is an ownership gate, not live DMA
or a measured RAM minimum. Generated instructions and reports stay in tmp/.
"""
import argparse
import json
import struct
from pathlib import Path
from ocs_c2p import assemble
from ocs_display_check import Native, CODE, DATA, STACK, long, word
from ocs_reconstruct import ROOT, new_output, require

MODULE = 0x180000
SURFACE = DATA+0x7ffe+0x10e2
RECTANGLE = 0x184000
EXEC = 0x8000


def source():
    return '\n'.join(f'{name} equ ${CODE+offset:x}' for name,offset in (
        ('OCS_CHIP_ALLOC',0x33b60),('OCS_REGISTER',0x33c8e),
        ('OCS_SURFACE_CREATE',0x31dc4),('OCS_SURFACE_FREE',0x32476),
        ('OCS_DISPLAY_CREATE',0x33200),('OCS_PUBLIC_ALLOC',0x33b76),
        ('OCS_DISPLAY_FREE',0x32526),('OCS_CONVERSION',0x324a8),
        ('OCS_WAIT',0x32990),('OCS_SURFACE_FREE_BODY',0x3247c)))+'\n'+(ROOT/'src/ocs_memory.s').read_text()


def case(blob, sy, backend, fast_bank, failures, primary=True, public=False, full=False, width=320, height=200):
    c=Native(ROOT/'tmp/game/WingCommander/data/Wing.english')
    active={}; events=[]; calls=0
    cursor={'chip':0x20000,'fast':fast_bank,'public':0x190000}
    try:
        c.write(MODULE,blob)
        c.write(MODULE+sy['ocs_requested_backend'],long(backend))
        c.write(4,long(EXEC))
        c.write(CODE+0x31e1e,struct.pack('>HI',0x4eb9,MODULE+sy['ocs_source_allocate']))
        c.write(CODE+0x32476,struct.pack('>HI',0x4ef9,MODULE+sy['ocs_source_free']))
        def retire():
            events.append(('retire',))
            c.return_call()
        c.intercept(CODE+0x32990,retire)
        if full: c.write(DATA+0x7ffe-0x844,word(120))
        def allocate():
            nonlocal calls
            calls+=1
            size,flags=c.reg(9),c.reg(10)
            bank='chip' if flags&2 else 'fast' if flags&4 else 'public'
            events.append(('alloc',bank,size,calls))
            if calls in failures:
                c.return_call(0);return
            address=cursor[bank];cursor[bank]+=(size+7)&~7
            require(address not in active,'overlapping allocator result')
            active[address]=size
            c.write(address,bytes(size))
            c.return_call(address)
        def free():
            address,size=c.reg(2),c.reg(9)
            require(active.pop(address,None)==size,'wrong or double free')
            if primary and not public and not full and address in (0x20000,0x200000):
                require(('retire',) in events,'owned source freed before retirement')
            events.append(('free',address,size))
            c.return_call()
        c.intercept(EXEC-198,allocate)
        c.intercept(EXEC-210,free)
        surface=SURFACE if primary else SURFACE+64
        c.write(RECTANGLE,struct.pack('>4h',5,7,4+width,6+height))
        args=long(surface)+long(RECTANGLE)
        entry=MODULE-CODE+sy['ocs_source_create'] if primary and not public else 0x31da8 if public else 0x31dc4
        regs={r:0x13570000+r for r in list(range(3,5))+list(range(6,8))+list(range(11,17))}
        c.run(entry,args,regs)
        require(all(c.reg(r)==v for r,v in regs.items()),'nonvolatile register changed')
        require(c.reg(8)==STACK+4,'unbalanced stack')
        result=c.reg(9)
        source_pointer=c.get(surface+4,4);rows=c.get(surface+8,4)
        selected=c.get(MODULE+sy['ocs_source_backend'],4)
        if result:
            require(len(active)==2,'successful surface must own exactly source and rows')
            require(active[source_pointer]==width*height and active[rows]==4*height,'wrong extent')
            for y in range(height):
                require(c.get(rows+4*y,4)==source_pointer-5+width*y,'wrong row alias')
            require(c.get(surface,4)==rows-28,'wrong biased row owner')
            expected=backend if primary and not public and backend and fast_bank==0x200000 and 1 not in failures and (width,height)==(320,200) else 0
            require(selected==expected,'wrong selected owner')
            require((0x200000<=source_pointer<0xa00000)==bool(expected),'wrong memory bank')
            # Native surface cleanup clears all owning pointers and registry.
            c.run(0x32476,long(surface))
        else:
            require(primary and not public,'unexpected unwrapped failure')
            require(source_pointer==rows==c.get(surface,4)==selected==0,'partial setup not rolled back')
        if primary and not public:
            require(('retire',) in events,'source retirement missing')
            retirement=events.index(('retire',))
            # Rejected Fast blocks may be freed before retirement: they were
            # never published. Native owned source/rows must be freed after it.
            require(all(e[0]!='free' for e in events[retirement+1:]) if full else True,'unexpected full-registry free')
            require(c.get(MODULE+sy['ocs_source_backend'],4)==0,'stale source backend')
        require(not active,'allocation leaked')
        require(c.get(DATA+0x7ffe-0x844)==(120 if full else 0),'registry leak')
        return dict(backend=backend,fast_bank=hex(fast_bank),failures=failures,
                    primary=primary,public=public,registry_full=full,width=width,height=height,success=bool(result),events=events)
    finally:c.close()


def display_cases(blob,sy):
    c=Native(ROOT/'tmp/game/WingCommander/data/Wing.english')
    active={}; events=[]; calls=0; fail=0
    cursor={'chip':0x20000,'public':0x190000}
    try:
        c.write(MODULE,blob);c.write(4,long(EXEC))
        for off in (0x33614,0x33674,0x34076):
            c.intercept(CODE+off,lambda:c.return_call(1))
        def allocate():
            nonlocal calls
            calls+=1
            size,flags=c.reg(9),c.reg(10)
            if calls==fail:c.return_call(0);return
            bank='chip' if flags&2 else 'public'
            address=cursor[bank];cursor[bank]+=(size+7)&~7
            active[address]=size;c.write(address,bytes(size))
            events.append(('alloc',bank,size));c.return_call(address)
        def free():
            address,size=c.reg(2),c.reg(9)
            require(active.pop(address,None)==size,'display double/invalid free')
            events.append(('free',address,size));c.return_call()
        c.intercept(EXEC-198,allocate);c.intercept(EXEC-210,free)
        results=[]
        # Repeated native-size transitions, failure at every setup allocation,
        # followed by a successful retry in the same live native state.
        for height in (200,128,200):
            for failure in (1,2,3,0):
                calls=0;fail=failure;cursor.update(chip=0x20000,public=0x190000)
                c.run(MODULE-CODE+sy['ocs_display_create'],word(320)+word(height))
                require(c.reg(9)==int(failure==0),'display failure result')
                if not failure:
                    size=4*40*(height+2)
                    require(sorted(active.values())==[668,668,3*size],'display budget')
                    c.run(0x32526)
                require(not active,'display rollback leaked')
                require(c.get(DATA+0x7ffe-0x844)==0,'display registry leaked')
                require(c.get(CODE+0x331c0,4)==0,'display owner not cleared')
                require(c.get(CODE+0x324b8,4)==c.get(CODE+0x324bc,4)==0,'descriptor owner not cleared')
                results.append((height,failure))
        return results
    finally:c.close()


def check(blob,sy):
    results=[]
    for backend in (0,1,2):
        for bank in (0x200000,0xc00000):
            for failures in ([],[1],[2],[1,2],[1,3]):
                results.append(case(blob,sy,backend,bank,failures))
        results.append(case(blob,sy,backend,0x200000,[],primary=False))
        results.append(case(blob,sy,backend,0x200000,[],public=True))
        results.append(case(blob,sy,backend,0x200000,[],full=True))
        for width,height in ((160,200),(320,128)):
            results.append(case(blob,sy,backend,0x200000,[],width=width,height=height))
    return results


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True)
    a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
    text=source();blob,sy=assemble(out,'memory',text)
    results=check(blob,sy)
    displays=display_cases(blob,sy)
    rejected=[]
    for name,old,new in (
        ('missing rollback','jsr     OCS_SURFACE_FREE','nop'),
        ('accept slow RAM','cmpi.l  #$a00000,d1','cmpi.l  #$e00000,d1'),
        ('missing registry','jsr     OCS_REGISTER','nop'),
        ('missing display rollback','jsr     OCS_DISPLAY_FREE','nop'),
        ('missing source retirement','jsr     OCS_WAIT','nop')):
        require(old in text,'mutation absent')
        bad,bs=assemble(out,name,text.replace(old,new))
        try:
            check(bad,bs)
            display_cases(bad,bs)
        except (ValueError,RuntimeError,AssertionError):rejected.append(name)
        else:raise ValueError('mutation passed: '+name)
    report=dict(passed=True,cases=results,display_cases=displays,bytes=len(blob),rejected=rejected,
                limits=['Exec allocation stubbed','not installed at game startup',
                        'no live transition/DMA or minimum-RAM claim'])
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'{len(results)} allocation cases; {len(rejected)} rejecting controls')

if __name__=='__main__':main()
