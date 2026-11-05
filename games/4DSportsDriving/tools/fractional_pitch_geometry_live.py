#!/usr/bin/env python3
"""Straight-course diagnostic: carry-aware wheel matrix and anchored old pitch."""
import json,re,sys,struct
from pathlib import Path
from native_contact_response import sine
from profile_window import command,ROOT
from simulation_fixture import read_fixture
identity='--identity' in sys.argv
cap=Path(sys.argv[1]);m=json.loads((cap/'anchor.json').read_text());assert m['simulation_tick']==450 and m['active_simulation_word']==50 and m['opponent']==0
mem=(cap/'memory.bin').read_bytes();private=m['memory_base']+mem.index(b'4DA4PHYS')+12;g=m['game_base'];aa=m['data_base']+0x7ffe
listing=(cap/'slave.lst').read_text(encoding='latin1')
symbols={k:int(v,16) for k,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)$',listing,re.M)}
base=private-symbols['sim_a4000_private']
anchor=[int(a,16) for a in re.findall(r'^00:([0-9A-F]+).*bsr sim_tilt_stabilize$',listing,re.M)]
assert len(anchor)==1
tick='*(unsigned short *)($a4-0x940)'
def printf(tag,expr):return 'printf "'+tag+' '+' '.join('%d' for _ in expr)+'\\n", '+', '.join(expr)+'\n'
pose_expr=[tick,'*(unsigned int *)($a5+8)']+[f'*(short *)($a4+{o})' for o in (0xbaa,0xba8,0xbac)]+[f'*(short *){private+o}' for o in (144,146)]+[f'*(short *)($a4+{0xbae+2*i})' for i in range(9)]
body_names=('tick','x','y','z','heading','pitch','roll','speed','slip','spin','contact','w0','w1','w2','w3','crash')
body_offsets=(-0x940,-0x92e,-0x92a,-0x926,-0x916,-0x914,-0x912,-0x904,-0x8f8,-0x8f0,-0x86d,-0x86c,-0x86b,-0x86a,-0x869,-0x865)
body_types=('unsigned short','int','int','int','short','short','short','unsigned short','short','short',*(['unsigned char']*6))
setup='delete\n'+f'break *{g+0xc37a:#x}\ncommands\nsilent\n'+printf('POSE',pose_expr)+'end\n'
setup+=f'break *{base+anchor[0]:#x} if $a2=={private+144:#x}\ncommands\nsilent\n'+printf('ANGLE',[tick,'(int)$d5','(int)$d0'])+'end\n'
setup+=f'break *{g+0xe7b4:#x}\ncommands\nsilent\n'+printf('BODY',[f'*({t} *)($a4+({o}))' for t,o in zip(body_types,body_offsets)])+'if '+tick+'<650\ncontinue\nend\nend\n'
f=cap/'fractional-setup.gdb';f.write_text(setup);command('gdb source '+str(f.resolve()))
poses=[];angles=[];bodies=[];writes=[];old_pitch=None
def matrix(p,f):
    k,t=divmod(p*256+f,256)
    s=(sine(k)*(256-t)+sine(k+1)*t)//256
    c=(sine(k+256)*(256-t)+sine(k+257)*t)//256
    return [16384,0,0,0,c,-s,0,s,c]
with (cap/'fractional-log.txt').open('w') as log:
    while True:
        result=command('gdb continue');log.write(result);log.flush()
        for values in re.findall(r'^BODY (.*)$',result,re.M):bodies.append(dict(zip(body_names,map(int,values.split()))))
        if bodies and bodies[-1]['tick']==650:break
        ps=re.findall(r'^POSE (.*)$',result,re.M);ags=re.findall(r'^ANGLE (.*)$',result,re.M)
        assert len(ps)+len(ags)==1,result
        changes=[];reads=[];expected=[]
        if ps:
            row=list(map(int,ps[0].split()));t,car,p,r,h,pf,rf,*original=row
            assert car==aa-0x92e and r==h==rf==0 and -256<p<256 and -128<=pf<=127,row
            assert original==matrix(p,0),(row,matrix(p,0))
            old_pitch=p;new=original if identity else matrix(p,pf);poses.append(dict(tick=t,pitch=p,fraction=pf,original=original,modified=new))
            for i,value in enumerate(new):
                pointer=f'*(short *){aa+0xbae+2*i:#x}'
                changes.append(f'set {pointer}={value}');reads.append(pointer);expected.append(value)
        else:
            t,d5,delta=map(int,ags[0].split());assert old_pitch is not None
            value=d5 if identity else (old_pitch+256)*256
            angles.append(dict(tick=t,native_baseline=d5,anchored_baseline=value,delta=delta))
            changes=[f'set $d5={value}'];reads=['(int)$d5'];expected=[value]
        f=cap/'fractional-write.gdb';f.write_text('\n'.join(changes)+'\nmaintenance flush register-cache\n'+printf('APPLIED',reads))
        out=command('gdb source '+str(f.resolve()));log.write(out);log.flush()
        observed=re.findall(r'^APPLIED (.*)$',out,re.M);assert len(observed)==1 and list(map(int,observed[0].split()))==expected,(t,out,expected)
        writes.append(dict(tick=t,kind='matrix' if ps else 'baseline',values=expected))
        if len(writes)%80==0:print('Verified interventions',len(writes),flush=True)
command('gdb delete')
assert len(poses)==len(angles)==len(bodies)==200
assert [r['tick'] for r in bodies]==list(range(451,651))
command(f'gdb dump binary memory {cap}/fractional-end.bin {m["memory_base"]:#x} {m["memory_base"]+m["memory_size"]:#x}')
ref={r['tick']:r for r in json.loads((ROOT/'tmp/prof/natural-crest20/bridge.json').read_text())['rows']}
common=[dict(time=r['tick']/50,error={k:r[k]-ref[r['tick']*2//5][k] for k in ('y','z','pitch')}) for r in bodies if r['tick']%10==0]
if identity:
    baseline={r['tick']:r for r in json.loads((ROOT/'tmp/prof/crest-d9e7903/bridge.json').read_text())['rows']}
    assert all(r==baseline[r['tick']] for r in bodies)
    full={t:s for t,hz,s in read_fixture(ROOT/'tmp/prof/crest-d9e7903','bridge-end.bin')}
    samples=read_fixture(cap,'fractional-end.bin');assert all(s==full[t] for t,hz,s in samples)
    print('Identity exact:',len(bodies),'body updates and',len(samples),'full states')
report=dict(identity=identity,poses=poses,angles=angles,bodies=bodies,writes=writes,common=common,
 scope='Diagnostic straight heading0/roll0: fractional pitch used in wheel matrix, old integer pitch anchors geometric delta to prevent a second native atan rounding. No interpolation in time. Other later body-obstacle matrices remain native integer; not a general runtime implementation, replay/capacity proof or full16s handling result.')
(cap/'fractional-result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(common[-3:],indent=2))
