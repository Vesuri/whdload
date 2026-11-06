"""Compare A/B (e.g. MASK_OFF/on) controlled scenes: complete displayed planes, PNGs and end state.

  check_opt20_mask_scene.py OFF_DIR ON_DIR OUT.json
"""
import json, os, struct, sys
from pathlib import Path
import replay_flight
from amigaxdev import barto

a, b, report_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
# PATCH=start:length (hex) of the code site that legitimately differs; default _MaskSprite.
PATCH = [int(x, 16) for x in os.environ.get('PATCH', '4e400:6').split(':')]
images = []
for n in [1, 10, 30, 45, 57, 200, 400]:
    if not (a / f'swap-{n:03d}.trace').exists(): continue
    planes = []
    for p in (a, b):
        t = barto.load(p / f'swap-{n:03d}.trace'); pub = json.loads((p / 'publications.json').read_text())[n - 1]; c = pub['copper']
        words = dict(struct.unpack_from('>HH', t.chip, o) for o in range(c, c + 192, 4))
        ptr = [words[0xe0 + 4 * i] * 65536 + words[0xe2 + 4 * i] for i in range(8)]
        planes.append(b''.join(t.chip[o:o + 8000] for o in ptr))
    same = planes[0] == planes[1]; png = (a / f'swap-{n:03d}.png').read_bytes() == (b / f'swap-{n:03d}.png').read_bytes()
    images.append(dict(swap=n, planes_equal=same, png_equal=png))
changes = {}
for i in range(3):
    x = (a / f'end-hunk{i}.bin').read_bytes(); y = (b / f'end-hunk{i}.bin').read_bytes()
    diff = sorted(o for o, (u, v) in enumerate(zip(x, y)) if u != v)
    patch = set(range(PATCH[0], PATCH[0] + PATCH[1])) if i == 0 else set()
    clocks = set()
    for o in ([0x4d85a, 0x4d884] if i == 0 else [0x10678, 0x13de0, 0x17012] if i == 1 else []): clocks.update(range(o, o + 4))
    changes[i] = dict(differing_bytes=len(diff), patch=[hex(o) for o in diff if o in patch], clocks=[hex(o) for o in diff if o in clocks],
                      other=[hex(o) for o in diff if o not in patch and o not in clocks][:64], other_count=sum(1 for o in diff if o not in patch and o not in clocks))
report = dict(images=images, images_all_equal=bool(images) and all(r['planes_equal'] and r['png_equal'] for r in images), hunks=changes,
              strict_state_equal_except_patch_and_clocks=all(c['other_count'] == 0 for c in changes.values()))
report_path.write_text(json.dumps(report, indent=2)); print(json.dumps(report, indent=1)[:3000])
assert report['images_all_equal'], 'displayed image mismatch'
