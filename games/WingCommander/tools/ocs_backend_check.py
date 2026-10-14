#!/usr/bin/env python3
"""Execute C3 selection, once-only cache flush and ABI gates on CPU models."""
import argparse
import itertools
import json
import struct
from c2p_check import CPU, BASE, STACK, STOP, ck, u
from ocs_c2p import assemble
from ocs_backend import choose, diagnostic, source
from ocs_reconstruct import new_output

STATE, COUNTER = 0x30000, 0x30010


def call(c, entry, values, init=False):
    for r in range(1,17): c.reg(r,0x12340000+r)
    c.reg(8,STACK)
    for n,v in enumerate(values):c.reg(9+n,v)
    if init:
        c.reg(1,STATE);c.reg(2,BASE+entry['flush'])
        pc=entry['ocs_backend_init']
    else: pc=entry['ocs_backend_choose']
    before=[c.reg(r) for r in range(1,17)]
    c.write(STACK,struct.pack('>I',STOP));c.writes=[]
    ck(u.uc_emu_start(c.h,BASE+pc,STOP,1000000,1000))
    assert c.reg(18)==STOP,'did not return'
    after=[c.reg(r) for r in range(1,17)]
    assert all(before[r-1]==after[r-1] for r in range(1,17) if r not in (8,9)),'ABI register'
    assert c.reg(8)==STACK+4,'stack'
    for address,size in c.writes:
        assert STACK-64<=address and address+size<=STACK or init and (
            STATE<=address and address+size<=STATE+8 or address==COUNTER and size==4),'unexpected write'
    return c.reg(9)


def check(blob,sy):
    count=0
    for model in (1,2,4):
        c=CPU(blob,model)
        try:
            for option,cpu,profile,ready in itertools.product((0,1,2,3,0xffffffff),(0,10,20,30,40,60,1,0xffffffff),(0,1,2),range(9)):
                values=(option,cpu,profile,ready)
                # Explicit expected table, independent of host selection helper.
                expected=0
                if ready==7:
                    if option==2 and cpu in (0,10):expected=1
                    if option==2 and cpu in (20,30,40,60):expected=2
                    if option==0 and profile==1 and cpu==20:expected=2
                assert choose(*values)==expected
                assert call(c,sy,values)==expected,(model,values,expected)
                count+=1
            for values,expected in (((0,20,1,7),2),((2,0,0,7),1),((2,10,0,7),1),((0,40,0,7),0),((2,20,1,0),0),((1,20,1,7),0)):
                c.write(STATE,bytes(20))
                assert call(c,sy,values,True)==expected
                # Flush executes before either state word is committed.
                writes=[a for a,n in c.writes if a in (STATE,STATE+4,COUNTER)]
                assert writes==[COUNTER,STATE+4,STATE],'flush/commit ordering'
                assert c.read(STATE,8)==struct.pack('>II',0x4f435333,expected)
                assert c.read(COUNTER,4)==struct.pack('>I',1)
                # Different subsequent option/CPU/readiness cannot switch a live source.
                assert call(c,sy,(2,60,1,7) if expected!=2 else (1,0,0,0),True)==expected
                assert not [a for a,n in c.writes if STATE<=a<COUNTER+4],'reinitialized'
            assert c.read(BASE,len(blob))==blob,'code changed'
        finally:c.close()
    return count


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True)
    a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
    text=source()+f'\nflush: addq.l #1,${COUNTER:x}\n rts\n'
    blob,sy=assemble(out,'backend',text)
    count=check(blob,sy)
    # MEMF_FAST must not turn trapdoor slow RAM or a missing reservation into Fast.
    for option in ('auto','cpu'):
        assert diagnostic(option,'68020',0xc00000,0xce0000,64000)['arm']=='native'
        assert diagnostic(option,'68020',0x200000,0x5f0000,64000,unavailable=True)['arm']=='native'
        assert diagnostic(option,'68020',0x200000,0x5ffffe,64000)['arm']=='native'
    assert diagnostic('auto','68040',0x200000,0x500000,64000)['arm']=='native'
    assert diagnostic('cpu','68040',0x200000,0x500000,64000)['arm']=='fast-long'
    assert diagnostic('auto','68020',0x200000,0x500000,64000,profile='unknown')['arm']=='native'
    mutations=[]
    for name,old,new in (('wrong long path','moveq   #2,d0','moveq   #1,d0'),
                         ('missing flush','jsr     (a1)','nop'),
                         ('reselection','beq.s   .ready','nop')):
        bad,bs=assemble(out,name,text.replace(old,new,1))
        try:check(bad,bs)
        except AssertionError:mutations.append(name)
        else:raise AssertionError('accepted mutation: '+name)
    result=dict(passed=True,selection_cases=count,init_and_repeat_cases=36,
                rejected_mutations=mutations,models=[68000,68020,68040],bytes=len(blob))
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
if __name__=='__main__':main()
