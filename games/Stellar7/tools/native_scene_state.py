#!/usr/bin/env python3
"""Validate a native-timing combat reference and its self-removed scene setup."""
import argparse
import json
from pathlib import Path
import re
import struct

import check_disabled
import encounter_state
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev.patchlist import slave_code
from stellar7_report import locate


def inspect(folder, listing, scene):
    folder, listing = Path(folder), Path(listing)
    preservation = check_disabled.inspect(folder, listing, True, True)
    meta = json.loads((folder/'metadata.json').read_text())
    symbols = {name:int(value,16) for name,value in re.findall(
        r'^(\w+)\s+00:([0-9A-F]+)',listing.read_text(encoding='latin1'),re.M)}
    memory = (folder/'code.bin').read_bytes()
    origin = locate(memory,slave_code(folder/'slave.slave'),meta['base'],header=32)
    assert origin is not None
    def read(address,size):
        offset = address-meta['base']
        assert 0 <= offset and offset+size <= len(memory)
        return memory[offset:offset+size]
    record = origin+symbols['native_scene_results']
    assert read(record,4) == b'NR60'
    exits,restored,target,reserved = struct.unpack('>4H',read(record+4,8))
    expected = 6 if scene == 'type10' else 0
    assert (exits,restored,target,reserved) == (expected,1,expected,0)
    # Compiled SIM60 is used only for the VERIFY boss setup; it never runs.
    assert read(origin+symbols['s60_running'],2) == b'\0\0'
    assert read(origin+symbols['s60_ticks'],4) == bytes(4)
    data = meta['data_base']
    level, = struct.unpack('>H',read(data+0x46a0,2))
    active = read(data+0x1e53,1)[0]
    death, = struct.unpack('>H',read(data+0x1e90,2))
    assert level == expected and active and not death
    count, = struct.unpack('>H',read(data+0x43b2,2))
    assert 0 < count <= 256
    actors = struct.unpack('>'+str(count)+'I',read(data+0x3fb2,count*4))
    types = {}
    for actor in actors:
        kind, = struct.unpack('>H',read(actor+2,2))
        types[str(kind)] = types.get(str(kind),0)+1
    if scene == 'type10':
        assert types.get('10',0)>0, 'type-10 actor absent from reference window'
    else:
        encounter = encounter_state.read(folder,listing)
        encounter_state.validate(encounter)
        assert any(types.get(str(kind),0) for kind in range(44,49)), 'boss absent from reference window'
    return dict(scene=scene,level=level,native_frame=meta['frame'],
                scene_setup_removed=True,simulation_running=False,
                active_actor_types=types,original_code=preservation)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture',type=Path)
    parser.add_argument('--listing',type=Path,required=True)
    parser.add_argument('--scene',choices=('type10','boss'),required=True)
    args = parser.parse_args()
    print(json.dumps(inspect(args.capture,args.listing,args.scene),indent=2))
