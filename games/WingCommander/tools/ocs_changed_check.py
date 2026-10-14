#!/usr/bin/env python3
"""Execute C6 dual histories and invalidation against independent OCS pixels.
Unicorn is a functional instrument, never a performance measurement.
"""
import argparse
import hashlib
import json
import random
import struct
from c2p_check import CPU, BASE, STACK, STOP, u, ck
from ocs_c2p import assemble, source, candidates
from ocs_display_check import reference
from ocs_reconstruct import ROOT, new_output, require

SRC, DST = 0x40000, (0x60000,0x70000)


def exercise(blob,sy,model,arm):
    c=CPU(blob,model);rng=random.Random(0xc6);cases=[]
    history=BASE+sy['ocs_changed_history'];meta=BASE+sy['ocs_changed_meta']
    def call(label,src,height,index):
        c.write(SRC,src);c.write(STACK,struct.pack('>I',STOP))
        for r in range(1,17):c.reg(r,0x12340000+r)
        c.reg(1,SRC);c.reg(2,DST[index]);c.reg(8,STACK);c.reg(9,320);c.reg(10,height)
        before=[c.reg(r) for r in range(1,17)]
        planes=[c.read(p-64,32448) for p in DST];c.writes=[]
        ck(u.uc_emu_start(c.h,BASE+sy[label],STOP,10000000,3000000))
        require(c.reg(18)==STOP and c.reg(9)==0,'conversion failed')
        require(c.reg(8)==STACK+4,'stack balance')
        require(all(c.reg(r)==before[r-1] for r in range(1,17) if r not in (8,9)),'register preservation')
        require(c.read(SRC,len(src))==src,'source changed')
        packed=reference(src,320,height);plane=40*(height+2);n=40*(height-1)
        expected=bytearray(planes[index])
        for p in range(4): expected[64+p*plane+80:64+p*plane+80+n]=packed[p*n:(p+1)*n]
        require(c.read(DST[index]-64,32448)==expected,'pixels/padding differ')
        require(c.read(DST[1-index]-64,32448)==planes[1-index],'opposite destination modified')
        stores=0
        for address,size in c.writes:
            if DST[index]<=address<DST[index]+32320:
                require(any(DST[index]+p*plane+80<=address and address+size<=DST[index]+p*plane+80+n for p in range(4)),'padding write')
                stores+=size
            else:
                require(STACK-512<=address and address+size<=STACK or history<=address and address+size<=history+128000 or meta<=address and address+size<=meta+34,'unowned write')
        cases.append(dict(height=height,index=index,stores=stores))
        return stores
    try:
        for p in DST:c.write(p-64,b'\xa5'*32448)
        for height in (128,200,166,16,200):
            src=bytearray(rng.randbytes(320*height))
            for index in (0,1):call('ocs_changed_'+arm,bytes(src),height,index)
            for index in (0,1):require(call('ocs_changed_'+arm,bytes(src),height,index)==0,'unchanged block stored')
            # Last byte of first block, first byte of second, row parity, edge,
            # last converted pixel; each must affect both independent histories.
            for at in (31,32,321,643,320*(height-1)-1):
                src[at]^=255
                for index in (0,1):require(call('ocs_changed_'+arm,bytes(src),height,index)==16,'wrong changed block extent')
            # A direct planar writer/clear/modal display rebuild invalidates both.
            c.write(STACK,struct.pack('>I',STOP));c.reg(8,STACK)
            ck(u.uc_emu_start(c.h,BASE+sy['ocs_changed_invalidate'],STOP,1000000,10000))
            for p in DST:c.write(p,b'\x5a'*32320)
            for index in (0,1):require(call('ocs_changed_'+arm,bytes(src),height,index)==160*(height-1),'invalidation omitted full refresh')
            # Palette-only change leaves indices valid; still no store needed.
            for index in (0,1):require(call('ocs_changed_'+arm,bytes(src),height,index)==0,'palette-independent repeat')
        return cases
    finally:c.close()



def borrow(build):
    """Execute the native scratch-loan API with the generated guarded wrapper."""
    from pathlib import Path
    from ocs_display_check import Native, CODE, long, word
    b=json.loads((Path(build)/'build.json').read_text());sy=b['symbols']
    payload=bytearray((Path(build)/'WingCommander.Slave').read_bytes()[32:-4]);base=0x500000
    for pos in b['fixups']:
        value=int.from_bytes(payload[pos:pos+4],'big')
        payload[pos:pos+4]=long(CODE+(value&0xfffffff))
    for index in (0,1):
        c=Native(ROOT/'tmp/originals/ocs/WingCommander/data/Wing.english');events=[]
        try:
            c.write(base,bytes(payload))
            c.write(CODE+0x3250c,struct.pack('>HI',0x4ef9,base+sy['ocs_changed_borrow']))
            c.write(CODE+0x331b8,long(32320));c.write(CODE+0x331c0,long(0x20000))
            c.write(CODE+0x331d8,word(index))
            for offset in (0,16):c.write(base+sy['ocs_changed_meta']+offset,long(0x20000+offset))
            def native_wait():events.append('native wait');c.return_call()
            def drain():events.append('publication drain');c.return_call()
            c.intercept(CODE+0x3262e,native_wait)
            c.intercept(base+sy['ocs_publish_drain'],drain)
            c.run(0x32504,long(0x180000))
            require(events==['native wait','publication drain'],'scratch loan before ownership drain')
            require(c.get(0x180000,4)==0x20000+(32320 if index==0 else 0),'wrong scratch base')
            require(c.get(0x180004,4)==64640,'wrong scratch extent')
            require(all(c.get(base+sy['ocs_changed_meta']+offset,4)==0 for offset in (0,16)),'scratch loan left valid history')
        finally:c.close()
    return 2


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--build');a=p.parse_args()
    out=new_output(a.output);out.mkdir(parents=True)
    text=(ROOT/'whdload/ocs_changed.s').read_text()+'\n'+source(candidates())+'\nocs_changed_history: ds.b 128000\n'
    blob,sy=assemble(out,'changed',text)
    results={f'{model}-{arm}':exercise(blob,sy,model,arm) for model,arm in ((1,'word'),(2,'long'))}
    rejected=[]
    for name,old,new in [('ignore_invalidation','clr.l   16(a0)','nop'),('skip_last_long','moveq   #7,d2','moveq #6,d2'),('omit_history_write','move.l  d0,(a1)+','addq.l #4,a1')]:
        bad,bs=assemble(out,name,text.replace(old,new))
        try:exercise(bad,bs,1,'word')
        except (ValueError,AssertionError):rejected.append(name)
        else:raise ValueError('mutation escaped: '+name)
    (out/'report.json').write_text(json.dumps(dict(passed=True,cases=results,borrow_cases=borrow(a.build) if a.build else 0,rejected=rejected,sha256=hashlib.sha256(blob).hexdigest()),indent=2)+'\n')
    print(sum(map(len,results.values())),'pixel/history cases;',len(rejected),'mutations rejected')

if __name__=='__main__':main()
