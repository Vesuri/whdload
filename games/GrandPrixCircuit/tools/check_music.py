#!/usr/bin/env python3
"""Verify live song-driver patches and compare hook helper code with a baseline."""
import argparse,collections,struct
from pathlib import Path
from gpc_report import locate
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('dump',type=Path);p.add_argument('--base',type=lambda s:int(s,0),default=0xc00000);p.add_argument('--reference',type=Path);p.add_argument('--beta2',action='store_true');p.add_argument('--candidate',action='store_true');p.add_argument('--audio040',action='store_true');a=p.parse_args()
original=(ROOT/'tmp/game/GrandPrixCircuit_v1.0_0008/GrandPrixCircuit/data/song1').read_bytes()[40:40+0xb80]
def check(dump):
    votes=collections.Counter()
    for off in range(0,len(original)-16,64):
        word=original[off:off+16];i=dump.find(word)
        while i>=0:
            votes[i-off]+=1;i=dump.find(word,i+1)
    candidates=[i for i,n in votes.items() if n>=8 and i>=8 and dump[i-8:i-4]==bytes.fromhex('00000b88')]
    assert len(candidates)==1,'live song code allocation missing or ambiguous'
    h=a.base+candidates[0]
    def read(addr,size):return dump[addr-a.base:addr-a.base+size]
    for off in (0x4fe,0xa44,0xa74):assert read(h+off,4)==bytes.fromhex('00dff09c'),f'INTREQ patch {off:x}'
    if a.beta2 or a.candidate or a.audio040:
        assert read(h+0x8c8,2)==bytes.fromhex('6762')
        assert read(h+0x926,2)==bytes.fromhex('4eb9')
        target=struct.unpack('>I',read(h+0x928,4))[0]
        assert read(target,14)==bytes.fromhex('33c300dff09c4a7900dff01e4e75')
        print('Snapshot-missing IRQ bypass and serializing acknowledgement intact; song hunk',hex(h))
    if a.candidate:
        for off in (0x776,0x86a):assert read(h+off,2)==bytes.fromhex('4eb9')
        target=struct.unpack('>I',read(h+0x778,4))[0]
        assert read(target,6)==bytes.fromhex('48e78040227a')
        slot=target+6+struct.unpack('>h',read(target+6,2))[0]
        assert read(slot,4)==read(h+0x4bc,4), 'wrong channel mask source'
        assert read(target+8,32)==bytes.fromhex('3029000402407fff33c000dff09a4a7900dff01c4cdf02012c6b00302c884e75')
        target=struct.unpack('>I',read(h+0x86c,4))[0]
        assert read(target,14)==bytes.fromhex('303900dff01ec07900dff01c4e75')
        print('Note preparation mask and enabled-request snapshot intact')
    if a.audio040:
        for off in (0x758,0x86a):assert read(h+off,2)==bytes.fromhex('4eb9')
        assert read(h+0x776,6)==original[0x776:0x77c]
        target=struct.unpack('>I',read(h+0x75a,4))[0]
        assert read(target,6)==bytes.fromhex('4a6b00466620')
        target=struct.unpack('>I',read(h+0x86c,4))[0]
        assert read(target,14)==bytes.fromhex('303900dff01ec07900dff01c4e75')
        print('Early pitch mask, effect ownership guard and enabled IRQ snapshot intact')
    helpers=[]
    for off in (0x1e8,0x8fa,0x110,0x1a4,0x7e0,0x5c8,0x8a,0x23a,0x42e,0x502,0xa78):
        assert read(h+off,2)==bytes.fromhex('4eb9'),f'DMACON hook {off:x}'
        target=struct.unpack('>I',read(h+off+2,4))[0];helpers.append(read(target,16));assert len(helpers[-1])==16
    return helpers
helpers=check(a.dump.read_bytes())
if a.reference:
    assert helpers==check(a.reference.read_bytes()),'hook helper code differs from baseline'
print('3 INTREQ patches and 11 DMACON hooks intact'+('; helper bytes match baseline' if a.reference else ''))
