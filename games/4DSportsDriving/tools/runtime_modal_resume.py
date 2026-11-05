#!/usr/bin/env python3
"""Trace native Escape resume, historical input, and250 post-request fields."""
import json,re
from runtime_lifecycle_probe import cap,m,s,a,base,irq,snapshot,command
before=snapshot('resume-request');field=before['sim_clock_fields'];g=m['game_base']
script=f'''delete
set $completed=0
monitor key 45 1
break *{g+0xe7b4:#x}
commands
silent
set $completed=$completed+1
set $tick=*(unsigned short *){a-0x940:#x}
set $history=*(unsigned int *){a-0x1770:#x}
printf "BODY %u %u %u\\n", *(unsigned int *){base+s['sim_clock_fields']:#x}, $tick, *(unsigned char *)($history+$tick-1)
continue
end
break *{irq:#x}
commands
silent
printf "FIELD %u %u %u %u %u %u %u %u\\n", *(unsigned int *){base+s['sim_clock_fields']:#x}, $completed, *(unsigned int *){base+s['sim_schedule_ticks']:#x}, *(unsigned short *){base+s['sim_schedule_read']:#x}, *(unsigned short *){base+s['sim_schedule_write']:#x}, *(unsigned short *){base+s['sim_schedule_modal']:#x}, *(unsigned short *){a-0x940:#x}, *(unsigned int *){base+s['sim_schedule_modal_dropped']:#x}
if *(unsigned int *){base+s['sim_clock_fields']:#x}=={field+10}
monitor key 45 0
end
if *(unsigned int *){base+s['sim_clock_fields']:#x}<{field+250}
continue
end
end
continue
delete
'''
f=cap/'resume.gdb';f.write_text(script);out=command('gdb source '+str(f.relative_to(cap.parents[1])));(cap/'resume-log.txt').write_text(out)
fields=[list(map(int,x.split())) for x in re.findall(r'^FIELD (.*)$',out,re.M)]
bodies=[list(map(int,x.split())) for x in re.findall(r'^BODY (.*)$',out,re.M)]
assert [r[0] for r in fields]==list(range(field+1,field+251))
end=snapshot('resume-end');report=dict(start=before,end=end,fields=fields,bodies=bodies)
(cap/'resume-trace.json').write_text(json.dumps(report,indent=2)+'\n')
print('Bodies',len(bodies),'first',bodies[:6],'last',bodies[-2:],'first fields',fields[:5])
