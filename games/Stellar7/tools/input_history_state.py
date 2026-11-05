#!/usr/bin/env python3
"""Read input history at completed ticks and check the elapsed-field fixture."""
import argparse
import json
import re
import struct
from pathlib import Path
from sim60_state import read as scheduler


def memory(folder):
    folder = Path(folder)
    addresses = {k: int(v, 0) for k, v in re.findall(
        r'^(code|data|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    blob = (folder/'code.bin').read_bytes()
    entry = struct.unpack_from('>I', blob, addresses['code']-addresses['base']+0x2af8)[0]
    return blob, entry-addresses['base'], addresses


def read(folder):
    blob, entry, _ = memory(folder)
    s = scheduler(folder)
    assert s['abi_version'] >= 30
    offset, size = struct.unpack_from('>HH', blob, entry+136)
    assert size == 32 and blob[entry+offset:entry+offset+4] == b'IH60'
    names = ('buffer', 'produced_field', 'next_field', 'fraction', 'capacity',
             'missing_ticks', 'queue_drops', 'selected_field')
    result = dict(zip(names, struct.unpack_from('>3I2H3I', blob, entry+offset+4)))
    result['sample_field'] = struct.unpack_from('>I', blob, entry+offset+size)[0]
    assert result['sample_field'] == result['selected_field']
    if s['running'] and not s['modal_depth']:
        assert result['produced_field']*s['rate_hz']+s['field_hz'] == (
            s['ticks']*s['field_hz']+s['credit']+s['unaccounted_fields']*s['rate_hz']), 'input and simulation clocks diverged'
    return result


def fixture(folder):
    blob, _, _ = memory(folder)
    state = scheduler(folder)
    history = read(folder)
    start = blob.find(b'HT60\x00\xc8\x00\x18')
    assert start >= 0, 'elapsed-field fixture missing'
    rows = [struct.unpack_from('>6I', blob, start+8+i*24) for i in range(200)]
    assert not history['missing_ticks'] and not history['queue_drops'], history
    edges = []
    previous = (0, 0)
    for tick, field, consumed, joy, fire, presented in rows:
        expected_field = (tick-1)*state['field_hz']//state['rate_hz']
        assert field == expected_field, (tick, field, expected_field)
        expected = (8 if 20 <= field < 40 else 4 if 60 <= field < 80 else
                    2 if 100 <= field < 120 else 0, int(140 <= field < 160))
        assert (joy, fire) == expected, (tick, field, joy, fire, expected)
        assert consumed >= field
        if expected != previous:
            assert presented >= consumed, (tick, consumed, presented)
            edges.append(dict(tick=tick, field=field, joy=joy, fire=fire,
                              consumed_field=consumed, first_render_field=presented,
                              consumption_delay_fields=consumed-field,
                              render_handoff_delay_fields=presented-field))
        previous = expected
    assert [r[0] for r in rows] == list(range(1, 201))
    assert len(edges) == 8
    queue = blob.find(b'HQ60')
    assertions = None
    if queue >= 0:
        completed, failures, assertions = struct.unpack_from('>3I', blob, queue+4)
        assert completed == state['session'] and failures == 0 and assertions == 96*completed, (completed, failures, assertions)
    return dict(scheduler=state, history=history, edges=edges, native_assertions=assertions,
                scope='Render completion after the tick; not a display scanout or physical-device latency measurement.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture', type=Path)
    p.add_argument('--fixture', action='store_true')
    a = p.parse_args()
    print(json.dumps(fixture(a.capture) if a.fixture else read(a.capture), indent=2))
