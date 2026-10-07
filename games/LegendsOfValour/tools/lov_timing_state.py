#!/usr/bin/env python3
"""Read persistent LoV simulation state from retained memory or per-field samples.
Only interpreted values are reported; game-derived snapshots stay under ignored tmp.
Actor coordinates use four times the player's coordinate units. Names are provisional.
"""
import argparse, json, os, re
from pathlib import Path
from lov_report import regions

def decode(read, h11, h12, extended=False):
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
    if extended:
        state['mouse_look'] = n(h11)
        state['pending_days'] = n(h11+6)
        state['calendar'] = dict(day=n(h12+0xa1ed,1), hour=n(h12+0xa0c8),
            period64=n(h12+0xa2e4), period4096=n(h12+0xa2e2), event_pending=n(h12+0xa0d0))
        state['daily_timers'] = [dict(remaining=n(h11+0x6080+4*i), value=n(h11+0x6082+4*i)) for i in range(11)]
        state['daily_records'] = [[n(h11+0x4060+56*i+2*j) for j in range(28)] for i in range(16)]
        state['view_bob'] = dict(enabled=n(h11+0x4dc), phase=n(h11+0x4de), offset=n(h11+0x4e0,signed=True))
        state['projectiles'] = []
        for i in range(60):
            at=h11+0x90c+18*i
            state['projectiles'].append(dict(index=i, type=n(at), x=n(at+2),
                height=n(at+4,signed=True), y=n(at+6), velocity_x=n(at+8,signed=True),
                vertical=n(at+10,signed=True), velocity_y=n(at+12,signed=True),
                extra=n(at+14), region=n(at+16)))
    return state


def simulation_symbols(listing, slave):
    names = ('_sim_suspended', '_sim_started', '_sim_render_tick', '_sim_fields', '_sim_consumed',
             '_sim_started_ticks', '_sim_completed_ticks', '_sim_catchups', '_sim_tick_clock',
             '_sim_input_recoveries', '_sim_options_entries', '_sim_options_entry_tick',
             '_sim_options_returns', '_sim_options_return_tick', '_sim_ui_suppressed')
    result = {}
    for name in names:
        match = re.search(r'^' + name + r'\s+00:([0-9A-F]{8})\s*$', listing, re.M)
        if match:
            result[name] = slave + int(match[1], 16)
    return result

def simulation_state(read, symbols):
    result = {}
    for name, at in symbols.items():
        size = 2 if name in ('_sim_suspended', '_sim_started', '_sim_render_tick') else 4
        data = read(at, size)
        if len(data) != size:
            raise ValueError(f'incomplete simulation-state read at {at:#x}')
        result[name.removeprefix('_sim_')] = int.from_bytes(data, 'big')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path)
    p.add_argument('--base',type=lambda s:int(s,0),default=0xc00000)
    a=p.parse_args();os.environ['SLAVE']=str(a.capture/'slave.slave')
    b=(a.capture/'code.bin').read_bytes();r={n:lo for lo,hi,n,o in regions(b,a.base)}
    read = lambda at,n: b[at-a.base:at-a.base+n]
    state = decode(read,r['h11'],r['h12'])
    symbols = simulation_symbols((a.capture/'slave.lst').read_text(errors='replace'), r['slave'])
    if symbols: state['simulation'] = simulation_state(read, symbols)
    print(json.dumps(state,indent=2))
if __name__=='__main__':main()
