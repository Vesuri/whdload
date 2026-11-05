#!/usr/bin/env python3
"""Read all inputs/outputs needed to predict straight contact plus suspension."""
import json,re,sys
from pathlib import Path
from profile_window import command,ROOT
from simulation_fixture import read_fixture
cap=Path(sys.argv[1]);end=int(sys.argv[2]);m=json.loads((cap/'anchor.json').read_text());g=m['game_base']
assert m['active_simulation_word']==50 and m['opponent']==0
mem=(cap/'memory.bin').read_bytes();private=m['memory_base']+mem.index(b'4DA4PHYS')+12
syms={k:int(v,16) for k,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)$',(cap/'slave.lst').read_text(encoding='latin1'),re.M)}
tick='*(unsigned short *)($a4-0x940)';wheel='*(unsigned char *)($a5-3)';car='*(unsigned int *)($a5+8)'
def log(tag,expr):return 'printf "'+tag+' '+' '.join('%d' for _ in expr)+'\\n", '+', '.join(expr)+'\n'
def carwords(off,n):return [f'*(short *)(({car})+{off+2*i})' for i in range(n)]
entry=[tick]+carwords(0x18,3)+[f'*(short *)($a4+{0xbae+2*i})' for i in range(9)]
entry+=carwords(0x54,4)+carwords(0x6c,4)+carwords(0x4c,4)
entry+=[f'*(short *){private+off+stride*w}' for off,stride in ((8,4),(10,4),(24,2),(40,2)) for w in range(4)]
entry+=[f'*(short *){private+144}']+[f'*(unsigned short *){private+132+2*i}' for i in range(3)]
entry+=[f'*(int *)($a5+({base+4*i}))' for base in (-0xe2,-0xb2) for i in range(12)]
probe=(ROOT/'tools/release_step_probe.py').read_text();context={'private':private};exec(probe[probe.index('fields=['):probe.index('for off,tag in ')],context)
fields=context['fields'];names=('tick','wheel','clearance','correction','velocity','world_y','world_x','world_z','plane','base_x','base_y','base_z','node_x','node_y','node_z','normal_x','normal_y','normal_z','extension','velocity_fraction','position_fraction','extension_fraction','old_world_x','old_world_y','old_world_z','distance','plane_flags','impact_flags')
fields += [f'*(short *)(*(unsigned int *)($a4+0x1ee)+{16+2*i})' for i in range(9)]
names += tuple('matrix'+str(i) for i in range(9))
final=[tick,wheel]+[f'*(int *)(*(unsigned int *)($a5-0xe6)+{4*i})' for i in range(3)]+['*(short *)($a4+0xbc0)']+[f'*(short *)(({car})+0x4c+2*({wheel}))']+[f'*(short *)({private+off}+{stride}*({wheel}))' for off,stride in ((8,4),(10,4),(24,2))]
body=[tick]+[f'*(int *)($a4+({o}))' for o in (-0x92e,-0x92a,-0x926)]+[f'*(short *)($a4+({o}))' for o in (-0x916,-0x914,-0x912)]+[f'*(short *){private+144}']+[f'*(unsigned short *){private+132+2*i}' for i in range(3)]
s='delete\n'
for off,tag,expr in ((0xc520,'BUILD',[tick,wheel]+[f'*(short *)($a5+({-0x40+2*i}))' for i in range(3)]),(0xc60c,'ENTRY',entry),(0xcb06,'SELECT',fields),(0xd1b8,'FINAL',final)):
    s+=f'break *{g+off:#x}\ncommands\nsilent\n'+log(tag,expr)+'continue\nend\n'
s+=f'break *{g+0xd2b6:#x}\ncommands\nsilent\nset $car=*(unsigned int *)$sp\nset $wheel=*(short *)($sp+6)\n'
s+=log('SUSP_IN',[tick,'$wheel','*(short *)($sp+4)','*(short *)($car+0x54+2*$wheel)','*(short *)($car+0x6c+2*$wheel)',f'*(short *)({private+24}+2*$wheel)',f'*(short *)({private+40}+2*$wheel)'])+'continue\nend\n'
s+=f'break *{g+0xd2ba:#x}\ncommands\nsilent\n'+log('SUSP_OUT',[tick,'$wheel','(short)$d0','*(short *)($car+0x54+2*$wheel)','*(short *)($car+0x6c+2*$wheel)',f'*(short *)({private+24}+2*$wheel)',f'*(short *)({private+40}+2*$wheel)'])+'continue\nend\n'
s+=f'break *{g+0xe7b4:#x}\ncommands\nsilent\n'+log('BODY',body)+f'if {tick}<{end}\ncontinue\nend\nend\ncontinue\ndelete\n'
f=cap/'prediction.gdb';f.write_text(s);out=command('gdb source '+str(f.resolve()));(cap/'prediction.txt').write_text(out)
records={tag:[list(map(int,v.split())) for v in re.findall(r'^'+tag+r' (.*)$',out,re.M)] for tag in ('BUILD','ENTRY','SELECT','FINAL','SUSP_IN','SUSP_OUT','BODY')}
n=end-m['simulation_tick'];assert all(len(v)==n*(1 if k in ('ENTRY','BODY') else 4) for k,v in records.items()),{k:len(v) for k,v in records.items()}
records['SELECT']=[dict(zip(names,r)) for r in records['SELECT']]
command(f'gdb dump binary memory {cap}/prediction-end.bin {m["memory_base"]:#x} {m["memory_base"]+m["memory_size"]:#x}')
ref={t:s for t,hz,s in read_fixture(ROOT/'tmp/prof'/(sys.argv[3] if len(sys.argv)>3 else 'crest-d9e7903'),'bridge-end.bin')}
samples=read_fixture(cap,'prediction-end.bin');assert all(s==ref[t] for t,hz,s in samples)
(cap/'prediction.json').write_text(json.dumps(dict(records=records,matching_full_states=len(samples),scope='Read-only canonical trace. Selected terrain geometry is an observed query result; predicting selection for altered motion is separate unfinished work.'),indent=2)+'\n')
print({k:len(v) for k,v in records.items()},'exact full states',len(samples))
