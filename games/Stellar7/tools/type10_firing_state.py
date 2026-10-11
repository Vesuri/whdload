#!/usr/bin/env python3
"""Validate native type-10 firing returns and their state/yaw consequences.

Reads raw snapshots, not the observer's derived event JSON. All three native
return sites must be observed; allocation failures are reported when present.
This does not synthesize enemy state, RNG, hits, or allocation failures.
"""
import argparse
import collections
import json
import re
import struct
from pathlib import Path
from sim60_state import read as clock


RETURNS = (0xf86e, 0xf8e4, 0xf912)


def capture(path, slave):
    assert (path/'slave.slave').read_bytes() == slave, 'exact build mismatch'
    text = (path/'anchor.txt').read_text()
    assert 'SIGINT' not in text and 'Program received signal' not in text
    meta = {k: int(v, 0) for k, v in re.findall(r'^(code|data|base)=(\S+)', text, re.M)}
    regs = {k: int(v, 16) for k, v in re.findall(r'^(pc|a3|d0)\s+0x([0-9a-f]+)', text, re.M)}
    stops = re.findall(r'^Breakpoint \d+, (0x[0-9a-f]+)', text, re.M)
    assert stops and int(stops[-1], 16) == regs['pc'], 'not a native breakpoint stop'
    memory = (path/'code.bin').read_bytes()

    def read(address, size):
        at = address-meta['base']
        assert 0 <= at <= len(memory)-size, 'unmapped actor/code address'
        return memory[at:at+size]

    return meta, regs, read, clock(path)


def validate(folder, listing):
    folder, listing = Path(folder), Path(listing)
    slave = listing.with_suffix('.slave').read_bytes()
    events, sites, stop = [], collections.Counter(), None
    paths = sorted((folder/'events').iterdir())
    assert paths and all(path.is_dir() for path in paths)
    for index, path in enumerate(paths):
        meta, regs, read, state = capture(path, slave)
        pc = regs['pc']-meta['code']
        if pc not in RETURNS:
            assert index == len(paths)-1 and not (path/'after').exists()
            entry = struct.unpack('>I', read(meta['code']+0x2af8, 4))[0]
            completed = entry+struct.unpack('>H', read(entry+44, 2))[0]
            assert regs['pc'] == completed
            assert state['ticks'] == 5400, 'did not reach the bounded route endpoint'
            assert struct.unpack('>H', read(meta['data']+0x1e90, 2))[0] == 0, 'route ended in death'
            stop = dict(tick=state['ticks'], path=path.name)
            continue
        assert read(regs['pc'], 2) == bytes.fromhex('5c4f')
        assert state['running'] and state['event_due'] == 1 and state['phase'] == 0
        assert struct.unpack('>H', read(meta['data']+0x46a0, 2))[0] == 6
        actor = read(regs['a3'], 112)
        assert struct.unpack_from('>H', actor, 2)[0] == 10
        assert actor[0x59] == (0 if pc == 0xf86e else 2)
        am, ar, after_read, after_state = capture(path/'after', slave)
        assert am == meta and ar['pc'] == meta['code']+0xf94e and ar['a3'] == regs['a3']
        assert after_read(ar['pc'], 4) == bytes.fromhex('4cdf0c80')
        assert after_state['ticks'] == state['ticks'] and after_state['event_due'] == 1
        assert after_state['phase'] == 0 and after_state['running']
        expected = bytearray(actor)
        if pc == 0xf86e:
            turn = abs(struct.unpack_from('>h', actor, 0x38)[0])
            assert turn
            expected[0x59], expected[0x5b] = 1, (8192//turn) & 255
        elif pc == 0xf912:
            expected[0x59], expected[0x5b] = 3, 63
        assert after_read(regs['a3'], 112) == expected, 'unexpected firing-state consequence'
        shot = regs['d0']
        item = dict(path=path.name, tick=state['ticks'], site=hex(pc),
                    allocated=bool(shot), state_before=actor[0x59], state_after=expected[0x59],
                    counter_after=expected[0x5b])
        if shot:
            projectile = read(shot, 112)
            assert struct.unpack_from('>I', projectile, 0x6a)[0] == regs['a3'], 'incorrect projectile owner'
            yaw = struct.unpack_from('>h', projectile, 0x18)[0]
            expected_projectile = bytearray(projectile)
            if pc == 0xf912:
                value = yaw+(-24576 if yaw > 0 else 24576)
                struct.pack_into('>H', expected_projectile, 0x18, value & 65535)
            assert after_read(shot, 112) == expected_projectile, 'unexpected projectile yaw/state consequence'
            item.update(projectile_type=struct.unpack_from('>H', projectile, 2)[0],
                        yaw_before=yaw, yaw_after=struct.unpack_from('>h', expected_projectile, 0x18)[0])
        sites[hex(pc)] += 1
        events.append(item)
    assert stop is not None and set(sites) == {hex(site) for site in RETURNS}, 'incomplete firing-branch coverage'
    assert all(event['tick'] % 12 == 0 for event in events), 'firing outside twelve-tick cadence'
    return dict(events=events, sites=dict(sites), allocation_failures=sum(not e['allocated'] for e in events),
                stop=stop, scope='Input-only route; native spawn returns, owner, actor state, projectile yaw, decision gate')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.capture, args.listing), indent=2))
