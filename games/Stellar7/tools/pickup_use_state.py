#!/usr/bin/env python3
"""Check native power selection/use after the controlled PE61 pickup scene."""
import argparse
import json
import struct
from pathlib import Path
import pickup_encounter_state
import simulation_state
import sim60_state

def configuration(folder, listing):
    clock = sim60_state.read(folder)
    n = clock['substeps']
    use = sim60_state.build_constant(listing, 'PICKUP_USE')
    return n, use, clock['ticks']


def nominal(tick, n):
    """Round a retained 60 Hz observation time up to an actual tick."""
    return (tick*n+11)//12


def ordered(initial, points):
    return [initial]+sorted(set(points)-{initial})


def validate(folder, listing):
    folder = Path(folder)
    n, use, initial = configuration(folder, listing)
    activation = use+2
    points = ordered(initial, [use, use+1, activation, activation+1, activation+n-1, activation+n, activation+n+1, activation+2*n, nominal(1500,n)])
    rows = []
    for tick in points:
        point = folder if tick == initial else folder/'checkpoints'/str(tick)
        raw = pickup_encounter_state.capture(point, listing)
        state = simulation_state.snapshot(point, True, True)
        assert raw['pc'] == raw['completed_pc'] and raw['clock']['ticks'] == tick
        assert raw['setup']['setups'] == 1 and raw['setup']['errors'] == 0
        assert raw['pointer'] == 0 and raw['pickup_state'] == bytes(16)
        code, data = raw['meta']['code'], raw['meta']['data']
        target = raw['slave']+raw['symbols']['fixture_power_buttons']
        assert raw['read'](code+0x196d0, 6) == bytes.fromhex('4ef9')+struct.pack('>I', target)
        assert raw['read'](data+0x2114, 4) == struct.pack('>I', code+0x3e32)
        selected = 65535 if tick < activation else 0
        assert raw['selected'] == selected, 'native selection edge differs'
        active = tick > activation
        expected_inventory = bytes([254 if active else 3])+bytes([1])*6
        assert raw['inventory'] == expected_inventory, 'native charge consumption differs'
        timers = struct.unpack('>7H', bytes.fromhex(state['power_timers']))
        phases = struct.unpack('>10H', bytes.fromhex(state['power_phases']))
        elapsed = max(0, tick-activation)
        timer = 900-elapsed//n if active else 0
        phase = n-elapsed % n if active else 0
        assert timers == (timer, 0, 0, 0, 0, 0, 0), 'native power timer differs'
        assert phases == (phase, timer)+(0,)*8, 'power decrement phase differs'
        assert state['clone_active'] == 0, 'clone became active before native deadline'
        rows.append(dict(tick=tick, selected=selected, inventory=raw['inventory'].hex(),
                         timer=timer, phase=phase))
    return dict(points=rows, scope='Controlled pickup scene; native second-button release selects power zero, simultaneous buttons activate it. Checks consumption and initial N-tick timer cadence, not expiry or audible output.')


def validate_clone(folder, listing):
    result = validate(folder, listing)
    n, use, _ = configuration(folder, listing)
    activation, clone_tick = use+2, use+2+40*n
    rows = []
    for tick in sorted({nominal(1500,n), clone_tick-1, clone_tick, clone_tick+1, nominal(2000,n)}):
        point = Path(folder)/'checkpoints'/str(tick)
        raw = pickup_encounter_state.capture(point, listing)
        state = simulation_state.snapshot(point, True, True)
        assert raw['pc'] == raw['completed_pc'] and raw['clock']['ticks'] == tick
        code, data = raw['meta']['code'], raw['meta']['data']
        # Native activation changes the view object's mesh pointer and its
        # active word; guard both instructions rather than inferring from time.
        assert raw['read'](code+0x3e80, 10) == bytes.fromhex('217c')+struct.pack('>I', data+0x4598)+bytes.fromhex('0016')+bytes.fromhex('33fc')
        assert raw['read'](code+0x3e88, 8) == bytes.fromhex('33fc0001')+struct.pack('>I', data+0x34c)
        elapsed = tick-activation
        timer, phase = 900-elapsed//n, n-elapsed % n
        assert state['power_timers'] == struct.pack('>7H', timer, 0, 0, 0, 0, 0, 0).hex(), 'clone timer differs'
        assert state['power_phases'] == struct.pack('>10H', phase, timer, *(0,)*8).hex(), 'clone phase differs'
        active = int(tick >= clone_tick)
        assert state['clone_active'] == active, 'native clone activation edge differs'
        view, = struct.unpack('>I', raw['read'](data+0x43b4, 4))
        mesh, = struct.unpack('>I', raw['read'](view+22, 4))
        assert mesh == data+(0x4598 if active else 0x4498), 'native clone mesh switch differs'
        assert raw['selected'] == 0 and raw['inventory'] == bytes([254])+bytes([1])*6
        rows.append(dict(tick=tick, timer=timer, phase=phase, clone_active=active,
                         view_mesh_data_offset=hex(mesh-data)))
    result['clone_points'] = rows
    result['scope'] += ' Also checks native clone activation at 40-native-update deadline and its sampled mesh switch; no expiry or depletion claim.'
    return result





def validate_expiry(folder, listing):
    """Check native expiry after pickup, selection and use, without timer writes."""
    n, use, initial = configuration(folder, listing)
    activation = use+2
    expiry = activation+900*n
    points = ordered(initial, [nominal(t,n) for t in (3000,6000,9000)]+[expiry-1,expiry,expiry+1])
    rows = []
    for tick in points:
        point = Path(folder) if tick == initial else Path(folder)/'checkpoints'/str(tick)
        raw = pickup_encounter_state.capture(point, listing)
        state = simulation_state.snapshot(point, True, True)
        assert raw['pc'] == raw['completed_pc'] and raw['clock']['ticks'] == tick
        assert raw['setup']['setups'] == 1 and raw['setup']['errors'] == 0
        code, data = raw['meta']['code'], raw['meta']['data']
        assert raw['read'](code+0x3eb2, 8) == bytes.fromhex('217c')+struct.pack('>I', data+0x4498)+bytes.fromhex('0016')
        assert raw['read'](code+0x3eba, 6) == bytes.fromhex('4279')+struct.pack('>I', data+0x34c)
        elapsed = tick-activation
        expired = tick >= expiry
        timer = max(0, 900-elapsed//n)
        phase = n if expired else n-elapsed % n
        assert state['power_timers'] == struct.pack('>7H', timer, *(0,)*6).hex(), 'expiry timer differs'
        assert state['power_phases'] == struct.pack('>10H', phase, timer, *(0,)*8).hex(), 'expiry phase differs'
        assert state['clone_active'] == int(not expired), 'native clone expiry edge differs'
        assert raw['inventory'] == bytes([2 if expired else 254])+bytes([1])*6, 'expiry inventory differs'
        assert raw['selected'] == 0, 'expiry selection differs'
        view, = struct.unpack('>I', raw['read'](data+0x43b4, 4))
        mesh, = struct.unpack('>I', raw['read'](view+22, 4))
        assert mesh == data+(0x4498 if expired else 0x4598), 'expiry mesh differs'
        rows.append(dict(tick=tick, timer=timer, phase=phase,
                         clone_active=state['clone_active'], inventory=raw['inventory'].hex(),
                         mesh_data_offset=hex(mesh-data)))
    return dict(points=rows, scope='Controlled real pickup and input-only activation; native clone expiry 900 native updates after activation. Mesh checked only at sampled points; no animation, audio or depletion claim.')



def validate_speed(folder, listing):
    """Seven native selection edges, last-charge speed use and native expiry."""
    n, use, initial = configuration(folder, listing)
    activation, expiry = use+14, use+14+200*n
    points = ordered(initial, [use+2*i for i in range(1,8)]+[activation+1,activation+n-1,activation+n,nominal(1500,n),expiry-1,expiry,expiry+1])
    rows = []
    for tick in points:
        point = Path(folder) if tick == initial else Path(folder)/'checkpoints'/str(tick)
        raw = pickup_encounter_state.capture(point, listing)
        state = simulation_state.snapshot(point, True, True)
        assert raw['pc'] == raw['completed_pc'] and raw['clock']['ticks'] == tick
        assert raw['setup']['setups'] == 1 and raw['setup']['errors'] == 0
        assert raw['pointer'] == 0 and raw['pickup_state'] == bytes(16)
        code, data = raw['meta']['code'], raw['meta']['data']
        target = raw['slave']+raw['symbols']['fixture_power_buttons']
        assert raw['read'](code+0x196d0, 6) == bytes.fromhex('4ef9')+struct.pack('>I', target)
        assert raw['read'](data+0x2114+6*4, 4) == struct.pack('>I', code+0xecae)
        # Expiry invokes native inventory/UI cleanup for slot six.
        assert raw['read'](code+0xed8e, 8) == bytes.fromhex('70063f006100fbb4')
        selected = 65535 if tick < use+2 else min(6, (tick-use-2)//2)
        if tick >= expiry:
            selected = 0  # Exhausted slot six advances to the first available slot.
        assert raw['selected'] == selected, ('speed selection', tick, raw['selected'])
        used = tick > activation
        inventory = bytes([3])+bytes([1])*5+bytes([0 if used else 1])
        assert raw['inventory'] == inventory, ('speed inventory', tick)
        elapsed = max(0, tick-activation)
        timer = max(0, 200-elapsed//n) if used else 0
        phase = (n if tick >= expiry else n-elapsed % n) if used else 0
        assert state['power_timers'] == struct.pack('>7H', *(0,)*6, timer).hex(), ('speed timer', tick)
        assert state['power_phases'] == struct.pack('>10H', *(0,)*8, phase, timer).hex(), ('speed phase', tick)
        assert state['clone_active'] == 0
        # Guard the actual native boost addition and 400-unit cap. The only
        # changed instruction here is the 40/N per-tick acceleration quantum.
        view, = struct.unpack('>I', raw['read'](data+0x43c0, 4))
        for offset in (0x10082, 0x1008c, 0x1009e):
            assert raw['read'](code+offset, 6) == bytes.fromhex('2079')+struct.pack('>I', data+0x43c0)
        assert raw['read'](code+0x10088, 4) == bytes.fromhex('d1680040')
        assert raw['read'](code+0x10092, 12) == bytes.fromhex('0c68019000406f0e303c0190')
        assert raw['read'](code+0x100a4, 4) == bytes.fromhex('31400040')
        # Completed-tick snapshots follow phase (tick-1)%N. Derive the
        # expected integrated native acceleration without reading the table.
        quantum = tick*40//n-(tick-1)*40//n
        assert raw['read'](code+0x10080, 2) == bytes((0x70, quantum))
        speed, = struct.unpack('>h', raw['read'](view+64, 2))
        expected_speed = min(400, tick*40//n-activation*40//n) if activation < tick <= expiry else 0
        assert speed == expected_speed, ('boost speed', tick, speed, expected_speed)
        rows.append(dict(tick=tick, selected=selected, inventory=inventory.hex(), timer=timer,
                         phase=phase, speed=speed, acceleration_quantum=quantum))
    return dict(points=rows, scope='Controlled pickup scene with native button selection across all seven slots. Uses the existing single speed charge; activation and expiry span 200 native updates (40 seconds). Checks native 40-unit acceleration integrated over N ticks, the 400-unit cap, and return to zero speed with neutral mouse input after expiry at sampled points. Does not independently establish displacement or audible output.')


def timed_points(slot, n=12, use=1400, initial=1318):
    assert slot in (1, 4, 5)
    activation = use+2*(slot+1)
    return ordered(initial, [use+2+2*i for i in range(slot+1)]+[
        activation+1, activation+n-1, activation+n, activation+n+1,
        activation+10*n, activation+500*n-1, activation+500*n, activation+500*n+1])


def validate_timed(folder, listing, slot):
    """Native input-driven activation and full lifetime of the 500-unit powers."""
    n, use, initial = configuration(folder, listing)
    activation = use+2*(slot+1)
    callback, record = {1: (0xec62, 1), 4: (0xec86, 2), 5: (0xec9c, 3)}[slot]
    rows = []
    for tick in timed_points(slot,n,use,initial):
        point = Path(folder) if tick == initial else Path(folder)/'checkpoints'/str(tick)
        raw = pickup_encounter_state.capture(point, listing)
        state = simulation_state.snapshot(point, True, True)
        assert raw['pc'] == raw['completed_pc'] and raw['clock']['ticks'] == tick
        assert raw['setup']['setups'] == 1 and raw['setup']['errors'] == 0
        assert raw['pointer'] == 0 and raw['pickup_state'] == bytes(16)
        code, data = raw['meta']['code'], raw['meta']['data']
        target = raw['slave']+raw['symbols']['fixture_power_buttons']
        assert raw['read'](code+0x196d0, 6) == bytes.fromhex('4ef9')+struct.pack('>I', target)
        assert raw['read'](data+0x2114+slot*4, 4) == struct.pack('>I', code+callback)
        selected = 65535 if tick < use+2 else min(slot, (tick-use-2)//2)
        if tick >= activation+500*n:
            selected = slot+1
        assert raw['selected'] == selected, ('timed selection', slot, tick, raw['selected'])
        used = tick > activation
        inventory = bytearray([3]+[1]*6)
        if used:
            inventory[slot] = 0
        assert raw['inventory'] == inventory, ('timed inventory', slot, tick)
        elapsed = max(0, tick-activation)
        timer = max(0, 500-elapsed//n) if used else 0
        phase = (n if elapsed >= 500*n else n-elapsed % n) if used else 0
        timers, phases = [0]*7, [0]*10
        timers[slot] = timer
        phases[record*2:record*2+2] = [phase, timer]
        assert state['power_timers'] == struct.pack('>7H', *timers).hex(), ('timed timer', slot, tick)
        assert state['power_phases'] == struct.pack('>10H', *phases).hex(), ('timed phase', slot, tick)
        assert state['clone_active'] == 0
        rows.append(dict(tick=tick, selected=selected, inventory=inventory.hex(), timer=timer, phase=phase))
    return dict(slot=slot, activation=activation, expiry=activation+500*n, points=rows,
                scope='Controlled pickup scene; native input selection consumes the existing last charge. Full 500-native-update (100-second) lifetime and exhausted-slot reselection. Effect-specific combat and audible output are outside this check.')



def validate_jump(folder, listing):
    """Input-driven jump reproduces all 45 native height boundaries and lands."""
    n, use, initial = configuration(folder, listing)
    activation = use+6
    apex, landing = activation+45*n//2, activation+45*n
    points = ordered(initial, [use+2,use+4,activation,activation+1]+[activation+n*k for k in range(1,46)]+[apex-1,apex,apex+1,landing-1,landing+1])
    rows = []
    for tick in points:
        point = Path(folder) if tick == initial else Path(folder)/'checkpoints'/str(tick)
        raw = pickup_encounter_state.capture(point, listing)
        state = simulation_state.snapshot(point, True, True)
        assert raw['pc'] == raw['completed_pc'] and raw['clock']['ticks'] == tick
        assert raw['setup']['setups'] == 1 and raw['setup']['errors'] == 0
        assert raw['pointer'] == 0 and raw['pickup_state'] == bytes(16)
        code, data = raw['meta']['code'], raw['meta']['data']
        target = raw['slave']+raw['symbols']['fixture_power_buttons']
        assert raw['read'](code+0x196d0, 6) == bytes.fromhex('4ef9')+struct.pack('>I', target)
        assert raw['read'](data+0x2114+8, 4) == struct.pack('>I', code+0xec74)
        assert raw['read'](code+0xec7c, 8) == bytes.fromhex('33fc00dc')+struct.pack('>I', data+0x1ea0)
        # Native jump adds vertical velocity, then subtracts ten per update.
        assert raw['read'](code+0xed02, 12) == bytes.fromhex('d1a80010700a9179')+struct.pack('>I', data+0x1ea0)
        player, = struct.unpack('>I', raw['read'](data+0x43c0, 4))
        height, = struct.unpack('>i', raw['read'](player+16, 4))
        elapsed = max(0, tick-activation)
        airborne = 0 < elapsed < 45*n
        selected = 65535 if tick < use+2 else min(2, (tick-use-2)//2)
        if elapsed >= 45*n:
            selected = 3
        assert raw['selected'] == selected, ('jump selection', tick)
        inventory = bytes([3, 1, 0 if elapsed else 1, 1, 1, 1, 1])
        assert raw['inventory'] == inventory, ('jump charge', tick)
        valid, last, velocity, remainder, reserved = struct.unpack('>HhihH', bytes.fromhex(state['jump_integrator']))
        if airborne:
            assert valid == 1 and reserved == 0
            assert velocity == 220*n-10*elapsed, ('jump velocity', tick)
            expected_velocity = (abs(velocity)//n)*(1 if velocity >= 0 else -1)
            assert last == expected_velocity
            # Interpolated rational trajectory through native 5 Hz positions.
            numerator = elapsed*(225*n-5*elapsed)
            assert height*n*n+remainder == numerator, ('jump integral', tick)
            assert abs(remainder) < n*n
            if elapsed % n == 0:
                native_steps = elapsed//n
                native_height = 220*native_steps-5*native_steps*(native_steps-1)
                assert height == native_height and remainder == 0, ('native jump boundary', tick)
        else:
            expected_velocity = 0
            assert height == 0 and state['jump_integrator'] == bytes(12).hex(), ('jump landing/reset', tick)
        timers = [0]*7
        timers[2] = expected_velocity
        assert state['power_timers'] == struct.pack('>7h', *timers).hex(), ('jump published velocity', tick)
        assert state['power_phases'] == bytes(20).hex()
        rows.append(dict(tick=tick, height=height, velocity=expected_velocity,
                         remainder=remainder, selected=selected, inventory=inventory.hex()))
    return dict(points=rows, scope='Controlled pickup scene; native button selection and last-charge jump activation. Checks all 45 native height boundaries, fractional samples around apex/landing, 45-native-update flight and native exhausted-slot reselection. No arbitrary terrain, midair impacts or audio claim.')



def validate_mine(folder, listing):
    """Native slot-three placement must retain a full, untimed displacement."""
    n, use, initial = configuration(folder, listing)
    activation = use+8
    points = ordered(initial, [use+2,use+4,use+6,activation,activation+1,activation+2,activation+n]+[nominal(t,n) for t in (1500,1800,2400)])
    rows = []
    expected_position = None
    for tick in points:
        point = Path(folder) if tick == initial else Path(folder)/'checkpoints'/str(tick)
        raw = pickup_encounter_state.capture(point, listing)
        state = simulation_state.snapshot(point, True, True)
        assert raw['pc'] == raw['completed_pc'] and raw['clock']['ticks'] == tick
        assert raw['setup']['setups'] == 1 and raw['setup']['errors'] == 0
        assert raw['pointer'] == 0 and raw['pickup_state'] == bytes(16)
        code, data = raw['meta']['code'], raw['meta']['data']
        target = raw['slave']+raw['symbols']['fixture_power_buttons']
        assert raw['read'](code+0x196d0, 6) == bytes.fromhex('4ef9')+struct.pack('>I', target)
        assert raw['read'](data+0x2114+12, 4) == struct.pack('>I', code+0xe88e)
        assert raw['read'](code+0xe8d6, 14) == bytes.fromhex('377cfc1800402f0b4eba9da2584f')
        assert raw['read'](code+0x8a7a, 6) == bytes.fromhex('4ef9')+struct.pack('>I', code+0x16ab8)
        assert raw['read'](code+0x8a86, 6) == bytes.fromhex('4ef9')+struct.pack('>I', code+0x16a90)
        assert raw['read'](code+0x16a98, 8) == bytes.fromhex('e8480800000b6708')
        assert raw['read'](code+0x16aaa, 6) == bytes.fromhex('41f9')+struct.pack('>I', code+0x14e88)
        player, = struct.unpack('>I', raw['read'](data+0x43c0, 4))
        position = struct.unpack('>3i', raw['read'](player+8, 12))
        angles = struct.unpack('>3H', raw['read'](player+20, 6))
        assert angles[:2] == (0, 0) and raw['read'](player+52, 14) == bytes(14)
        def cosine(angle):
            index = (angle & 65535) >> 4
            if index & 2048:
                index = 4096-index
            return struct.unpack('>h', raw['read'](code+0x14e88+index*2, 2))[0]
        if tick == activation:
            sine = cosine(angles[2]+0xc000)
            negative_sine = ((-sine+32768) % 65536)-32768
            dx, dz = (negative_sine*-1000) >> 14, (cosine(angles[2])*-1000) >> 14
            expected_position = (position[0]+dx, position[1]+dz, 0)
        mines = [a for a in raw['world'] if struct.unpack('>H', raw['read'](a+2, 2))[0] == 43]
        used = tick > activation
        assert len(mines) == int(used), ('mine allocation', tick)
        selected = (65535 if tick < use+2 else min(3, (tick-use-2)//2)) if not used else 4
        assert raw['selected'] == selected, ('mine selection', tick)
        inventory = bytes([3, 1, 1, 0 if used else 1, 1, 1, 1])
        assert raw['inventory'] == inventory, ('mine charge', tick)
        mine_position = None
        if used:
            actor = mines[0]
            mine_position = struct.unpack('>3i', raw['read'](actor+8, 12))
            assert mine_position == expected_position, ('mine full native placement', tick, mine_position, expected_position)
            assert struct.unpack('>3H', raw['read'](actor+20, 6)) == angles
            assert raw['read'](actor+52, 14) == bytes(14)
            assert raw['read'](actor+85, 1) == bytes([1])
        assert state['power_timers'] == bytes(14).hex() and state['power_phases'] == bytes(20).hex()
        rows.append(dict(tick=tick, selected=selected, inventory=inventory.hex(), position=mine_position))
    return dict(points=rows, scope='Controlled pickup scene; native slot-three selection, last-charge use, type-43 allocation and full -1000-speed placement using guarded native trig tables. Stable placement through the requested observation window. This checks placement is not divided into N timestep increments; no mine impact or detonation claim.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    parser.add_argument('--clone', action='store_true', help='also check delayed native clone activation through tick 2000')
    parser.add_argument('--expiry', action='store_true', help='check the longer native expiry capture')
    parser.add_argument('--speed', action='store_true', help='check seven selections, speed use and expiry')
    parser.add_argument('--timed-slot', type=int, choices=(1, 4, 5), help='check full native lifetime of another timed power')
    parser.add_argument('--jump', action='store_true', help='check input-driven jump trajectory and landing')
    parser.add_argument('--mine', action='store_true', help='check native immediate placement and depletion')
    args = parser.parse_args()
    if sum((args.clone, args.expiry, args.speed, args.timed_slot is not None, args.jump, args.mine)) > 1:
        parser.error('choose only one capture layout option')
    check = validate_mine if args.mine else validate_jump if args.jump else validate_speed if args.speed else validate_expiry if args.expiry else validate_clone if args.clone else validate
    result = validate_timed(args.capture, args.listing, args.timed_slot) if args.timed_slot is not None else check(args.capture, args.listing)
    print(json.dumps(result, indent=2))
