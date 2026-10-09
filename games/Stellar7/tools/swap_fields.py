#!/usr/bin/env python3
"""Count frames (gameplay swaps, s7:2c16) over PAL fields with read-only debugger breakpoints.
Used by fixed_window.sh when a CPU backend provides no instruction trace (68030).
Fields are counted at Kickstart 1.3's VERTB branch ($FC0D4A in the relocated image).
Only debugger convenience variables change; target memory/registers are read-only.

  swap_fields.py FIELDS OUTDIR CODE.bin BASE CHIP.bin
"""
import argparse, os, re, socket, sys
from pathlib import Path
sys.path.insert(0, os.path.dirname(__file__))
from stellar7 import SOCK
from stellar7_report import regions
C2P = 0x2c16


def command(s):
    with socket.socket(socket.AF_UNIX) as c:
        c.connect(SOCK); c.sendall(('gdb ' + s).encode()); out = b''
        while chunk := c.recv(65536): out += chunk
    reply = out.decode()
    if 'ERROR' in reply: raise RuntimeError(reply)
    return reply


p = argparse.ArgumentParser(description=__doc__)
p.add_argument('fields', type=int)
p.add_argument('out', type=Path)
p.add_argument('dump', type=Path)
p.add_argument('base', type=lambda x: int(x, 0))
p.add_argument('chip', type=Path)
a = p.parse_args()
assert a.fields > 1
r = {name: (lo, origin) for lo, hi, name, origin in regions(a.dump.read_bytes(), a.base, a.chip.read_bytes())}
frame = r['s7'][0] + C2P
vbl = 0xfc0d4a + r['kick'][1]
reply = command(f'''break *{vbl:#x}
break *{frame:#x}
set $s7_field = -1
while $s7_field < {a.fields}
continue
if $pc == {vbl:#x}
set $s7_field = $s7_field + 1
else
printf "S7FRAME %d\\n", $s7_field
end
end
delete
''')
(a.out / 'swaps-gdb.txt').write_text(reply)
swaps = [0] * a.fields
for field in re.findall(r'^S7FRAME (-?\d+)$', reply, re.M):
    index = int(field)
    if 0 <= index < a.fields:
        swaps[index] += 1
first = next((i for i, n in enumerate(swaps) if n), None)
last = max((i for i, n in enumerate(swaps) if n), default=None)
assert first is not None and last > first, 'insufficient frames for FPS'
frames = sum(swaps[first + 1:last + 1])
report = (f'Read-only frame counter ({a.fields} PAL fields)\n'
          f'gameplay swaps per field: {"".join(str(n) for n in swaps)}\n'
          f'{frames} frames in {last - first} fields: {(last - first) / frames:.2f} fields/frame, '
          f'{50 * frames / (last - first):.1f} fps (PAL)\n')
(a.out / 'frames.txt').write_text(report)
print(report, end='')
