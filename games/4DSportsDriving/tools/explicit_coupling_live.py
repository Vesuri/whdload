#!/usr/bin/env python3
"""Causal two-stage direction-order diagnostic; no lookahead or reference data."""
import json,re,sys
from pathlib import Path
from profile_window import command,ROOT
from contact_body_predictor import body as predict_body
from crest_terrain_query import query
from native_contact_response import sine
from simulation_fixture import read_fixture
# Reuse the established read-only field definitions, before any probe execution.
prefix=(ROOT/'tools/contact_prediction_probe.py').read_text().split("s='delete\\n'",1)[0]
exec(prefix)
identity='--identity' in sys.argv
extra=['*(short *)($a5-6)','*(short *)($a5-8)',f'*(unsigned char *)(({car})+0xcf)']
extra += [f'*(short *)(({car})+0x74+{2*i})' for i in range(12)]
s='delete\n'
for off,tag,expr,cont in ((0xc520,'BUILD',[tick,wheel]+[f'*(short *)($a5+({-0x40+2*i}))' for i in range(3)],True),(0xc60c,'ENTRY',entry+extra,False),(0xcb06,'SELECT',fields,True),(0xd1b8,'FINAL',final,True)):
    s+=f'break *{g+off:#x}\ncommands\nsilent\n'+log(tag,expr)+('continue\n' if cont else '')+'end\n'
s+=f'break *{g+0xd2b6:#x}\ncommands\nsilent\nset $car=*(unsigned int *)$sp\nset $wheel=*(short *)($sp+6)\ncontinue\nend\n'
s+=f'break *{g+0xd2ba:#x}\ncommands\nsilent\n'+log('SUSP',[tick,'$wheel','(short)$d0','*(short *)($car+0x54+2*$wheel)','*(short *)($car+0x6c+2*$wheel)',f'*(short *)({private+24}+2*$wheel)',f'*(short *)({private+40}+2*$wheel)'])+'continue\nend\n'
s+=f'break *{g+0xe7b4:#x}\ncommands\nsilent\n'+log('BODY',body)+f'if {tick}<{end}\ncontinue\nend\nend\n'
f=cap/'explicit-setup.gdb';f.write_text(s);command('gdb source '+str(f.resolve()))

def sine8(a):
    i,f=divmod(a,256);return (256-f)*sine(i)+f*sine(i+1)
def evaluate(e,build,extras,correction):
    e=e.copy();distance,roof,impact=extras[:3];cached=extras[3:];rows=[]
    for w in range(4):
        for i in range(3):e[57+3*w+i]+=correction[i]
        world=e[57+3*w:60+3*w];r=query(world,cached[3*w:3*w+3])
        r.update(tick=e[0],wheel=w,distance=distance,correction=roof,impact_flags=impact)
        for key,offset in (('extension',13),('velocity',21),('velocity_fraction',25),('position_fraction',29),('extension_fraction',33)):r[key]=e[offset+w]
        r.update({'old_world_'+a:v for a,v in zip('xyz',e[45+3*w:48+3*w])})
        r.update({'world_'+a:v for a,v in zip('xyz',world)})
        rows.append(r)
    return predict_body(e,build,rows),rows,e
records=[];verified=dict(select=0,wheel=0,suspension=0,body=0);residue=[0,0,0];pending=None
with (cap/'explicit-log.txt').open('w') as logfile:
    while True:
        text=command('gdb continue');logfile.write(text);logfile.flush()
        for tag,values in re.findall(r'^(SELECT|FINAL|SUSP|BODY) (.*)$',text,re.M):
            v=list(map(int,values.split()));assert pending is not None
            assert v[0]==pending['tick']
            if tag=='SELECT':
                actual=dict(zip(names,v));row=pending['selected'][v[1]]
                for k in ('plane','base_x','base_y','base_z','node_x','node_y','node_z','normal_x','normal_y','normal_z','plane_flags','clearance',*('matrix'+str(i) for i in range(9))):assert actual[k]==row[k],(tag,v[0],v[1],k,actual[k],row[k])
                verified['select']+=1
            elif tag=='FINAL':
                w=pending['prediction']['wheels'][v[1]];expected=w['position']+[w[k] for k in ('clearance','velocity','vf','pf','ef')]
                assert v[2:]==expected,(tag,v,expected);verified['wheel']+=1
            elif tag=='SUSP':
                su=pending['prediction']['suspensions'][v[1]];expected=[su[k] for k in ('returned','extension','bias','ef','bf')]
                assert v[2:]==expected,(tag,v,expected);verified['suspension']+=1
            else:
                pred=pending['prediction'];expected=pred['position']+[0,pred['pitch'],0,pred['pitch_carry']]+pred['centroid_carries']
                assert v[1:]==expected,(tag,v,expected);verified['body']+=1
        if pending and pending['tick']==end and verified['body']==len(records):break
        entries=re.findall(r'^ENTRY (.*)$',text,re.M);assert len(entries)==1,text
        values=list(map(int,entries[0].split()));e=values[:69];extras=values[69:];assert len(extras)==15
        builds=[list(map(int,v.split())) for v in re.findall(r'^BUILD (.*)$',text,re.M)]
        assert [(v[0],v[1]) for v in builds]==[(e[0],w) for w in range(4)];build=[v[2:] for v in builds]
        stage1,_,_=evaluate(e,build,extras,[0,0,0])
        old=e[2]*256+e[41];new=stage1['pitch']*256+stage1['pitch_carry'];distance=extras[0];correction=[0,0,0]
        for i,a in ((1,0),(2,65536)):
            correction[i],residue[i]=divmod(residue[i]+3*distance*(sine8(old+a)-sine8(new+a)),16777216)
        if identity:correction=[0,0,0];residue=[0,0,0]
        pred,selected,changed=evaluate(e,build,extras,correction)
        changes=[];reads=[];expected=[]
        for w in range(4):
            for i in range(3):
                pointer=f'*(int *)($a5+({-0xb2+12*w+4*i}))';value=changed[57+3*w+i]
                changes.append(f'set {pointer}={value}');reads.append(pointer);expected.append(value)
        f=cap/'explicit-write.gdb';f.write_text('\n'.join(changes)+'\n'+log('APPLIED',reads))
        applied=command('gdb source '+str(f.resolve()));logfile.write(applied);logfile.flush()
        readback=re.findall(r'^APPLIED (.*)$',applied,re.M);assert len(readback)==1 and list(map(int,readback[0].split()))==expected
        pending=dict(tick=e[0],entry=e,extra=extras,build=build,stage1_pitch=stage1['pitch'],stage1_carry=stage1['pitch_carry'],correction=correction,residue=residue.copy(),selected=selected,prediction=pred)
        records.append(pending)
        if len(records)%50==0:print('verified completed',verified,'now prepared tick',e[0],flush=True)
command('gdb delete');command(f'gdb dump binary memory {cap}/explicit-end.bin {m["memory_base"]:#x} {m["memory_base"]+m["memory_size"]:#x}')
ref={t:s for t,hz,s in read_fixture(ROOT/'tmp/prof/crest-d9e7903','bridge-end.bin')};samples=read_fixture(cap,'explicit-end.bin')
matching=sum(s==ref[t] for t,hz,s in samples)
if identity:assert matching==len(samples)
assert verified==dict(select=4*len(records),wheel=4*len(records),suspension=4*len(records),body=len(records))
report=dict(identity=identity,verified=verified,verified_writes=12*len(records),matching_full_states=matching,records=records,
 scope='Causal two-stage smooth ordering-term extension through contact, one prediction then one corrected movement; no implicit solve/reference injection. All predictor inputs read before native queries; same-step native outputs checked. Experimental host residue, no production/replay/capacity acceptance.')
(cap/'explicit-result.json').write_text(json.dumps(report,indent=2)+'\n');print(verified,'matching saved states',matching)
