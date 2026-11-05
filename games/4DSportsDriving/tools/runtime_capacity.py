#!/usr/bin/env python3
"""Count complete physics bodies and rendered frames over a bounded continuous PAL-field window."""
import argparse,json,re,struct,hashlib
from pathlib import Path
from profile_window import command,ROOT
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('capture',type=Path)
parser.add_argument('--lifecycle',action='store_true')
parser.add_argument('--detail',type=int,choices=(0,3),default=0,help='Expected graphics level: FULL=0, FAST=3')
parser.add_argument('--fields',type=int,default=250,help='Continuous PAL fields; default 250')
args=parser.parse_args();lifecycle=args.lifecycle
assert args.fields>0
cap=args.capture.resolve();m=json.loads((cap/'anchor.json').read_text());assert m['standalone_runtime']
s={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9a-fA-F]+)\s*$',(cap/'slave.lst').read_text(encoding='latin1'),re.M)}
base=m['slave_base'];aa=m['data_base']+0x7ffe;g=m['game_base'];irq=base+s['sim_clock_interrupt']+10
clock=base+s['sim_clock_fields'];command('stop')
command(f'gdb delete\ntbreak *{irq:#x}\ncontinue')
def snap(name):
 f=cap/name;command(f'gdb dump binary memory {f.relative_to(ROOT)} 0x200000 0x600000');b=f.read_bytes()
 def rd(addr,fmt):return struct.unpack_from('>'+fmt,b,addr-0x200000)[0]
 r={k:rd(base+s[n],fmt) for k,n,fmt in [('field','sim_clock_fields','I'),('produced','sim_schedule_ticks','I'),('read','sim_schedule_read','H'),('write','sim_schedule_write','H'),('overflow','sim_schedule_overflow','H'),('active','sim_schedule_active','H'),('modal','sim_schedule_modal','H'),('failure','perf_failure','I')]}
 r.update({k:rd(aa+off,fmt) for k,off,fmt in [('consumer',-0x940,'H'),('history_base',-0x2e0,'H'),('started',-0x68b,'B'),('imported',0xa0,'H'),('rate',-0x15fa,'H'),('mode',0x45,'B'),('detail',-0x7708,'B'),('opponent',-0x174a,'B')]})
 r['queue']=(r['write']-r['read'])&65535
 r['cars']={name:dict(position=[rd(aa+off+d,'i') for d in (0,4,8)],speed=rd(aa+off+0x2a,'H'),crashed=rd(aa+off+0xc9,'B')) for name,off in [('player',-0x92e),('opponent',-0x85e)]}
 return r
start=snap('capacity-start.bin');assert (start['active'],start['rate'],start['mode'],start['modal'],start['detail'])==(1,50,0,0,args.detail),start
if not lifecycle:assert start['started']==1,'Pre-start race counters can reset; start driving before a steady capacity capture'
script=f'''gdb delete
set $completed=0
set $frames=0
set $ai=0
break *{g+0xe7b4:#x}
commands
silent
set $completed=$completed+1
printf "EPOCH %u %u %u\\n", *(unsigned short *){aa-0x940:#x}, *(unsigned short *){aa-0x2e0:#x}, *(unsigned char *){aa-0x68b:#x}
printf "CAR %u %d %d %d %d %u %d %d %d %d %u\\n", *(unsigned short *){aa-0x940:#x}, *(int *){aa-0x92e:#x}, *(int *){aa-0x92e+4:#x}, *(int *){aa-0x92e+8:#x}, *(short *){aa-0x92e+0x1a:#x}, *(unsigned char *){aa-0x92e+0xc9:#x}, *(int *){aa-0x85e:#x}, *(int *){aa-0x85e+4:#x}, *(int *){aa-0x85e+8:#x}, *(short *){aa-0x85e+0x1a:#x}, *(unsigned char *){aa-0x85e+0xc9:#x}
continue
end
break *{g+0x7500:#x}
commands
silent
set $frames=$frames+1
continue
end
break *{g+0xbc48:#x}
commands
silent
set $ai=$ai+1
continue
end
break *{irq:#x}
commands
silent
printf "FIELD %u %u %u %u %u\\n", *(unsigned int *){clock:#x}, $completed, $frames, *(unsigned short *){base+s['sim_schedule_write']:#x}, *(unsigned short *){base+s['sim_schedule_read']:#x}
if *(unsigned int *){clock:#x} < {start['field']+args.fields}
continue
end
end
continue
printf "AI_CALLS %u\\n", $ai
delete'''
(cap/'capacity.commands.gdb').write_text(script.removeprefix('gdb '))
out=command('gdb source '+str((cap/'capacity.commands.gdb').relative_to(ROOT)));(cap/'capacity-log.txt').write_text(out)
rows=[list(map(int,x.split())) for x in re.findall(r'^FIELD (.*)$',out,re.M)];assert [x[0] for x in rows]==list(range(start['field']+1,start['field']+args.fields+1))
end=snap('capacity-end.bin');assert end['failure']==end['overflow']==0
if not lifecycle: assert end['modal']==0 and end['active']==1 and end['rate']==50 and end['mode']==0 and end['detail']==args.detail
r=dict(scope=f'Standalone runtime, graphics level {args.detail}; configured 68040 MMU model; see capture workload metadata; not hardware or worst-case capacity proof',fields=args.fields,start=start,end=end,completed=rows[-1][1],renders=rows[-1][2],produced=end['produced']-start['produced'],rows=rows,slave_sha256=hashlib.sha256((cap/'slave.slave').read_bytes()).hexdigest())
r['completed_car_states']=[list(map(int,x.split())) for x in re.findall(r'^CAR (.*)$',out,re.M)]
assert len(r['completed_car_states'])==r['completed']
r['completed_epochs']=[list(map(int,x.split())) for x in re.findall(r'^EPOCH (.*)$',out,re.M)]
assert len(r['completed_epochs'])==r['completed']
assert [x[0] for x in r['completed_epochs']]==[x[0] for x in r['completed_car_states']]
absolute=[tick+history_base for tick,history_base,_ in r['completed_epochs']]
r['steady_tick_continuity']=(bool(absolute) and start['started']==end['started']==1
    and all(started==1 for _,_,started in r['completed_epochs'])
    and all(b==a+1 for a,b in zip(absolute,absolute[1:])))
if not lifecycle:assert r['steady_tick_continuity'],'Race epoch or tick discontinuity during steady capacity capture'

r['opponent_calls']=int(re.search(r'AI_CALLS (\d+)',out)[1])
r['completion_debt_change']=r['produced']-r['completed'];assert lifecycle or r['produced']==args.fields
r['lifecycle_observation']=lifecycle
(cap/'capacity.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ('rows','completed_car_states','completed_epochs')},indent=2))
