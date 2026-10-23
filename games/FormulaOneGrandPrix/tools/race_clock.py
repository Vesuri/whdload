#!/usr/bin/env python3
"""Race progress against emulated time: how game time relates to fields on a machine.

  python3 tools/f1gp.py raceclock DIR     (a server command; see tools/f1gp.py)

Runs `quickrace`, then the race to the Non Championship Results screen in STEP-field
steps, counting fields from the quickrace stop (the first cockpit field).  After each step
it reads the frame pacer's words in hunk 0 (minimum fields, fields of the last frame's
work, field counter, frame count) and checks a screenshot for the results screen (and
the green light, which a step can miss).  DIR gets samples.json, the green and
results screenshots and every STEP-th screenshot.  It then opens Race Finishing Times
and saves it as times.png (the winner's time and the gaps, in game time).

Field counts need the harness's exact-fields and gapless-profile (checked by quickrace):
after a `fields` or `profile` stop, `monitor fields N` runs N fields and a one-field
screenshot trace one.
"""
import json, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401

STEP = 200
LIMIT = 60000              # fields after the race start before giving up
# RAM per named machine (AmigaXDev headless-fsuae.md): (base, KB) regions to search.
REGIONS = {
    '':           [(0, 512), (0xc00000, 1536)],
    'a500':       [(0, 512), (0xc00000, 512)],
    'a500-1.5m':  [(0, 512), (0xc00000, 1536)],
    'a500+':      [(0, 1024)],
    'a1200':      [(0, 2048)],
    'a1200-fast': [(0, 2048), (0x200000, 8192)],
    'a1200-030':  [(0, 2048), (0x200000, 8192)],
    'a1200-040':  [(0, 2048), (0x200000, 8192)],
    'a1200-060':  [(0, 2048), (0x200000, 8192)],
    'a3000':      [(0, 2048), (0x200000, 8192)],
}
# The pacer's minimum-field tables and the move.w after them, at hunk 0 $1262.
PACER_SIGNATURE = bytes.fromhex('000600060006000700070008000700' '0833f9')
PACER_TABLES = 0x1262
WORDS = 0x125a             # minimum, last work, counter, frame count


def find_hunk0(server, g):
    regions = REGIONS[os.environ.get('AMIGA_SETUP', '')]
    found = []
    for base, kb in regions:
        dump = os.path.join(server.run_dir, 'region.bin')
        g.cmd(f'dump binary memory {os.path.relpath(dump)} {base:#x} {base + kb * 1024:#x}',
              timeout=600)
        data = open(dump, 'rb').read()
        os.unlink(dump)
        # The loaded hunk's move.w after the tables is relocated: it addresses h0+$125E.
        # WHDLoad's PRELOAD copy of the file holds the unrelocated offset instead.
        at = data.find(PACER_SIGNATURE)
        while at >= 0:
            h0 = base + at - PACER_TABLES
            operand = struct.unpack_from('>I', data, at + len(PACER_SIGNATURE))[0]
            if operand == h0 + 0x125e:
                found.append(h0)
            at = data.find(PACER_SIGNATURE, at + 1)
    if len(found) != 1:
        raise RuntimeError(f'loaded pacer found {len(found)} times')
    return found[0]


def read_words(g, h0):
    for _ in range(3):                  # the stub occasionally answers a read with an error
        out = g.cmd(f'x/4hx {h0 + WORDS:#x}')
        words = out.split(':', 1)[1].split() if ':' in out else []
        if len(words) == 4 and all(w.startswith('0x') for w in words):
            return [int(w, 16) for w in words]
    raise RuntimeError(f'reading the pacer words: {out!r}')


def raceclock(server, g, rest):
    import f1gp
    out = os.path.abspath(rest.strip() or 'tmp/clock')
    os.makedirs(out, exist_ok=True)
    route = f1gp.quickrace(server, g, os.path.join(out, 'route.jsonl'))
    h0 = find_hunk0(server, g)
    bases = [h0]
    for _ in range(3):
        reply = g.cmd(f'x/wx {bases[-1]-4:#x}')
        bases.append(int(reply.split(':', 1)[1].strip(), 16)*4+4)
    meta = dict(setup=os.environ.get('AMIGA_SETUP', ''), h0=h0, hunk_bases=bases,
                step=STEP, route=route, status='INCOMPLETE', samples=[])
    meta_path = os.path.join(out, 'samples.json')
    json.dump(meta, open(meta_path, 'w'), indent=1)
    samples, field, frames, last, green = [], 0, 0, None, None
    while field < LIMIT:
        g.cmd(f'monitor fields {STEP}', timeout=1800)
        field += STEP
        minimum, work, counter, count = read_words(g, h0)
        if last is not None:
            frames += (count - last) & 0xffff
        last = count
        image = f1gp.screenshot(server, g)
        field += 1
        image.save(os.path.join(out, f'{field:06d}.png'))
        state = ('results' if f1gp.showing(image, 'results') else
                 'green' if f1gp.showing(image, 'green') else '')
        if state == 'green' and green is None:
            green = field
            image.save(os.path.join(out, 'green.png'))
        samples.append(dict(field=field, frames=frames, minimum=minimum, work=work,
                            counter=counter, state=state))
        meta.update(samples=samples, green=green)
        json.dump(meta, open(meta_path, 'w'), indent=1)
        if state == 'results':
            image.save(os.path.join(out, 'results.png'))
            break
    else:
        raise TimeoutError(f'no results screen within {LIMIT} fields')
    with f1gp.Input(g) as c:
        f1gp.click(c, f1gp.OK['times'])
        for _ in range(200):
            c.fields(25)
            image = f1gp.screenshot(server, g)
            if f1gp.showing(image, 'times'):
                image.save(os.path.join(out, 'times.png'))
                break
        else:
            raise TimeoutError('no finishing times screen')
    meta.update(green=green, results=field, samples=samples, status='COMPLETE')
    json.dump(meta, open(meta_path, 'w'), indent=1)
    fps = (samples[-1]['frames'] - samples[0]['frames']) * 50 / (samples[-1]['field'] - samples[0]['field'])
    return (f'results@{field} (fields after the quickrace stop, to {STEP}-field steps; green '
            f'seen at {green}); {samples[-1]["frames"]} frames, {fps:.2f} frames/s; h0 {h0:#x}')
