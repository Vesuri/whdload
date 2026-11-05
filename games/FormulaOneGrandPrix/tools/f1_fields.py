#!/usr/bin/env python3
"""F1: merge attribution saves into datafile fields and the f1gp ranges they write.

  python3 tools/f1_fields.py BASE DATAFILE DIR...

BASE is the save of DATAFILE unchanged; each DIR holds tools/f1_writemap.py saves named
bNNN.f1gp (datafile byte NNN changed) or cNNN.f1gp (16-byte chunk NNN after the 4-byte
header changed). Byte runs take precedence over the chunks they cover. Consecutive
datafile bytes whose targets continue contiguously are merged into one field.
"""
import glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f1_diff import hunks, where  # noqa: E402


def changed(base, path):
    b = open(path, 'rb').read()
    return sorted(i for i in range(len(base)) if base[i] != b[i])


def spans(layout, offsets):
    runs = []
    for i in offsets:
        if runs and i - runs[-1][1] <= 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    out = []
    for a, b in runs:
        h, o = where(layout, a)
        out.append((f'h{h}+${o:X}' if h is not None else f'file ${o:X}') + (f'–${o+b-a:X}' if b > a else ''))
    return out


def main():
    base, src = (open(p, 'rb').read() for p in sys.argv[1:3])
    layout = hunks(base)
    per, width = {}, {}
    for d in sys.argv[3:]:
        for p in glob.glob(os.path.join(d, 'b*.f1gp')):
            per[int(os.path.basename(p)[1:-5])] = changed(base, p)
    for d in sys.argv[3:]:
        for p in glob.glob(os.path.join(d, 'c*.f1gp')):
            s = 4 + 16*int(os.path.basename(p)[1:-5])
            if not any(i in per for i in range(s, s + 16)):
                per[s], width[s] = changed(base, p), 16     # the chunk, keyed by its first byte
    fields = []
    for i in sorted(per):
        t = per[i]
        if not t:
            continue
        f = fields[-1] if fields else None
        if f and f['next'] == i and (t[0] == f['t'][-1] + 1 or t == f['t']):
            f['t'] = sorted(set(f['t']) | set(t))
        else:
            f = {'start': i, 't': t}
            fields.append(f)
        f['next'] = i + width.get(i, 1)
        f['end'] = f['next'] - 1
    for f in fields:
        r = spans(layout, f['t'])
        print(f"df+${f['start']:04X}" + (f"–${min(f['end'], len(src) - 1):04X}" if f['end'] > f['start'] else ''),
              ' '.join(r[:8]) + (f' (+{len(r) - 8} ranges)' if len(r) > 8 else ''))


if __name__ == '__main__':
    main()
