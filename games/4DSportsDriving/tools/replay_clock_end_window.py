#!/usr/bin/env python3
"""Check native end-of-replay handling and a subsequent 250-field hold."""
import argparse,json,re,struct
from pathlib import Path
from profile_window import command,ROOT
p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);a=p.parse_args();cap=a.capture.resolve();m=json.loads((cap/'anchor.json').read_text())
s={n:int(v,16) for n,v in re.findall(r'^([\w.]+)\s+00:([0-9a-fA-F]+)\s*$',(cap/'slave.lst').read_text(encoding='latin1'),re.M)}
base=m['marker']+8-s['tape_game'];irq=base+s['sim_clock_interrupt']+10;aa=m['data_base']+0x7ffe;clock=base+s['sim_clock_fields']
# Stop before the native end handler sets its pause flag; both cursors must
# have reached the recording bound. This handler now runs in the main task.
at=m['game_base']+0x7a96
r=command(f'gdb delete\ntbreak *{at:#x} if *(unsigned short *){base+s["sim_schedule_active"]:#x}==3\ncontinue\ninfo registers pc');print(r,flush=True)
assert int(re.search(r'^pc\s+0x([0-9a-f]+)',r,re.M)[1],16)==at

def dump(name):
 f=cap/name;command(f'gdb dump binary memory {f.relative_to(ROOT)} 0x200000 0x600000');return f.read_bytes()
def report(b):
 u16=lambda addr:struct.unpack_from('>H',b,addr-m['memory_base'])[0]
 u32=lambda addr:struct.unpack_from('>I',b,addr-m['memory_base'])[0]
 return dict(field=u32(clock),producer=u16(aa+0xa0),consumer=u16(aa-0x940),length=u16(aa-0x1738),published=u32(base+s['sim_schedule_ticks']),failure=u32(base+s['perf_failure']),paused=b[aa+0x44-m['memory_base']])
b=dump('replay-before-end.bin');before=report(b);assert before['producer']==before['consumer']==before['length'] and not before['failure']
r=command(f'gdb delete\ntbreak *{irq:#x} if *(unsigned char *){aa+0x44:#x}!=0\ncontinue\ninfo registers pc');print(r,flush=True)
assert int(re.search(r'^pc\s+0x([0-9a-f]+)',r,re.M)[1],16)==irq
b=dump('replay-hold-start.bin');start=report(b)
r=command(f'gdb delete\ntbreak *{irq:#x} if *(unsigned int *){clock:#x}=={start["field"]+250}\ncontinue\ninfo registers pc');print(r,flush=True)
assert int(re.search(r'^pc\s+0x([0-9a-f]+)',r,re.M)[1],16)==irq
end=report(dump('replay-hold-end.bin'))
assert end['field']-start['field']==250 and end['producer']==end['consumer']==end['length']
assert end['published']==start['published'] and end['paused'] and not end['failure']
r=dict(fields=250,native_end_after_final_step=True,before=before,start=start,end=end)
(cap/'replay-end-window.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
