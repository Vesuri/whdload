#!/usr/bin/env python3
"""Phase 1: compare all hunk-0 bytes after undoing relocations, except named native
mutable slots and JOTD's pre-existing patches (which are verified separately).
No optional simulation/render patches exist yet. Any other changed byte fails.
"""
import argparse,os,struct
from pathlib import Path
from gpc_report import regions
ROOT=Path(__file__).resolve().parents[1]
GAME=Path(os.environ.get('GPC_GAME',ROOT/'tmp/game/GrandPrixCircuit_v1.0_0008/GrandPrixCircuit'))
SR=(0xac2c,0xac96,0xace6,0xad36,0xad82,0xaf12,0xaf5e)

def check(dump,base,cpu='68000'):
    b=(GAME/'data/GrandPrixCircuit').read_bytes();assert len(b)==94708
    r={n:lo for lo,hi,n,o in regions(dump,base)};h=r['gpc'];db=r['gpc-data']
    live=bytearray(dump[h-base:h-base+0xe544]); assert len(live)==0xe544
    original=b[40:40+0xe544]; pos=0xe570
    while (n:=struct.unpack_from('>I',b,pos)[0]):
        t=struct.unpack_from('>I',b,pos+4)[0]
        for x in struct.unpack_from('>'+str(n)+'I',b,pos+8):
            struct.pack_into('>I',live,x,(struct.unpack_from('>I',live,x)[0]-[h,db][t])&0xffffffff)
        pos+=8+4*n
    patches={0x174:bytes.fromhex('4eb9'),0x2b90:bytes.fromhex('60000012'),0x4978:bytes.fromhex('6000000a'),0xb2f4:bytes.fromhex('70004e75'),0xb444:bytes.fromhex('4e75'),0xe516:bytes.fromhex('4e75')}
    if cpu!='68000':patches.update({x:bytes.fromhex('42e7') for x in SR})
    mask=set()
    for off,expected in patches.items():
        assert live[off:off+len(expected)]==expected,f'JOTD patch differs h0:{off:04x}'
        mask.update(range(off,off+(6 if off==0x174 else len(expected))))
    # C runtime startup slots; audio state fields; native runtime storage.
    for lo,hi in ((8,24),(0xb220,0xb224),(0xb228,0xb22c),(0xb6ea,0xb6ee)):
        mask.update(range(lo,hi))
    differences=[i for i,(x,y) in enumerate(zip(live,original)) if i not in mask and x!=y]
    assert not differences,f'unexpected modified bytes: {[hex(i) for i in differences[:30]]}'
    # All 139 data-hunk jump stubs remain the relocated file bytes.
    table=bytearray(b[0xe5bc:0xe5bc+0x342])
    for off in range(0,0x342,6):
        assert table[off:off+2]==bytes.fromhex('4ef9')
        target=struct.unpack_from('>I',table,off+2)[0]
        struct.pack_into('>I',table,off+2,target+h)
    assert dump[db-base:db-base+len(table)]==table,'jump stubs changed'
    print(f'{len(live)-len(mask)} original code bytes checked; {len(patches)} JOTD patches intact; all 139 jump stubs intact')
    return h,db

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('dump',type=Path);p.add_argument('--base',type=lambda s:int(s,0),default=0xc00000);p.add_argument('--cpu',default='68000');a=p.parse_args();check(a.dump.read_bytes(),a.base,a.cpu)
