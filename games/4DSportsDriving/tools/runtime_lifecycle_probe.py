#!/usr/bin/env python3
"""Read-only snapshots and field-bounded native keyboard lifecycle probes."""
import json,re,struct,sys,hashlib,os
from pathlib import Path
from profile_window import command,ROOT
cap=(ROOT/os.environ.get('RUNTIME_CAPTURE','tmp/lifecycle-runtime-67')).resolve();assert cap.is_relative_to(ROOT/'tmp');anchor=cap/'start';m=json.loads((anchor/'anchor.json').read_text())
s={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9a-fA-F]+)\s*$',(anchor/'slave.lst').read_text(encoding='latin1'),re.M)}
a=m['data_base']+0x7ffe;base=m['slave_base'];irq=base+s['sim_clock_interrupt']+10

def fields(n):
    command('stop');out=command(f'gdb delete\nbreak *{irq:#x}\nignore $bpnum {n-1}\ncontinue\ndelete')
    with (cap/'probe-log.txt').open('a') as f:f.write(out)

def key(raw,state):
    command('stop');command(f'gdb monitor key {raw:x} {state}')

def snapshot(name):
    command('stop');p=cap/(name+'.bin');command(f'gdb dump binary memory {p.relative_to(ROOT)} 0x200000 0x600000');b=p.read_bytes()
    rd=lambda address,fmt:struct.unpack_from('>'+fmt,b,address-m['memory_base'])[0]
    vals={n:rd(base+s[n],fmt) for n,fmt in [('sim_clock_fields','I'),('sim_schedule_ticks','I'),('sim_schedule_read','H'),('sim_schedule_write','H'),('sim_schedule_active','H'),('sim_schedule_modal','H'),('sim_schedule_phase','H'),('sim_schedule_overflow','H'),('sim_schedule_modal_enters','I'),('sim_schedule_modal_resumes','I'),('sim_schedule_modal_dropped','I'),('sim_schedule_modal_fields','I'),('perf_failure','I')]}
    vals.update({n:rd(a+o,fmt) for n,o,fmt in [('selected',-0xbc,'H'),('active_rate',-0x15fa,'H'),('recorded_rate',-0x173a,'B'),('mode',0x45,'B'),('paused',0x42,'B'),('native_modal',0xa9c,'H'),('native_modal_depth',-0x3ff4,'B'),('replay_selection',-0x74c1,'B'),('replay_speed',0x3d,'B'),('replay_pause',0x44,'B'),('recorded_length',-0x1738,'H'),('started',-0x68b,'B'),('consumer',-0x940,'H'),('imported',0xa0,'H'),('detail',-0x7708,'B')]})
    vals['queue']=(vals['sim_schedule_write']-vals['sim_schedule_read'])&65535
    for label,off in [('player',-0x92e),('opponent',-0x85e)]:
        car=b[a+off-m['memory_base']:a+off-m['memory_base']+208]
        vals[label]=dict(sha256=hashlib.sha256(car).hexdigest(),position=list(struct.unpack_from('>3i',car)),speed=struct.unpack_from('>H',car,0x2a)[0],crashed=car[0xc9])
    po=b.index(b'4DA4PHYS')+12;vals['private_sha256']=hashlib.sha256(b[po:po+152]).hexdigest()
    (cap/(name+'.json')).write_text(json.dumps(vals,indent=2)+'\n');print(name,json.dumps(vals));return vals

if __name__=='__main__':
    if sys.argv[1]=='fields':fields(int(sys.argv[2]));snapshot(sys.argv[3])
    elif sys.argv[1]=='key':key(int(sys.argv[2],16),int(sys.argv[3]))
    elif sys.argv[1]=='snapshot':snapshot(sys.argv[2])
    else:raise ValueError(sys.argv)
