#!/usr/bin/env python3
"""Sparse VBL snapshots for lap handling, not callback/FPS measurements."""
import argparse,json,os,re,shutil,tempfile
from pathlib import Path
from state_fields import command
p=argparse.ArgumentParser();p.add_argument('fields',type=int);p.add_argument('out',type=Path);a=p.parse_args();out=a.out.resolve();m=json.loads((out/'metadata.json').read_text());h=m['code_base'];db=m['data_base'];a4=db+32766
(out/'state').mkdir(exist_ok=True);stride=6
with tempfile.TemporaryDirectory(prefix='gpc-lap-',dir='tmp') as temp:
 temp=os.path.relpath(temp)
 reply=command(f"""set remote memory-read-packet-size 1024
break *{h+0x772a:#x}
set $lap_vbl_bp=$bpnum
break *{h+0x1e32:#x}
break *{h+0x7b8e:#x}
set $lap_done=0
set $lap_field=0
while $lap_field < {a.fields} && $lap_done == 0
continue
set $lap_field=*(unsigned int*){a4-31790:#x}-{m['epoch']}
if $pc == {h+0x772a:#x}
eval \"dump binary memory {temp}/%05d.bin {db:#x} {db+0x9364:#x}\", $lap_field-1
printf \"GPCLAPFIELD %d\\n\", $lap_field
set $lap_done=(*(unsigned short*){a4+3728:#x} != 0 || (*(unsigned short*){a4-29944:#x} == 0 && *(short*){a4-29942:#x} >= 2 && *(short*){a4-29942:#x} <= 4))
ignore $lap_vbl_bp {stride-1}
else
printf \"GPCLAPEVENT %d %x\\n\", $lap_field, $pc-{h:#x}
end
end
delete
""")
 (out/'state/gdb.txt').write_text(reply)
 assert 'Invalid hex' not in reply and 'Error' not in reply,reply[-1000:]
 files=list(Path(temp).glob('*.bin'));assert files
 for f in files:shutil.move(str(f),out/'state'/f.name)
rows=[int(x) for x in re.findall(r'^GPCLAPFIELD (\d+)$',reply,re.M)];assert rows
assert len(rows)==len(files)
(out/'state/events.json').write_text(json.dumps(re.findall(r'^GPCLAPEVENT (\d+) ([0-9a-f]+)$',reply,re.M))+'\n')
(out/'state/metadata.json').write_text(json.dumps(m|{'sampling_mode':'sparse lap only; no callback or publication counts','stride':stride},indent=2)+'\n')
print(f'{len(rows)} sparse states through native field {rows[-1]}; no FPS or callback count measured')
