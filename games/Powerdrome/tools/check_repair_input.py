#!/usr/bin/env python3
"""Check one input-only native-ring publication during a dropped repair step.

Requires the TIMING_REPAIR_INPUT_TEST=1 fixture and full repair service probes.
Does not certify special-command exits, queue wrapping or interrupt concurrency.
"""
import argparse
from pathlib import Path
from check_repair_service import check as check_service


def check(root):
    check_service(root)
    records = []
    current = None
    for line in (root/'swaps-gdb.txt').read_text().splitlines():
        v = line.split()
        if not v:
            continue
        if v[0] == 'PDTIME_EVENT':
            current = {'field': int(v[1]), 'off': int(v[2], 16)}
            records.append(current)
        elif v[0] in ('PDRKEY_EVENT', 'PDRDROP_EVENT'):
            assert current is not None
            assert (int(v[1]), int(v[2], 16)) == (current['field'], current['off'])
            current[v[0]] = list(map(int, v[3:]))
    assert records and all(len(r['PDRKEY_EVENT']) == 11 for r in records)
    publications = [r['PDRKEY_EVENT'][0] for r in records]
    assert publications[0] == 0 and publications[-1] == 1
    assert publications == sorted(publications) and set(publications) == {0, 1}
    start = publications.index(1)
    entry = records[start]
    assert entry['off'] in (0x148d8, 0x14a20)
    assert entry['PDRDROP_EVENT'][0] == 1, 'Publication did not occur on a dropped step'
    k = entry['PDRKEY_EVENT']
    count, key, old_reader, old_writer, new_writer, writer, reader, capacity = k[:8]
    assert key == ord('x') and capacity > 1
    assert 0 <= old_reader == old_writer < capacity
    assert new_writer == (old_writer+1) % capacity
    assert writer == new_writer and reader == old_reader, 'Native queue was not published exactly once'
    post_off = 0x14962 if entry['off'] == 0x148d8 else 0x14aa6
    end = next(i for i in range(start+1, len(records)) if records[i]['off'] == post_off)
    step = records[start:end+1]
    expected = [entry['off'], 0xe3bc, 0xe3c4, 0xe3d0, 0xe3d6,
                0xe3e6, 0xe3ec, 0xe422, 0xe426, post_off]
    assert [r['off'] for r in step] == expected, 'Unexpected native input control flow'
    by_off = {r['off']: r['PDRKEY_EVENT'] for r in step}
    assert by_off[0xe3d6][9] == 0xffffffff, 'Native availability check missed the queued key'
    assert by_off[0xe3e6][5:7] == [new_writer, old_reader]
    consumed = by_off[0xe3ec]
    assert consumed[9] == key and consumed[5:7] == [new_writer, new_writer]
    assert consumed[10] == by_off[0xe3e6][10], 'Native key reader changed caller stack depth'
    assert by_off[0xe422][9] == key and by_off[0xe426][8] == key
    post = records[end]
    assert post['PDRDROP_EVENT'][0] == 0
    assert post['PDRKEY_EVENT'][5:7] == [new_writer, new_writer]
    assert post['PDRKEY_EVENT'][10] == k[10]+24, 'Repair step did not restore its native MOVEM frame'
    assert sum(r['off'] == 0xe3ec for r in records) == 1, 'Missing or repeated native consumption'
    assert all(r['PDRKEY_EVENT'][:5] == k[:5] for r in records[start:])
    print(f'{root.name}: one native x key published on a dropped step at field {entry["field"]}')
    print('  Availability, exactly-once consumption, command handoff, queue indices and stack restoration pass')
    print('  Special commands, nonlocal exits, queue wrap/capacity and concurrent producers remain separate')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    check(parser.parse_args().capture)
