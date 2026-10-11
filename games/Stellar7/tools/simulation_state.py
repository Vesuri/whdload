#!/usr/bin/env python3
"""Compare mapped gameplay state at the same simulation boundary.

Includes all objects in world/active lists, player, power timers, RNG and stars.
Excludes raw pointers, projected coordinates and radar flag backups by default.
Use --render-scratch to expose the saved radar flags from the most recent draw.
This is a mapped-state test, not a claim that every game variable is understood.
"""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path


def snapshot(folder, include_projection=False, include_presentation=False, include_render_scratch=False):
    folder = Path(folder)
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|data|base|frame)=(\S+)', (folder / 'anchor.txt').read_text(), re.M)}
    memory = (folder / 'code.bin').read_bytes()
    chip = (folder / 'chip.bin').read_bytes()

    def read(address, size):
        for base, blob in ((meta['base'], memory), (0, chip)):
            if base <= address and address + size <= base + len(blob):
                return blob[address-base:address-base+size]
        raise ValueError(f'Unmapped address {address:#x}, size {size}')

    data = read(meta['data'], 0x823c)
    word = lambda offset: struct.unpack_from('>H', data, offset)[0]
    long = lambda offset: struct.unpack_from('>I', data, offset)[0]
    world = [long(0x3bb0 + i*4) for i in range(word(0x3fb0))]
    active = [long(0x3fb2 + i*4) for i in range(word(0x43b2))]
    assert len(world) <= 256 and len(active) <= 256
    addresses = list(dict.fromkeys([long(0x43c0), long(0x43c4)] + world + active))
    identities = {address: i for i, address in enumerate(addresses)}
    # Native $8e58 allocates these persistent actor pools. Removal at $9492
    # drops world membership without freeing the pool slot; collision links can
    # still name it. Resolve by table/slot, never by guessed address deltas.
    pool_references = {}
    for pool, count in ((0x43d8, 8), (0x43f8, 16), (0x4438, 16), (0x4478, 8)):
        for slot in range(count):
            address = long(pool + slot*4)
            if address:
                assert address not in pool_references, 'aliased native actor pool slots'
                pool_references[address] = ['pool', pool, slot]
    def reference(address):
        if not address:
            return None
        if address in identities:
            return ['object', identities[address]]
        if address in pool_references:
            return pool_references[address]
        for label, base, size in [('code', meta['code'], 0x25360), ('data', meta['data'], 0x823c)]:
            if base <= address < base+size:
                return [label, address-base]
        return ['unmapped', address]  # surface unknown references, never mask them

    # Actor byte 0 is live flags. Byte 1 is saved by the radar renderer and
    # restored into byte 0 within that same render pass; it then stays stale.
    # Keep it available explicitly, rather than treating draw history as physics.
    assert read(meta['code']+0xbfe2, 4) == bytes.fromhex('17530001')
    assert read(meta['code']+0xc0d2, 4) == bytes.fromhex('16ab0001')
    radar_backups = []
    objects = []
    for address in addresses:
        b = read(address, 0x6e)
        radar_backups.append(b[1:2].hex())
        objects.append(dict(
            flags=b[:1].hex(),
            type=struct.unpack_from('>H', b, 2)[0],
            distance=struct.unpack_from('>i', b, 0x50)[0],
            radius=struct.unpack_from('>i', b, 4)[0],
            position=struct.unpack_from('>3i', b, 8),
            angles=struct.unpack_from('>3H', b, 0x14),
            motion=b[0x34:0x50].hex(),
            behavior=b[0x54:0x66].hex(),
            link=reference(struct.unpack_from('>I', b, 0x66)[0]),
            owner=reference(struct.unpack_from('>I', b, 0x6a)[0]),
        ))
        if include_projection:
            # Untracked actors retain coordinates from their last render. Compare
            # only fields refreshed by the native visibility path at this tick.
            objects[-1]['projected'] = b[0x28:0x34].hex() if b[0] & 8 else None
            objects[-1]['screen'] = b[0x22:0x28].hex() if b[0] & 12 == 12 else None
    # Six-byte star stride, but only x/y (first four bytes) are initialized/read
    # by $99ec/$9bd4/$9a2a. The third word is unused allocation residue.
    stars = read(long(0xee4), word(0x3b94)*6)
    result = dict(terrain_contact=word(0x46d8), preference_settings=[word(offset) for offset in (0x1e74, 0x1e76, 0x1e78, 0x1e7a)], boss_spawn_ready=data[0x1efc], spawn_progress=word(0x1e70), spawn_target=data[0x46b0], game_active=data[0x1e53], pickup=[reference(long(0x46c0)), word(0x0346), word(0x0348), word(0x034a), data[0x1e56]], damage_flash=word(0x026a), shield_contact=word(0x0344), knockback_pending=word(0x026c), frame=word(0x1e96), level=word(0x46a0), energy=word(0x46c4),
                  score=long(0x46c8), power_inventory=data[0x20f8:0x20ff].hex(),
                  selected_power=word(0x20be), clone_active=word(0x034c), game_counters=data[0x1e90:0x1eba].hex(), power_timers=data[0x1e9c:0x1eaa].hex(),
                  rng=hashlib.sha256(data[0x2434:0x24a8]).hexdigest(),
                  stars=hashlib.sha256(b''.join(stars[i:i+4] for i in range(0, len(stars), 6))).hexdigest(), objects=objects,
                  world=[identities[x] for x in world], active=[identities[x] for x in active])
    if include_presentation:
        # Unpatched $c3ba..$c3e4 advances this indicator once per draw.
        # Compare its phase explicitly, including the installed clock if any.
        result['hud_oscillator'] = [word(0x1f5c), word(0x1f5e)]
        hud_hook = read(meta['code']+0xc3ba, 6)
        result['hud_clock'] = None
        if hud_hook[:2] == bytes.fromhex('4ef9'):
            hud_entry = struct.unpack_from('>I', hud_hook, 2)[0]
            hud_header = read(hud_entry, 14)
            if hud_header[4:8] == b'HU60':
                result['hud_clock'] = list(struct.unpack_from('>IH', hud_header, 8))
    if include_projection:
        # Exact destinations written by $12ae8..$12b72 for every processed
        # actor. Other projection scratch can legitimately retain render data.
        result['projection_scratch'] = [data[a:b].hex() for a, b in
                                        ((0x5d98, 0x5db2), (0x5db4, 0x5db8),
                                         (0x5e16, 0x5e1a), (0x5e22, 0x5e2a))]
    hook = read(meta['code']+0x2af6, 6)
    if hook[:2] == bytes.fromhex('4ef9'):
        entry = struct.unpack_from('>I', hook, 2)[0]
        abi = read(entry, 52)
        if abi[4:8] == b'S760':
            assert 1 <= struct.unpack_from('>H', abi, 50)[0] <= 29, 'Unsupported SIM60 state ABI'
            motion_offset, stars_offset = struct.unpack_from('>2H', abi, 46)
            table = struct.unpack('>I', read(entry+motion_offset, 4))[0]
            stride = struct.unpack('>H', read(entry+70, 2))[0] if struct.unpack_from('>H', abi, 50)[0] >= 5 else 64
            records = read(table, 272*stride)
            by_actor = {struct.unpack_from('>I', records, i)[0]: records[i+4:i+stride].hex()
                        for i in range(0, len(records), stride)
                        if struct.unpack_from('>I', records, i)[0]}
            if struct.unpack_from('>H', abi, 50)[0] >= 6:
                knock_offset,knock_size=struct.unpack('>2H',read(entry+74,4))
                result['knockback_phase']=read(entry+knock_offset,knock_size).hex()
            if struct.unpack_from('>H', abi, 50)[0] >= 8:
                pickup_offset,pickup_size=struct.unpack('>2H',read(entry+82,4))
                pickup=read(entry+pickup_offset,pickup_size)
                result['pickup_integrator']=[reference(struct.unpack_from('>I',pickup)[0]),pickup[4:].hex()]
            if struct.unpack_from('>H', abi, 50)[0] >= 15:
                shake_offset,shake_size=struct.unpack('>2H',read(entry+92,4))
                result['shake_phase']=read(entry+shake_offset,shake_size).hex()
                result['shake_rng']=data[0x3558]
                result['shake_offsets']=struct.unpack_from('>2h',data,0x7156)
            if struct.unpack_from('>H', abi, 50)[0] >= 25:
                terrain_offset,terrain_size=struct.unpack('>2H',read(entry+120,4))
                assert terrain_size == 8
                result['terrain_clock']=read(entry+terrain_offset,terrain_size).hex()
            if struct.unpack_from('>H', abi, 50)[0] >= 29:
                friction_offset,friction_size=struct.unpack('>2H',read(entry+132,4))
                assert friction_size == 8
                result['terrain_friction_clock']=read(entry+friction_offset,friction_size).hex()
            result['fractional_motion'] = [by_actor.get(actor) for actor in addresses]
            result['fractional_stars'] = read(entry+stars_offset, 200).hex()
            result['tick_phase'] = struct.unpack_from('>H', abi, 30)[0]
            if struct.unpack_from('>H', abi, 50)[0] >= 2:
                jump_offset,jump_size=struct.unpack('>2H',read(entry+52,4))
                result['jump_integrator']=read(entry+jump_offset,jump_size).hex()
            if struct.unpack_from('>H', abi, 50)[0] >= 4:
                timer_offset,timer_size=struct.unpack('>2H',read(entry+60,4))
                result['power_phases']=read(entry+timer_offset,timer_size).hex()
            if struct.unpack_from('>H', abi, 50)[0] >= 3:
                timer_offset,timer_size=struct.unpack('>2H',read(entry+56,4))
                result['player_cooldowns']=read(entry+timer_offset,timer_size).hex()
    if include_render_scratch:
        result['render_scratch'] = {'radar_flag_backups': radar_backups}
    return result


def differences(a, b, path=''):
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(a.keys() | b.keys()):
            yield from differences(a.get(key), b.get(key), f'{path}.{key}'.strip('.'))
    elif isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            yield f'{path}: length {len(a)} != {len(b)}'
        for i, (x, y) in enumerate(zip(a, b)):
            yield from differences(x, y, f'{path}[{i}]')
    elif a != b:
        yield f'{path}: {a} != {b}'


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('captures', nargs='+', type=Path)
    p.add_argument('--projection', action='store_true', help='also compare freshly updated actor coordinates and simulation-written projection scratch')
    p.add_argument('--presentation', action='store_true', help='also compare cockpit indicator position, step and installed simulation clock')
    p.add_argument('--render-scratch', action='store_true', help='also compare radar flag backups left by the most recent draw; these may differ across render schedules')
    args = p.parse_args()
    states = [snapshot(c, include_projection=args.projection, include_presentation=args.presentation, include_render_scratch=args.render_scratch) for c in args.captures]
    if len(states) == 1:
        print(json.dumps(states[0], indent=2))
    else:
        failed = False
        for folder, state in zip(args.captures[1:], states[1:]):
            diff = list(differences(states[0], state))
            print(f'{args.captures[0]} vs {folder}: ' + ('mapped state matches' if not diff else '\n'+'\n'.join(diff)))
            failed |= bool(diff)
        raise SystemExit(int(failed))
