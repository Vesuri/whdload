#!/usr/bin/env python3
"""Read native suspension inputs, selected clearance and outputs for each wheel."""
import json,re,sys
from pathlib import Path
from profile_window import command
p=Path(sys.argv[1]);updates=int(sys.argv[2]);m=json.loads((p/'anchor.json').read_text());g=m['game_base'];a=m['data_base']+0x7ffe
script=f'''gdb delete
set $n=0
break *{g+0xd2b6:#x}
commands
silent
set $car=*(unsigned int *)$sp
set $wheel=*(short *)($sp+6)
printf "IN %d %d %d %d %d %d\\n", *(unsigned short *){a-0x940:#x}, $wheel, *(short *)($sp+4), *(short *)($car+0x54+2*$wheel), *(short *)($car+0x6c+2*$wheel), *(short *)($car+0x4c+2*$wheel)
continue
end
break *{g+0x10114:#x}
commands
silent
printf "CLEAR %d\\n", *(short *)($a5+12)
continue
end
break *{g+0xd2ba:#x}
commands
silent
printf "OUT %d %d %d %d\\n", (short)$d0, *(short *)($car+0x54+2*$wheel), *(short *)($car+0x6c+2*$wheel), *(short *)($car+0x4c+2*$wheel)
continue
end
break *{g+0xe7b4:#x}
commands
silent
set $n=$n+1
if $n<{updates}
continue
end
end
continue
delete
'''
(p/'landing-suspension.gdb').write_text(script);out=command(script);(p/'landing-suspension.txt').write_text(out)
inputs=[list(map(int,x.split())) for x in re.findall(r'^IN (.*)$',out,re.M)];clear=[int(x) for x in re.findall(r'^CLEAR (.*)$',out,re.M)];outputs=[list(map(int,x.split())) for x in re.findall(r'^OUT (.*)$',out,re.M)]
assert len(inputs)==len(clear)==len(outputs)==updates*4
assert [(r[0],r[1]) for r in inputs]==[(inputs[0][0]+n,w) for n in range(updates) for w in range(4)]
rows=[dict(tick=i[0],wheel=i[1],clearance=i[2],branch_clearance=c,old_extension=i[3],old_bias=i[4],old_velocity=i[5],returned=o[0],new_extension=o[1],new_bias=o[2],new_velocity=o[3]) for i,c,o in zip(inputs,clear,outputs)]
result=dict(rate=m['active_simulation_word'],updates=updates,rows=rows,branches={str(sign):sum((r['branch_clearance']>0)-(r['branch_clearance']<0)==sign for r in rows) for sign in (-1,0,1)})
(p/'landing-suspension.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
