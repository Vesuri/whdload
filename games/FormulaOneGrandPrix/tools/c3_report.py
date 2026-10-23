#!/usr/bin/env python3
"""Verify saved C3 evidence and optionally compare exact repeated modal routes."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report(directory):
    root = Path(directory)
    meta = json.loads((root/'meta.json').read_text())
    assert meta['status'] == 'CAPTURED' and meta['quit'] == 'OK'
    assert meta['modal']['status'] == 'PASS'
    assert digest(root/'slave.bin') == meta['build']['slave_sha256']
    observations = []
    previous = None
    for item in meta['modal']['observations']:
        name = item['name']
        data = (root/(name+'.bin')).read_bytes()
        assert hashlib.sha256(data).hexdigest() == item['sha256']
        assert digest(root/(name+'-cars.bin')) == item['cars_sha256']
        if 'session_sha256' in item:
            assert digest(root/(name+'-session.bin')) == item['session_sha256']
        if item['name'].endswith('-held') and not item['name'].startswith('accelerated'):
            assert previous is not None
            for key in ('clock','cars_sha256','session_sha256'):
                assert item[key] == previous[key], (item['name'],key)
        previous = item
        clock = item['clock']
        assert clock['observed'] == (clock['consumed']+clock['credit']+clock['dropped']+item['c3_rebased']) & 0xffffffff
        assert item['c2_hud_overflows'] == 0
        idle = struct.unpack_from('>I',data,meta['symbols']['c3_idle_start'])[0]
        if item['c3_suspended']:
            assert idle == clock['last'], 'suspension used a second serial sample'
        if item.get('c3_inactive') and item['c2_mode'] == 0:
            assert idle == struct.unpack_from('>I',data,meta['symbols']['c3_closed_clock'])[0]
        closed = None
        if item['c3_exits']:
            values = struct.unpack_from('>I4H5I3H',data,meta['symbols']['c3_closed_clock'])
            last,credit,rate,phase,batch,observed,consumed,dropped,ticks,rebased,pending,mode,reason = values
            assert observed == (consumed+credit+dropped+rebased)&0xffffffff
            assert rate in (50,60) and pending in (0,1) and mode in (1,2) and reason in (1,2,3,4)
            closed = dict(ticks=ticks,pending=pending,mode=mode,reason=reason,rebased=rebased,dropped=dropped)
        picture = root/(name+'.png')
        observations.append(dict(name=name, snapshot=item['sha256'],cars=item['cars_sha256'],
                                 picture=digest(picture) if picture.exists() else None,
                                 clock=clock,closed=closed,epochs=item['c3_epochs'],exits=item['c3_exits'],
                                 excluded=item['c3_excluded']))
    return dict(status='PASS',scenario=meta['modal']['scenario'],build=meta['build'],
                runtime=meta['runtime'],game_inputs=meta['game_inputs'],setup=meta['setup'],
                whd_args=meta['whd_args'],extra_args=meta['extra_args'],route=meta['route'],
                route_reply=meta['route_reply'],hunk_bases=meta['hunk_bases'],observations=observations)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture')
    parser.add_argument('--repeat')
    parser.add_argument('--out',required=True)
    args = parser.parse_args()
    result = report(args.capture)
    if args.repeat:
        twin = report(args.repeat)
        assert result == twin, 'repeat differs in pinned configuration, layout, route, state or pictures'
        result['exact_repeat'] = 'PASS'
    path = Path(args.out).resolve()
    scratch = Path(__file__).resolve().parents[1]/'tmp'
    if not path.is_relative_to(scratch):
        raise ValueError('report must stay in project tmp/')
    path.write_text(json.dumps(result,indent=2)+'\n')
    print('C3 saved evidence PASS'+('; exact repeat PASS' if args.repeat else ''))
