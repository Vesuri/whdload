"""Locate BSS allocations using every hunk-0 relocation to each target hunk.
No game bytes are embedded. Conflicting inferred bases are fatal.
"""
import struct
from pathlib import Path
from i500_report import DISK, game_hunks

def hunk0_relocations(disk):
    _,_,start,size,_=game_hunks(disk)[0]
    pos=start+size
    assert struct.unpack_from('>I',disk,pos)[0]==0x3ec
    pos+=4
    entries=[]
    while True:
        count=struct.unpack_from('>I',disk,pos)[0]; pos+=4
        if not count: break
        target=struct.unpack_from('>I',disk,pos)[0]; pos+=4
        for _ in range(count):
            off=struct.unpack_from('>I',disk,pos)[0]; pos+=4
            entries.append((off,target))
    return start,entries

def bss_regions(dump, base, game):
    disk=Path(DISK).read_bytes()
    hunks=game_hunks(disk)
    start,entries=hunk0_relocations(disk)
    inferred={}
    for off,target in entries:
        original=struct.unpack_from('>I',disk,start+off)[0]
        live=struct.unpack_from('>I',dump,game-base+off)[0]
        inferred.setdefault(target,set()).add((live-original)&0xffffffff)
    result={}
    for index,kind,_,size,_ in hunks:
        if kind!='bss': continue
        candidates=inferred.get(index,set())
        if len(candidates)!=1:
            raise ValueError(f'hunk {index}: conflicting/missing relocation bases: {candidates}')
        address=candidates.pop()
        result[f'hunk{index}']=(address,address+size)
    return result
