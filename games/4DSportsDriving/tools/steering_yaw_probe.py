#!/usr/bin/env python3
"""Read-only debugger trace of wheel-geometry heading reconstruction."""
import json,re,sys
from pathlib import Path
from profile_window import command
cap=Path(sys.argv[1]).resolve()
a=json.loads((cap/'anchor.json').read_text())
g=a['game_base']; aa=a['data_base']+0x7ffe; hz=a['active_simulation_word']
assert a['simulation_tick']==hz
script=f'''gdb delete
set $n=0
break *{g+0xd49e:#x}
commands
silent
printf "YAWIN %u %d %d %d %d %d %d %d\\n", *(unsigned short *){aa-0x940:#x}, *(short *){aa-0x916:#x}, *(short *){aa-0x90e:#x}, *(short *)($a5-0x72), *(short *)($a5-0x74), *(short *)(*(unsigned int *)($a5+8)+0x3e), *(int *)($a5-0xca)+*(int *)($a5-0xbe)-*(int *)($a5-0xe2)-*(int *)($a5-0xd6), *(int *)($a5-0xc2)+*(int *)($a5-0xb6)-*(int *)($a5-0xda)-*(int *)($a5-0xce)
continue
end
break *{g+0xd4a2:#x}
commands
silent
printf "YAWOUT %d\\n", (short)$d0
set $n=$n+1
if $n<{hz//2+1}
continue
end
end
continue
delete'''
(cap/'yaw-probe.gdb').write_text(script)
out=command(script);(cap/'yaw-probe.txt').write_text(out)
ins=[list(map(int,x.split())) for x in re.findall(r'^YAWIN (.*)$',out,re.M)]
outs=[int(x) for x in re.findall(r'^YAWOUT (-?\d+)$',out,re.M)]
assert len(ins)==len(outs)==hz//2+1
rows=[dict(tick=i[0],old_heading=i[1],steering=i[2],x=i[3],z=i[4],spin=i[5],baseline_x=i[6],baseline_z=i[7],new_heading=o) for i,o in zip(ins,outs)]
(cap/'yaw-probe.json').write_text(json.dumps(dict(rate=hz,rows=rows),indent=2)+'\n')
print(json.dumps(rows,indent=2))
