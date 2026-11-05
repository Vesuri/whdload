#!/usr/bin/env python3
"""Observe flat settled contact quantization without modifying the guest."""
import sys,json,re
from pathlib import Path
from profile_window import command
cap=Path(sys.argv[1]);m=json.loads((cap/'anchor.json').read_text());g=m['game_base'];a=m['data_base']+0x7ffe
script=f'''gdb delete
set $n=0
break *{g+0xc71e:#x}
commands
silent
printf "IN %u %u %d %d %d %d %d %d %d %d\\n", *(unsigned short *)($a4-0x940), *(unsigned char *)($a5-3), *(int *)($a4-0x92a), *(int *)(*(unsigned int *)($a5-0xe6)+4), *(short *)($a5-0x3e), *(short *)$sp, *(short *)($a4+0x92)+*(short *)(*(unsigned int *)($a4+0x1ee)+6), *(short *)($a4-0x914), *(short *)($a4-0x912), *(short *)($a4-0x8da+2*(*(unsigned char *)($a5-3)))
continue
end
break *{g+0xc722:#x}
commands
silent
printf "OUT %d\\n", (short)$d0
continue
end
break *{g+0xe7b4:#x}
commands
silent
set $n=$n+1
if $n<5
continue
end
end
continue
delete
'''
if '--analyze-existing' in sys.argv:out=(cap/'flat-contact.txt').read_text()
else:
 (cap/'flat-contact.gdb').write_text(script);out=command(script);(cap/'flat-contact.txt').write_text(out)
rows=[list(map(int,s.split())) for s in re.findall(r'^IN (.*)$',out,re.M)]
returns=[int(s) for s in re.findall(r'^OUT (.*)$',out,re.M)]
assert len(rows)==len(returns)==20
checks=[]
for r,ret in zip(rows,returns):
 tick,wheel,body,raw,quantized,plane,ground,pitch,roll,extension=r
 assert plane<4 and plane>=0,'not a flat-plane fast path'
 assert quantized==raw//64 and ret==quantized-ground
 if pitch==roll==extension==0:assert raw==body-384
 interval=[64*ground+384,64*ground+447]
 checks.append(dict(tick=tick,wheel=wheel,body=body,raw_wheel=raw,contact_y=quantized,plane=plane,ground=ground,distance=ret,pitch=pitch,roll=roll,extension=extension,level_unextended_zero_distance_body_interval=interval))
result=dict(passed=True,rate=m['active_simulation_word'],rows=checks,scope='Five updates with the flat-plane terrain helper. Exact signed ASR/64 and ground subtraction are checked. Hypothetical level/unextended zero-distance intervals are per wheel, not evidence of equilibrium. Captured wheels can see different ground heights.')
(cap/'flat-contact-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2));print(checks[0])
