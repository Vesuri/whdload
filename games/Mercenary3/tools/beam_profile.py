#!/usr/bin/env python3
"""Elapsed time of chosen routines on any CPU, from beam positions at entry and return.

  SLAVE=tmp/build/Mercenary3.verify.Slave WHD_ARGS='CUSTOM1=131071' AMIGA_SETUP=a1200-030 \\
    python3 tools/beam_profile.py OUT.json 577be 5765e _savepresent ...

For the CPUs without an instruction profile (68030, 68040, 68060). Runs the standard route
(ROUTE as in route_profile.py) with a breakpoint at each root: a Disk.1 offset (hex), or a
slave symbol when SLAVE_LST names a vasm listing of the running slave (`vasm ... -L FILE`).
A root the slave copied to expansion memory (M1, S3, F2, F5; tools/relocation.py) is caught at both
its chip entry and its copy. At entry the tool reads the beam position (VPOSR/VHPOSR) and the
VERTB counter, then runs to the return address with the entry stack pointer, and reads them
again. Emulated time does not advance while the debugger holds the machine, so the elapsed
time includes interrupts but no probe overhead. Roots called inside another root's
measurement are not counted that time: probe nested routines in separate runs.

PROBE_FIELDS=FIRST:LAST probes only those route fields (default: all), advancing untraced before.
OUT receives the rows and a summary: per root, calls and milliseconds per published frame,
split into logic and presentation frames (the VERIFY build's P1 flag).
"""
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from relocation import DISK_DELTA, Map
from route_profile import ROUTE
from route_runtime import deadline, delta, output_path, session, snapshot, timeouts, word
from amigaxdev.input import Input

VERTB = 0x529f4
LINES, CLOCKS = 313, 227      # PAL long field, colour clocks per line


def reg(g, name):
    return int(re.search(r'\b0x([0-9a-f]+)', g.cmd('info registers ' + name)).group(1), 16)


def beam(g):
    v, h = word(g, 0xdff004), word(g, 0xdff006)
    return dict(field=word(g, VERTB), line=((v & 7) << 8) | (h >> 8), clock=h & 0xff)


def ms(a, b):
    """Milliseconds between two beam samples (20 ms per field)."""
    pos = lambda s: s['line'] * CLOCKS + s['clock']
    return (delta(b['field'], a['field']) + (pos(b) - pos(a)) / (LINES * CLOCKS)) * 20


def resolve(g, names):
    """{breakpoint address: root name}."""
    symbols = {}
    if os.environ.get('SLAVE_LST'):
        text = open(os.environ['SLAVE_LST'], encoding='latin1').read()
        symbols = {n: int(a, 16) for a, n in re.findall(r'^([0-9A-F]{8}) (_\w+)$', text, re.M)}
    # The VERIFY publication hook calls _pubcount; WHDLoad fills in ws_ExpMem (offset $20).
    base = None
    if word(g, 0x5a82e) == 0x4eb9 and '_pubcount' in symbols:
        base = ((word(g, 0x5a830) << 16) | word(g, 0x5a832)) - symbols['_pubcount']
    expmem = 0
    if base is not None:
        expmem = (word(g, base + 0x20) << 16) | word(g, base + 0x22)
    reloc = Map(expmem if expmem < 0x80000000 else 0)
    roots = {}
    for name in names:
        if name.startswith('_'):
            if base is None or name not in symbols:
                raise ValueError(f'{name}: needs SLAVE_LST and the VERIFY publication hook')
            roots[base + symbols[name]] = name
            continue
        chip = int(name.lstrip('$'), 16) - DISK_DELTA
        roots[chip] = name
        copy = reloc.to_copy(chip)
        if copy is not None:
            roots[copy] = name
    return roots, expmem


def main():
    out = output_path(sys.argv[1])
    names = [n.lower() if not n.startswith('_') else n for n in sys.argv[2:]]
    if not names:
        sys.exit('name at least one root')
    first, last = (int(x) for x in os.environ.get('PROBE_FIELDS', f'0:{sum(n for n, _ in ROUTE)}').split(':'))
    boot_timeout, run_timeout = timeouts()
    rows = []
    with session(boot_timeout) as (g, meta):
        flag = getattr(g, 'presentation_flag', None)
        roots, expmem = resolve(g, names)

        def arm():
            g.cmd('delete')
            for pc in roots:
                g.cmd(f'break *{pc:#x}')

        controls = Input(g)
        field, start, end = 0, None, None
        with deadline(run_timeout, 'beam route'):
            for n, held in ROUTE:
                for h in held:
                    controls.button(h, True)
                seg_end = field + n
                while field < seg_end:
                    if field < first or field >= last:
                        step = min(seg_end, first if field < first else seg_end) - field
                        controls.fields(step)
                        field += step
                        continue
                    if start is None:
                        start = dict(snapshot(g), beam=beam(g))
                        arm()
                    stop = min(seg_end, last)
                    mark = word(g, VERTB)
                    while field + delta(word(g, VERTB), mark) < stop:
                        g.cmd('continue', timeout=120)
                        pc = reg(g, 'pc')
                        if pc not in roots:
                            raise RuntimeError(f'unexpected stop at {pc:#x}')
                        before, extra = beam(g), word(g, flag) if flag else 0
                        sp = reg(g, 'sp')
                        ret = (word(g, sp) << 16) | word(g, sp + 2)
                        g.cmd('delete')
                        g.cmd(f'break *{ret:#x}')
                        while True:
                            g.cmd('continue', timeout=120)
                            if reg(g, 'pc') == ret and reg(g, 'sp') == sp + 4:
                                break
                        after = beam(g)
                        rows.append(dict(root=roots[pc], extra=extra, before=before, after=after,
                                         ms=ms(before, after)))
                        arm()
                    field += delta(word(g, VERTB), mark)
                    if field >= last and end is None:
                        g.cmd('delete')
                        end = dict(snapshot(g), beam=beam(g))
                for h in held:
                    controls.button(h, False)
                print(f'field {field}: {len(rows)} calls', flush=True)
        if end is None:
            g.cmd('delete')
            end = dict(snapshot(g), beam=beam(g))
    frames = delta(end['frames'], start['frames'])
    window = ms(start['beam'], end['beam'])
    summary = {}
    for name in names:
        r = [x for x in rows if x['root'] == name]
        logic = [x['ms'] for x in r if not x['extra']]
        extra = [x['ms'] for x in r if x['extra']]
        summary[name] = dict(calls=len(r), calls_per_frame=len(r) / max(frames, 1),
                             ms_per_frame=sum(logic + extra) / max(frames, 1),
                             share=sum(logic + extra) / window if window else 0,
                             logic_calls=len(logic), logic_ms_per_call=sum(logic) / len(logic) if logic else 0,
                             extra_calls=len(extra), extra_ms_per_call=sum(extra) / len(extra) if extra else 0)
    result = dict(meta, expmem=f'{expmem:#x}', roots=names, window_fields=[first, last],
                  frames=frames, window_ms=window, start=start, end=end, summary=summary, rows=rows)
    with open(out, 'x') as f:
        json.dump(result, f, indent=1)
    print(f'{meta["setup"]} {meta["whd_args"]}: {frames} frames in {window:.0f} ms '
          f'({frames * 1000 / window:.2f} fps)' if window else '')
    print(f'{"root":14} {"calls/fr":>8} {"ms/frame":>8} {"share":>6}  {"logic ms/call":>13} {"pres. ms/call":>13}')
    for name, s in summary.items():
        print(f'{name:14} {s["calls_per_frame"]:8.2f} {s["ms_per_frame"]:8.2f} {100 * s["share"]:5.1f}%  '
              f'{s["logic_ms_per_call"]:8.2f} ({s["logic_calls"]}) {s["extra_ms_per_call"]:8.2f} ({s["extra_calls"]})')


if __name__ == '__main__':
    try:
        main()
    except (TimeoutError, RuntimeError, ValueError) as error:
        sys.exit(f'beam_profile: measurement failed: {error}')
