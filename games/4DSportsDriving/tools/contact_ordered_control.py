#!/usr/bin/env python3
"""Validate host-driven per-wheel stops before any numerical intervention."""
import json,re,hashlib
from pathlib import Path
import sys
from profile_window import command,ROOT
from simulation_fixture import read_fixture
cap=Path(sys.argv[1]).resolve();m=json.loads((cap/'anchor.json').read_text());assert m['simulation_tick']==450 and m['active_simulation_word']==50 and m['opponent']==0
g=m['game_base'];mem=(cap/'memory.bin').read_bytes();private=m['memory_base']+mem.index(b'4DA4PHYS')+12
# The same live field definitions as the independently validated release probe.
probe=(ROOT/'tools/release_step_probe.py').read_text();start=probe.index('fields=[');end=probe.index('for off,tag in ')
context={'private':private};exec(probe[start:end],context);fields=context['fields']
names=('tick','wheel','clearance','correction','velocity','world_y','world_x','world_z','plane','base_x','base_y','base_z','node_x','node_y','node_z','normal_x','normal_y','normal_z','extension','velocity_fraction','position_fraction','extension_fraction','old_world_x','old_world_y','old_world_z','distance','plane_flags','impact_flags')
assert len(fields)==len(names)
body_names=('tick','x','y','z','heading','pitch','roll','speed','slip','spin','contact','w0','w1','w2','w3','crash')
body_offsets=(-0x940,-0x92e,-0x92a,-0x926,-0x916,-0x914,-0x912,-0x904,-0x8f8,-0x8f0,-0x86d,-0x86c,-0x86b,-0x86a,-0x869,-0x865)
body_types=('unsigned short','int','int','int','short','short','short','unsigned short','short','short',*(['unsigned char']*6))
def printf(tag,expressions):return 'printf "'+tag+' '+' '.join('%d' for _ in expressions)+'\\n", '+', '.join(expressions)+'\n'
setup=f'delete\nbreak *{g+0xcb06:#x} if *(unsigned short *)($a4-0x940)<=585\ncommands\nsilent\n'+printf('SELECT',fields)+'end\n'
setup+=f'break *{g+0xe7b4:#x}\ncommands\nsilent\n'+printf('BODY',[f'*({t} *)($a4+({o}))' for t,o in zip(body_types,body_offsets)])+'if *(unsigned short *)($a4-0x940)<650\ncontinue\nend\nend\n'
f=cap/'callback-setup.gdb';f.write_text(setup);command('gdb source '+str(f));rows=[];bodies=[]
with (cap/'callback.txt').open('w') as log:
    while True:
        result=command('gdb continue');log.write(result);log.flush()
        selected=[dict(zip(names,map(int,s.split()))) for s in re.findall(r'^SELECT (.*)$',result,re.M)]
        completed=[dict(zip(body_names,map(int,s.split()))) for s in re.findall(r'^BODY (.*)$',result,re.M)]
        rows.extend(selected);bodies.extend(completed)
        if bodies and bodies[-1]['tick']==650:break
        assert len(selected)==1,(len(selected),result)
        if len(rows)%40==0:print('Observed wheel callbacks',len(rows),flush=True)
command('gdb delete')
assert [(r['tick'],r['wheel']) for r in rows]==[(t,w) for t in range(451,586) for w in range(4)]
assert [r['tick'] for r in bodies]==list(range(451,651))
ref={r['tick']:r for r in json.loads((ROOT/'tmp/prof/ordered-distance-d9-crest/bridge.json').read_text())['rows']}
assert all(r==ref[r['tick']] for r in bodies)
command(f'gdb dump binary memory {cap.relative_to(ROOT)}/callback-end.bin {m["memory_base"]:#x} {m["memory_base"]+m["memory_size"]:#x}')
expected={t:s for t,h,s in read_fixture(ROOT/'tmp/prof/ordered-distance-d9-crest','bridge-end.bin')};samples=read_fixture(cap,'callback-end.bin');assert all(s==expected[t] for t,h,s in samples)
report=dict(callbacks=len(rows),exact_body_updates=len(bodies),exact_full_states=len(samples),slave_sha256=hashlib.sha256((cap/'slave.slave').read_bytes()).hexdigest(),scope='Host-mediated stop/read/continue control only; no physics writes. All captured body updates and full saved states match uninterrupted current source.',rows=rows,bodies=bodies)
(cap/'callback-control.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('rows','bodies')})
