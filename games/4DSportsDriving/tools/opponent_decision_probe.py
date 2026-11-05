#!/usr/bin/env python3
"""Read-only 250-completed-step opponent/waypoint/RNG trace from tick0.
This is a determinism/decision audit, not a wall-clock capacity measurement.
"""
import json,re,struct,sys,hashlib
from pathlib import Path
from profile_window import command,ROOT
cap=Path(sys.argv[1]).resolve();m=json.loads((cap/'anchor.json').read_text())
assert m['simulation_tick']==0 and m['opponent']==1 and m['active_simulation_word']==50
resume='--resume-waypoint' in sys.argv
assert resume or not (cap/'ai-log.txt').exists()
g=m['game_base'];aa=m['data_base']+0x7ffe;car=aa-0x85e
s={n:int(v,16) for n,v in re.findall(r'^([\w.]+)\s+00:([0-9a-fA-F]+)\s*$',(cap/'slave.lst').read_text(encoding='latin1'),re.M)}
slave=m['marker']+8-s['tape_game']
def expr(addr,kind):return f'*({kind} *){addr:#x}'
fields=[('tick',aa-0x940,'unsigned short')]
fields += [(n,car+o,k) for n,o,k in [('x',0,'int'),('y',4,'int'),('z',8,'int'),('heading',0x18,'short'),('pitch',0x1a,'short'),('roll',0x1c,'short'),('steering',0x20,'short'),('speed',0x2a,'unsigned short'),('target_speed',0x2c,'unsigned short'),('slip',0x36,'short'),('spin',0x3e,'short'),('crashed',0xc9,'unsigned char')]]
fields += [(n,aa+o,k) for n,o,k in [('route_index',-0x814,'unsigned short'),('segment',-0x790,'unsigned char'),('lap',-0x791,'unsigned char'),('goal_x',-0x7ba,'short'),('goal_y',-0x7b8,'short'),('goal_z',-0x7b6,'short'),('speed_goal',-0x687,'unsigned char'),('rng01',0x228,'unsigned short'),('rng23',0x22a,'unsigned short'),('rng45',0x22c,'unsigned short')]]
fmt='AI '+' '.join(['%d']*len(fields))+r'\n'
args=', '.join(expr(a,k) for _,a,k in fields)
script=rf'''gdb delete
set $ai_calls=0
set $ai_paths=0
set $ai_rng=0
break *{g+0xbc48:#x}
commands
silent
set $ai_calls=$ai_calls+1
continue
end
break *{g+0x109c2:#x} if *(unsigned int *)($sp+6)=={aa-0x7ba:#x}
commands
silent
set $ai_paths=$ai_paths+1
printf "PATH %u %u %u %u\n", *(unsigned short *)($a4-0x940), *(unsigned int *)$sp-{g}, *(unsigned short *)($sp+4), *(unsigned char *)($sp+10)
continue
end
break *{g+0x11e1c:#x}
commands
silent
set $ai_rng=$ai_rng+1
printf "RNG %u %u\n", *(unsigned short *)($a4-0x940), *(unsigned int *)$sp-{g}
continue
end
break *{g+0xe7b4:#x}
commands
silent
printf "{fmt}", {args}
if *(unsigned short *)($a4-0x940)<250
continue
end
end
continue
printf "COUNTS %u %u %u %u\n", $ai_calls, $ai_paths, $ai_rng, {expr(slave+s['tape_frames'],'unsigned int')}
info registers pc
'''
prefix=''
if resume:
 prefix=(cap/'ai-log.txt').read_text()
 assert int(re.findall(r'^pc\s+0x([0-9a-f]+)',prefix,re.M)[-1],16)==g+0x109c2
 (cap/'ai-prefix.txt').write_text(prefix)
 for name in ('calls','paths','rng'): script=script.replace(f'set $ai_{name}=0\n','')
 line=next(l for l in script.splitlines() if l.startswith('printf "PATH '))
 script=script.replace('gdb delete\n','gdb delete\n'+line+'\n',1)
(cap/'ai-probe.gdb').write_text(script)
answer=prefix+'\n'+command(script);(cap/'ai-log.txt').write_text(answer)
assert int(re.findall(r'^pc\s+0x([0-9a-f]+)',answer,re.M)[-1],16)==g+0xe7b4
command(f'gdb dump binary memory {cap.relative_to(ROOT)}/ai-end.bin 0x200000 0x600000')
b=(cap/'ai-end.bin').read_bytes();off=m['memory_base']
assert struct.unpack_from('>I',b,slave+s['perf_failure']-off)[0]==0
steps=[[int(x) for x in l.split()[1:]] for l in answer.splitlines() if l.startswith('AI ')]
paths=[[int(x) for x in l.split()[1:]] for l in answer.splitlines() if l.startswith('PATH ')]
rng=[[int(x) for x in l.split()[1:]] for l in answer.splitlines() if l.startswith('RNG ')]
counts=[int(x) for x in re.search(r'^COUNTS (.*)$',answer,re.M)[1].split()]
assert [x[0] for x in steps]==list(range(1,251)) and counts[:3]==[250,len(paths),len(rng)]
state=b[aa-off-0xa80:aa-off-0x620]+b[aa-off+0x228:aa-off+0x22e]
for marker,n in [(b'4DA4PHYS',128),(b'4DTSTATE',32),(b'4DAUXPHY',192),(b'4DCAM050',8)]:
 q=b.index(marker)+12;state+=b[q:q+n]
assert len(state)==1486
(cap/'ai-final-state.bin').write_bytes(state)
result={'columns':[n for n,_,_ in fields],'steps':steps,'path_calls':paths,'rng_calls':rng,'counts':counts,'final_state_sha256':hashlib.sha256(state).hexdigest(),'graphics':m['graphics'],'scope':'250 complete simulation updates under deterministic controls; not250PAL fields/capacity'}
(cap/'ai-probe.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('counts','path_calls','rng_calls','final_state_sha256','graphics')},indent=2))
