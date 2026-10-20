#!/usr/bin/env python3
"""Check stored/allocated sizes and execute workspace startup on dirty memory."""
import argparse,json,re,struct
from pathlib import Path
from runtime_buffers import load
from ocs_display_check import Native,CODE,STACK
from ocs_reconstruct import ROOT,new_output
from variants import get


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('variant',choices=('ocs','cd32'));p.add_argument('build',type=Path)
    p.add_argument('--output',required=True);a=p.parse_args()
    out=new_output(a.output);out.mkdir(parents=True)
    meta=json.loads((a.build/'build.json').read_text())
    if a.variant=='ocs':sy=meta['symbols'];name='WingCommander.Slave'
    else:
        sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(a.build/'slave.lst').read_text(),re.M)}
        name='WingCommanderCD32.Slave'
    file=(a.build/name).read_bytes();image=load(file)
    start,end=sy['runtime_workspace'],sy['runtime_workspace_end']
    assert len(file)==start+36 and len(image)==end and not any(image[start:])
    assert meta['runtime_workspace_bytes']==end-start
    expected=(a.build/('candidate.bin' if a.variant=='ocs' else 'payload.bin')).read_bytes()
    # OCS writes its native header changes after the assembler output.
    if a.variant=='cd32':assert expected==image
    original=(ROOT/('tmp/originals/ocs/WingCommander/WingCommander.Slave' if a.variant=='ocs' else
                    'tmp/originals/cd32/WingCommanderCD32/WingCommanderCD32.Slave')).read_bytes()
    entry=int.from_bytes(original[32+0x18:32+0x1a],'big')
    assert int.from_bytes(image[0x18:0x1a],'big')==sy['runtime_workspace_init']<32768
    cases=[]
    for model in ((1,2,4) if a.variant=='ocs' else (2,4)):
      for base in (0x200000,0x500000):
        c=Native(ROOT/get(a.variant).GAME,model=model,variant=a.variant)
        try:
            c.write(base,image[:start]+b'\xa5'*(end-start))
            c.write(base-4,b'BEGN');c.write(base+end,b'END!')
            reached=[]
            def original_entry():reached.append(True);c.return_call()
            c.intercept(base+entry,original_entry)
            regs={r:0x12340000+r for r in (*range(1,8),*range(9,17))}
            for repeat in range(2):
                c.write(base+start,b'\xa5'*(end-start))
                c.run(base-CODE+sy['runtime_workspace_init'],registers=regs)
                assert all(c.reg(r)==v for r,v in regs.items()) and c.reg(8)==STACK+4
                assert c.read(base,start)==image[:start]
                assert c.read(base+start,end-start)==bytes(end-start)
                assert c.read(base-4,4)==b'BEGN' and c.read(base+end,4)==b'END!'
            assert len(reached)==2
            # Negative control: entering the old loader bypasses initialization.
            c.write(base+start,b'\xa5'*(end-start));c.run(base-CODE+entry)
            assert c.read(base+start,4)==b'\xa5'*4
            cases.append(dict(model=model,base=base,reentry=True,negative_control=True))
        finally:c.close()
    (out/'report.json').write_text(json.dumps(dict(passed=True,stored=len(file),allocated=len(image),cases=cases),indent=2)+'\n')
    print('PASS:',a.variant,len(cases),'startup cases; dirty allocation, re-entry, ABI, guards and negative controls')

if __name__=='__main__':main()
