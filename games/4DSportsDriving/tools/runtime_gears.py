#!/usr/bin/env python3
"""Trace ordinary keyboard manual shifts through complete native physics updates."""
import json,struct,re,sys
from pathlib import Path
from profile_window import command,ROOT
cap=Path(sys.argv[1]).resolve();m=json.loads((cap/'anchor.json').read_text());b=(cap/'memory.bin').read_bytes();aa=m['data_base']+0x7ffe;car=aa-0x92e;g=m['game_base']
assert b[car+0xcc-m['memory_base']]==0,'Car is not manual: shift controls would be ignored'
assert b[aa+0x45-m['memory_base']]==0
assert b[car+0xbe-m['memory_base']]==1,'Scenario must start in first gear'
rate=struct.unpack_from('>H',b,aa-0x15fa-m['memory_base'])[0];assert rate in (10,20,50)
command('stop');command('gdb monitor key 4c 1')
script=f'''gdb delete
set $n=0
break *{g+0xe7b4:#x}
commands
silent
set $n=$n+1
printf "GEAR %u %u %u %u %u %u %u %u %u %u %u %u\\n", $n, *(unsigned short *){aa-0x940:#x}, *(unsigned char *){car+0xbe:#x}, *(unsigned char *){car+0xca:#x}, *(unsigned char *){car+0xcb:#x}, *(unsigned short *){car+0x34:#x}, *(unsigned short *){car+0x38:#x}, *(unsigned short *){car+0x3a:#x}, *(unsigned short *){car+0x3c:#x}, *(unsigned short *){car+0x22:#x}, *(unsigned short *){car+0x2a:#x}, *(unsigned char *){car+0xc9:#x}
if $n=={rate//2}
monitor key 20 1
end
if $n=={rate//2+max(2,rate//10)}
monitor key 20 0
end
if $n=={2*rate}
monitor key 31 1
end
if $n=={2*rate+max(2,rate//10)}
monitor key 31 0
end
if $n<{4*rate}
continue
end
end
continue
delete
monitor key 4c 0
monitor key 20 0
monitor key 31 0'''
out=command(script);(cap/'gear-log.txt').write_text(out)
rows=[list(map(int,s.split())) for s in re.findall(r'^GEAR (.*)$',out,re.M)]
assert len(rows)==4*rate and [r[0] for r in rows]==list(range(1,4*rate+1))
assert all(r[-1]==0 for r in rows),'Crash during gear scenario'
changes=[];last=1
for r in rows:
 if r[2]!=last:changes.append(dict(step=r[0],tick=r[1],gear=r[2]));last=r[2]
assert [r['gear'] for r in changes]==[2,1],changes
settled=[]
for change in changes:
 r=next(r for r in rows if r[0]>=change['step'] and r[2]==change['gear'] and r[3]==0)
 assert r[5:7]==r[7:9],r
 settled.append(dict(gear=r[2],step=r[0],tick=r[1],delay_after_change_seconds=(r[0]-change['step'])/rate))
result=dict(rate=rate,changes=changes,settled=settled,rows=rows,scope='Real native menu selection and debug keyboard queue input; timing starts at completed physics, not host latency')
(cap/'gears.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
command(f'gdb dump binary memory {str((cap/"gear-end.bin").relative_to(ROOT))} 0x200000 0x600000')
