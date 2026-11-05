#!/usr/bin/env python3
"""Causal movement-order diagnostic in a matched, fully airborne interval."""
import json,re,sys
from pathlib import Path
from airborne_pitch_predictor import predict
from native_contact_response import sine
from profile_window import command,ROOT
from simulation_fixture import read_fixture
cap=Path(sys.argv[1]);identity='--identity' in sys.argv;m=json.loads((cap/'anchor.json').read_text())
assert m['simulation_tick']==3 and m['active_simulation_word']==50 and m['opponent']==0
mem=(cap/'memory.bin').read_bytes();private=m['memory_base']+mem.index(b'4DA4PHYS')+12;g=m['game_base']
tick='*(unsigned short *)($a4-0x940)';car='*(unsigned int *)($a5+8)'
def log(tag,expr):return 'printf "'+tag+' '+' '.join('%d' for _ in expr)+'\\n", '+', '.join(expr)+'\n'
entry=[tick]+[f'*(short *)(({car})+{off})' for off in (0x1a,0x1c,0x18)]+['*(short *)($a5-6)']
entry += [f'*(short *)(({car})+{off+2*w})' for off in (0x54,0x4c) for w in range(4)]
entry += [f'*(short *){private+off+4*w}' for off in (8,10) for w in range(4)]
entry += [f'*(short *){private+144}']
entry += [f'*(int *)($a5+({base+4*i}))' for base in (-0xe2,-0xb2) for i in range(12)]
body_names=('tick','x','y','z','pitch','carry','v0','v1','v2','v3')
body=[tick]+[f'*(int *)($a4+({o}))' for o in (-0x92e,-0x92a,-0x926)]+['*(short *)($a4-0x914)',f'*(short *){private+144}']+[f'*(short *)($a4+({-0x92e+0x4c+2*w}))' for w in range(4)]
setup='delete\n'+f'break *{g+0xc60c:#x}\ncommands\nsilent\n'+log('ENTRY',entry)+'end\n'
for off,tag in ((0xcb06,'CLEAR'),(0xcc2e,'AFTER')):
    setup+=f'break *{g+off:#x}\ncommands\nsilent\n'+log(tag,[tick,'*(unsigned char *)($a5-3)','*(short *)($a4+0xbc0)','*(short *)($a5-8)'])+'continue\nend\n'
setup+=f'break *{g+0xe7b4:#x}\ncommands\nsilent\n'+log('BODY',body)+'if '+tick+'<31\ncontinue\nend\nend\n'
f=cap/'order-setup.gdb';f.write_text(setup);command('gdb source '+str(f.resolve()))
records=[];bodies=[];clearances=[];residues=[0,0,0];pending=None
with (cap/'order-log.txt').open('w') as output:
    while True:
        result=command('gdb continue');output.write(result);output.flush()
        for tag,values in re.findall(r'^(CLEAR|AFTER) (.*)$',result,re.M):
            r=list(map(int,values.split()));assert r[2]>12 and r[3]==0,(tag,r)
            clearances.append([tag,*r])
        for values in re.findall(r'^BODY (.*)$',result,re.M):
            r=dict(zip(body_names,map(int,values.split())));assert pending is not None
            assert r['tick']==pending['tick'] and r['pitch']==pending['prediction']['pitch'] and r['carry']==pending['prediction']['carry'],(r,pending)
            assert [r[f'v{i}'] for i in range(4)]==pending['prediction']['velocities']
            bodies.append(r)
        if bodies and bodies[-1]['tick']==31:break
        values=re.findall(r'^ENTRY (.*)$',result,re.M);assert len(values)==1,result
        r=list(map(int,values[0].split()));assert len(r)==46,len(r)
        t,pitch,roll,heading,distance=r[:5];extension=r[5:9];velocity=r[9:13];vf=r[13:17];pf=r[17:21];carry=r[21]
        assert extension==[384]*4 and roll==heading==0
        wheels=[r[22+3*w:25+3*w] for w in range(4)];translated=[r[34+3*w:37+3*w] for w in range(4)]
        pred=predict(wheels,velocity,vf,pf,carry)
        old=[0,sine(pitch),sine(pitch+256)];new=[0,sine(pred['pitch']),sine(pred['pitch']+256)]
        correction=[]
        for axis in range(3):
            c,rem=divmod(residues[axis]+3*distance*(old[axis]-new[axis]),65536)
            if identity:c=0;rem=0
            correction.append(c);residues[axis]=rem
        changes=[];reads=[];expected=[]
        for w in range(4):
            for axis in range(3):
                pointer=f'*(int *)($a5+({-0xb2+12*w+4*axis}))';value=translated[w][axis]+correction[axis]
                changes.append(f'set {pointer}={value}');reads.append(pointer);expected.append(value)
        f=cap/'order-write.gdb';f.write_text('\n'.join(changes)+'\nmaintenance flush register-cache\n'+log('APPLIED',reads))
        applied=command('gdb source '+str(f.resolve()));output.write(applied);output.flush()
        obs=re.findall(r'^APPLIED (.*)$',applied,re.M);assert len(obs)==1 and list(map(int,obs[0].split()))==expected
        pending=dict(tick=t,old_pitch=pitch,prediction=pred,distance=distance,correction=correction,residues=residues.copy());records.append(pending)
command('gdb delete')
assert len(records)==len(bodies)==28 and len(clearances)==224
command(f'gdb dump binary memory {cap}/order-end.bin {m["memory_base"]:#x} {m["memory_base"]+m["memory_size"]:#x}')
baseline=json.loads((ROOT/'tmp/prof/matched-flight50/landing-motion-check.json').read_text())['rows']
assert [r['tick'] for r in baseline]==[r['tick'] for r in bodies]
if identity:assert all(b['final_position']==[r[k] for k in ('x','y','z')] for b,r in zip(baseline,bodies))
errors=[dict(tick=r['tick'],position_delta=[r[k]-b['final_position'][i] for i,k in enumerate(('x','y','z'))]) for b,r in zip(baseline,bodies)]
report=dict(identity=identity,records=records,bodies=bodies,clearance_checks=len(clearances),baseline_position_deltas=errors,
 scope='Matched airborne source, ticks4..31. Pre-contact common-vector correction 3/4 times old-minus-predicted-new direction times current distance; fixed Q16 host residue. All224 actual queries remain>12 and roof correction0; every predicted pitch/carry/velocity verified after the SAME update. No contact-domain rule, runtime/replay promotion, or full-course acceptance.')
(cap/'order-result.json').write_text(json.dumps(report,indent=2)+'\n')
print('28 verified movement writes/predictions,224 positive clearance checks')
print('Final position difference from unmodified matched50:',errors[-1])
