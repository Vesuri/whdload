#!/usr/bin/env python3
"""Read actual joystick hook results from race start, without writing target state."""
import argparse,json,re,struct
from pathlib import Path
from state_fields import command
p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();m=json.loads((a.out/'metadata.json').read_text());h=m['code_base'];epoch=m['epoch'];a4=m['data_base']+0x7ffe
reply=command(f'''break *{h+0xc1e4:#x}
set $tape_age = 0
while $tape_age < 450
continue
set $tape_age = *(unsigned long *){a4-31790:#x} - {epoch}
printf "GPCTAPE %d %u\\n", $tape_age, ($d0 & 65535)
end
delete
''')
(a.out/'tape-gdb.txt').write_text(reply)
rows=[(int(x),int(y)) for x,y in re.findall(r'^GPCTAPE (\d+) (\d+)$',reply,re.M)]
def expected(age):
 if 100<=age<106:return 0x200
 if 106<=age<112:return 0x103
 if 200<=age<300:return 1
 if 300<=age<400:return 0
 return 0x100
assert rows and rows[-1][0]>=450
assert all(value==expected(age) for age,value in rows),rows
assert {v for _,v in rows}=={0x100,0x200,0x103,1,0}, 'not all input phases observed'
(a.out/'tape.json').write_text(json.dumps(rows,indent=2)+'\n')
print(f'{len(rows)} actual joystick reads checked through race field {rows[-1][0]}; all five raw input values observed')
