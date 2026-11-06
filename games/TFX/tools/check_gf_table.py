#!/usr/bin/env python3
"""Static check of gouraud_fill_040's per-colour OR table in a slave listing.

  check_gf_table.py LISTING

Every gf_offsets entry must start an entry of OR.L D0,d16(A1) (OR.L D0,(A1) for plane 4)
ending in JMP (A6), whose planes are exactly the colour's set bits. If the listing has
gf_recip, entry i (1..319) must be ceil(2^32/(i+1)) and entry 0 zero.
"""
import re, struct, sys
lst = open(sys.argv[1], encoding='latin1').read()
sym = lambda n: int(re.search(r'^' + n + r'\s+00:([0-9A-Fa-f]+)', lst, re.M)[1], 16)
code = {}
for m in re.finditer(r'^00:([0-9A-F]{8}) ([0-9A-F]+)', lst, re.M):
    for i, x in enumerate(bytes.fromhex(m[2])): code[int(m[1], 16) + i] = x
rd = lambda a, n: bytes(code[a + i] for i in range(n))
go, gr = sym('gf_offsets'), sym('gf_or')
for c in range(256):
    a = gr + struct.unpack('>h', rd(go + 2 * c, 2))[0]; planes = 0
    while (w := rd(a, 2)) != bytes.fromhex('4ed6'):
        if w == bytes.fromhex('8191'): planes |= 16; a += 2; continue
        assert w == bytes.fromhex('81a9'), (c, w.hex()); d = struct.unpack('>h', rd(a + 2, 2))[0]
        assert d % 8000 == 0; planes |= 1 << (d // 8000 + 4); a += 4
    assert planes == c, (c, planes)
print('gf_or table verified for 256 colours')
if re.search(r'^gf_recip\s', lst, re.M):
    a = sym('gf_recip'); v = [struct.unpack('>I', rd(a + 4 * i, 4))[0] for i in range(320)]
    assert v[0] == 0 and all(v[i] == -(-(1 << 32) // (i + 1)) for i in range(1, 320))
    print('gf_recip verified for widths 2-320')
