#!/usr/bin/env python3
"""Inspect/compare unmasked native replay-state samples in SIM_FIXTURE captures."""
import argparse
import collections
import hashlib
import json
import struct
from pathlib import Path

def read_fixture(directory, memory_name="memory.bin"):
    root = Path(directory)
    blob = (root/memory_name).read_bytes()
    candidates = []
    start = 0
    while True:
        off = blob.find(b'4DSIMFIX', start)
        if off < 0:
            break
        start = off + 1
        version, size, active, count = struct.unpack_from('>4H', blob, off+8)
        if (version, size, active) not in ((1, 1124, 1), (2, 1130, 1), (3, 1258, 1), (4, 1274, 1), (5, 1282, 1), (6, 1290, 1), (7, 1482, 1), (8, 1490, 1), (9, 1494, 1), (10, 1506, 1), (11, 1514, 1)) or not 0 < count <= 64:
            continue
        rows = []
        for n in range(count):
            pos = off+16+n*size
            tick, mode = struct.unpack_from('>HH',blob,pos)
            state = blob[pos+4:pos+size]
            assert len(state) == ({1:0x460,2:0x466,3:0x4e6,4:0x4f6,5:0x4fe,6:0x506,7:0x5c6,8:0x5ce,9:0x5d2,10:0x5de,11:0x5e6}[version])
            rows.append((tick, mode, state))
        candidates.append(rows)
    if len(candidates) != 1:
        raise ValueError(f'Expected one active fixture in {root}, got {len(candidates)}')
    return candidates[0]

def summarize(rows):
    return [{'tick':t,'mode':m,'sha256':hashlib.sha256(b).hexdigest(),
             'position':struct.unpack_from('>iii',b,0x152)} for t,m,b in rows]

def state_offset(i, shift=0):
    if i >= 0x5c6+shift: return f"camera+{i-0x5c6+shift:#x}"
    if i >= 0x506+shift: return f"auxiliary+{i-0x506+shift:#x}"
    if i >= 0x4e6+shift: return f"time_state+{i-0x4e6+shift:#x}"
    if i >= 0x466: return f"private+{i-0x466:#x}"
    return f"{i-0xa80:+#x}" if i < 0x460 else f"{i-0x460+0x228:+#x}"

def compare(left,right):
    if [(t,m) for t,m,b in left] != [(t,m) for t,m,b in right]:
        raise ValueError('Only equal-tick, equal-mode samples can be byte compared')
    mismatches=[]
    frequency=collections.Counter()
    for (tick,mode,a),(_,_,b) in zip(left,right):
        if len(a) != len(b):
            raise ValueError("Fixture versions differ; input schedule and RNG coverage changed")
        changed=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y]
        frequency.update(changed)
        if changed:
            mismatches.append({'tick':tick,'offsets_from_a4':[state_offset(i, len(a)-1486 if len(a)>=1486 else 0) for i in changed],
                               'left_bytes':[a[i] for i in changed],
                               'right_bytes':[b[i] for i in changed]})
    return {'samples':len(left),'equal_samples':len(left)-len(mismatches),
            'differing_offsets':{state_offset(i, len(left[0][2])-1486 if len(left[0][2])>=1486 else 0):n for i,n in sorted(frequency.items())},
            'mismatches':mismatches}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture');p.add_argument('other',nargs='?')
    a=p.parse_args()
    left=read_fixture(a.capture)
    print(json.dumps(compare(left,read_fixture(a.other)) if a.other else summarize(left),indent=2))
