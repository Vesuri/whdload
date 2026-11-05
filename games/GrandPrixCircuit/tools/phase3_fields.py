#!/usr/bin/env python3
"""Read complete data at native VBL entries, counting ticks and publications."""
import argparse,json,os,re,shutil,tempfile
from pathlib import Path
from state_fields import command
p=argparse.ArgumentParser();p.add_argument('fields',type=int);p.add_argument('out',type=Path);a=p.parse_args();out=a.out.resolve();m=json.loads((out/'metadata.json').read_text());h=m['code_base'];db=m['data_base'];end=db+0x9364
(out/'state').mkdir(exist_ok=True)
events=[0x5f62,0x61e2,0x66e8,0x66fc,0x7250,0x70f6,0x70fa,0x71e4,0x1e32,0x7b8e,0x7fce] if os.environ.get('EVENT_AUDIT')=='1' else []
stride=int(os.environ.get('STATE_STRIDE','1')); assert stride>=1
stop_expr=f'(*(unsigned short*){db+32766+3728:#x} != 0 || (*(unsigned short*){db+32766-29944:#x} == 0 && *(short*){db+32766-29942:#x} >= 2 && *(short*){db+32766-29942:#x} <= 4))' if os.environ.get('STOP_AT_LAP')=='1' else '0'
extra_breaks='\n'.join(f'break *{h+x:#x}' for x in events)
if os.environ.get('LATCH_AUDIT')=='1':extra_breaks+=f'\nbreak *{h+0xa6ea:#x}'

with tempfile.TemporaryDirectory(prefix='gpc-p3-',dir='tmp') as temp:
 temp=os.path.relpath(temp)
 reply=command(f'''set remote memory-read-packet-size 1024
break *{h+0x772a:#x}
break *{h+0x7754:#x}
break *{h+0x39e:#x}
{extra_breaks}
set $p3_done=0
set $p3_field=0
set $p3_ticks=0
set $p3_swaps=0
while $p3_field < {a.fields} && $p3_done == 0
continue
if $pc == {h+0x772a:#x}
set $p3_done = {stop_expr}
if $p3_field % {stride} == 0 || $p3_done != 0
eval "dump binary memory {temp}/%05d.bin {db:#x} {end:#x}", $p3_field
end
printf "GPCFIELD %d %d %d\\n", $p3_field, $p3_ticks, $p3_swaps
set $p3_field=$p3_field+1
else
if $pc == {h+0x7754:#x}
set $p3_ticks=$p3_ticks+1
else
if $pc == {h+0x39e:#x}
set $p3_swaps=$p3_swaps+1
else
if $pc == {h+0xa6ea:#x}
printf "GPCLATCH %d %d\\n", $p3_field, $p3_ticks
end
printf "GPCEVENT %d %x\\n", $p3_field, $pc-{h:#x}
if $pc == {h+0x66fc:#x}
printf "GPCPITTIME %d %d\\n", $p3_field, $d0
end
end
end
end
end
delete
''')
 (out/'state/gdb.txt').write_text(reply)
 files=sorted(Path(temp).glob('*.bin')); assert files
 assert 'Invalid hex' not in reply, 'debugger transport error: reject capture'
 assert 'Error' not in reply, 'debugger command error: reject capture'
 for f in files:shutil.move(str(f),out/'state'/f.name)
rows=[list(map(int,r)) for r in re.findall(r'^GPCFIELD (\d+) (\d+) (\d+)$',reply,re.M)];assert len(rows)==a.fields or os.environ.get('STOP_AT_LAP')=='1'
expected=set(range(0,len(rows),stride)); actual={int(f.stem) for f in (out/'state').glob('[0-9]*.bin')}; assert expected<=actual and actual<=expected|{len(rows)-1},(len(expected),len(actual))
(out/'state/latches.json').write_text(json.dumps([list(map(int,x)) for x in re.findall(r'^GPCLATCH (\d+) (\d+)$',reply,re.M)])+'\n')
(out/'state/pit-time.json').write_text(json.dumps(re.findall(r'^GPCPITTIME (\d+) (\d+)$',reply,re.M))+'\n')
(out/'state/events.json').write_text(json.dumps(re.findall(r'^GPCEVENT (\d+) ([0-9a-f]+)$',reply,re.M))+'\n')
(out/'state/counts.json').write_text(json.dumps(rows)+'\n');(out/'state/metadata.json').write_text(json.dumps(m,indent=2)+'\n')
print(f'{len(rows)} VBL observations ({len(files)} state snapshots), {rows[-1][1]} steps and {rows[-1][2]} publications')
