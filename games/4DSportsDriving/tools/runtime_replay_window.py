#!/usr/bin/env python3
"""Observe 250 PAL fields of ordinary replay; no guest writes."""
import sys,json,re
from runtime_lifecycle_probe import cap,command,m,a,base,s,irq,snapshot
from profile_window import ROOT
label=sys.argv[1];start=snapshot(label+'-window-start');assert start['mode']==2 and start['replay_pause']==0
lines=['delete',f"break *{m['game_base']+0xe5f8:#x}",'commands','silent']
for tick in (200,400,600):
    lines += [f'if *(unsigned short *){a-0x940:#x}=={tick}',f'dump binary memory {(cap/(label+"-"+str(tick)+".bin")).relative_to(ROOT)} 0x200000 0x600000',f'printf "SAVED {tick}\\n"','end']
lines += ['continue','end',f"break *{m['game_base']+0xe7b4:#x}",'commands','silent',f'printf "BODY %u %u\\n", *(unsigned int *){base+s["sim_clock_fields"]:#x}, *(unsigned short *){a-0x940:#x}','continue','end',f'break *{irq:#x}','commands','silent',f'if *(unsigned int *){base+s["sim_clock_fields"]:#x}<{start["sim_clock_fields"]+250}','continue','end','end','continue','delete']
p=cap/(label+'-window.gdb');p.write_text('\n'.join(lines)+'\n');out=command('gdb source '+str(p.relative_to(ROOT)));(cap/(label+'-window.log')).write_text(out)
end=snapshot(label+'-window-end');rows=[list(map(int,x)) for x in re.findall(r'BODY (\d+) (\d+)',out)]
assert end['sim_clock_fields']-start['sim_clock_fields']==250
assert end['perf_failure']==end['sim_schedule_overflow']==0
report=dict(start=start,end=end,bodies=rows,published=end['sim_schedule_ticks']-start['sim_schedule_ticks'],completed=len(rows))
(cap/(label+'-window.json')).write_text(json.dumps(report,indent=2)+'\n');print(label,report['published'],report['completed'])
