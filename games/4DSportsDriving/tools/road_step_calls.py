#!/usr/bin/env python3
import re,json,sys
from pathlib import Path
from profile_window import command
p=Path(sys.argv[1]);m=json.loads((p/'anchor.json').read_text());g=m['game_base'];s={n:int(v,16) for n,v in re.findall(r'^([\w.]+)\s+00:([0-9A-Fa-f]+)\s*$',(p/'slave.lst').read_text(encoding='latin1'),re.M)};base=m['marker']+8-s['tape_game']
script=f'''gdb delete
break *{base+s['sim_road_step_fixture']:#x}
commands
silent
printf "CALL %u %u\\n", *(unsigned short *)($a4-0x940), *(unsigned int *)($a5+4)-{g}
continue
end
break *{g+0xe7b4:#x}
continue
delete
'''
(p/'road-calls.gdb').write_text(script);out=command(script);(p/'road-calls.txt').write_text(out)
rows=[list(map(int,x.split())) for x in re.findall(r'^CALL (.*)$',out,re.M)];assert len(rows)==8 and len({x[0] for x in rows})==1
counts={hex(v):sum(x[1]==v for x in rows) for _,v in rows}
result=dict(calls=8,tick=rows[0][0],callers=counts);(p/'road-calls.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
