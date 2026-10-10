#!/usr/bin/env python3
"""Count frame completions over PAL fields with read-only debugger breakpoints.
Independent validation of the instruction-trace frame marker.
Only debugger convenience variables change; target memory/registers are read-only.
"""
import argparse
import os
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
probes = [int(x, 0) for x in os.environ.get('COVERAGE_PROBES', '').split()]
assert len(probes) == len(set(probes)) and a.marker not in probes and 0x5684 not in probes
probe_breaks = ''.join(f'break *{r["game"][0]+x:#x}\n' for x in probes)
probe_tests = ''.join(f'if $pc == {r["game"][0]+x:#x}\nprintf "PDEVENT %d {x:#x}\\n", $pd_field\nend\n' for x in probes)
state = r['game'][0] + 0xa6e
state_offsets = [0xbe, 0x5c, 0x11e, 0x138, 0x194, 0x1ba, 0x2ea, 0x2f2, 0x4ce, 0x4d0, 0xaa, 0xe6, 0xfc, 0xf6]
state_probe = ''
if os.environ.get('COVERAGE_STATE') == '1':
    values = ', '.join(f'*(unsigned short*){state+x:#x}' for x in state_offsets)
    state_probe = 'printf \"PDSTATE %d ' + ' '.join(['%u']*len(state_offsets)) + '\\n\", $pd_field, ' + values + '\n'
# Optional timing samples are read-only and use the same completed-frame marker.
if os.environ.get('TIMING_STATE') == '1':
    timing_words = [0x21c, 0x194, 0x1ba, 0x11e, 0x12c, 0x12e, 0x130,
                    0x11a, 0x138, 0x45a, 0x196, 0x198, 0x4ce, 0x4d2,
                    0x4c6, 0x1e0, 0x1e6, 0x432, 0x42a, 0x42e]
    vals = [f'*(unsigned int*){r["game"][0]+0xf96:#x}',
            f'*(unsigned int*){state+0x5e:#x}']
    vals += [f'*(unsigned short*){state+x:#x}' for x in timing_words]
    state_probe += 'printf "PDTIME %d ' + ' '.join(['%u']*len(vals)) + '\\n", $pd_field, ' + ', '.join(vals) + '\n'
    # Keep event samples separate from presentation samples used by timing_report.
    for off in probes:
        sample = 'printf "PDTIME_EVENT %d ' + hex(off) + ' ' + ' '.join(['%u']*len(vals)) + '\\n", $pd_field, ' + ', '.join(vals) + '\n'
        probe_tests += f'if $pc == {r["game"][0]+off:#x}\n{sample}end\n'

setup = f'break *{vbl:#x}\nbreak *{swap:#x}\n{probe_breaks}set $pd_field = -1\n'
reply = command(setup)
logpath = a.out/'swaps-gdb.txt'
logpath.write_text(reply)
try:
    for end in range(min(2000,a.fields), a.fields+2000, 2000):
        end=min(end,a.fields)
        part=command(f'''while $pd_field < {end}
continue
if $pc == {vbl:#x}
set $pd_field = $pd_field + 1
else
if $pc == {swap:#x}
printf "PDFRAME %d\\n", $pd_field
{state_probe}end
{probe_tests}end
end
''')
        reply+=part
        with logpath.open('a') as log: log.write(part)
        assert 'ERROR' not in part, 'Debugger reported an error'
        print(f'Counted {end}/{a.fields} PAL fields', flush=True)
        if end==a.fields: break
finally:
    command('delete')
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
kind = 'Driving' if a.marker == 0xbc7c else 'demo'
report = (f'Read-only {kind} frame counter ({a.fields} PAL fields, marker {a.marker:#x})\n'
          f'{kind} frame completions per field: {"".join(str(n) for n in swaps)}\n'
          f'{frames} frames in {last-first} fields: {(last-first)/frames:.2f} fields/frame, '
          f'{50*frames/(last-first):.1f} fps (PAL)\n')
(a.out/'frames.txt').write_text(report)
print(report, end='')
