#!/usr/bin/env python3
"""Audit retained ordinary-runtime replay captures; no emulation or guest writes."""
import hashlib,json,struct
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/'tmp/runtime-render-replay'
m=json.loads((p/'start/anchor.json').read_text())
a=m['data_base']+0x7ffe-m['memory_base']
names=['loaded-full','reloaded','loaded-fast']
bs={n:(p/(n+'.bin')).read_bytes() for n in names}
sha=lambda b:hashlib.sha256(b).hexdigest()
def ptr(b,o):return struct.unpack_from('>I',b,a+o)[0]-m['memory_base']
def semantic(b):
    out=b[a-0xa80:a-0x620]+b[a+0x228:a+0x22e]
    for tag,size in [(b'4DA4PHYS',152),(b'4DTSTATE',32),(b'4DAUXPHY',192),(b'4DCAM050',8)]:
        assert b.count(tag)==1
        off=b.index(tag)+12;out+=b[off:off+size]
    assert len(out)==1510
    return out
initial={n:sha(semantic(b)) for n,b in bs.items()}
assert len(set(initial.values()))==1
arrays={}
for name,off,size in [('opponent_path',-0x17a4,1802),('route_links',-0x17ac,1802),('tiles',-0x176c,901),('tile_orientation',-0x1768,901),('route_x',-0x175c,901),('route_z',-0x1758,901)]:
    blocks={n:b[ptr(b,off):ptr(b,off)+size] for n,b in bs.items()}
    assert all(len(b)==size for b in blocks.values())
    arrays[name]={'pointer_offset':off,'bytes':size,'sha256':{n:sha(b) for n,b in blocks.items()},'changed_from_first':{n:sum(x!=y for x,y in zip(blocks[n],blocks[names[0]])) for n in names[1:]}}
    if name=='opponent_path':arrays[name]['first_70_words']={n:list(struct.unpack('>70H',b[:140])) for n,b in blocks.items()}
full=(p/'full/states.bin').read_bytes();fast=(p/'fast/states.bin').read_bytes()
assert len(full)==len(fast)==250*1510
groups={'native':(0,1120),'player':(338,546),'opponent':(546,754),'rng':(1120,1126),'physics':(1126,1278),'time':(1278,1310),'auxiliary':(1310,1502),'camera':(1502,1510),'complete':(0,1510)}
equal={k:sum(full[i*1510+s:i*1510+e]==fast[i*1510+s:i*1510+e] for i in range(250)) for k,(s,e) in groups.items()}
report={'snapshot_sha256':{n:sha(b) for n,b in bs.items()},'initial_semantic_sha256':initial,'arrays':arrays,'equal_checkpoints_of_250':equal,'conclusion':'Replay reload changes the opponent path before the graphics dialog. FULL/FAST comparison is confounded; render independence not established. Static native BC48 AI consumes this external table at BD88/BDA8; native 162F6 resource/path builder writes it at 16488. Causal runtime control still required.'}
(p/'path-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'equal_checkpoints_of_250':equal,'array_changes':{k:v['changed_from_first'] for k,v in arrays.items()},'conclusion':report['conclusion']},indent=2))
