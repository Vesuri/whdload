#!/usr/bin/env python3
"""Profile a scripted walk out of the prison cell on a cycle-exact machine.

  python3 tools/route_profile.py [OUT]       default OUT: tmp/prof/a1200-fast-route

Boots the shipped game with the native FS-UAE (AMIGA_SETUP, default a1200-fast; WARP=1,
DETERMINISTIC=1, JOY0=none), stops at the game's entry and traces the route below from there
in chunks of at most CHUNK fields, holding the port-1 joystick directions each segment lists.
Each chunk is reduced with amigaxdev.callprofile and deleted. OUT receives profile.pkl.gz
(the reduction), report.txt, route.json (the route, input log and machine), a screenshot of
each chunk's last field and sheet.png (all of them). Set KEEP_TRACE=1 to keep the chunks.
"""
import bisect
import collections
import hashlib
import json
import os
import signal
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev.callprofile import Reduction
from amigaxdev.gdbserve import Server
from amigaxdev.input import Input

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHIPPED = os.path.join(ROOT, 'tmp/game/Mercenary3_v1.2_0356/Mercenary3/Mercenary3.Slave')
# SLAVE= runs another build (amiga/run.sh copies it in); WHD_ARGS= passes WHDLoad options.
SLAVE = os.path.abspath(os.environ.get('SLAVE') or SHIPPED)


def slave_code(path):
    """The code hunk of a single-hunk slave file."""
    d = open(path, 'rb').read()
    return d[0x20:0x20 + 4 * int.from_bytes(d[0x1c:0x20], 'big')]


CODE = slave_code(SLAVE)
IS_SHIPPED = CODE == slave_code(SHIPPED)
# The slave's vertical blank wait (_waitvb): btst #0,$dff005 until set, then until clear.
WAITVB = bytes.fromhex('0839000000dff00567f6' '0839000000dff00566f6' '4e75')

# The game's entry: the slave jumps here once the game image is loaded and patched.
ENTRY = 0x4b100
# The game image: chip $5350.. is Disk.1 $9000.. (docs/internals.md).
IMAGE, IMAGE_END, DISK_DELTA = 0x5350, 0x5350 + 0x6d7b0, 0x3cb0
# The frame publication routine (Disk.1 $5E4B0..): it writes COP1LC, waits for the VERTB
# counter at chip $529F4 to change (the loop at $5A826), then counts the frame at $5A82E.
FRAME, FRAME_WAIT = 0x5a82e, (0x5a826, 0x5a82c)
# Main loop points (Disk.1 $5E992.., docs/internals.md): the loop head, each world tick, the
# first instruction after the tick loop, and the frame publication call.
MARKS = {'frame': FRAME, 'loop': 0x5a2e2, 'tick': 0x5a3b0, 'ticks_done': 0x5a3d4}
# Main loop call sites after the ticks (chip addresses of the call instructions) and their
# callees; the report times each site to the next mark.
CALLS = {0x5a3da: 0x5b678, 0x5a420: 0x59b94, 0x5a424: 0x59da0, 0x5a428: 0x56c6e,
         0x5a42c: 0x5213e, 0x5a432: 0x5a7a8, 0x5a436: 0x5ab90, 0x5a43a: 0x50408,
         0x5a46c: 0x42d14, 0x5a472: 0x42d18, 0x5a4a0: 0x5045e, 0x5a4cc: 0x5045e,
         0x5a4d6: 0x56e00, 0x5a51a: None, 0x5a520: 0x557d0, 0x5a524: 0x50408,
         0x5a52a: 0x556f6, 0x5a52e: 0x572fa, 0x5a532: 0x53b0e, 0x5a536: 0x509f2,
         0x5a53c: 0x51d2a, 0x5a542: 0x51dfc, 0x5a548: None, 0x5a54c: 0x5b774}
MARKS.update({f'site{a:05x}': a for a in CALLS})
# Shipped slave code offsets (whdload/original/Mercenary3.slave.asm), named in the report
# when the shipped slave runs.
SLAVE_SYMBOLS = {0x27c: '_dmaon', 0x28e: '_diskload', 0x298: '_patch_vertb',
                 0x2aa: '_patch_aud1', 0x2bc: '_int68', 0x2ce: '_checkkeyboard',
                 0x332: '_quit', 0x33e: '_loadgame', 0x390: '_savegame', 0x3ae: '_setsavename',
                 0x3ca: '_subd0', 0x3e8: '_waitvb'}
# Where WHDLoad keeps itself and the slave: fast RAM, or slow RAM on the A500 setups.
FAST = (0xc00000, 0xd80000) if os.environ.get('AMIGA_SETUP', 'a1200-fast').startswith('a500') \
    else (0x200000, 0xa00000)
slave_base = None

# (fields, joystick directions held), 500 fields (10 s PAL) from the game's entry. The door
# opens on the game clock; walking earlier reaches it while still closed ("LOCKED").
# ROUTE='F:EV+EV,F:,...'
# overrides it, for example ROUTE='250:,200:JOY2_UP,100:JOY2_RIGHT'.
ROUTE = [
    (175, []),                # the cell door starts opening at about field 200
    (185, ['JOY2_UP']),       # walk through it and out towards the mailbox
    (140, ['JOY2_RIGHT']),    # outside: turn right, rotating the view
]
if os.environ.get('ROUTE'):
    ROUTE = [(int(f), [e for e in evs.split('+') if e])
             for f, evs in (seg.split(':') for seg in os.environ['ROUTE'].split(','))]
CHUNK = int(os.environ.get('CHUNK', '50'))


def label(pc):
    if isinstance(pc, str):
        return pc
    if IMAGE <= pc < IMAGE_END:
        return f'D1:{pc + DISK_DELTA:05x}'
    if pc < 0x200000:
        return f'chip:{pc:06x}'
    if slave_base is not None and slave_base <= pc < slave_base + len(CODE):
        return f'slave:{pc - slave_base:04x}'
    if pc < 0xa00000:
        return f'fast:{pc:06x}'
    if pc >= 0xf80000:
        return f'rom:{pc:06x}'
    return f'{pc:06x}'


def slave_name(off):
    if not IS_SHIPPED:
        return ''
    start = max((o for o in SLAVE_SYMBOLS if o <= off), default=None)
    return f'{SLAVE_SYMBOLS[start]}+{off - start:x}' if start is not None else ''


def region(pc):
    if IMAGE <= pc < IMAGE_END:
        return 'game image (chip)'
    if pc < 0x200000:
        return 'other chip'
    if slave_base is not None and slave_base <= pc < slave_base + len(CODE):
        return 'slave (fast RAM)' if FAST[0] < 0xa00000 else 'slave (slow RAM)'
    if FAST[0] <= pc < FAST[1]:
        return 'other fast RAM (WHDLoad)' if FAST[0] < 0xa00000 else 'other slow RAM (WHDLoad)'
    if pc >= 0xf80000:
        return 'Kickstart ROM'
    return 'other'


def loop_split(red):
    """Cycles per main loop pass between its marks: before the ticks, the ticks, after them."""
    ev = [(n, p) for n, p, _ in red.events if n != 'frame']
    passes, cur = [], None
    for name, pos in ev:
        if name == 'loop':
            if cur and {'tick', 'ticks_done'} <= set(cur):
                passes.append(cur)
            cur = {'loop': pos, 'ticks': 0}
        elif cur is not None:
            if name == 'tick':
                cur['ticks'] += 1
                cur.setdefault('tick', pos)
            elif name not in cur:
                cur[name] = pos
    for a, b in zip(passes, passes[1:]):
        a['end'] = b['loop']
    passes = [p for p in passes if 'end' in p]
    if not passes:
        return []
    n = len(passes)
    pre = sum(p['tick'] - p['loop'] for p in passes) / n
    ticks = sum(p['ticks_done'] - p['tick'] for p in passes) / n
    post = sum(p['end'] - p['ticks_done'] for p in passes) / n
    nt = sum(p['ticks'] for p in passes)
    per_tick = sum(p['ticks_done'] - p['tick'] for p in passes) / max(nt, 1)
    # Cycles from each marked call site to the next mark: the call and the glue after it.
    seq = [(nm, p) for nm, p, _ in red.events if nm.startswith('site') or nm == 'loop']
    cost, cnt = collections.Counter(), collections.Counter()
    for (a, pa), (_, pb) in zip(seq, seq[1:]):
        if a.startswith('site'):
            cost[a] += pb - pa
            cnt[a] += 1
    sites = []
    for name, c in cost.most_common(8):
        site = int(name[4:], 16)
        callee = CALLS[site]
        sites.append(f'  {label(site):10} call {label(callee) if callee else "-":10} '
                     f'{c / n:12,.0f} per pass  ({cnt[name]} times)')
    return ['', f'Main loop passes {n} (complete, between loop-head marks), cycles per pass '
            '(interrupts included):',
            f'  before the ticks  {pre:12,.0f}',
            f'  world ticks       {ticks:12,.0f}  ({nt / n:.2f} ticks per pass, '
            f'{per_tick:,.0f} per tick)',
            f'  after the ticks   {post:12,.0f}  (frame publication, drawing, panel)',
            'Costliest call sites after the ticks (to the next marked site):'] + sites


def report(red, meta):
    tot = red.total() or 1
    pct = lambda c: f'{c / tot * 100:6.2f}%'
    nf = len(red.fields)
    lines = [f'Mercenary 3 route profile: {meta["setup"]}, {nf} fields '
             f'({nf / 50:.1f} s PAL) from the game entry',
             f'slave {meta["slave"]} ({meta["slave_sha256"][:12]}), WHDLoad options '
             f'"{meta["whd_args"]}"',
             f'traced cycles {tot:,} ({tot // max(nf, 1):,} per field)', '']
    nopc = sum(f['nopc'] for f in red.fields)
    gap = sum(f['gap'] for f in red.fields)
    lines += [f'CPU stopped (STOP) {pct(nopc)}', f'exception entry/exit {pct(gap)}', '',
              'Chip-bus DMA slots:']
    lines += [f'  {k:10} {v * 100:6.2f}%' for k, v in red.dma_shares().items()]

    regions = collections.Counter()
    for pc, c in red.self.items():
        regions[region(pc)] += c
    frames = [pos for name, pos, _ in red.events if name == 'frame']
    if len(frames) > 1:
        span = (frames[-1] - frames[0]) / (tot / nf)
        lines += ['', f'frames counted at {label(FRAME)}: {len(frames)}; '
                  f'{span / (len(frames) - 1):.2f} fields per frame, '
                  f'{(len(frames) - 1) / span * 50:.2f} fps over the window']
    lines += loop_split(red)
    waits = {'game: wait for the VERTB counter (' + label(FRAME_WAIT[0]) + ')':
             sum(red.self[pc] for pc in FRAME_WAIT)}
    if slave_base is not None:
        wv = CODE.find(WAITVB)
        spans = [('slave: _waitvb (called by _dmaon)', wv, wv + len(WAITVB))] if wv >= 0 else []
        if IS_SHIPPED:
            spans += [('slave: _subd0 raster delay', 0x3ca, 0x3e8),
                      ('slave: _checkkeyboard handshake', 0x2ce, 0x332)]
        for name, lo, hi in spans:
            waits[name] = sum(c for pc, c in red.self.items()
                              if slave_base + lo <= pc < slave_base + hi)
    lines += ['', 'Waits (self cycles):'] + [f'  {k:52} {pct(c)}' for k, c in waits.items()]
    lines += ['', 'Self cycles by region:']
    lines += [f'  {k:28} {pct(c)}' for k, c in regions.most_common()]

    # Self time by function: the nearest preceding call or interrupt entry.
    starts = sorted({fr if isinstance(fr, int) else fr[1]
                     for st in red.stacks for fr in st if not isinstance(fr, str)})
    funcs = collections.Counter()
    for pc, c in red.self.items():
        i = bisect.bisect_right(starts, pc) - 1
        funcs[starts[i] if i >= 0 else pc] += c
    incl = red.inclusive()
    lines += ['', 'Top functions by self cycles (function = nearest preceding call target):']
    lines += [f'  {label(f):14} self {pct(c)}  incl {pct(incl.get(f, 0))}'
              for f, c in funcs.most_common(30)]
    lines += ['', 'Top instructions by self cycles:']
    lines += [f'  {label(pc):14} {pct(c)}  {red.counts[pc]:>9,} executions  '
              f'{slave_name(pc - slave_base) if label(pc).startswith("slave") else ""}'
              for pc, c in red.self.most_common(30)]
    lines += ['', 'Inclusive call tree (children under 1% hidden):', red.tree(label, 0.01, 8)]
    return '\n'.join(lines) + '\n'


def locate_slave(g, out):
    """Find the live slave in fast (or slow) RAM. WHDLoad's file copy equals the file; the live copy
    matches its loader code but differs elsewhere (WHDLoad fills in _resload)."""
    global slave_base
    dump = os.path.relpath(os.path.join(out, 'fast.bin'), ROOT)
    g.cmd(f'dump binary memory {dump} {FAST[0]:#x} {FAST[1]:#x}', timeout=300)
    mem = open(dump, 'rb').read()
    os.unlink(dump)
    loader = int.from_bytes(CODE[0x18:0x1a], 'big')
    probe = CODE[loader:loader + 0x100]
    hits, i = [], mem.find(probe)
    while i >= 0:
        base = i - loader
        if base >= 0 and mem[base:base + len(CODE)] != CODE:
            hits.append(FAST[0] + base)
        i = mem.find(probe, i + 1)
    # A stale copy can remain in freed memory; the live one differs only in its filled-in data.
    diffs = {h: sum(a != b for a, b in zip(mem[h - FAST[0]:h - FAST[0] + len(CODE)], CODE)) for h in hits}
    print('slave candidates (differing bytes):', {hex(h): n for h, n in diffs.items()})
    if not hits or sorted(diffs.values())[:2].count(min(diffs.values())) > 1:
        raise RuntimeError(f'expected one live slave, found {diffs}')
    slave_base = min(hits, key=diffs.get)


def sheet(out, shots):
    from PIL import Image, ImageDraw
    ims = [Image.open(p).convert('RGB') for _, p in shots]
    w, h = ims[0].size
    W, H, cols = w // 2, h // 2, 4
    s = Image.new('RGB', (W * cols, (H + 14) * ((len(ims) + cols - 1) // cols)), 'white')
    for i, ((field, _), im) in enumerate(zip(shots, ims)):
        x, y = i % cols * W, i // cols * (H + 14)
        s.paste(im.resize((W, H)), (x, y + 14))
        ImageDraw.Draw(s).text((x + 2, y + 1), f'field {field}', fill='black')
    s.save(out)


def main():
    out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else
                          os.path.join(ROOT, 'tmp/prof/a1200-fast-route'))
    os.makedirs(out, exist_ok=True)
    os.chdir(ROOT)  # gdb splits paths at spaces: give it repo-relative ones
    env = dict(AMIGA_SETUP=os.environ.get('AMIGA_SETUP', 'a1200-fast'),
               FSUAE=os.environ.get('FSUAE') or os.environ['FSUAE_ARM'],
               WARP='1', DETERMINISTIC='1', JOY0='none')
    os.environ.update(env)
    server = Server('merc3', root=ROOT, profile_window=False)
    g = server.boot()
    log = []
    try:
        g.cmd(f'break *{ENTRY:#x}')
        print(g.cmd('continue', timeout=600), flush=True)
        g.cmd('delete')
        red, shots, field = Reduction(marks=MARKS), [], 0
        with Input(g, log=log.append) as controls:
            for fields, held in ROUTE:
                for name in held:
                    controls.button(name, True)
                left = fields
                while left:
                    n = min(CHUNK, left)
                    path = os.path.join(out, f'chunk-{field:05d}.bin')
                    reply = g.cmd(f'monitor profile {n} "" "{path}"', timeout=1800)
                    if not os.path.exists(path):
                        raise RuntimeError(f'no trace at field {field}: {reply}')
                    t = red.feed(path)
                    field += n
                    left -= n
                    png = os.path.join(out, f'field-{field:05d}.png')
                    open(png, 'wb').write(t.fields[-1].shot)
                    shots.append((field, png))
                    if os.environ.get('KEEP_TRACE') != '1':
                        os.unlink(path)
                    print(f'field {field}: {sum(f["total"] for f in red.fields[-n:]) // n:,} '
                          f'cycles/field', flush=True)
                for name in held:
                    controls.button(name, False)
        locate_slave(g, out)
        red.save(os.path.join(out, 'profile.pkl.gz'))
        meta = dict(setup=env['AMIGA_SETUP'], fsuae=env['FSUAE'].replace(os.path.expanduser('~'), '~'),
                    entry=f'{ENTRY:#x}', chunk=CHUNK,
                    slave_base=None if slave_base is None else f'{slave_base:#x}', route=ROUTE, input=log,
                    slave=os.path.relpath(SLAVE, ROOT), whd_args=os.environ.get('WHD_ARGS', ''),
                    slave_sha256=hashlib.sha256(open(SLAVE, 'rb').read()).hexdigest())
        json.dump(meta, open(os.path.join(out, 'route.json'), 'w'), indent=1)
        open(os.path.join(out, 'report.txt'), 'w').write(report(red, meta))
        sheet(os.path.join(out, 'sheet.png'), shots)
        print('wrote', out)
    finally:
        g.p.kill()
        # Kill only this run's emulator: the recorded pid, if it is still an fs-uae.
        pid = open(os.path.join(server.run_dir, 'fsuae.pid')).read().strip()
        comm = subprocess.run(['ps', '-o', 'comm=', '-p', pid], capture_output=True,
                              text=True).stdout
        if 'fs-uae' in comm:
            os.kill(int(pid), signal.SIGKILL)


if __name__ == '__main__':
    main()
