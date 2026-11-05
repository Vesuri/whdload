#!/usr/bin/env python3
"""Chip-bus census of raw race traces.

  RACE_KEEP_TRACES=1 python3 tools/f1gp.py raceprofile PHASE DIR 50    (keeps DIR/trace-*.bin)
  python3 tools/dma_census.py DIR [DIR...]

Per field: CPU chip accesses by kind (instruction fetch, data read, data write) and by
region (hunk 2 by 4 KB page, other chip RAM by 16 KB), every other DMA channel by region
(which hunk 2 bytes DMA reads), and the display registers of the first field."""
import collections, glob, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev import barto
import race_profile

TYPES = {0: 'free', 1: 'refresh', 2: 'CPU', 3: 'copper', 4: 'audio', 5: 'blitter',
         6: 'bitplane', 7: 'sprite'}
SLOTS = 227 * 313                      # PAL colour clocks per field
# Packed dma_rec (FS-UAE debug.h): reg u16 @0, addr u32 @12, type s16 @29, extra u16 @31.
# CPU records: reg 0x10xx read / 0x11xx write; extra 0 instruction fetch, 1 data.


def census(directory):
    hunks = race_profile.game_hunks()
    memory = race_profile.image(
        open(os.path.join(directory, 'chip.bin'), 'rb').read(),
        *(open(os.path.join(directory, n), 'rb').read() if os.path.exists(os.path.join(directory, n))
          else b'' for n in ('fast.bin', 'slow.bin')))
    h2 = race_profile.locate(memory, hunks)[2][0]
    h2len = next(len(data) for i, data, _ in hunks if i == 2)

    def where(a, page):
        if h2 <= a < h2 + h2len:
            return f'h2+{(a - h2) >> page << page:05x}'
        return f'chip {a >> 14 << 14:06x}'

    cpu, cpu_at, dma_at, types = (collections.Counter() for _ in range(4))
    fields, custom = 0, None
    for path in sorted(glob.glob(os.path.join(directory, 'trace-*.bin'))):
        for f in barto.load(path).fields:
            fields += 1
            custom = custom or bytes(f.custom)
            d, n = f.dma, f.dma_size
            for i in range(0, len(d), n):
                typ = d[i + 29]
                types[typ] += 1
                if typ in (0, 1):
                    continue
                addr = struct.unpack_from('<I', d, i + 12)[0]
                if typ == 2:
                    kind = ('write' if d[i + 1] & 1 else
                            'fetch' if (d[i + 31] | d[i + 32] << 8) == 0 else 'read')
                    cpu[kind] += 1
                    cpu_at[(where(addr, 12), kind)] += 1
                else:
                    dma_at[(TYPES.get(typ, typ), where(addr, 12))] += 1
    if not fields:
        raise SystemExit(f'{directory}: no trace-*.bin (capture with RACE_KEEP_TRACES=1)')
    per = lambda v: v / fields
    out = [f'# {directory}: {fields} fields, hunk 2 at {h2:#x}',
           'DMA slots per field: ' + ', '.join(f'{TYPES.get(k, k)} {per(v):.0f} ({v / fields / SLOTS * 100:.1f}%)'
                                               for k, v in sorted(types.items())),
           f'CPU chip accesses per field {per(sum(cpu.values())):.0f}: ' +
           ', '.join(f'{k} {per(v):.0f}' for k, v in cpu.most_common()),
           '## CPU chip accesses by region (per field, top 24)']
    out += [f'  {r:12s} {k:5s} {per(v):8.0f}' for (r, k), v in cpu_at.most_common(24)]
    out.append('## Other DMA by region (per field, at least 1)')
    out += [f'  {t:9s} {r:12s} {per(v):8.0f}' for (t, r), v in sorted(dma_at.items())
            if per(v) >= 1]
    reg = lambda o: struct.unpack_from('>H', custom, o + 4)[0]      # save_custom: 4-byte header
    out.append('display: ' + ' '.join(f'{name} {reg(o):04x}' for name, o in (
        ('BPLCON0', 0x100), ('BPLCON1', 0x102), ('DDFSTRT', 0x092), ('DDFSTOP', 0x094),
        ('DIWSTRT', 0x08e), ('DIWSTOP', 0x090), ('BPL1MOD', 0x108), ('BPL2MOD', 0x10a),
        ('FMODE', 0x1fc))))
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    for d in sys.argv[1:]:
        print(census(d))
