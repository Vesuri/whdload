#!/usr/bin/env python3
"""FR0g: build the Fast RAM replay data for one captured frame.

  fr0_replay_gen.py CAPTURE_DIR OUT_DIR

OUT_DIR/FR0Blob.bin      Fast image: every region the frame's blits read or
                         write (merged segments, 64-byte margins, address
                         parity mod 4 kept), initial contents from the Chip
                         snapshot at the frame's B8Draw entry
OUT_DIR/FR0BlitTab.bin   44-byte big-endian records (see fr0_replay.s)
OUT_DIR/FR0FillTab.bin   fill tables: [ife][fc][byte] -> out<<8 | newfc
OUT_DIR/FR0Expect.bin    the image after replaying every blit in order
                         (verified Python blitter, tools/fr0_blits.py)
OUT_DIR/replay.json      segments, counts, sizes
"""
import json, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fr0_blits as F

cap, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
blits = F.parse(cap / 'blits.bin')
chip = bytearray((cap / 'frame-start.bin').read_bytes()) + bytes(2)
iv = sorted((max(0, a - 64), a + len(d) + 64) for b in blits for k, a, d in b['regions'])
seg = []
for a, e in iv:
    if seg and a <= seg[-1][1]:
        seg[-1][1] = max(seg[-1][1], e)
    else:
        seg.append([a, e])
blob = bytearray(); segs = []
for a, e in seg:
    a &= ~3
    while len(blob) % 4:
        blob.append(0)
    segs.append((a, e, len(blob))); blob += chip[a:e]


def tr(p):
    for a, e, o in segs:
        if a <= p < e:
            return o + p - a
    raise ValueError(hex(p))


rec = bytearray()
for b in blits:
    use = b['con0']; line = b['con1'] & 1
    pt = []
    for ch, bit in zip('abcd', (0x800, 0x400, 0x200, 0x100)):
        on = (use & bit or (line and ch in 'cd')) and not (line and ch == 'a')
        pt.append(tr(b[ch + 'pt']) if on else 0)
    if line:
        pt[0] = b['apt'] & 0xffff                       # line A pointer is the error term
    assert b['h'] and b['v'], 'zero size encodes 64/1024'
    rec += struct.pack('>4H4I4h3H2H2x', b['con0'], b['con1'], b['afwm'], b['alwm'], *pt,
                       b['amod'], b['bmod'], b['cmod'], b['dmod'], b['adat'], b['bdat'], b['cdat'], b['h'], b['v'])
    assert len(rec) % 44 == 0
fill = bytearray()
for ife in (0, 2):
    for fc in (0, 1):
        for d in range(256):
            x, nfc = F.FILL[d, ife + fc]; fill += struct.pack('>H', x << 8 | nfc)
# Expected result: replay on the Chip model, then gather the segments.
for b in blits:
    F.blit(chip, b)
exp = bytearray(len(blob))
for a, e, o in segs:
    exp[o:o + e - a] = chip[a:e]
(out / 'FR0Blob.bin').write_bytes(blob); (out / 'FR0BlitTab.bin').write_bytes(rec)
(out / 'FR0FillTab.bin').write_bytes(fill); (out / 'FR0Expect.bin').write_bytes(exp)
(out / 'replay.json').write_text(json.dumps({'capture': str(cap), 'blits': len(blits), 'blob_bytes': len(blob),
    'segments': [[hex(a), hex(e), o] for a, e, o in segs]}, indent=1) + '\n')
print('blits', len(blits), 'blob', len(blob), 'segments', len(segs))
