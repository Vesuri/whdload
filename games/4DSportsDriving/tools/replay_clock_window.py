#!/usr/bin/env python3
"""Observe exactly 250 PAL fields of native replay; never write guest memory."""
import argparse,json,re,struct
from pathlib import Path
from profile_window import command,ROOT
p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);a=p.parse_args();cap=a.capture.resolve()
m=json.loads((cap/'anchor.json').read_text());blob=(cap/'memory.bin').read_bytes()
s={n:int(v,16) for n,v in re.findall(r'^([\w.]+)\s+00:([0-9a-fA-F]+)\s*$',(cap/'slave.lst').read_text(encoding='latin1'),re.M)}
base=m['marker']+8-s['tape_game'];irq=base+s['sim_clock_interrupt']+10;aa=m['data_base']+0x7ffe
assert blob[irq-m['memory_base']:irq-m['memory_base']+8]==bytes.fromhex('4cdf7ffe70004e75')
sy=lambda n:base+s[n]
condition=f'*(unsigned short *){sy("sim_schedule_active"):#x}==3 && *(unsigned char *){aa+0x45:#x}==2 && *(unsigned short *){aa-0x940:#x}>=10'
r=command(f'gdb delete\ntbreak *{irq:#x} if {condition}\ncontinue\ninfo registers pc');print(r,flush=True)
assert int(re.search(r'^pc\s+0x([0-9a-f]+)',r,re.M)[1],16)==irq
specs=[('field',sy('sim_clock_fields'),32),('published',sy('sim_schedule_ticks'),32),('producer',aa+0xa0,16),('consumer',aa-0x940,16),('phase',sy('sim_schedule_phase'),16),('rate',sy('sim_schedule_rate'),16),('speed',aa+0x3d,8),('paused',aa+0x44,8),('end',aa+0x42,8),('modal',sy('sim_schedule_modal'),16),('failure',sy('perf_failure'),32)]
def snapshot(name):
 f=cap/name;command(f'gdb dump binary memory {f.relative_to(ROOT)} 0x200000 0x600000');b=f.read_bytes()
 return {key:struct.unpack_from('>'+{8:'B',16:'H',32:'I'}[bits],b,addr-m['memory_base'])[0] for key,addr,bits in specs}
start=snapshot('replay-clock-start.bin');assert not any(start[k] for k in ('paused','end','modal','failure'))
args=', '.join(f'*(unsigned '+{8:'char',16:'short',32:'int'}[bits]+f' *){addr:#x}' for _,addr,bits in specs)
fmt='RCLK '+' '.join(['%u']*len(specs))+r'\n'
script=f'''gdb delete
set $oldtimer=0
break *{m['game_base']+0x7a0a:#x}
commands
silent
set $oldtimer=$oldtimer+1
continue
end
break *{irq:#x}
commands
silent
printf "{fmt}", {args}
if *(unsigned int *){sy('sim_clock_fields'):#x} < {start['field']+250}
continue
end
end
continue
printf "OLDTIMER %u\\n", $oldtimer
info registers pc'''
r=command(script);(cap/'replay-clock-log.txt').write_text(r)
assert int(re.search(r'^pc\s+0x([0-9a-f]+)',r,re.M)[1],16)==irq
rows=[dict(zip([key for key,_,_ in specs],map(int,x.split()))) for x in re.findall(r'^RCLK (.*)$',r,re.M)]
assert [x['field'] for x in rows]==list(range(start['field']+1,start['field']+251))
assert all(not any(x[k] for k in ('paused','end','modal','failure')) for x in rows)
assert all((x['rate'],x['speed'])==(start['rate'],start['speed']) for x in rows)
mult={2:1,3:4}.get(start['speed'],2)
for i,x in enumerate(rows,1):
 expected,phase=divmod(start['phase']+i*start['rate']*mult,100)
 assert x['producer']-start['producer']==expected,(i,x,expected)
 assert x['published']-start['published']==expected and x['phase']==phase
oldtimer=int(re.search(r'^OLDTIMER (\d+)$',r,re.M)[1]);assert oldtimer==0
end=snapshot('replay-clock-end.bin');assert end==rows[-1]
report=dict(fields=250,rate=start['rate'],speed=start['speed'],published=end['producer']-start['producer'],old_timer_production_entries=oldtimer,all_field_targets_exact=True,start=start,end=end,samples=rows)
(cap/'replay-clock-window.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='samples'},indent=2))
