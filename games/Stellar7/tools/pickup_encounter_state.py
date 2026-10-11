#!/usr/bin/env python3
"""Validate a controlled, real type-31 acquisition and all thirty native events."""
import argparse
import json
import re
import struct
from pathlib import Path
import sim60_state


def capture(folder, listing):
    folder, listing = Path(folder), Path(listing)
    root = folder
    while not (root/'slave.slave').exists():
        assert root != root.parent, 'retained slave missing'
        root = root.parent
    assert (root/'slave.slave').read_bytes() == listing.with_suffix('.slave').read_bytes()
    symbols = {n: int(v, 16) for n, v in re.findall(
        r'^(\w+)\s+00:([0-9A-F]+)', listing.read_text(encoding='latin1'), re.M)}
    anchor = (folder/'anchor.txt').read_text()
    assert 'SIGINT' not in anchor and 'Program received signal' not in anchor
    meta = {n: int(v, 0) for n, v in re.findall(r'^(code|data|base|tick)=(\S+)', anchor, re.M)}
    pcs = re.findall(r'^pc\s+(0x[0-9a-fA-F]+)', anchor, re.M)
    if not pcs:
        pcs = re.findall(r'^Breakpoint \d+, (0x[0-9a-fA-F]+)', anchor, re.M)
    assert pcs, 'actual breakpoint PC missing'
    memory, chip = (folder/'code.bin').read_bytes(), (folder/'chip.bin').read_bytes()

    def read(address, size):
        for base, blob in ((meta['base'], memory), (0, chip)):
            if base <= address and address+size <= base+len(blob):
                return blob[address-base:address-base+size]
        raise ValueError((hex(address), size))

    def unpack(fmt, address):
        return struct.unpack(fmt, read(address, struct.calcsize(fmt)))

    code, data = meta['code'], meta['data']
    assert read(code+0x2af6, 2) == bytes.fromhex('4ef9')
    entry, = unpack('>I', code+0x2af8)
    slave = entry-symbols['s60_entry']
    fixture = slave+symbols['s60_pickup_encounter_results']
    assert read(fixture, 4) == b'PE61'
    names = ('setups', 'errors', 'setup_tick', 'actor', 'session', 'level',
             'world_before', 'world_after', 'energy_before', 'inventory_before',
             'inventory_assigned', 'selected_before', 'reserved')
    setup = dict(zip(names, unpack('>2H3I8H', fixture+4)))
    assert setup['errors'] == 0
    actor = read(setup['actor'], 112) if setup['actor'] else None
    world_count, = unpack('>H', data+0x3fb0)
    active_count, = unpack('>H', data+0x43b2)
    assert world_count <= 256 and active_count <= 256
    world = unpack('>'+str(world_count)+'I', data+0x3bb0)
    active = unpack('>'+str(active_count)+'I', data+0x3fb2)
    pointer, = unpack('>I', data+0x46c0)
    counters = unpack('>3H', data+0x346)
    # These helpers were stubbed in the old isolated oracle. Require their
    # actual native trampolines here; the installed removal hook is audited too.
    assert read(code+0x4238, 6) == bytes.fromhex('4ef9')+struct.pack('>I', code+0xec12)
    assert read(code+0x83c6, 6) == bytes.fromhex('4ef9')+struct.pack('>I', code+0x2144e)
    assert read(code+0x9492, 2) == bytes.fromhex('4ef9')
    assert unpack('>I', code+0x9494)[0] == slave+symbols['s60_forget']
    assert read(code+0x3d2a, 6) == bytes.fromhex('5279')+struct.pack('>I', data+0x346)
    assert read(code+0x3dc2, 2) == bytes.fromhex('4e75')
    clock = sim60_state.read(folder)
    assert clock['ticks'] == meta['tick'] and clock['running'] == 1
    return dict(meta=meta, pc=int(pcs[-1], 16), setup=setup, actor=actor,
                world=world, active=active, pointer=pointer, counters=counters,
                energy=unpack('>h', data+0x46c4)[0],
                inventory=read(data+0x20f8, 7), selected=unpack('>H', data+0x20be)[0],
                ui_active=unpack('>H', data+0x268)[0],
                pickup_state=read(slave+symbols['s60_pickup_state'], 16),
                completed_pc=slave+symbols['s60_loop_complete'], clock=clock,
                read=read, slave=slave, symbols=symbols)


def validate(folder, listing):
    folder = Path(folder)
    initial = capture(folder, listing)
    n = initial['clock']['substeps']
    setup_tick = sim60_state.build_constant(listing, 'PICKUP_ENCOUNTER')
    spawn = capture(folder/'spawn', listing)
    acquired = capture(folder/'acquired', listing)
    assert initial['setup']['setups'] == 0 and initial['clock']['ticks'] == setup_tick
    setup = spawn['setup']
    assert setup['setups'] == 1 and setup['setup_tick'] == setup_tick
    assert setup['session'] == 1 and setup['level'] == 0
    assert setup['world_after'] == setup['world_before']+1
    assert setup['energy_before'] == initial['energy'] == 680
    assert setup['inventory_before'] == initial['inventory'][0]
    assert setup['inventory_assigned'] == 1
    assert spawn['clock']['ticks'] == setup_tick+1 and spawn['energy'] == 300
    expected_inventory = bytes([1])+initial['inventory'][1:]
    assert spawn['inventory'] == expected_inventory
    actor = setup['actor']
    assert actor in spawn['world'] and spawn['pointer'] == 0
    assert struct.unpack_from('>H', spawn['actor'], 2)[0] == 31
    assert spawn['actor'][0x55] == 100
    assert struct.unpack_from('>I', spawn['actor'], 0x1e)[0] == actor+0x56
    assert acquired['setup'] == setup and acquired['pointer'] == actor
    assert acquired['pc'] == acquired['meta']['code']+0x3662
    assert actor in acquired['world'] and actor in acquired['active']
    assert struct.unpack_from('>i', acquired['actor'], 0x50)[0] < 700
    assert acquired['actor'][0x56] == 1
    assert acquired['counters'][0] == 0
    tick = acquired['clock']['ticks']
    height = struct.unpack_from('>i', acquired['actor'], 16)[0]
    yaw = struct.unpack_from('>H', acquired['actor'], 24)[0]
    _, yaw_step, height_step = acquired['counters']
    rows = []
    event_dirs = sorted((folder/'events').iterdir())
    assert [p.name for p in event_dirs] == [f'{i:02}' for i in range(1, 31)], 'expected thirty native pickup events'
    for number, event in enumerate(event_dirs, 1):
        before, after = capture(event, listing), capture(event/'after', listing)
        assert before['setup'] == after['setup'] == setup
        assert before['pc'] == before['meta']['code']+0x3d2a
        assert after['pc'] == after['meta']['code']+0x3dc2
        assert before['clock']['ticks'] == after['clock']['ticks'] == tick+n*number, 'pickup callback cadence changed'
        assert before['pointer'] == actor and before['counters'][0] == number-1
        assert before['ui_active'] == 1
        assert before['inventory'] == expected_inventory
        assert struct.unpack_from('>i', before['actor'], 16)[0] == height
        assert struct.unpack_from('>H', before['actor'], 24)[0] == yaw
        if number < 30:
            height += height_step
            yaw = (yaw+yaw_step) & 65535
            height_step = (height_step+5) & 65535
            yaw_step = (yaw_step+256) & 65535
            assert after['counters'] == (number, yaw_step, height_step)
            assert after['energy'] == 680 and after['pointer'] == actor, 'native healing/pickup pointer consequence'
            assert actor in after['world'] and after['actor'][0x55] == 100
            assert after['inventory'] == expected_inventory and after['ui_active'] == 1
        else:
            assert after['counters'] == (0, 20, 10) and after['pointer'] == 0
            assert after['energy'] == before['energy']
            assert actor not in after['world'] and after['actor'][0x55] == 0, 'native removal missing or actor still live'
            assert after['inventory'] == bytes([3])+expected_inventory[1:], 'native inventory grant missing or incorrect'
            assert after['ui_active'] == 0
        assert struct.unpack_from('>i', after['actor'], 16)[0] == height, 'native pickup height consequence'
        assert struct.unpack_from('>H', after['actor'], 24)[0] == yaw
        assert before['selected'] == after['selected'] == setup['selected_before'], 'unexpected power selection change'
        rows.append(dict(number=number, tick=before['clock']['ticks'], height=height, yaw=yaw,
                         energy_before=before['energy'], energy_after=after['energy']))
    for name, elapsed in (('complete', 30*n+1), ('later', 40*n+1)):
        state = capture(folder/name, listing)
        assert state['pc'] == state['completed_pc']
        assert state['clock']['ticks'] == tick+elapsed
        assert state['pointer'] == 0 and state['pickup_state'] == bytes(16), 'pickup state not cleared after removal'
        assert actor not in state['world'] and actor not in state['active']
        assert state['actor'][0x55] == 0
        assert state['inventory'] == bytes([3])+expected_inventory[1:]
        assert state['selected'] == setup['selected_before']
        table, = struct.unpack('>I', state['read'](state['slave']+state['symbols']['s60_motion_table'], 4))
        records = state['read'](table, 272*144)
        assert all(struct.unpack_from('>I', records, at)[0] != actor for at in range(0, len(records), 144))
    return dict(acquired_tick=tick, complete_tick=tick+30*n+1, later_tick=tick+40*n+1,
                events=rows, inventory_before=expected_inventory.hex(),
                inventory_after=(bytes([3])+expected_inventory[1:]).hex(),
                selected_power=setup['selected_before'],
                scope='Controlled allocation, placement, energy and inventory; native contact acquisition, 30 events, healing, grant, removal and record cleanup; selection remains unchanged.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.capture, args.listing), indent=2))
