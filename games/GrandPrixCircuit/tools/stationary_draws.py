"""Read front-car draw coordinates while neutral input holds the player still."""
import json,re,sys
from pathlib import Path
from state_fields import command
from gpc import server
p=Path(sys.argv[1]);m=json.loads((p/'metadata.json').read_text());h=m['code_base'];a=m['data_base']+32766
r=command(f'''break *{h+0x772a:#x}
break *{h+0x8e4e:#x}
set $sf=0
while $sf < 360
continue
if $pc == {h+0x772a:#x}
set $sf=$sf+1
else
printf "DRAW %d %d %d %d %d\\n", $sf, *(short*){a-1518:#x}, (short)$d4, (short)$d5, *(short*){a-29944:#x}
end
end
delete
''')
(p/'draws-gdb.txt').write_text(r)
assert 'Error' not in r and 'Invalid hex' not in r
rows=[list(map(int,x)) for x in re.findall(r'^DRAW (\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+)$',r,re.M)]
assert rows
(p/'draws.json').write_text(json.dumps(rows)+'\n')
print('draws',len(rows),'IDs',sorted(set(x[1]//2 for x in rows)), 'x',min(x[2] for x in rows),max(x[2] for x in rows),'y',min(x[3] for x in rows),max(x[3] for x in rows),'speed',sorted(set(x[4] for x in rows)))
