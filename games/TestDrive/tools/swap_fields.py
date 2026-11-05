#!/usr/bin/env python3
"""Count gameplay LoadView publications between consecutive TD VBL entries."""
import argparse,re
from pathlib import Path
from td import server
from td_report import regions
from harness import command
p=argparse.ArgumentParser(description=__doc__);p.add_argument('fields',type=int);p.add_argument('out',type=Path);p.add_argument('dump',type=Path);p.add_argument('base',type=lambda x:int(x,0));p.add_argument('--swap-offset',type=lambda x:int(x,0),default=0x7aaa);a=p.parse_args()
if a.fields<2 or not 0<=a.swap_offset<0x7c0c:p.error('invalid count or root-hunk offset')
rr={n:lo for lo,hi,n,o in regions(a.dump.read_bytes(),a.base)};vbl=rr['td']+0x18ba;swap=rr['td']+a.swap_offset
raw=a.dump.read_bytes();off=swap-a.base
if a.swap_offset==0x7aaa and raw[off:off+12]!=bytes.fromhex('226f00042c6c83d64eeeff22'):raise ValueError('LoadView signature mismatch')
server.request('stop');reply=command(f'''break *{vbl:#x}
break *{swap:#x}
set $td_field = -1
while $td_field < {a.fields}
continue
if $pc == {vbl:#x}
set $td_field = $td_field + 1
else
printf "TDSWAP %d\\n", $td_field
end
end
delete
''')
a.out.mkdir(parents=True,exist_ok=True);(a.out/'swaps-gdb.txt').write_text(reply)
counts=[0]*a.fields
for x in re.findall(r'^TDSWAP (-?\d+)$',reply,re.M):
    i=int(x)
    if 0<=i<len(counts):counts[i]+=1
text=f'Gameplay presentation marker TD:{a.swap_offset:05x}; counts per PAL field: {counts}\n'
text+=f'{sum(counts)} marker hits / {a.fields} PAL fields = {50*sum(counts)/a.fields:.3f} hits/s.\n'
text+=('Gameplay LoadView validated against alternating plane DMA.\n' if a.swap_offset==0x7aaa else 'Diagnostic marker; this is not an FPS measurement.\n')
(a.out/'frames.txt').write_text(text)
import json
(a.out/'swaps.json').write_text(json.dumps(dict(fields=a.fields,marker_counts=counts,presentations=sum(counts),window_fps=50*sum(counts)/a.fields if a.swap_offset==0x7aaa else None),indent=2)+'\n')
print(text)
