#!/usr/bin/env python3
"""Read actual pose carries, wheel matrices and direction-selection paths."""
import json,re,sys
from pathlib import Path
from profile_window import command,ROOT
from simulation_fixture import read_fixture
cap=Path(sys.argv[1]);m=json.loads((cap/'anchor.json').read_text())
assert m['active_simulation_word']==50 and m['simulation_tick']==450
mem=(cap/'memory.bin').read_bytes();private=m['memory_base']+mem.index(b'4DA4PHYS')+12;g=m['game_base']
tick='*(unsigned short *)($a4-0x940)';wheel='*(unsigned char *)($a5-3)'
tags={
'POSE':(0xc37a,[tick,'*(unsigned int *)($a5+8)']+[f'*(short *)($a4+{o})' for o in (0xbaa,0xba8,0xbac)]+[f'*(short *){private+o}' for o in (144,146)]+[f'*(short *)($a4+{0xbae+2*i})' for i in range(9)]),
'BUILD':(0xc520,[tick,wheel]+[f'*(short *)($a5+({-0x40+2*i}))' for i in range(3)]),
'BUILT':(0xc528,[tick,wheel]+[f'*(short *)($a5+({-0x46+2*i}))' for i in range(3)]),
'MOVE':(0xc5c6,[tick,wheel,'*(short *)($a4+0x206)','*(short *)($a5-6)','*(short *)($a4+0x200)']+[f'*(short *)($a4+{0x1f8+2*i})' for i in range(3)])
}
s='delete\n'
for tag,(off,expr) in tags.items():
    s+=f'break *{g+off:#x}\ncommands\nsilent\nprintf "{tag} '+ ' '.join('%d' for _ in expr)+'\\n", '+', '.join(expr)+'\ncontinue\nend\n'
s+=f'break *{g+0xe7b4:#x}\ncommands\nsilent\nif {tick}<585\ncontinue\nend\nend\ncontinue\ndelete\n'
f=cap/'geometry.gdb';f.write_text(s)
out=command('gdb source '+str(f.resolve()));(cap/'geometry.txt').write_text(out)
rows={tag:[list(map(int,s.split())) for s in re.findall(r'^'+tag+r' (.*)$',out,re.M)] for tag in tags}
assert len(rows['POSE'])==135
assert all(len(rows[tag])==540 for tag in ('BUILD','BUILT','MOVE'))
command(f'gdb dump binary memory {cap}/geometry-end.bin {m["memory_base"]:#x} {m["memory_base"]+m["memory_size"]:#x}')
ref={t:s for t,hz,s in read_fixture(ROOT/'tmp/prof/crest-d9e7903','bridge-end.bin')}
samples=read_fixture(cap,'geometry-end.bin');assert all(s==ref[t] for t,hz,s in samples)
(cap/'geometry.json').write_text(json.dumps(dict(records=rows,matching_full_states=len(samples),scope='Read-only canonical source; no fractional geometry intervention.'),indent=2)+'\n')
print('Captured135 poses/540 wheel projections and movements;',len(samples),'exact full baseline states')
