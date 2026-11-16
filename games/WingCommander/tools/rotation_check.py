#!/usr/bin/env python3
"""Native CD32 rotated-bitmap draws (E:2d746) with and without src/rotation.s.

Synthetic one-frame TM6 images (one pixel colour, the hotspot marked) are drawn
into a 320x200 byte bitmap at every tested angle by the executable's own
renderer, first unchanged and then with the release slave's rot_* hooks
installed at their BUFFERED_HOOKS sites. Checks: the native draw drifts against
its centre (the control); with the hooks the hotspot lands on the requested
pixel at every angle and a symmetric image's centroid stays within a quarter
pixel; a draw clipped by a smaller rectangle equals the unclipped draw inside
it, and nothing is written outside the clip rectangle. --full runs the larger
sweep recorded in docs/internals.md.
"""
import argparse, json, struct
from pathlib import Path
import numpy as np
from field_objects_check import machine
from ocs_display_check import CODE, word, long
from ocs_clock_check import SLAVE
from ocs_reconstruct import new_output, require
from variants import get

IMG, DST, ROWS, BUF = 0x400000, 0x410000, 0x420000, 0x430000
W, H = 320, 200
MARK = 9


def image(width, height, hx, hy):
    """Word-record TM6 frame: every pixel 1, the hotspot MARK."""
    pix = bytearray(); recs = bytearray()
    for y in range(height):
        pix += bytes(MARK if (x, y) == (hx, hy) else 1 for x in range(width))
        recs += struct.pack('>HHH', width, 0, (0x4000 if y else 0) | width)
    recs += struct.pack('>H', 0)
    frame = struct.pack('>hhhhhBB', hx, hy, width-1-hx, height-1-hy, 0, 0, 0)
    rpos = 20+20; ppos = rpos+len(recs); counts = ppos+len(pix); remap = counts+256
    frame += struct.pack('>II', rpos, ppos)
    return (b'TM6\0'+struct.pack('>HHII', 0, 1, counts, remap)+struct.pack('>I', 20)
            + frame+recs+pix+bytes([1]*256)+bytes(range(256)))


class Renderer:
    def __init__(self, build, model, german):
        self.c, sy = machine(build, 'cd32', model, german)
        if german:
            import german_map
            self.at = german_map.get().code
        else:
            self.at = lambda e: e
        v = get('cd32')
        self.sites = []
        for offset, label, opcode in v.BUFFERED_HOOKS:
            if label.startswith('rot_'):
                width = 8 if offset in v.WIDE_GUARDS else 6
                at = CODE+self.at(offset)
                patch = struct.pack('>HI', opcode, SLAVE+sy[label])+b'\x4e\x71'*((width-6)//2)
                self.sites.append((at, self.c.read(at, width), patch))
        require(len(self.sites) == 13, 'rotation hook sites')
        c = self.c
        c.write(ROWS, b''.join(long(BUF+W*y) for y in range(H)))
        d = bytearray(32); d[0:4] = long(ROWS); d[20:22] = word(W)
        c.write(DST, bytes(d)); self.clip(0, 0, W-1, H-1)

    def hooks(self, on):
        for at, native, patch in self.sites:
            self.c.write(at, patch if on else native)

    def clip(self, *rect):
        self.c.write(DST+24, b''.join(word(v) for v in rect))

    def draw(self, angle, scale, flags=0, x=160, y=100):
        c = self.c
        c.write(BUF, bytes(W*H))
        c.run(self.at(0x2d746), long(DST)+word(x)+word(y)+long(IMG)+word(0)+word(angle)+word(scale)+word(flags))
        return np.frombuffer(c.read(BUF, W*H), np.uint8).reshape(H, W)


def centroid(b, x, y):
    ys, xs = np.nonzero(b)
    return xs.mean()-x, ys.mean()-y


def steady(r, cases, angles):
    rows = []
    for (w, h, hx, hy), scale, flags in cases:
        r.c.write(IMG, image(w, h, hx, hy))
        out = {}
        for on in (False, True):
            r.hooks(on)
            cen = []; hit = 0
            for a in angles:
                b = r.draw(a, scale, flags)
                cen.append(centroid(b, 160, 100)); hit += int(b[100, 160] == MARK)
            cen = np.array(cen)
            steps = np.abs(np.diff(cen, axis=0)).sum(axis=1)
            out['hooks' if on else 'native'] = dict(
                marker_at_centre=hit, x=[round(cen[:, 0].min(), 3), round(cen[:, 0].max(), 3)],
                y=[round(cen[:, 1].min(), 3), round(cen[:, 1].max(), 3)], mean_step=round(float(steps.mean()), 4))
        symmetric = 2*hx+1 == w and 2*hy+1 == h
        spacing = angles[1]-angles[0]
        require(out['hooks']['marker_at_centre'] == len(angles), f'hotspot off centre {w}x{h} scale {scale}')
        require(out['native']['mean_step'] > 0.5, 'control: the native draw no longer drifts')
        if symmetric:
            require(max(map(abs, out['hooks']['x']+out['hooks']['y'])) <= 0.26, f'centroid drift {w}x{h} scale {scale}')
            require(out['hooks']['mean_step'] < 0.02*spacing, f'centroid steps {w}x{h} scale {scale}')
        rows.append(dict(image=[w, h, hx, hy], scale=scale, flags=flags, **out))
    return rows


def clipped(r, images, scales, flags_set, angles, places, rects):
    r.hooks(True)
    n = differing = outside = 0
    for w, h, hx, hy in images:
        r.c.write(IMG, image(w, h, hx, hy))
        for scale in scales:
            for flags in flags_set:
                for a in angles:
                    for x, y in places:
                        r.clip(0, 0, W-1, H-1)
                        full = r.draw(a, scale, flags, x, y)
                        for x0, y0, x1, y1 in rects:
                            r.clip(x0, y0, x1, y1)
                            part = r.draw(a, scale, flags, x, y)
                            want = np.zeros_like(full); want[y0:y1+1, x0:x1+1] = full[y0:y1+1, x0:x1+1]
                            mask = np.ones_like(full, bool); mask[y0:y1+1, x0:x1+1] = False
                            n += 1; differing += int((part != want).any()); outside += int(part[mask].astype(bool).sum())
    r.clip(0, 0, W-1, H-1)
    require(outside == 0, f'{outside} pixels written outside the clip rectangle')
    require(differing == 0, f'{differing} clipped draws differ from the unclipped draw')
    return dict(cases=n, differing=differing, outside=outside)


def check(build, model, german, full):
    r = Renderer(build, model, german)
    shapes = [(41, 41, 20, 20), (81, 41, 40, 20), (40, 24, 20, 12)]
    angles = range(360) if full else range(0, 360, 3)
    cases = [(s, sc, f) for s in shapes for sc in (128, 256, 400) for f in ((0, 16, 32) if full else (0, 16))]
    result = dict(model=model, german=german, steadiness=steady(r, cases, angles))
    edges = [(0, 0, 170, 199), (150, 0, 319, 199), (0, 0, 319, 105), (0, 95, 319, 199),
             (0, 0, 162, 102), (157, 97, 319, 199), (60, 60, 161, 140), (159, 40, 260, 140)]
    result['edges'] = clipped(r, [(41, 41, 20, 20), (40, 24, 20, 12), (25, 61, 5, 40)],
                              (256, 180, 333) if full else (256, 333), (0, 16),
                              range(0, 360, 3 if full else 13), [(160, 100)], edges)
    places = [(160, 100), (5, 100), (315, 100), (160, 3), (160, 196), (2, 2), (318, 197)]
    result['wide'] = clipped(r, [(121, 81, 60, 40), (9, 5, 4, 2), (64, 33, 31, 17)],
                             (40, 96, 512, 900) if full else (96, 900), (0, 16, 32, 48) if full else (16, 48),
                             range(0, 360, 11 if full else 29), places, [(20, 15, 299, 184)])
    r.c.close()
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('build', type=Path, help='CD32 release build directory')
    p.add_argument('--output', required=True)
    p.add_argument('--german', action='store_true', help='the German executable')
    p.add_argument('--full', action='store_true', help='every angle and the larger edge sweep')
    a = p.parse_args()
    out = new_output(a.output); out.mkdir(parents=True)
    rows = [check(a.build, m, a.german, a.full) for m in ((2, 4) if a.full else (2,))]
    (out/'report.json').write_text(json.dumps(dict(complete=True, german=a.german, full=a.full, results=rows), indent=2)+'\n')
    print(json.dumps(dict(complete=True, german=a.german, models=[r['model'] for r in rows],
                          clipped=sum(r['edges']['cases']+r['wide']['cases'] for r in rows))))


if __name__ == '__main__':
    main()
