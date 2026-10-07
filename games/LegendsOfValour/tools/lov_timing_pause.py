#!/usr/bin/env python3
"""Observe the first mapped actor/script pause for 100 fields after an early tape anchor.
The tape must keep standing still until the event and throughout the sample interval.
Called by a capture runner while the emulator is stopped; guest memory is read only.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from lov_timing_fields import command
from lov_timing_state import decode
from lov_report import regions

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture', type=Path)
    p.add_argument('base', type=lambda s: int(s, 0))
    a = p.parse_args()
    os.environ['SLAVE'] = str(a.capture / 'slave.slave')
    initial = (a.capture / 'code.bin').read_bytes()
    rr = {n: lo for lo, hi, n, off in regions(initial, a.base)}
    h11, h12 = rr['h11'], rr['h12']
    entries = {0x10910: 'scripted-dialog', 0x10b92: 'actor-conversation',
               0x132e6: 'actor-encounter', 0x1702e: 'scripted-event'}
    addresses = [h12 + off for off in entries]
    result = command('\n'.join([f'break *{at:#x}' for at in addresses] +
                               ['continue', 'info registers pc', 'delete']))
    (a.capture / 'pause-enter-gdb.txt').write_text(result)
    match = re.search(r'^pc\s+0x([0-9a-f]+)\s', result, re.M)
    if not match or int(match[1], 16) not in addresses:
        raise RuntimeError('expected a known pause entry: ' + result)
    offset = int(match[1], 16) - h12
    def snapshot(name):
        with tempfile.TemporaryDirectory(prefix='lov-pause-') as temp:
            path = Path(temp, 'memory.bin')
            command(f'dump binary memory {path} {a.base:#x} {a.base+len(initial):#x}')
            data = path.read_bytes()
        (a.capture / f'{name}.bin').write_bytes(data)
        return decode(lambda at,n: data[at-a.base:at-a.base+n], h11, h12)
    # Immediately after disabling the active clock, before entering the conversation.
    entered = snapshot('conversation-enter')
    subprocess.run([sys.executable, str(Path(__file__).with_name('lov_timing_fields.py')),
                    '100', str(a.capture/'pause-state'), str(a.capture), hex(a.base), '--initial-point', f'h12:{offset:05x} pause entry'], check=True)
    exited = snapshot('pause-end')
    selected = entered['encounter_actor_offset' if offset == 0x132e6 else 'selected_actor_offset']
    delta = selected + 15214
    index = delta // 128 if selected and delta % 128 == 0 and 0 <= delta // 128 < 56 else None
    report = dict(entry=entries[offset], entry_offset=hex(offset), actor_index=index, selected_actor_offset=selected,
                  elapsed_fields=(exited['field']-entered['field']) & 0xffffffff,
                  elapsed_game_clock=(exited['game_clock']-entered['game_clock']) & 0xffffffff,
                  enabled_at_entry=entered['simulation_enabled'], enabled_at_end=exited['simulation_enabled'],
                  actors_equal=entered['actors']==exited['actors'],
                  actor_at_entry=entered['actors'][index] if index is not None else None)
    (a.capture/'pause-report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    subprocess.run([sys.executable, str(Path(__file__).with_name('lov.py')),
                    'shot', str((a.capture/'pause.png').resolve())], check=True)
if __name__ == '__main__':
    main()
