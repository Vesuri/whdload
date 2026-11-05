#!/usr/bin/env python3
"""Read-only ordered drivetrain/contact-state capture through the crest course."""
import json,re,struct,sys
from pathlib import Path
from profile_window import command
from simulation_fixture import read_fixture
cap=Path(sys.argv[1]);m=json.loads((cap/'anchor.json').read_text());g=m['game_base'];memory=(cap/'memory.bin').read_bytes();private=m['memory_base']+memory.index(b'4DA4PHYS')+12
assert m['active_simulation_word']==50 and m['opponent']==0 and m['simulation_tick']==450
T='*(unsigned short *)($a4-0x940)'
def cw(ptr,offset,typ='unsigned short'):return f'*({typ} *)(({ptr})+{offset})'
def log(tag,expr):return 'printf "'+tag+' '+' '.join('%d' for _ in expr)+'\\n", '+', '.join(expr)+'\n'
car='*(unsigned int *)($a5+12)';move_car='*(unsigned int *)($a5+8)';body_car='$a4-0x92e'
def common(ptr):return [cw(ptr,o,typ) for o,typ in ((0x1e,'short'),(0x22,'unsigned short'),(0x2a,'unsigned short'),(0x2c,'unsigned short'),(0x2e,'unsigned short'),(0x30,'unsigned short'),(0x32,'unsigned short'),(0xc0,'unsigned char'),(0xc1,'unsigned char'))]
s='delete\n'
for off,tag,expr in [(0xf3ca,'PRE_ENGINE',[T,'*(unsigned int *)($a5+16)','*(unsigned char *)($a5+8)','*(unsigned char *)($a5+10)']+[cw(car,o) for o in range(0,208,2)]),(0xf60c,'ACCEL',[T,'*(unsigned short *)($a5-2)','*(short *)($a5-4)',f'*(short *){private+2}']+common(car)),(0xf66e,'APPLIED',[T,'*(unsigned short *)($a5-2)']+common(car)),(0xf6f2,'SYNC',[T]+common(car)),(0xf7d2,'ENGINE_END',[T]+common(car)),(0xc326,'DIST',[T,f'*(unsigned short *){private+4}']+common(move_car)),(0xc346,'DIST_END',[T,'*(unsigned short *)($a5-6)',f'*(unsigned short *){private+4}'])]:
    s+=f'break *{g+off:#x}\ncommands\nsilent\n'+log(tag,expr)+'continue\nend\n'
s+=f'break *{g+0xe7b4:#x}\ncommands\nsilent\n'+log('BODY',[T]+common(body_car))+f'if {T}<800\ncontinue\nend\nend\ncontinue\ndelete\n'
f=cap/'drivetrain.gdb';f.write_text(s);out=command('gdb source '+str(f.resolve()));(cap/'drivetrain.txt').write_text(out)
r={tag:[list(map(int,v.split())) for v in re.findall(r'^'+tag+r' (.*)$',out,re.M)] for tag in ('PRE_ENGINE','ACCEL','APPLIED','SYNC','ENGINE_END','DIST','DIST_END','BODY')}
assert all(len(v)==350 for v in r.values()),{k:len(v) for k,v in r.items()}
assert all([row[0] for row in v]==list(range(451,801)) for v in r.values())
command(f'gdb dump binary memory {cap}/drivetrain-end.bin {m["memory_base"]:#x} {m["memory_base"]+m["memory_size"]:#x}')
ref={t:s for t,hz,s in read_fixture(Path('tmp/prof/crest-d9e7903'),'bridge-end.bin')};samples=read_fixture(cap,'drivetrain-end.bin');assert all(s==ref[t] for t,hz,s in samples)
(cap/'drivetrain.json').write_text(json.dumps(dict(records=r,common_fields=['slope_force','rpm','speed','target','saved_target','ratio30','ratio32','flag_c0','flag_c1'],matching_full_states=len(samples)),indent=2)+'\n')
print({k:len(v) for k,v in r.items()},'matching full states',len(samples))
