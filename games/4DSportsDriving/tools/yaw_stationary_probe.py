#!/usr/bin/env python3
"""Count actual idle physics completions; native recorded tick stays zero."""
import argparse,json,re,struct
from pathlib import Path
from profile_window import command,ROOT
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('heading',type=int);p.add_argument('fraction',type=int);p.add_argument('--after-driving',action='store_true');p.add_argument('--steps',type=int,default=250);a=p.parse_args();cap=a.capture.resolve();m=json.loads((cap/'anchor.json').read_text());b=(cap/'memory.bin').read_bytes();g=m['game_base'];aa=m['data_base']+0x7ffe;car=aa-0x92e;private=m['memory_base']+b.index(b'4DA4PHYS')+12
script=f'''gdb delete
set $n=0
set $yawcalls=0
break *{g+0xd4a6:#x}
commands
silent
set $yawcalls=$yawcalls+1
continue
end
break *{g+0xe7b4:#x}
commands
silent
set $n=$n+1
printf "IDLE %u %u %u %u %d %d %d %d %u %u %u\\n", $n, $yawcalls, *(unsigned short *){aa-0x940:#x}, *(unsigned short *){car+0x18:#x}, *(short *){private+128:#x}, *(int *){car:#x}, *(int *){car+4:#x}, *(int *){car+8:#x}, *(unsigned short *){car+0x2a:#x}, *(unsigned short *){car+0x2c:#x}, *(unsigned char *){car+0xc9:#x}
if $n<{a.steps}
continue
end
end
continue
delete'''
(cap/'stationary-probe.gdb').write_text(script)
out=command(script);(cap/'stationary-probe.txt').write_text(out)
rows=[list(map(int,s.split())) for s in re.findall(r'^IDLE (.*)$',out,re.M)]
(cap/'stationary-observations.json').write_text(json.dumps(dict(rows=rows,rate=m['active_simulation_word'],expected_heading=a.heading,expected_fraction=a.fraction),indent=2)+'\n')
assert len(rows)==a.steps
assert [r[0] for r in rows]==list(range(1,a.steps+1))
assert rows[-1][1] in (0,a.steps), 'Unexpected partial geometry coverage'
assert all(r[3:5]==[a.heading,a.fraction] and r[8:]==[0,0,0] for r in rows),rows[:3]
assert len({tuple(r[5:8]) for r in rows})==1
if a.after_driving:assert [r[2] for r in rows]==list(range(rows[0][2],rows[0][2]+a.steps))
result=dict(update_returns=a.steps,geometry_calls=rows[-1][1],first_recorded_tick=rows[0][2],last_recorded_tick=rows[-1][2],heading=a.heading,fraction=a.fraction,position=rows[0][5:8],drift=False,crash_free=True,scope='Source-seeded fraction; counted native update returns. Geometry count reported separately. Not a PAL timing/capacity measurement')
(cap/'stationary-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
command(f'gdb dump binary memory {cap.relative_to(ROOT)}/stationary-end.bin 0x200000 0x600000')
