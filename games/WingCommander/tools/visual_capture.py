#!/usr/bin/env python3
"""Check CPU-converted pixels against DMA-visible CHIP without a debugger."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import wc_run

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--emulator', required=True, type=Path)
    p.add_argument('--slave', required=True, type=Path)
    p.add_argument('--layout', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--frames', type=int, default=0, help='default: stop at Origin FX fade')
    p.add_argument('--expect-corruption', action='store_true')
    a = p.parse_args()
    out = a.output.resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():
        p.error('output must be a fresh directory below tmp/')
    meta = json.loads((a.emulator/'mmu-fix.json').read_text())
    binary = (a.emulator/'fs-uae').resolve()
    if not meta['audit'] or digest(binary) != meta['sha256']:
        p.error('requires an intact audited emulator build')
    build = json.loads((a.slave.parent/'build.json').read_text())
    if digest(a.slave) != build['sha256']:
        p.error('slave differs from its build manifest')
    layout = json.loads(a.layout.read_text())
    out.mkdir(parents=True)
    env = wc_run.run_env(out, FSUAE=str(binary),
               WC_VISUAL_OUT=str(out), WC_VISUAL_H0=format(layout['hunks'][0], 'x'),
               WC_VISUAL_H3=format(layout['hunks'][3], 'x'), WC_VISUAL_FRAMES=str(a.frames),
               SLAVE=str(a.slave.resolve()), AMIGA_SETUP='a1200-040',
               WHD_ARGS='CUSTOM1=0 CUSTOM5=0 CACHE DCACHE'+
               (' CUSTOM2=2 CUSTOM3=1 CUSTOM4=0' if build.get('direct_flight') else ''), DEBUG='0', WARP='0',
               DETERMINISTIC='0', FSUAE_QUIET='1')
    try:
        wc_run.launch(env)
        deadline = time.monotonic()+120
        while time.monotonic() < deadline:
            shots = list((wc_run.run_dir(env)/'shots').glob('*.png'))
            if (out/'done.txt').exists() and shots:
                break
            time.sleep(1)
        else:
            raise TimeoutError('scene not captured; verify layout matches this slave/setup')
    finally:
        wc_run.stop(env)
    rows = [line.split() for line in (out/'frames.txt').read_text().splitlines()]
    assert rows, 'no conversion observations'
    if build.get('direct_flight'):
        assert any(int(r[3]) == 200 for r in rows), 'flight converter not observed'
    assert all(int(r[7], 16) & 0x80008000 == 0x80008000 for r in rows), 'caches were not enabled'
    assert all(int(r[4]) == 0 for r in rows), 'CPU converter output differs'
    # Independently decode saved planar snapshots, rather than trust only the C++ counters.
    for source in out.glob('*-source.bin'):
        index = int(source.name.split('-')[0])
        pixels = source.read_bytes()
        stride = len(pixels)//8
        for kind, column in [('plane', 4), ('rawplane', 5)]:
            plane = (out/f'{index}-{kind}.bin').read_bytes()
            differences = sum(pixel != sum(((plane[b*stride+i//8] >> (7-i%8)) & 1) << b
                                          for b in range(8)) for i, pixel in enumerate(pixels))
            assert differences == int(rows[index][column]), 'independent decoder disagrees'
    bad = sum(int(r[5]) != 0 for r in rows)
    result = dict(frames=len(rows), bad_dma_frames=bad, max_dma_pixels=max(int(r[5]) for r in rows),
                  cpu_mismatches=0, heights=sorted({int(r[3]) for r in rows}),
                  emulator_sha256=meta['sha256'], fixed=meta['fixed'], slave_sha256=digest(a.slave),
                  screenshots=[str(s.relative_to(out)) for s in shots])
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    assert bool(bad) == a.expect_corruption, 'unexpected DMA pixel result'


if __name__ == '__main__':
    main()
