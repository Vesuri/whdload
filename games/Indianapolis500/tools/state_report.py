#!/usr/bin/env python3
"""Report per-field state snapshots (raw big-endian game values, never screenshots).
  state_report.py OUT/state [--changes] [--fields 0,5,99]
Snapshot n is at VBL entry n; initial.bin is the anchor.  Offsets are game: hunk-0 offsets.
The table holds only what has been identified so far (docs/game.md);
add variables as they are found.  --changes lists every changing word in hunk 0.
"""
import argparse, collections, json
from pathlib import Path
VARIABLES = {
    'ticks_pending': (0x9832, 2),    # +1 per level-1 (SOFT) interrupt; main loop consumes it
    'attract': (0x9b2f, 1),          # bit 0: title/attract mode (no tick counting in level 2)
    'cia_ticks': (0x12388, 2),       # +1 per CIA-A timer B interrupt (59.7 Hz); cleared at swap
    'soft_countdown': (0x12382, 2),  # CIA ticks until the next SOFT interrupt (period 4)
    'swap_request': (0x12396, 1),    # bit 0 set by the renderer (game:0b57e), cleared by VBL
    'soft_owed': (0x12397, 1),       # bit 0 set every 4th CIA tick (game:09c1a), taken at game:0b59c
    'mode': (0x268da, 1),            # compared with 1 in the level-1 handler
}
def value(b, offset, size):
    return int.from_bytes(b[offset:offset+size], 'big')
def main():
    p=argparse.ArgumentParser(); p.add_argument('path'); p.add_argument('--changes',action='store_true')
    p.add_argument('--fields',default='0,1,2,5,10,25,50,99');a=p.parse_args()
    root=Path(a.path); json.loads((root/'metadata.json').read_text())
    files=sorted(root.glob('[0-9][0-9][0-9][0-9].bin')); data=[f.read_bytes() for f in files]
    initial=(root/'initial.bin').read_bytes()
    print('initial:',{n:value(initial,*v) for n,v in VARIABLES.items()})
    print('field,'+','.join(VARIABLES))
    for f in map(int,a.fields.split(',')):
        if f<len(data):print(str(f)+','+','.join(str(value(data[f],*v)) for v in VARIABLES.values()))
    print('update fields (observed changes, excluding same-value stores):')
    for n,v in VARIABLES.items():
        changes=[i for i in range(1,len(data)) if value(data[i],*v)!=value(data[i-1],*v)]
        periods=collections.Counter(b-a for a,b in zip(changes,changes[1:]))
        print(n, 'count',len(changes),'first',changes[:25],'periods',dict(periods))
    if a.changes:
        for off in range(0,len(initial),2):
            changes=[i for i in range(1,len(data)) if data[i][off:off+2]!=data[i-1][off:off+2]]
            if changes:
                periods=collections.Counter(b-a for a,b in zip(changes,changes[1:]))
                print(f'game:{off:05x}: {len(changes)} changes; first={changes[:15]}; periods={dict(periods)}')
if __name__=='__main__':main()
