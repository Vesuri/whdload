#!/usr/bin/env python3
"""Observe 250 consecutive PAL fields after replay reconstruction, checking bounds."""
import argparse,json,re,struct
from pathlib import Path
from profile_window import command,ROOT
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args();cap=a.capture.resolve();m=json.loads((cap/'anchor.json').read_text());mem=(cap/'memory.bin').read_bytes();s={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)$',(cap/'slave.lst').read_text(encoding='latin1'),re.M)};base=m['marker']+8-s['tape_game'];irq=base+s['sim_clock_interrupt']+10;clock=base+s['sim_clock_fields'];aa=m['data_base']+0x7ffe;fail=base+s['perf_failure']
assert mem[irq-m['memory_base']:irq-m['memory_base']+8]==bytes.fromhex('4cdf7ffe70004e75')
r=command(f'gdb delete\ntbreak *{irq:#x}\ncontinue\ninfo registers pc');assert int(re.search(r'^pc\s+0x([0-9a-f]+)',r,re.M)[1],16)==irq
f=cap/'replay-bound-start.bin';command(f'gdb dump binary memory {f.relative_to(ROOT)} 0x200000 0x600000');b=f.read_bytes();start=struct.unpack_from('>I',b,clock-m['memory_base'])[0];count=struct.unpack_from('>H',b,aa-m['memory_base']-0x1738)[0]
fmt=r'BOUND %u %u %u %u %u\n';args=f'*(unsigned int *){clock:#x}, *(unsigned short *){aa-0x940:#x}, *(unsigned short *){aa+0xa0:#x}, *(unsigned char *){aa+0x45:#x}, *(unsigned int *){fail:#x}'
script=f'gdb delete\nbreak *{irq:#x}\ncommands\nsilent\nprintf "{fmt}", {args}\nif *(unsigned int *){clock:#x} < {start+250}\ncontinue\nend\nend\nbreak *{base+s["sim_history_failed"]:#x}\ncontinue\ninfo registers pc'
r=command(script);(cap/'replay-bound-fields.log').write_text(r);assert int(re.search(r'^pc\s+0x([0-9a-f]+)',r,re.M)[1],16)==irq
rows=[list(map(int,x.split())) for x in re.findall(r'^BOUND (.*)$',r,re.M)];assert [v[0] for v in rows]==list(range(start+1,start+251));assert all(v[1]<=count and v[2]<=count and v[4]==0 for v in rows)
f=cap/'replay-bound-end.bin';command(f'gdb dump binary memory {f.relative_to(ROOT)} 0x200000 0x600000');result=dict(fields=250,input_count=count,consumer_min=min(v[1] for v in rows),consumer_max=max(v[1] for v in rows),producer_min=min(v[2] for v in rows),producer_max=max(v[2] for v in rows),modes=sorted(set(v[3] for v in rows)),no_runtime_failure=True,within_recorded_range=True)
(cap/'replay-bound-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
