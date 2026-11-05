#!/usr/bin/env python3
"""Conservative word-aligned static branch audit of the pinned TD root hunk."""
from pathlib import Path
import hashlib, struct
root = Path(__file__).resolve().parents[1]
p = root/'tmp/game/TestDrive_v1.3_0089/TestDrive/data/TD'
b = p.read_bytes()
assert hashlib.sha256(b).hexdigest() == 'dd5b9608d64de145a6138c99d175f148939bd8e8c37d793631314a50c9d606db'
b = b[40:40+0x7c0c]
hooks = {0x6390: bytes.fromhex('4cdf4c004e75'), 0x6916: bytes.fromhex('4cdf1f074e75')}
for a, expected in hooks.items():
    assert b[a:a+6] == expected
    print(f'TD:{a:05x} six-byte boundary: {expected.hex()}')
for a in range(0,len(b)-6,2):
    w = int.from_bytes(b[a:a+2],'big'); target = None
    if w >> 12 == 6:
        d = struct.unpack('b', b[a+1:a+2])[0]
        if not d: d = struct.unpack('>h',b[a+2:a+4])[0]
        target = a+2+d
    elif w & 0xf0f8 == 0x50c8 or w in (0x4eba,0x4efa):
        target = a+2+struct.unpack('>h',b[a+2:a+4])[0]
    elif w in (0x4eb9,0x4ef9):
        target = int.from_bytes(b[a+2:a+6],'big')
    for h in hooks:
        if target is not None and h <= target < h+6:
            print(f'candidate incoming branch TD:{a:05x} -> TD:{target:05x}')
            assert target == h, 'branch into hook interior'
print('PASS: no word-aligned direct branch candidate enters a hook interior. Indirect targets are not statically proven.')
