#!/usr/bin/env python3
"""Evaluate predeclared stopped-car drift limits using completed native updates."""
import json,re,struct,sys
from pathlib import Path
from profile_window import command,ROOT
cap=Path(sys.argv[1]).resolve();criteria=Path(sys.argv[2]);limits=json.loads(criteria.read_text());m=json.loads((cap/'anchor.json').read_text());b=(cap/'memory.bin').read_bytes();aa=m['data_base']+0x7ffe;car=aa-0x92e;g=m['game_base'];priv=m['memory_base']+b.index(b'4DA4PHYS')+12
start=struct.unpack_from('>iii',b,car-m['memory_base'])
script=f'''gdb delete
set $n=0
set $geometry=0
break *{g+0xd4a6:#x}
commands
silent
set $geometry=$geometry+1
continue
end
break *{g+0xe7b4:#x}
commands
silent
set $n=$n+1
printf "STOP %u %u %u %d %d %d %u %u %u %u %u %u %u\\n", $n, $geometry, *(unsigned short *){aa-0x940:#x}, *(int *){car:#x}, *(int *){car+4:#x}, *(int *){car+8:#x}, *(unsigned short *){car+0x18:#x}, *(unsigned short *){car+0x2a:#x}, *(unsigned short *){car+0x2c:#x}, *(unsigned char *){car+0xc9:#x}, *(unsigned short *){priv+132:#x}, *(unsigned short *){priv+134:#x}, *(unsigned short *){priv+136:#x}
if $n<{limits['updates']}
continue
end
end
continue
delete'''
(cap/'centroid-stop.gdb').write_text(script);out=command(script);(cap/'centroid-stop.txt').write_text(out)
rows=[list(map(int,x.split())) for x in re.findall(r'^STOP (.*)$',out,re.M)]
assert len(rows)==limits['updates'] and [r[0] for r in rows]==list(range(1,len(rows)+1))
assert [r[1] for r in rows]==list(range(1,len(rows)+1))
assert [r[2] for r in rows]==list(range(rows[0][2],rows[0][2]+len(rows)))
positions=[start]+[r[3:6] for r in rows];span=[max(p[i] for p in positions)-min(p[i] for p in positions) for i in range(3)];delta=[positions[-1][i]-start[i] for i in range(3)]
checks=dict(horizontal_span=all(span[i]<=limits['maximum_horizontal_span'] for i in (0,2)),horizontal_displacement=all(abs(delta[i])<=limits['maximum_horizontal_net_displacement'] for i in (0,2)),heading=all(r[6]==limits['require_stable_heading'] for r in rows),speed=all(r[7:9]==[0,0] for r in rows),crash=all(r[9]==0 for r in rows))
result=dict(passed=all(checks.values()),checks=checks,rate=m['active_simulation_word'],updates=len(rows),start=start,end=positions[-1],delta=delta,span=span,carry_start=struct.unpack_from('>HHH',b,priv+132-m['memory_base']),carry_end=rows[-1][10:13],rows=rows)
(cap/'centroid-stop-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
command(f'gdb dump binary memory {cap.relative_to(ROOT)}/centroid-stop-end.bin 0x200000 0x600000')
raise SystemExit(0 if result['passed'] else 1)
