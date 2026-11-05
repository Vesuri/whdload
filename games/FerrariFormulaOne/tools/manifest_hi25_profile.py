#!/usr/bin/env python3
# Index the hi25 high-end profile evidence into manifest/hi25-profile.json.
from pathlib import Path
import json,hashlib,collections
r=Path(__file__).resolve().parents[1];os=__import__('os');os.chdir(r)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
traces=json.loads(Path('tmp/hi25-trace-rows.json').read_text())
fps={}
for d in sorted(Path('tmp/step5').glob('c4-q03-h5-fps-*-hi25-*')):
 j=json.loads((d/'result.json').read_text())
 fps[d.name]={'fps':j['fps'],'mean_ms':j['mean_ms'],'p95_ms':j['p95_ms'],'intervals':dict(collections.Counter(j['interval_fields'])),'error':j['error'],'heavy_incomplete':j.get('heavy_incomplete'),'extra_args':j['extra_args'],'slave_sha256':j['slave_sha256'],'emulator_sha256':j['emulator_sha256'],'result_sha256':sha(d/'result.json')}
builds={b:sha(f'tmp/build/{b}/FerrariFormulaOne.slave') for b in ['render-hi25-solo','render-hi25-solo-nbi','render-hi25-grid-nbi','render-h5-grid','render-h5-dense','render-h5-matched']}
out={'date':'2026-10-15','head':'25ca4b9','plan':'tmp/dev/docs/HI25_PLAN.md','scope':'Short diagnostic profile of the high-end 020+Fast path on accelerated emulator profiles; fixtures and what-if builds are test-only. No game code change.',
 'emulators':{'observer':sha('tmp/step5-frame-observer-build/fs-uae'),'observer_040_060_trace_hook':sha('tmp/step5-frame-observer-040prof-build/fs-uae'),'hook':'barto cpu_profiler added around the opcode dispatch in m68k_run_3ce (040/060 cycle-exact loop)'},
 'blitter_model_note':'uae_cpu_cycle_exact=true does not set blitter_cycle_exact; "-bce" runs add --uae_blitter_cycle_exact=true.',
 'what_if_note':'-nbi builds write INTENA $0040 before every draw (fixture HeavyBegin); diagnostic only, no ownership/restore.',
 'builds_sha256':builds,'traces':traces,'fps_300':fps,
 'findings':['BLIT interrupt enabled on 030+/040/060 (INTENAR $67EC); ~100-120 L3 entries/field, ~37 us each; H5 020+Fast trace had $67AC.','Accelerated profiles run the blitter non-cycle-exact; cycle-exact adds 5-6 ms per frame.','Post-wait draw is blitter-bound: WaitBlit spin 24-60 ms/frame; ticks 0.8 ms each on 040.']}
Path('tmp/manifest/hi25-profile.json').write_text(json.dumps(out,indent=1)+'\n');print('written',len(fps),'fps rows',len(traces),'traces')
