#!/usr/bin/env python3
"""Summarize mapped Stellar 7 state at a capture anchor; offsets are hunk-relative.
This is a selected-state comparison aid, not a claim of complete state equivalence.
"""
import hashlib,json,re,struct,sys
from pathlib import Path

def summarize(folder):
    folder=Path(folder)
    text=(folder/'anchor.txt').read_text()
    meta={k:int(v,0) for k,v in re.findall(r'^(code|data|base|frame)=(\S+)',text,re.M)}
    mem=(folder/'code.bin').read_bytes(); chip=(folder/'chip.bin').read_bytes()
    def read(a,n):
        if meta['base']<=a and a+n<=meta['base']+len(mem):return mem[a-meta['base']:a-meta['base']+n]
        if 0<=a and a+n<=len(chip):return chip[a:a+n]
        raise ValueError(f'address outside snapshots: {a:#x}')
    data=read(meta['data'],0x823c)
    word=lambda off:struct.unpack_from('>H',data,off)[0]
    long=lambda off:struct.unpack_from('>I',data,off)[0]
    player=read(long(0x43c0),0x6e)
    return dict(frame=word(0x1e96),level=word(0x46a0),energy=word(0x46c4),
        tick=long(0x24a8),timer_scale=word(0x6870),
        rng_sha256=hashlib.sha256(data[0x2434:0x24a8]).hexdigest(),
        player_x=struct.unpack_from('>i',player,8)[0],player_z=struct.unpack_from('>i',player,12)[0],
        player_heading=struct.unpack_from('>H',player,0x18)[0],
        player_speed=struct.unpack_from('>h',player,0x40)[0])

if __name__=='__main__':
    for name in sys.argv[1:]:print(name,json.dumps(summarize(name),sort_keys=True))
