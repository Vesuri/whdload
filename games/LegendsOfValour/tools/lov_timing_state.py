#!/usr/bin/env python3
"""Read persistent LoV simulation state from retained memory or per-field samples.
Only interpreted values are reported; game-derived snapshots stay under ignored tmp.
Actor coordinates use four times the player's coordinate units. Names are provisional.
"""
import argparse, json, os
from pathlib import Path
from lov_report import regions

def decode(read, h11, h12):
    def n(at, size=2, signed=False):
        data = read(at, size)
        if len(data) != size:
            raise ValueError(f'incomplete timing-state read at {at:#x}: {len(data)}/{size}')
        return int.from_bytes(data, 'big', signed=signed)
    state = dict(field=n(h11+0x602c,4), game_clock=n(h11+0x4d6,4),
        simulation_enabled=n(h12+0xa0c3,1), player=dict(
        x=n(h11+0x8c1c), y=n(h11+0x8c20), heading=n(h11+0x8c28),
        height=n(h11+0x8c1e), quantized_heading=n(h11+0x8c22)),
        animation=dict(count=n(h11+0xdf4), pacing=n(h11+0xdf6), phase=n(h11+0xdf8)),
        movement_step=n(h12+0xcdd6), rng=n(h12+0xcde0), periodic_count=n(h12+0x27ba),
        selected_actor_offset=n(h12+0x9716,signed=True),
        encounter_actor_offset=n(h12+0x9714,signed=True), actors=[])
    for i in range(56):
        at=h12+0xa2f0+128*i
        state['actors'].append(dict(index=i, flags=n(at), x=n(at+2), y=n(at+4),
            cell=n(at+6), distance=n(at+8), region=n(at+10,1), type=n(at+11,1),
            speed=n(at+28,signed=True), velocity_x=n(at+30,signed=True),
            velocity_y=n(at+32,signed=True), fraction_x=n(at+34,1), fraction_y=n(at+35,1),
            countdown=n(at+36,1), reload=n(at+37,1), animation=n(at+43,1),
            state_count=n(at+76), state=n(at+104), event=n(at+106)))
    return state

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path)
    p.add_argument('--base',type=lambda s:int(s,0),default=0xc00000)
    a=p.parse_args();os.environ['SLAVE']=str(a.capture/'slave.slave')
    b=(a.capture/'code.bin').read_bytes();r={n:lo for lo,hi,n,o in regions(b,a.base)}
    print(json.dumps(decode(lambda at,n:b[at-a.base:at-a.base+n],r['h11'],r['h12']),indent=2))
if __name__=='__main__':main()
