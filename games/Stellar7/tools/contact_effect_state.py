#!/usr/bin/env python3
"""Validate observed lethal shield/mine contacts from exact-build raw snapshots."""
import argparse
import json
import re
import struct
from pathlib import Path
import audit_hooks

SITES={'shield':(0x35a8,0x35ae),'mine':(0x38b2,0x38b8)}

def validate_rows(kind,rows):
    assert rows, 'no observed contacts'
    for row in rows:
        b,a=row['before'],row['after']
        assert (b['pc'],a['pc'])==SITES[kind], 'wrong native call/return'
        assert b['tick']==a['tick'], 'contact crossed a tick boundary'
        assert b['health']>0 and b['damage']>0 and b['class']==255
        assert a['health'] in (b['health'],max(0,b['health']-b['damage']))
        if kind=='shield':assert b['shield']>0 and b['damage'] in (5,15)
        else:assert b['mine_type']==43 and b['damage']==10
        assert a['energy']==b['energy'], 'unexpected player-energy change inside actor damage'
    assert any(r['after']['health']==0 for r in rows), 'no lethal contact observed'

def inspect(folder,listing,kind):
    folder,listing=Path(folder),Path(listing)
    assert (folder/'slave.slave').read_bytes()==listing.with_suffix('.slave').read_bytes(), 'exact build mismatch'
    m=json.loads((folder/'metadata.json').read_text());base=m['base'];code=m['code_base'];data=m['data_base']
    paths=sorted(folder.glob('hit-*'),key=lambda p:int(p.name.split('-')[-1]));rows=[]
    for path in paths:
        before=(path/'code.bin').read_bytes();after=(path/'after/code.bin').read_bytes()
        def regs(text):
            assert 'SIGINT' not in text and 'Program received signal' not in text
            assert re.search(r'^Breakpoint \d+,',text,re.M), 'missing native breakpoint stop'
            return {k:int(v,16) for k,v in re.findall(r'^(pc|a2|a3|sp)\s+0x([0-9a-f]+)',text,re.M)}
        r=regs((path/'before.txt').read_text());ret=regs((path/'after/registers.txt').read_text())
        def u(memory,address,fmt):return struct.unpack_from(fmt,memory,address-base)[0]
        entry=u(before,code+0x2af8,'>I')
        assert before[entry-base+4:entry-base+8]==b'S760'
        assert u(after,code+0x2af8,'>I')==entry
        actor=r['a3'];assert u(before,r['sp'],'>I')==actor, 'wrong actor argument'
        b=dict(pc=r['pc']-code,tick=u(before,entry+16,'>I'),type=u(before,actor+2,'>H'),health=u(before,actor+0x55,'>B'),damage=u(before,r['sp']+4,'>H'),energy=u(before,data+0x46c4,'>h'),shield=u(before,data+0x1e9e,'>H'))
        b['class']=u(before,actor+0x54,'>B')
        if kind=='mine':b['mine_type']=u(before,r['a2']+2,'>H')
        a=dict(pc=ret['pc']-code,tick=u(after,entry+16,'>I'),health=u(after,actor+0x55,'>B'),energy=u(after,data+0x46c4,'>h'))
        rows.append(dict(before=b,after=a))
    validate_rows(kind,rows)
    return dict(kind=kind,rows=rows,hooks=audit_hooks.installed(folder,listing),scope='Observed native contact and lethal actor damage; scene setup is recorded in capture metadata. No audible-output, mine-destruction or full-encounter claim.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--listing',type=Path,required=True);p.add_argument('--kind',choices=SITES,required=True);a=p.parse_args()
    print(json.dumps(inspect(a.capture,a.listing,a.kind),indent=2))
