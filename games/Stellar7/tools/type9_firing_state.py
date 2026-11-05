#!/usr/bin/env python3
"""Check successful native type-9 shot returns in the input-only level-5 route.

No claim about allocation failures, unobserved firing channels or other enemies.
The observer stops after the native channel-loop return and at tick 3600.
"""
import argparse
import json
import struct
from pathlib import Path
from type10_firing_state import capture
import audit_hooks


def validate(folder, listing):
    folder, listing = Path(folder), Path(listing)
    slave = listing.with_suffix('.slave').read_bytes()
    installed = audit_hooks.installed(folder, listing)
    events, stop = [], None
    paths = sorted((folder/'events').iterdir())
    assert paths, 'no firing observations'
    for index, path in enumerate(paths):
        meta, regs, read, state = capture(path, slave)
        code, data = meta['code'], meta['data']
        if regs['pc'] != code+0xf630:
            assert index == len(paths)-1 and not (path/'after').exists()
            entry, = struct.unpack('>I', read(code+0x2af8, 4))
            completed = entry+struct.unpack('>H', read(entry+44, 2))[0]
            assert regs['pc'] == completed and state['ticks'] == 300*state['substeps'], 'route endpoint not reached'
            assert read(data+0x1e90, 2) == bytes(2), 'route ended in death'
            stop = dict(tick=state['ticks'], path=path.name)
            continue
        for offset, expected in ((0xf630,'5c4f24406004'),
                                 (0xf636,'53337062524760d6'),
                                 (0xf63e,'200a4cdf0cc04e75'),
                                 (0xf6b2,'701e4600d1aa0010600e'),
                                 (0xf6e6,'357c01f40040'),
                                 (0xf6ec,'254b006a')):
            assert read(code+offset, len(bytes.fromhex(expected))) == bytes.fromhex(expected), hex(offset)
        for offset, destination in ((0xf65e,0x11ba), (0xf6fe,0x1242), (0xf70c,0x12df)):
            assert read(code+offset, 6) == bytes.fromhex('41f9')+struct.pack('>I',data+destination)
        assert state['running'] and state['event_due'] == 1 and state['phase'] == 0
        assert state['ticks'] % state['substeps'] == 0, 'firing outside decision cadence'
        assert read(data+0x46a0, 2) == struct.pack('>H', 5)
        actor = read(regs['a3'], 112)
        assert struct.unpack_from('>H', actor, 2)[0] == 9
        assert actor[0x58] != 5, 'special firing variant requires separate validation'
        shot = regs['d0']
        assert shot, 'allocation failure requires separate validation'
        projectile = read(shot, 112)
        projectile_type = read(data+0x11ba+9, 1)[0]
        assert struct.unpack_from('>H', projectile, 2)[0] == projectile_type, 'projectile type differs'
        assert struct.unpack_from('>I', projectile, 0x6a)[0] == regs['a3'], 'projectile owner differs'
        assert struct.unpack_from('>H', projectile, 0x40)[0] == 500, 'projectile lifetime differs'
        assert projectile[8:16] == actor[8:16] and projectile[20:26] == actor[20:26], 'projectile position/yaw differs'
        assert struct.unpack_from('>I', projectile, 16)[0] == (struct.unpack_from('>I', actor, 16)[0]+225) & 0xffffffff, 'type-9 launch height differs'
        life = (read(data+0x12df+projectile_type, 1)[0]*3) & 255
        assert projectile[0x55] == life and actor[0x61] == read(data+0x1242+9, 1)[0], 'native shot/cooldown initialization differs'
        am, ar, after_read, after_state = capture(path/'after', slave)
        assert am == meta and ar['pc'] == code+0xf640 and ar['a3'] == regs['a3']
        assert after_state['ticks'] == state['ticks'] and after_state['phase'] == 0 and after_state['event_due'] == 1
        assert after_read(shot, 112) == projectile, 'projectile changed in channel loop'
        channels = actor[0x60]
        assert 0 < channels <= 8
        # The observer retains no D7. Identify the fired channel by matching
        # its native initializer and the complete subsequent actor state.
        matches = []
        for fired in range(channels):
            if actor[0x62+fired] != life:
                continue
            expected = bytearray(actor)
            for channel in range(fired+1, channels):
                if expected[0x62+channel]:
                    expected[0x62+channel] -= 1
            if after_read(regs['a3'], 112) == expected:
                matches.append(fired)
        assert len(matches) == 1, 'native channel-loop consequence differs or is ambiguous'
        events.append(dict(path=path.name, tick=state['ticks'], projectile_type=projectile_type,
                           fired_channel=matches[0], cooldown=actor[0x61], channel_lifetime=life))
    assert events and stop is not None
    return dict(events=events, stop=stop, installed=installed,
                scope='Successful native type-9 shot returns: ownership, position, lifetime, cooldown, channel-loop effects and N-tick decision cadence. No allocation-failure claim.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.capture, args.listing), indent=2))
