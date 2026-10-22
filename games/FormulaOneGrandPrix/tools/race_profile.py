#!/usr/bin/env python3
"""Profile phases of the Quick Race: cycle-exact Barto traces, reduced chunk by chunk.

Capture (a server command, see tools/f1gp.py):
  python3 tools/f1gp.py raceprofile green|tow|follow DIR [FIELDS]
Report:
  python3 tools/race_profile.py report DIR

Each capture boots through `quickrace`, then finds its anchor field by field:
  green   first field with the start lights green
  tow     first field after green without the cockpit: the player's car has retired and the
          camera cuts to the marshals pushing it away ("Viewing Nigel Mansell")
  follow  first field, a lead after tow, with the green "Viewing" banner: the camera cuts to
          the competitor it then follows ("Viewing Riccardo Patrese")
The server holds the CPU from reset (tools/f1gp.py BOOT_BREAK), so every boot runs the same
race.  Each anchor is found after running a calibrated lead without polling, then polling
every field; a lead that overshoots (target already showing at the first poll) fails.
The window is the FIELDS fields after the anchor field.  Traces are taken CHUNK fields at
a time, reduced with amigaxdev.callprofile and deleted; DIR keeps the reduction, the chip
and fast RAM images, the first and last screenshots and meta.json.
"""
import bisect, collections, hashlib, json, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev import barto
from amigaxdev import callprofile
from amigaxdev.callprofile import Reduction

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, 'tmp/game/FormulaOneGrandPrix4Disk/data/f1gp')
CHUNK = 50                 # fields per trace file (about 7.5 MB per field on a1200-fast)
# Fields to run without polling before each anchor, after the previous one: race (the
# quickrace stop) -> green -> tow -> follow.  Calibrated on a1200-fast, each 50-100 fields
# short; RACE_LEADS=0,0,0 polls throughout (other machines; the follow lead must still pass
# the tow scene's own "Viewing" banner, so use RACE_LEADS=0,0,400 or so).
LEADS = (800, 1950, 400)
POLL_LIMIT = 6000
FAST = 0x200000            # Zorro II fast RAM base
FAST_KB = {'a1200-fast': 8192, 'a1200-030': 8192, 'a1200-040': 8192, 'a1200-060': 8192,
           'a3000': 8192}
HUNKS = (0, 2)             # f1gp's code hunks
# The frame pacer in hunk 0 (f1gp 582992 bytes): a busy-wait until the field counter that the
# VBL interrupt advances reaches the frame's minimum; FRAME_END runs once per frame.
FRAME_WAIT = (0x127c, 0x1282, 0x1288)
FRAME_END = 0x128c


class StackReduction(Reduction):
    """callprofile.Reduction with one call stack per CPU stack.  The game runs as a Kickstart
    1.3 task on its own stack and its interrupts on the supervisor stack; the shared reducer
    keeps one stack and never pops an interrupt frame once the task's SP is below it.  Here
    each instruction belongs to the context whose last SP is nearest (within STACK_SPAN),
    and an exception entry first pops that context's frames at or below its entry level."""
    STACK_SPAN = 0x4000

    def feed(self, trace):
        t = barto.load(str(trace)) if not isinstance(trace, barto.Trace) else trace
        if t.pc_base:
            raise ValueError('relative-PC traces (.pc-base) are not supported')
        d, u, cache = t.data, struct.unpack_from, {}
        ctxs = getattr(self, '_ctxs', None) or []   # [stack, sps, last sp]
        pend, pos, tallied, tally = self._pend, self.pos, self.tallied, self.tally
        stacks, selfc, counts, events = self.stacks, self.self, self.counts, self.events
        marks = {pc: name for name, pc in self.marks.items()}
        ctx = None
        for f in t.fields:
            off, end = f.insn_off, f.insn_end
            tot = nopc = gap = 0
            while off < end:
                pc = None
                while True:
                    v = u('<I', d, off)[0]
                    off += 4
                    if v >= 0xffff0000:
                        break
                    if pc is None:
                        pc = v
                c = 0xffffffff - v
                sp = u('<I', d, off + 60)[0]
                off += 68
                tot += c
                pos += c
                if pc is None or pc == 0x7fffffff:
                    key = ctx[0] if ctx else ()
                    if pc is None:
                        nopc += c
                        stacks[key + ('stop',)] += c
                    else:
                        gap += c
                        pend = 3
                        stacks[key + ('exception',)] += c
                    continue
                ctx = min(ctxs, key=lambda x: abs(x[2] - sp), default=None)
                if ctx is None or abs(ctx[2] - sp) > self.STACK_SPAN:
                    ctx = [(), (), sp]
                    ctxs.append(ctx)
                stack, sps = ctx[0], ctx[1]
                if pend == 3:
                    while sps and sp >= sps[-1]:
                        stack, sps = stack[:-1], sps[:-1]
                    stack, sps = stack + (('irq', pc),), sps + (sp,)
                else:
                    while sps and sp > sps[-1]:
                        stack, sps = stack[:-1], sps[:-1]
                    if pend == 1:
                        stack, sps = stack + (pc,), sps + (sp,)
                ctx[0], ctx[1], ctx[2] = stack, sps, sp
                if pc in marks:
                    events.append((marks[pc], pos - c, tallied))
                if pc in tally:
                    tallied += c
                selfc[pc] += c
                counts[pc] += 1
                stacks[stack] += c
                pend = callprofile._opkind(t, pc, cache)
            dma = collections.Counter(f.dma[i + 29] for i in range(0, len(f.dma), f.dma_size))
            self.fields.append(dict(cycles=f.cycles, idle=f.idle, total=tot, nopc=nopc, gap=gap,
                                    dma=dict(dma)))
        self._ctxs, self._pend, self.pos, self.tallied = ctxs, pend, pos, tallied
        return t


def cockpit(f1gp, image):
    return all(image.getpixel(p) == ((c >> 16) & 255, (c >> 8) & 255, c & 255)
               for p, c in f1gp.SCREENS['race'].items() if p != (100, 70))


def raceprofile(server, g, rest):
    import f1gp
    args = rest.split()
    if len(args) not in (2, 3) or args[0] not in ('green', 'tow', 'follow'):
        return 'usage: raceprofile green|tow|follow DIR [FIELDS]'
    phase, out = args[0], os.path.abspath(args[1])
    fields = int(args[2]) if len(args) == 3 else 500
    os.makedirs(out, exist_ok=True)
    leads = tuple(int(n) for n in os.environ['RACE_LEADS'].split(',')) \
        if os.environ.get('RACE_LEADS') else LEADS
    route = f1gp.quickrace(server, g, '')
    anchors, elapsed = {}, 0

    def anchor(name, lead, test):
        nonlocal elapsed
        if lead:
            g.cmd(f'monitor fields {lead}', timeout=1800)
            elapsed += lead
        for n in range(POLL_LIMIT):
            image = f1gp.screenshot(server, g)       # traces (runs) one field
            elapsed += 1
            if test(image):
                if n == 0 and lead:
                    image.save(os.path.join(out, f'overshot-{name}.png'))
                    raise RuntimeError(f'{name}: lead {lead} overshot the anchor')
                image.save(os.path.join(out, f'anchor-{name}.png'))
                anchors[name] = elapsed
                return
        raise TimeoutError(f'no {name} within {POLL_LIMIT} polls')

    anchor('green', leads[0], lambda im: f1gp.showing(im, 'green'))
    if phase in ('tow', 'follow'):
        anchor('tow', leads[1], lambda im: not cockpit(f1gp, im))
    if phase == 'follow':
        anchor('follow', leads[2], lambda im: f1gp.showing(im, 'viewing'))

    setup = os.environ.get('AMIGA_SETUP', '')
    fast_kb = FAST_KB.get(setup, int(os.environ.get('FAST_KB') or 0))
    if fast_kb:
        dump = os.path.join(out, 'fast.bin')
        g.cmd(f'dump binary memory {os.path.relpath(dump)} {FAST:#x} {FAST + fast_kb * 1024:#x}',
              timeout=600)
    fast = open(os.path.join(out, 'fast.bin'), 'rb').read() if fast_kb else b''

    red, digests = StackReduction(), []
    chunk = os.path.join(server.run_dir, 'chunk.bin')
    for start in range(0, fields, CHUNK):
        n = min(CHUNK, fields - start)
        reply = g.cmd(f'monitor profile {n} "" "{chunk}"', timeout=3600)
        t = barto.load(chunk)
        if len(t.fields) != n:
            raise RuntimeError(f'chunk at {start}: {len(t.fields)} fields, wanted {n}: {reply}')
        if start == 0:
            open(os.path.join(out, 'chip.bin'), 'wb').write(t.chip)
            open(os.path.join(out, 'first.png'), 'wb').write(t.fields[0].shot)
            h0 = locate(t.chip.ljust(FAST, b'\0') + fast, game_hunks())[0][0]
            red.marks = {'frame': h0 + FRAME_END}
            red.tally = {h0 + o for o in FRAME_WAIT}
        digests += [hashlib.sha1(f.shot).hexdigest()[:16] for f in t.fields]
        if start + n == fields:
            open(os.path.join(out, 'last.png'), 'wb').write(t.fields[-1].shot)
        # amigaxdev.callprofile finds JSR/BSR in t.chip for PCs below its length: make it a
        # flat image of chip RAM followed by fast RAM, so code in fast RAM is followed too.
        if fast:
            t.chip = t.chip.ljust(FAST, b'\0') + fast
        red.feed(t)
        os.unlink(chunk)
    red.save(os.path.join(out, 'profile.pkl.gz'))
    meta = dict(phase=phase, fields=fields, chunk=CHUNK, setup=setup, fast_kb=fast_kb,
                leads=leads, anchors=anchors, route=route, shot_digests=digests,
                fsuae=os.environ.get('FSUAE'), whd_args=os.environ.get('WHD_ARGS', ''))
    json.dump(meta, open(os.path.join(out, 'meta.json'), 'w'), indent=1)
    return f'{phase}: anchors {anchors} (fields after the quickrace stop); {fields} fields in {out}'


# -- report ------------------------------------------------------------------------------------

def game_hunks(path=GAME):
    """[(hunk, bytes, set of relocated byte offsets)] for f1gp's code and data hunks."""
    d = open(path, 'rb').read()
    u = lambda o: struct.unpack_from('>I', d, o)[0]
    first, last = u(12), u(16)
    p, i, hunks, cur = 20 + 4 * (last - first + 1), 0, [], None
    while p < len(d):
        t = u(p) & 0x3fffffff
        p += 4
        if t in (0x3e9, 0x3ea):
            n = u(p) * 4
            cur = [i, d[p + 4:p + 4 + n], set()]
            hunks.append(cur)
            p += 4 + n
        elif t == 0x3eb:
            p += 4
        elif t == 0x3ec:
            while (k := u(p)):
                for j in range(k):
                    o = u(p + 8 + 4 * j)
                    cur[2].update(range(o, o + 4))
                p += 8 + 4 * k
            p += 4
        elif t == 0x3f2:
            i += 1
        else:
            raise ValueError(f'hunk type {t:#x} at {p - 4:#x}')
    return hunks


def locate(memory, hunks):
    """hunk -> (load address, size): the copy whose unrelocated bytes match the file (90%:
    the game writes into its code hunks) and whose relocated longwords do not (WHDLoad's
    PRELOAD keeps the unrelocated file in memory too)."""
    bases = {}
    for h, data, rel in hunks:
        if h not in HUNKS:
            continue
        plain = [k for k in range(0, len(data), 7) if k not in rel]
        moved = sorted(rel)[::4]
        candidates = set()
        for start in range(0, len(data) - 32, len(data) // 16):   # probes across the hunk
            o = next(o for o in range(start, len(data) - 32, 2)
                     if not rel & set(range(o, o + 32)) and len(set(data[o:o + 32])) > 8)
            at = memory.find(data[o:o + 32])
            while at >= 0:
                candidates.add(at - o)
                at = memory.find(data[o:o + 32], at + 1)
        found = []
        for base in sorted(candidates):
            if base < 0 or base + len(data) > len(memory):
                continue
            same = sum(memory[base + k] == data[k] for k in plain)
            kept = sum(memory[base + k:base + k + 4] == data[k:k + 4] for k in moved)
            if same >= 0.9 * len(plain) and kept < 0.5 * len(moved):
                found.append(base)
        if len(found) != 1:
            raise RuntimeError(f'hunk {h}: {len(found)} matches')
        bases[h] = (found[0], len(data))
    return bases


def locate_kick(memory, path=None):
    """Load address of the KickEmu Kickstart 1.3 image ($KICK13, relocated with its .RTB), or
    None: the address whose sampled bytes match it best, if 80% do."""
    path = path or os.environ.get('KICK13') or os.path.expanduser(
        '~/.local/share/amiga/Kickstarts/kick34005.A500')
    rom = open(path, 'rb').read()
    candidates = collections.Counter()
    for o in range(0x100, len(rom) - 32, len(rom) // 64):
        if len(set(rom[o:o + 32])) > 8:
            at = memory.find(rom[o:o + 32])
            while at >= 0:
                candidates[at - o] += 1
                at = memory.find(rom[o:o + 32], at + 1)
    for base, _ in candidates.most_common(3):
        if base >= 0 and sum(memory[base + k] == rom[k] for k in range(0, len(rom), 97)) \
                >= 0.8 * len(range(0, len(rom), 97)):
            return base, len(rom)
    return None


def report(directory):
    meta = json.load(open(os.path.join(directory, 'meta.json')))
    red = StackReduction.load(os.path.join(directory, 'profile.pkl.gz'))
    memory = open(os.path.join(directory, 'chip.bin'), 'rb').read()
    if meta['fast_kb']:
        memory = memory.ljust(FAST, b'\0') + open(os.path.join(directory, 'fast.bin'), 'rb').read()
    bases = locate(memory, game_hunks())
    kick = locate_kick(memory)
    if kick:
        bases['kick'] = kick

    pacer = {bases[0][0] + o for o in FRAME_WAIT}

    def label(pc):
        if pc in pacer:
            return f'pacer h0+{FRAME_WAIT[0]:05x}'
        for h, (b, n) in bases.items():
            if b <= pc < b + n:
                return f'{h}+{pc - b:05x}' if h == 'kick' else f'h{h}+{pc - b:05x}'
        if pc >= 0xf80000:
            return f'rom:{pc:06x}'
        return f'{"chip" if pc < FAST else "fast"}:{pc:06x}'

    def frame_label(fr):
        if isinstance(fr, tuple):
            return 'IRQ ' + frame_label(fr[1])
        return fr if isinstance(fr, str) else label(fr)

    total = red.total()
    nf = len(red.fields)
    cyc = sum(f['cycles'] for f in red.fields)
    stop = sum(f['nopc'] for f in red.fields)
    gap = sum(f['gap'] for f in red.fields)
    d = meta['shot_digests']
    images = 1 + sum(d[i] != d[i - 1] for i in range(1, len(d)))
    lines = [f'# {meta["phase"]}: {nf} fields after the {meta["phase"]} anchor '
             f'({meta["setup"] or "default machine"})',
             f'anchors (fields after the quickrace stop): {meta["anchors"]}',
             'load addresses: ' + ', '.join(f'{h if h == "kick" else f"h{h}"} {b:#x}'
                                             for h, (b, _) in bases.items()),
             '',
             f'cycles per field {cyc / nf:.0f}; traced {total / cyc * 100:.2f}% of them',
             f'CPU stopped (no PC) {stop / total * 100:.2f}%; exception entry {gap / total * 100:.2f}%',
             f'distinct screenshots {images} in {nf} fields (any display change, not only frames)',
             'DMA slots: ' + ', '.join(f'{k} {v * 100:.1f}%' for k, v in red.dma_shares().items()),
             '']

    # Frames: one 'frame' event per pass through the pacer; between two of them, cycles in the
    # wait loop are waiting and the rest is the frame's work (interrupts included).
    ms = 20.0 / (cyc / nf)                       # ms per cycle at the PAL field rate
    ev = [(p, w) for name, p, w in red.events if name == 'frame']
    wait_total = red.tallied
    lines.append(f'frame pacer wait {wait_total / total * 100:.1f}% of all cycles; '
                 f'{len(ev)} frame ends in the window')
    if len(ev) >= 2:
        spans = [(b[0] - a[0], (b[0] - a[0]) - (b[1] - a[1])) for a, b in zip(ev, ev[1:])]
        def stats(xs):
            xs = sorted(xs)
            q = lambda f: xs[min(len(xs) - 1, int(f * len(xs)))]
            return (f'mean {sum(xs) / len(xs):.2f} p50 {q(0.5):.2f} p95 {q(0.95):.2f} '
                    f'max {xs[-1]:.2f}')
        lines += [f'{len(spans)} complete frames: {50 * len(spans) / (sum(s for s, _ in spans) * ms / 20):.2f} fps',
                  '  frame time ms  ' + stats([s * ms for s, _ in spans]),
                  '  work ms        ' + stats([w * ms for _, w in spans]),
                  '  fields/frame   ' + stats([s * ms / 20 for s, _ in spans]),
                  '  frames whose work exceeds 2 fields: '
                  f'{sum(w * ms > 40 for _, w in spans)}; 3 fields: {sum(w * ms > 60 for _, w in spans)}',
                  '']

    # Self time by function: each PC goes to the nearest preceding traced call target.
    starts = sorted({fr for st in red.stacks for fr in st if isinstance(fr, int)} |
                    {fr[1] for st in red.stacks for fr in st if isinstance(fr, tuple)})
    def owner(pc):
        i = bisect.bisect_right(starts, pc) - 1
        while i >= 0 and starts[i] in pacer:      # interrupt returns into the wait loop
            i -= 1
        if i >= 0 and label(starts[i]).split('+')[0].split(':')[0] == \
                label(pc).split('+')[0].split(':')[0] and pc - starts[i] < 0x4000:
            return starts[i]
        return pc
    by_fn = collections.Counter()
    for pc, c in red.self.items():
        by_fn[pacer and min(pacer) if pc in pacer else owner(pc)] += c
    region = collections.Counter()
    for pc, c in red.self.items():
        region[label(pc).split('+')[0].split(':')[0]] += c
    region['stop'] = stop
    region['exception'] = gap
    lines.append('Self cycles by region: ' + ', '.join(
        f'{k} {v / total * 100:.1f}%' for k, v in region.most_common()))
    lines += ['', '## Self cycles by function (entry = nearest preceding call target)',
              f'{"function":16} {"share":>7} {"ms/field":>9}']
    for pc, c in by_fn.most_common(30):
        lines.append(f'{label(pc):16} {c / total * 100:6.2f}% {c / nf * ms:9.3f}')
    lines += ['', '## Inclusive cycles by call target', f'{"function":20} {"share":>7}']
    for fr, c in red.inclusive().most_common(30):
        lines.append(f'{frame_label(fr):20} {c / total * 100:6.2f}%')
    lines += ['', '## Call tree (inclusive; children under 1% hidden)', red.tree(label=label, depth=7)]
    text = '\n'.join(lines) + '\n'
    open(os.path.join(directory, 'report.txt'), 'w').write(text)
    return text


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == 'report':
        print(report(sys.argv[2]), end='')
    else:
        sys.exit(__doc__)
