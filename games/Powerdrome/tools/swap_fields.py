#!/usr/bin/env python3
"""Count frame completions over PAL fields with read-only debugger breakpoints.
Independent validation of the instruction-trace frame marker.
Only debugger convenience variables change; target memory/registers are read-only.
"""
import argparse
from pathlib import Path
import re
import socket
from powerdrome import SOCK
from powerdrome_report import regions


def command(text):
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(600)
        client.connect(SOCK)
        client.sendall(('gdb '+text).encode())
        chunks=[]
        while data := client.recv(65536): chunks.append(data)
        return b''.join(chunks).decode()

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('fields', type=int)
p.add_argument('out', type=Path)
p.add_argument('dump', type=Path)
p.add_argument('base', type=lambda x: int(x, 0))
p.add_argument('--marker', type=lambda x: int(x, 0), default=0x1067e)
a = p.parse_args()
assert a.fields > 1
code = a.dump.read_bytes()
r = {name: (lo, hi) for lo, hi, name, origin in regions(code, a.base, (a.out/'chip.bin').read_bytes())}
# The game installs a VBL server at 5684. The default marker counts the title
# inset; bc7c counts normal driving presentations. No guest writes.
vbl = r['game'][0]+0x5684
swap = r['game'][0]+a.marker
reply = command(f'''break *{vbl:#x}
break *{swap:#x}
set $pd_field = -1
while $pd_field < {a.fields}
continue
if $pc == {vbl:#x}
set $pd_field = $pd_field + 1
else
printf "PDFRAME %d\\n", $pd_field
end
end
delete
''')
(a.out/'swaps-gdb.txt').write_text(reply)
swaps = [0]*a.fields
for field in re.findall(r'^PDFRAME (-?\d+)$', reply, re.M):
    index = int(field)
    if 0 <= index < a.fields:
        swaps[index] += 1
assert 'ERROR' not in reply
first = next((i for i, n in enumerate(swaps) if n), None)
last = max((i for i, n in enumerate(swaps) if n), default=None)
assert first is not None and last > first, 'insufficient swaps for FPS'
frames = sum(swaps[first+1:last+1])
kind = 'Practice' if a.marker == 0xbc7c else 'demo'
report = (f'Read-only {kind} frame counter ({a.fields} PAL fields, marker {a.marker:#x})\n'
          f'{kind} frame completions per field: {"".join(str(n) for n in swaps)}\n'
          f'{frames} frames in {last-first} fields: {(last-first)/frames:.2f} fields/frame, '
          f'{50*frames/(last-first):.1f} fps (PAL)\n')
(a.out/'frames.txt').write_text(report)
print(report, end='')
