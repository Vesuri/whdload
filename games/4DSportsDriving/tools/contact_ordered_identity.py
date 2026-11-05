#!/usr/bin/env python3
"""Validate host-driven per-wheel stops before any numerical intervention."""
import json,re,hashlib,math
from contact_interval_general import event_integrate
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
fields += ['*(unsigned int *)($a5+8)'];names += ('car_pointer',)
assert len(fields)==len(names)
syms={k:int(v,16) for k,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)$',(cap/'slave.lst').read_text(encoding='latin1'),re.M)}
steps=private-syms['sim_a4000_private']+syms['sim_a4000_wheel_steps']
prior={};v_res=[0.]*4;p_res=[0.]*4;interventions=[]
body_names=('tick','x','y','z','heading','pitch','roll','speed','slip','spin','contact','w0','w1','w2','w3','crash')
body_offsets=(-0x940,-0x92e,-0x92a,-0x926,-0x916,-0x914,-0x912,-0x904,-0x8f8,-0x8f0,-0x86d,-0x86c,-0x86b,-0x86a,-0x869,-0x865)
body_types=('unsigned short','int','int','int','short','short','short','unsigned short','short','short',*(['unsigned char']*6))
def printf(tag,expressions):return 'printf "'+tag+' '+' '.join('%d' for _ in expressions)+'\\n", '+', '.join(expressions)+'\n'
setup=f'delete\nbreak *{g+0xcb06:#x} if *(unsigned short *)($a4-0x940)<=585\ncommands\nsilent\n'+printf('SELECT',fields)+'end\n'
setup+=f'break *{g+0xe7b4:#x}\ncommands\nsilent\n'+printf('BODY',[f'*({t} *)($a4+({o}))' for t,o in zip(body_types,body_offsets)])+'if *(unsigned short *)($a4-0x940)<650\ncontinue\nend\nend\n'
for off in (0xcc9e,0xd1b0):
    setup+=f'break *{g+off:#x}\ncommands\nsilent\n'+printf('RESET',['*(unsigned char *)($a5-3)'])+'continue\nend\n'
f=cap/'callback-setup.gdb';f.write_text(setup);command('gdb source '+str(f));rows=[];bodies=[]
with (cap/'callback.txt').open('w') as log:
    while True:
        result=command('gdb continue');log.write(result);log.flush()
        selected=[dict(zip(names,map(int,s.split()))) for s in re.findall(r'^SELECT (.*)$',result,re.M)]
        completed=[dict(zip(body_names,map(int,s.split()))) for s in re.findall(r'^BODY (.*)$',result,re.M)]
        rows.extend(selected);bodies.extend(completed)
        for wheel in re.findall(r'^RESET (\d+)$',result,re.M): v_res[int(wheel)]=0.;p_res[int(wheel)]=0.
        if bodies and bodies[-1]['tick']==650:break
        assert len(selected)==1,(len(selected),result)
        r=selected[0];w=r['wheel'];assert r['car_pointer']==m['data_base']+0x7ffe-0x92e
        if w in prior:
            assert r['correction']==0
            eligible=int(r['clearance']>0)
            acceleration=21 if w<2 else 15
            # Exact existing ordered-pair arithmetic, with its unchanged input
            # carries. This is an identity intervention, not a new time law.
            out=dict(velocity=(5*r['velocity']+r['velocity_fraction']+eligible*2*acceleration)/5,
                     downward=(10*r['velocity']+2*r['velocity_fraction']+7*acceleration)/25 if eligible else 0.)
            next_pc=g+(0xcbdc if eligible else 0xcc2e)
            velocity5=math.floor(out['velocity']*5+1e-10);v_res[w]=out['velocity']-velocity5/5
            total_down=out['downward']+r['position_fraction']/25+p_res[w]
            down=math.floor(total_down+1e-10);fraction25=math.floor((total_down-down)*25+1e-10);p_res[w]=total_down-down-fraction25/25
            assert 0<=v_res[w]<.200000001 and -.000000001<=p_res[w]<.040000001
            assert 0<=down<=32767 and 0<=velocity5//5<=32767
            changes=[f'set *(int *)(*(unsigned int *)($a5-0xe6)+4)={r["world_y"]-down}',
                     f'set *(short *){r["car_pointer"]+0x4c+2*w:#x}={velocity5//5}',
                     f'set *(short *){private+8+4*w:#x}={velocity5%5}',
                     f'set *(short *){private+10+4*w:#x}={fraction25}',
                     f'set *(short *){steps+2*w:#x}={down}',f'set *(short *){steps+8+2*w:#x}={eligible}',
                     f'set $pc={next_pc:#x}']
            read_expr=[f'*(int *)(*(unsigned int *)($a5-0xe6)+4)',f'*(short *){r["car_pointer"]+0x4c+2*w:#x}',f'*(short *){private+8+4*w:#x}',f'*(short *){private+10+4*w:#x}',f'*(short *){steps+2*w:#x}',f'*(short *){steps+8+2*w:#x}','(unsigned int)$pc']
            writefile=cap/'callback-write.gdb';writefile.write_text('\n'.join(changes)+'\nmaintenance flush register-cache\n'+printf('APPLIED',read_expr));writeout=command('gdb source '+str(writefile));log.write(writeout);log.flush()
            observed=re.findall(r'^APPLIED (.*)$',writeout,re.M);assert len(observed)==1,writeout
            applied=list(map(int,observed[0].split()));expected=[r['world_y']-down,velocity5//5,velocity5%5,fraction25,down,eligible,next_pc]
            assert applied==expected,(r['tick'],w,applied,expected,writeout)
            interventions.append(dict(tick=r['tick'],wheel=w,velocity=out['velocity'],downward=out['downward'],applied_down=down,velocity_residual=v_res[w],position_residual=p_res[w],writes=changes))
        prior[w]=r

        if len(rows)%40==0:print('Observed wheel callbacks',len(rows),flush=True)
command('gdb delete')
assert [(r['tick'],r['wheel']) for r in rows]==[(t,w) for t in range(451,586) for w in range(4)]
assert [r['tick'] for r in bodies]==list(range(451,651))
ref={r['tick']:r for r in json.loads((ROOT/'tmp/prof/ordered-distance-d9-crest/bridge.json').read_text())['rows']}
differences=[dict(tick=r['tick'],fields={k:[v,ref[r['tick']][k]] for k,v in r.items() if v!=ref[r['tick']][k]}) for r in bodies if r!=ref[r['tick']]]
command(f'gdb dump binary memory {cap.relative_to(ROOT)}/callback-end.bin {m["memory_base"]:#x} {m["memory_base"]+m["memory_size"]:#x}')
expected={t:s for t,h,s in read_fixture(ROOT/'tmp/prof/ordered-distance-d9-crest','bridge-end.bin')};samples=read_fixture(cap,'callback-end.bin')
assert not differences,differences[:3]
assert all(s==expected[t] for t,h,s in samples)
native={r['tick']:r for r in json.loads((ROOT/'tmp/prof/natural-crest20/bridge.json').read_text())['rows']}
common=[dict(time=r['tick']/50,error={k:r[k]-native[r['tick']*2//5][k] for k in ('y','z','pitch')}) for r in bodies if r['tick']%10==0]
report=dict(callbacks=len(rows),body_updates=len(bodies),interventions=interventions,differences=differences,common=common,bodies=bodies,rows=rows,
            final_velocity_residual=v_res,final_position_residual=p_res,
            identity_body_updates=len(bodies),identity_full_states=len(samples),scope='Identity intervention: exact existing 50Hz ordered-pair equations, original airborne/pass branch continuations, and unchanged native endpoint response. Every write read back; all200 body updates and64 full saved states equal the uninterrupted matching baseline. No new physics rule.')
(cap/'callback-intervention.json').write_text(json.dumps(report,indent=2)+'\n');print('Interventions',len(interventions));print('IDENTITY exact bodies',len(bodies),'full states',len(samples))
