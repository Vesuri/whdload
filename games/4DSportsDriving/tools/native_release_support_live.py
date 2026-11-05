#!/usr/bin/env python3
"""Closed-loop diagnostic v2: transient support reaction with native zero-gravity release state."""
import json,re,hashlib,math
from native_release_support_reference import integrate
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
prior={};v_res=[0.]*4;p_res=[0.]*4;interventions=[];model_velocity=[None]*4;last_output=[None]*4;native_resets=[]
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
        for wheel in re.findall(r'^RESET (\d+)$',result,re.M):
            wreset=int(wheel);native_resets.append(dict(after_callbacks=len(interventions),wheel=wreset))
            model_velocity[wreset]=None;v_res[wreset]=0.
        if bodies and bodies[-1]['tick']==650:break
        assert len(selected)==1,(len(selected),result)
        r=selected[0];w=r['wheel'];assert r['car_pointer']==m['data_base']+0x7ffe-0x92e
        if w in prior:
            assert r['correction']==0
            entry=dict(r)
            if model_velocity[w] is not None:
                entry['velocity']=model_velocity[w];entry['velocity_fraction']=0
            try:
                out=integrate(entry,prior[w])
            except Exception as error:
                (cap/'unsupported.json').write_text(json.dumps(dict(reason=str(error),input=entry,previous=prior[w],interventions=interventions,bodies=bodies,rows=rows,native_resets=native_resets),indent=2)+'\n')
                raise
            model_velocity[w]=out['velocity'];last_output[w]=out
            coords=[math.floor(x) for x in out['position']]
            velocity5=math.floor(out['velocity']*5+1e-10);v_res[w]=out['velocity']-velocity5/5
            # BC0 is also a branch cache: positive continuous air must not be
            # mistaken for zero contact solely because the integer cache rounds.
            clearance=0 if out['supported'] else max(1,math.trunc(out['clearance_units']))
            assert 0<=clearance<=32767 and -32768<=velocity5//5<=32767
            changes=[];read_expr=[];expected=[]
            for axis,value in enumerate(coords):
                pointer=f'*(int *)(*(unsigned int *)($a5-0xe6)+{4*axis})'
                changes.append(f'set {pointer}={value}');read_expr.append(pointer);expected.append(value)
                local=f'*(short *)($a5+({-0x40+2*axis}))'
                coarse=(value//64+32768)%65536-32768
                changes.append(f'set {local}={coarse}');read_expr.append(local);expected.append(coarse)
            for address,value in ((r['car_pointer']+0x4c+2*w,velocity5//5),(private+8+4*w,velocity5%5),(private+10+4*w,0),(steps+2*w,0),(steps+8+2*w,0),(m['data_base']+0x7ffe+0xbc0,clearance)):
                pointer=f'*(short *){address:#x}';changes.append(f'set {pointer}={value}');read_expr.append(pointer);expected.append(value)
            if clearance>12:
                pointer=f'*(unsigned char *){r["car_pointer"]+0xc2+w:#x}';changes.append(f'set {pointer}=0');read_expr.append(pointer);expected.append(0)
            changes.append(f'set $pc={g+0xcc2e:#x}');read_expr.append('(unsigned int)$pc');expected.append(g+0xcc2e)
            writefile=cap/'callback-write.gdb';writefile.write_text('\n'.join(changes)+'\nmaintenance flush register-cache\n'+printf('APPLIED',read_expr));writeout=command('gdb source '+str(writefile));log.write(writeout);log.flush()
            observed=re.findall(r'^APPLIED (.*)$',writeout,re.M);assert len(observed)==1,writeout
            applied=list(map(int,observed[0].split()));assert applied==expected,(r['tick'],w,applied,expected)
            interventions.append(dict(tick=r['tick'],wheel=w,model=out,integer_position=coords,velocity_residual=v_res[w],clearance_cache=clearance,writes=changes))
        prior[w]=r

        if len(rows)%40==0:print('Observed wheel callbacks',len(rows),flush=True)
command('gdb delete')
assert all(out is not None and not out['supported'] and out['clearance_units']>12 and out['velocity']>=0 for out in last_output),last_output
assert all(-1e-9<=v<.200000001 for v in v_res),v_res
assert [(r['tick'],r['wheel']) for r in rows]==[(t,w) for t in range(451,586) for w in range(4)]
assert [r['tick'] for r in bodies]==list(range(451,651))
ref={r['tick']:r for r in json.loads((ROOT/'tmp/prof/ordered-distance-d9-crest/bridge.json').read_text())['rows']}
differences=[dict(tick=r['tick'],fields={k:[v,ref[r['tick']][k]] for k,v in r.items() if v!=ref[r['tick']][k]}) for r in bodies if r!=ref[r['tick']]]
command(f'gdb dump binary memory {cap.relative_to(ROOT)}/callback-end.bin {m["memory_base"]:#x} {m["memory_base"]+m["memory_size"]:#x}')
expected={t:s for t,h,s in read_fixture(ROOT/'tmp/prof/ordered-distance-d9-crest','bridge-end.bin')};samples=read_fixture(cap,'callback-end.bin')
native={r['tick']:r for r in json.loads((ROOT/'tmp/prof/natural-crest20/bridge.json').read_text())['rows']}
common=[dict(time=r['tick']/50,error={k:r[k]-native[r['tick']*2//5][k] for k in ('y','z','pitch')}) for r in bodies if r['tick']%10==0]
report=dict(callbacks=len(rows),body_updates=len(bodies),interventions=interventions,differences=differences,common=common,bodies=bodies,rows=rows,
            final_velocity_residual=v_res,final_position_residual=p_res,model_velocity=model_velocity,native_resets=native_resets,airborne_handoff_verified=True,
            scope='Experimental continuous raw-plane support/contact at452..585. Native suspension/body reconstruction retained; low-impact wheel geometric response replaced. World coordinates floor once per callback (<1 unit discarded per axis), gravity accumulator carried on host; support endpoints and supported seam departures reset to native zero, temporary normal reaction is not persistent gravity; final airborne handoff loses less than0.2 velocity per wheel. BC0 encodes support0/positive-air>=1; native >12 airborne-flag threshold retained. No runtime/replay/full handling acceptance.')
(cap/'callback-intervention.json').write_text(json.dumps(report,indent=2)+'\n');print('Interventions',len(interventions));print(json.dumps(common[-3:],indent=2))
