#!/usr/bin/env python3
import json,re,sys
from pathlib import Path
from profile_window import command
end=int(sys.argv[2]) if len(sys.argv)>2 else 8
p=Path(sys.argv[1]);m=json.loads((p/'anchor.json').read_text());g=m['game_base']
symbols={name:int(value,16) for name,value in re.findall(r'^([\w.]+)\s+00:([0-9A-Fa-f]+)\s*$',(p/'slave.lst').read_text(encoding='latin1'),re.M)}
base=m['marker']+8-symbols['tape_game'];gate=base+symbols['sim_tilt_stabilize']
s=f'''delete
break *{gate:#x}
commands
silent
printf "GATE %d %d %d %d %d\\n", *(unsigned short *)($a4-0x940), (int)$d0, (int)$d5, *(short *)$a2, *(short *)(*(unsigned int *)($a5+8)+0x1a)
continue
end
break *{g+0xd584:#x}
commands
silent
printf "PITCH %d %d\\n", *(unsigned short *)($a4-0x940), *(short *)($a4+0xbaa)
continue
end
break *{g+0xe7b4:#x}
commands
silent
if *(unsigned short *)($a4-0x940)<{end}
continue
end
end
continue
delete
'''
script=p/'gate.commands.gdb';script.write_text(s);out=command('gdb source '+str(script));(p/'gate.txt').write_text(out)
rows=[]
wrap=lambda n:(n+262144)%524288-262144
for vals in re.findall(r'^GATE (.*)$',out,re.M):
 t,d,b,c,old=map(int,vals.split());reference=wrap(2*(b-65536+c)+5*d);actual=wrap(2*(b-65536+c+d))
 rows.append(dict(tick=t,delta_q8=d,baseline_q8=b,carry=c,old_pitch=old,reference_q9=reference,actual_q9=actual,reference_pass=abs(reference)<816,actual_pass=abs(actual)<816))
pitches=[dict(tick=int(t),pitch=int(v)) for t,v in re.findall(r'^PITCH (\d+) (-?\d+)$',out,re.M)]
steps=end-m['simulation_tick']
assert len(rows)==2*steps and len(pitches)==steps,(len(rows),len(pitches))
report=dict(rows=rows,pitches=pitches,false_near_level=[r for r in rows if r['reference_pass'] and not r['actual_pass']],scope='Actual live gate inputs. Q9 reference extrapolates delta by2.5; actual uses one measured delta. Both independently wrapped. Pitch and roll invoke this gate; old_pitch helps identify pitch but is not alone a call discriminator.')
(p/'gate-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
