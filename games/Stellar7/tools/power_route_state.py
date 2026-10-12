#!/usr/bin/env python3
"""Validate native-button power cycling during combat, without pickup setup.

Checks charge consumption, overlapping powers, jump and landing in retained
snapshots. It does not prove shield hits, cannon damage, arbitrary terrain,
full power lifetimes, audible output or physical-device controls.
"""
import argparse
import json
import re
import struct
from pathlib import Path
import audit_hooks
import input_history_state
import sim60_state
import simulation_state


def validate_rows(rows):
    initial=bytes.fromhex(rows[0]['inventory'])
    assert len(initial)==7 and initial[0]>=2 and all(initial), 'missing initial charges'
    assert rows[0]['timers']==[0]*7 and rows[0]['selected']==65535
    assert all(r['level']==rows[0]['level'] for r in rows), 'level shortcut or transition'
    assert all(bytes.fromhex(r['inventory'])[3]==initial[3] and r['timers'][3]==0 for r in rows), 'mine was used'
    order=[]
    for slot in (0,1,2,4,5,6):
        activations=[r['tick'] for r in rows if r['timers'][slot]!=0]
        assert activations, ('power never activated',slot)
        order.append(min(activations))
    assert order==sorted(set(order)), 'power activation order differs'
    assert any(all(r['timers'][i]!=0 for i in (0,1,2,4,5,6)) for r in rows), 'no overlapping active-power coverage'
    final=rows[-1]
    expected=bytearray(x-1 for x in initial);expected[0]=(-(initial[0]-1))&255;expected[3]=initial[3]
    assert bytes.fromhex(final['inventory'])==expected, 'charge consumption differs'
    assert all(final['timers'][i]>0 for i in (0,1,4,5,6)), 'timed power unexpectedly expired'
    assert max(r['height'] for r in rows)>0 and final['height']==0 and final['timers'][2]==0, 'jump/landing absent'
    assert final['selected']==6, 'speed power not selected after cycling'
    return dict(first_observed_activation_ticks=order,final_inventory=final['inventory'],max_sampled_height=max(r['height'] for r in rows))


def inspect(folder,listing):
    folder,listing=Path(folder),Path(listing)
    assert (folder/'slave.slave').read_bytes()==listing.with_suffix('.slave').read_bytes()
    assert sim60_state.read(folder)['ticks']==sim60_state.build_constant(listing,'POWER_ROUTE')
    symbols={k:int(v,16) for k,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)',listing.read_text(encoding='latin1'),re.M)}
    assert 'fixture_power_route' in symbols and 's60_pickup_encounter_results' not in symbols
    meta={k:int(v,0) for k,v in re.findall(r'^(code|base)=(\S+)',(folder/'anchor.txt').read_text(),re.M)}
    memory=(folder/'code.bin').read_bytes();code=meta['code']-meta['base']
    entry=struct.unpack_from('>I',memory,code+0x2af8)[0]
    target=entry-symbols['s60_entry']+symbols['fixture_power_route']
    assert memory[code+0x196d0:code+0x196d6]==bytes.fromhex('4ef9')+struct.pack('>I',target)
    points=[folder]+sorted((folder/'checkpoints').iterdir(),key=lambda p:int(p.name));rows=[]
    for point in points:
        state=simulation_state.snapshot(point,True,True);clock=sim60_state.read(point);history=input_history_state.read(point)
        assert history['missing_ticks']==history['queue_drops']==0
        rows.append(dict(tick=clock['ticks'],inventory=state['power_inventory'],selected=state['selected_power'],timers=list(struct.unpack('>7H',bytes.fromhex(state['power_timers']))),height=state['objects'][0]['position'][2],level=state['level']))
    result=validate_rows(rows)
    result.update(substeps=sim60_state.read(folder)['substeps'],samples=rows,hooks=audit_hooks.installed(folder,listing),scope=__doc__.strip())
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--listing',type=Path,required=True);a=p.parse_args()
    print(json.dumps(inspect(a.capture,a.listing),indent=2))
