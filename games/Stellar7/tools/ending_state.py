#!/usr/bin/env python3
"""Check native final-boss/ending snapshots with explicit reduced-health or unchanged-health setup."""
import argparse
import json
import re
import struct
from pathlib import Path
from encounter_state import read as encounter, validate_finish, validate as validate_encounter
from sim60_state import read as clock


def validate(folder, listing, native_health=False):
    folder = Path(folder)
    slave = Path(listing).with_suffix('.slave').read_bytes()

    def capture(name, expected_pc):
        path = folder/name
        assert (path/'slave.slave').read_bytes() == slave, 'exact build mismatch'
        anchor = (path/'anchor.txt').read_text()
        meta = {k: int(v, 0) for k, v in re.findall(
            r'^(code|data|base)=(\S+)', anchor, re.M)}
        # A manual debugger interrupt must never count as a native event.
        assert 'SIGINT' not in anchor and 'Program received signal' not in anchor
        stops = re.findall(r'^Breakpoint \d+, (0x[0-9a-f]+)', anchor, re.M)
        assert stops and int(stops[-1], 16) == meta['code']+expected_pc, name
        memory = (path/'code.bin').read_bytes()
        chip = (path/'chip.bin').read_bytes()

        def read(address, size):
            for base, blob in ((meta['base'], memory), (0, chip)):
                if base <= address and address+size <= base+len(blob):
                    return blob[address-base:address-base+size]
            raise ValueError(f'unmapped address {address:#x}')

        def value(address, fmt):
            return struct.unpack(fmt, read(address, struct.calcsize(fmt)))[0]

        regs = {k: int(v, 16) for k, v in re.findall(
            r'^(a2|a3|sp)\s+0x([0-9a-f]+)', anchor, re.M)}
        return path, meta, read, value, regs, clock(path)

    hit_pc = 0x11202
    if native_health:
        anchor = (folder/'before-hit/anchor.txt').read_text()
        code = int(re.search(r'^code=(\S+)', anchor, re.M)[1], 0)
        hit_pc = int(re.search(r'^pc\s+0x([0-9a-f]+)', anchor, re.M)[1], 16)-code
        assert hit_pc in (0x3f04, 0x11202), 'unsupported native damage boundary'
    hit, meta, read, value, regs, hc = capture('before-hit', hit_pc)
    setup = encounter(hit, listing)
    if native_health:
        validate_encounter(setup)
        assert setup['requested_level'] == 6
        assert 'finish_setups' not in setup, 'reduced-health fixture is present'
        symbols = Path(listing).read_text(encoding='latin1')
        assert not re.search(r'^BOSS_FINISH_TEST\s+E:', symbols, re.M)
        if hit_pc == 0x3f04:
            assert read(meta['code']+0x3f04, 8) == bytes.fromhex('48e70310266f0010')
            boss = value(regs['sp']+4, '>I')
            damage = value(regs['sp']+8, '>H')
            caller = value(regs['sp'], '>I')-meta['code']
            if not 0 <= caller < 0x25360:
                table = {k: int(v, 16) for k, v in re.findall(r'^(\S+)\s+00:([0-9A-F]+)', symbols, re.M)}
                slave_base = value(meta['code']+0x2af8, '>I')-table['s60_entry']
                wrapper_return = value(regs['sp'], '>I')-slave_base
                assert table['s60_contact_health'] <= wrapper_return < table['s60_contact_shield_sound']
                caller = value(regs['sp']+10, '>I')-meta['code']
                assert caller == 0x35ae and value(meta['data']+0x1e9e, '>H') > 0, 'unverified contact caller'

        else:
            assert read(meta['code']+0x11202, 4) == bytes.fromhex('4eba04c8')
            boss, shot = regs['a3'], regs['a2']
            assert value(shot+2, '>H') == 23
            assert value(shot+0x6a, '>I') == value(meta['data']+0x43c0, '>I')
            damage = value(regs['sp']+4, '>H')
            caller = 0x11206
        health = value(boss+0x55, '>B')
        assert value(boss+2, '>H') == 44 and 0 < health <= damage
    else:
        validate_finish(setup)
        assert read(meta['code']+0x11202, 4) == bytes.fromhex('4eba04c8')
        boss, shot = regs['a3'], regs['a2']
        health = value(boss+0x55, '>B')
        assert value(boss+2, '>H') == 44 and health == 1
        assert value(shot+2, '>H') == 23
        assert value(shot+0x6a, '>I') == value(meta['data']+0x43c0, '>I')
        damage = value(regs['sp']+4, '>H')
        caller = 0x11206
        assert damage >= 1 and hc['ticks'] >= setup['finish_tick']
    assert hc['running'] == 1 and hc['session'] == 7

    _, cm, read, value, _, cc = capture('before-final-clear', 0x3ff4)
    assert cm == meta
    assert read(cm['code']+0x3ff4, 6) == bytes.fromhex('4239')+struct.pack('>I', cm['data']+0x1e53)
    assert cc['ticks'] == hc['ticks'] and value(boss+0x55, '>B') == 0
    assert value(cm['data']+0x46a0, '>H') == 6
    assert value(cm['data']+0x1e53, '>B') == 1
    assert value(cm['data']+0x1e90, '>H') == 0

    # The completed-update boundary precedes the loop's native cleanup.
    exit_path = folder/'completed-exit'
    ec = clock(exit_path)
    exit_memory = (exit_path/'code.bin').read_bytes()
    assert exit_memory[meta['data']-meta['base']+0x1e53] == 0
    assert (exit_path/'slave.slave').read_bytes() == slave
    assert ec['ticks'] == hc['ticks']+1 and ec['session'] == 7
    for name, pc in (('ending-entry', 0x2ebc), ('ending-return', 0x2ec0)):
        _, em, read, value, regs, state = capture(name, pc)
        assert em == meta
        assert state['ticks'] == ec['ticks'] and state['renders'] == ec['renders']
        assert state['running'] == 0 and state['session'] == 7
        # Native world reset ($9662) reuses this flag before the ending.
        # Scheduler running/ticks, not this scene flag, prove simulation stopped.
        assert value(em['data']+0x1e53, '>B') == 1
        assert value(em['data']+0x1e90, '>H') == 0
        assert value(em['data']+0x46a0, '>H') == 7
        assert value(em['data']+0x46da, '>H') == 1
        if name == 'ending-entry':
            assert read(em['code']+0x2eb6, 10) == bytes.fromhex('426770063f004eba7fbc')
            assert value(regs['sp'], '>H') == 6
    return dict(setup=setup, native_health=native_health, health_before=health, caller_offset=hex(caller), hit_tick=hc['ticks'], damage=damage,
                completed_tick=ec['ticks'], renders=ec['renders'], ending_returned=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    parser.add_argument('--native-health', action='store_true', help='require no boss-health shortcut and observe the native damage entry')
    args = parser.parse_args()
    print(json.dumps(validate(args.capture, args.listing, args.native_health), indent=2))
