#!/usr/bin/env python3
"""Read complete allocated data at completed native steps; never mutate target state."""
import argparse,json,os,re,shutil,tempfile
from pathlib import Path
from state_fields import command
p=argparse.ArgumentParser();p.add_argument('fields',type=int);p.add_argument('out',type=Path);a=p.parse_args();out=a.out.resolve();m=json.loads((out/'metadata.json').read_text());h=m['code_base'];db=m['data_base'];end=db+0x9364
(out/'state').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='gpc-p3-',dir='tmp') as temp:
 temp=os.path.relpath(temp)
 reply=command(f'''break *{h+0x7762:#x}
break *{h+0x7754:#x}
break *{h+0x39e:#x}
set $p3_step_active=0
set $p3_field=0
set $p3_ticks=0
set $p3_swaps=0
while $p3_field < {a.fields}
continue
if $pc == {h+0x7762:#x}
if $p3_step_active
set $p3_step_active=0
eval "dump binary memory {temp}/%04d.bin {db:#x} {end:#x}", $p3_field
printf "GPCFIELD %d %d %d\\n", $p3_field, $p3_ticks, $p3_swaps
set $p3_field=$p3_field+1
end
else
if $pc == {h+0x7754:#x}
set $p3_ticks=$p3_ticks+1
set $p3_step_active=1
else
set $p3_swaps=$p3_swaps+1
end
end
end
delete
''')
 (out/'state/gdb.txt').write_text(reply)
 files=sorted(Path(temp).glob('*.bin'));assert len(files)==a.fields,len(files)
 for f in files:shutil.move(str(f),out/'state'/f.name)
rows=[list(map(int,r)) for r in re.findall(r'^GPCFIELD (\d+) (\d+) (\d+)$',reply,re.M)];assert len(rows)==a.fields
(out/'state/counts.json').write_text(json.dumps(rows)+'\n');(out/'state/metadata.json').write_text(json.dumps(m,indent=2)+'\n')
print(f'{a.fields} completed-step snapshots, {rows[-1][1]} steps and {rows[-1][2]} publications')
