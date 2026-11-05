#!/usr/bin/env python3
"""Execute candidate startup guards, relocation, backend choice and cache flush."""
from runtime_buffers import load as load_slave
import argparse
import json
from pathlib import Path
from ocs_display_check import Native, CODE, long, word, STOP, ck, u
from ocs_memory_build import HOOKS, NATIVE
from ocs_reconstruct import ROOT, new_output, require


def check(build):
    b=json.loads((build/'build.json').read_text());sy=b['symbols']
    payload=load_slave((build/'WingCommander.Slave').read_bytes())
    hooks=b.get('hooks',HOOKS)
    guard_offsets=tuple(off for off,_,_ in hooks)
    if b.get('clock'):
        from ocs_clock_source import NOPS, MODALS
        guard_offsets+=NOPS+tuple(at for off,width,_,_ in MODALS for at in range(off+6,off+width,2))
    if b.get('prediction'):
        from ocs_prediction_source import NOPS as prediction_nops
        guard_offsets+=prediction_nops
    results=[]
    for slave in (0x500000,0xc00000):
        for flags,cpu in ((0,0),(1,10),(2,20),(4,30),(8,40),(128,60)):
            for revision in (0x1302,0x12bc,0x1348):
                for bad in (None,)+guard_offsets if revision==0x1302 else (None,):
                    c=Native(ROOT/'tmp/game/WingCommander/data/Wing.english')
                    events=[]
                    try:
                        c.write(slave,payload);c.write(4,long(0x8000));c.write(0x8000+296,word(flags))
                        c.write(slave+0xf24,long(0x190000))
                        def patch():events.append('patch');c.return_call()
                        def flush():events.append('flush');c.return_call()
                        def abort():
                            events.append(('abort',c.get(c.reg(8),4)))
                            c.reg(18,STOP);ck(u.uc_emu_stop(c.h))
                        c.intercept(0x190074,patch);c.intercept(0x190020,flush);c.intercept(0x190000,abort)
                        if bad is not None:c.write(CODE+bad,bytes([c.get(CODE+bad,1)^1]))
                        before=c.read(CODE,0x358c8)
                        c.run(slave-CODE+sy['install'],registers={3:0x190000,4:slave+revision,16:(CODE-4)//4})
                        if bad is not None:
                            require(events==['patch',('abort',9)],'bad hook not rejected before installation')
                            require(c.read(CODE,0x358c8)==before,'partial hook installation')
                        elif revision!=0x1302:
                            require(events==['patch'],'other revision enhanced')
                            require(c.read(CODE,0x358c8)==before,'other revision changed')
                        else:
                            require(events==['patch','flush'],'installation flush order')
                            for off,label,opcode in hooks:
                                require(c.get(CODE+off,2)==opcode and c.get(CODE+off+2,4)==slave+sy[label],f'hook destination O:{off:x}: {c.get(CODE+off,2):x}/{c.get(CODE+off+2,4):x}, expected {opcode:x}/{slave+sy[label]:x}')
                            for pos in b['fixups']:
                                expected=CODE+(int.from_bytes(payload[pos:pos+4],'big')&0xfffffff)
                                require(c.get(slave+pos,4)==expected,'wrong native operand relocation')
                            expected=0 if slave==0xc00000 or b['backend']!='cpu' else 1 if cpu<20 else 2
                            require(c.get(slave+sy['ocs_requested_backend'],4)==expected,'wrong integrated selection')
                        results.append((hex(slave),cpu,hex(revision),bad,events))
                    finally:c.close()
    return results


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('build');p.add_argument('--output',required=True)
    a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
    r=check(Path(a.build));(out/'report.json').write_text(json.dumps(dict(passed=True,cases=r),indent=2)+'\n')
    print(len(r),'startup cases passed')

if __name__=='__main__':main()
