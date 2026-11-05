#!/usr/bin/env python3
"""Read native terrain-query cached inputs and outputs without interventions."""
import json,re,sys
from pathlib import Path
from profile_window import command
from simulation_fixture import read_fixture
cap=Path(sys.argv[1]).resolve();end=int(sys.argv[2]);meta=json.loads((cap/'anchor.json').read_text());g=meta['game_base']
tick='*(unsigned short *)($a4-0x940)';wheel='*(unsigned char *)($a5-3)';car='*(unsigned int *)($a5+8)'
def log(tag,expr):return 'printf "'+tag+' '+' '.join('%d' for _ in expr)+'\\n", '+', '.join(expr)+'\n'
ins=[tick,wheel]+[f'*(short *)($a5+({-0x40+2*i}))' for i in range(3)]+[f'*(short *)(({car})+0x74+6*({wheel})+{2*i})' for i in range(3)]
outs=[tick,wheel]+[f'*(short *)($a4+{o})' for o in (0x96,0x94,0x92,0x90,0x8e,0x84,0x86)]+[f'*(unsigned char *)($a4+{o})' for o in (0x40,0x41)]+[f'*(short *)(*(unsigned int *)($a4+0x1ee)+{2*i})' for i in range(17)]
s='delete\n'
for off,tag,expr in ((0xc6bc,'QUERY_IN',ins),(0xc6c2,'QUERY_OUT',outs)):
 s+=f'break *{g+off:#x}\ncommands\nsilent\n'+log(tag,expr)+'continue\nend\n'
s+=f'break *{g+0xe7b4:#x}\ncommands\nsilent\nif {tick}<{end}\ncontinue\nend\nend\ncontinue\ndelete\n'
f=cap/'terrain-query.gdb';f.write_text(s);out=command('gdb source '+str(f));(cap/'terrain-query.txt').write_text(out)
r={t:[list(map(int,v.split())) for v in re.findall(r'^'+t+r' (.*)$',out,re.M)] for t in ('QUERY_IN','QUERY_OUT')}
assert len(r['QUERY_IN'])==len(r['QUERY_OUT'])==4*(end-meta['simulation_tick'])
command(f'gdb dump binary memory {cap.relative_to(Path.cwd())}/terrain-end.bin {meta["memory_base"]:#x} {meta["memory_base"]+meta["memory_size"]:#x}')
ref={t:s for t,hz,s in read_fixture(Path('tmp/prof/crest-d9e7903'),'bridge-end.bin')};samples=read_fixture(cap,'terrain-end.bin');assert all(s==ref[t] for t,hz,s in samples)
(cap/'terrain-query.json').write_text(json.dumps(dict(records=r,matching_full_states=len(samples)),indent=2)+'\n')
print({k:len(v) for k,v in r.items()},'exact full states',len(samples))
