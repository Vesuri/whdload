from pathlib import Path
import json
r=Path(__file__).resolve().parents[1];g=r.parents[1]/'Games/FerrariFormulaOne';read=lambda name:json.loads((r/'manifest'/name).read_text())
v=read('render-h5-validation.json');assert v['status']=='passed';m=read('render-h5-matched-profile.json');perf=read('render-h5-performance.json');o=read('render-h5-oracles.json');build=read('render-h5-build-audit.json');wait=json.loads((r/'tmp/step5/c4-q03-render-profile-a1200-fast-h5-candidate/wait-analysis.json').read_text());bitmap=json.loads((r/'tmp/step5/c4-q03-render-profile-a1200-fast-h5-candidate/bitmap-analysis.json').read_text())
a=m['mean_draw_ms']['control'];b=m['mean_draw_ms']['candidate'];saving=100*(1-b/a)
table='| Emulator / scene | FPS control → H5 | Mean ms control → H5 | p95 ms control → H5 |\n|---|---:|---:|---:|\n'
for row in perf['comparisons']:
 x,y=row['arms'].values();table+=f"| {row['profile']} / {row['scene']} | {x['fps']:.3f} → {y['fps']:.3f} | {x['mean_ms']:.3f} → {y['mean_ms']:.3f} | {x['p95_ms']:.3f} → {y['p95_ms']:.3f} |\n"
otable='| Emulator | Native μs/glyph | CPU μs/glyph | Reduction |\n|---|---:|---:|---:|\n'
for row in o['comparisons']:
 x,y=row['arms'];otable+=f"| {row['profile']} | {x['us_per_glyph']:.3f} | {y['us_per_glyph']:.3f} | {row['saving_percent']:.1f}% |\n"
text=f'''
## H5 accepted: bounded CPU font glyphs (2026-10-15)

`RenderBitmap.s` replaces the native bitmap operation only for byte-aligned
8 x 8 glyphs from either live native font, with three destination planes and
48-byte destination rows in the driving pointer views. It reads each font row
once, then writes eight bytes per plane with the exact foreground/background
operation. Each selected glyph replaces three blits with 24 CPU byte writes.
Other sizes, shifts, source types, multi-plane sources and unsupported coordinates
retain the native routine. Road lines/fills and sprite colour operations remain
on the blitter. The post-H4 histogram, not processor speed alone, selected this
small class; it does not establish a general CPU/blitter crossover curve.

The already-owned driving path is separately covered by 268 full-plane/CCR
comparisons on 020, plus the actual rendering profiles.

The previous DMA is completed by native WaitBlit before reading the font or
writing destination pixels. Conditional native OwnBlitter/DisownBlitter remains.
The same KickEmu ownership implementation explicitly preserves its scratch
registers. No font/destination cache or new DMA allocation is introduced; the
CPU code is in the existing public/Fast payload. The existing hunk ledger owns
the six-byte entry patch and restores it on release. Both A500 and chip-only 020
payloads remain byte-identical to H4. The final path also clears X before the
native exit, matching the original final-plane subtraction; it never reads SR.

The equal-layout control validates the same entry signature but leaves that
entry untouched. All new hook/selection overhead is charged to the candidate.
The preset is the sole differing binary byte. An earlier dispatch-bearing
control was retained as a diagnostic, not reused as final acceptance.

Each CPU profile passes 268 directed native-versus-CPU comparisons of all 30,960
destination bytes and the complete CCR: all 64 foreground/background pairs,
both fonts and byte positions, screen edges, and 12 shifted/size fallback cases.
The independent bit-level model passes 3,072 whole-row cases. The benchmark
executes 20,000 glyph calls per arm, acquiring/releasing native ownership per
call, after two settled VBLs with warp off;
readback verifies the control's original entry and the candidate's hook.
VBL endpoint resolution is approximately 1.002 μs/glyph. These are calibrated
emulator results, not physical CPU rankings or predictions for larger bitmaps.
The actual matched driving trace selects seven clock glyphs per draw; their
CPU function mean is approximately 82 μs with ownership already held.

{otable}

The {m['matched_draws']} complete matched draws average **{a:.6f} → {b:.6f} ms**, a
**{a-b:.6f} ms / {saving:.2f}%** reduction. Whole-loop matched entry intervals are
**{m['whole_loop_mean_interval_ms']['control']:.6f} → {m['whole_loop_mean_interval_ms']['candidate']:.6f} ms**.
The shared interior bitplane-DMA sequence count is
{m['intermediate_field_pixels']['exact_contiguous_common']}, aligned at zero after
collapsing repeated identical fields. Native projection registers, clipping,
colour planes, clear destinations and safe buffer handovers remain exact.
Beam waiting absorbs some primitive savings; the draw result is not an assumed
whole-frame speedup.

All 100 simulation updates and private fractions match exactly. Normal, grid and
dense each pass 30 complete RGB images without pixel masks or tolerance. Both
60-second elapsed tests pass the 0.25% gate. All twelve 300-interval performance
pairs below pass mean and p95 no-regression; retain their fresh equal-layout
baselines rather than summing speedups across older binary layouts. Accelerated
profiles use the calibrated real-frequency emulator settings; the functional
040/MMU/32 MiB check is separate from MMU-off timing.

{table}

Native F3 throttle/clutch/coast/braking/restart/steering, F1 manual gears,
040/MMU/32 MiB controls, pause/tow/pit/menu/re-entry and patch restoration pass.
The new entry is verified after reload. The CPU-write audit matches every selected write to an actual byte bus write.
Matched-scene destinations are not fetched in the same field. Three ordinary
trace fields also update a visible HUD glyph, but all affected rows and planes
have already been fetched before any update (minimum margin 21,709 Chip slots).
No selected write overlaps the affected display fetch interval. Both CUSTOM1 settings retain the
controlled four-profile CUSTOM2=0 exact-state gate. A deliberately damaged
bitmap signature exits before installing its hook. The independent ordinary
trace/census audit retains exact full snapshots, contexts and DMA; all DMA
addresses stay in Chip memory.

The historical H4 dense run recorded 8.883 FPS; the fresh H5 control already
records 7.131 FPS before the H5 hook is installed. Their performance windows
start after 557 versus 695 simulation updates even though both warm up 100 draws.
All 30 shared normal/dense completed images and seven shared grid images match
at fixed updates across H4-candidate/H5-control. The live-physics performance
fixtures and binary layouts are not identical historical timing experiments;
the cause of that absolute-rate shift remains unassigned. Acceptance uses the
fresh native-entry control pair; historical raw FPS values are reported separately.
See `manifest/render-h5-historical-baseline.json`.

The fresh ordinary trace has {wait['calls_per_draw']:.2f} WaitBlit calls/draw,
{wait['inclusive_wait_ms_per_draw']:.6f} ms/draw inclusive waits, and
{wait['exclusive_ms_per_draw'].get('irq',0):.6f} ms/draw of interrupt-level instructions.
The remaining IRQ budget is not empty-queue BLIT service: INTENA bit $40 is
already clear at every captured field start and throughout all recorded CPU/
copper INTENA writes, including conflict records. The fine path therefore
already satisfies C4's interrupt-disable condition; no ownership port is needed.
IRQ ownership remains unchanged. The histogram leaves larger bitmap/road/sprite work
native; further optimization needs a new measured case rather than broader
unvalidated CPU thresholds. H1's discarded dispatch-only experiment stays absent.

The existing **B8-PAL** diagnostic COLOR00 pulse remains separate cleanup.
Exact bitplane sequences and completed RGB images do not claim identical full
transitional RGB fields while that timing-dependent pulse exists. No palette
masks or edits were used. The normal ~25 FPS target is not reached.

The independently reproduced slave is {build['bytes']:,} bytes, SHA256
`{build['slave_sha256']}`. CUSTOM2 stays default-off. RC2 LHA is unchanged;
no successor packaging or broad release qualification is claimed. Human full
races and real hardware remain deferred. H1–H5's implementation work is closed
(H1 discarded); B8-PAL cleanup and successor packaging remain separate work.

Local evidence: `manifest/render-h5-validation.json`, `render-h5-histogram.json`,
`render-h5-oracles.json`, `render-h5-matched-profile.json`,
`render-h5-performance.json`, source/build/model/DMA audits and compressed traces.
'''
for p in [g/'RENDERING_PLAN.md',r/'docs/STEP5_CAPACITY.md']:
 s=p.read_text();assert '## H5 accepted: bounded CPU font glyphs' not in s;p.write_text(s+text)
p=g/'RENDERING_PLAN.md';s=p.read_text().replace('**H5 — Choose CPU or blitter per measured primitive; then reassess IRQs.** If','**H5 — Choose CPU or blitter per measured primitive; then reassess IRQs: accepted.** If');p.write_text(s)
p=g/'README.md';s=p.read_text().replace('The current H4 source','The accepted H4 source').replace('RC2 remains unchanged. H5 is next; human races','RC2 remains unchanged. H5 was next at that checkpoint; human races');s+=f'''\nH5 draws bounded aligned 8x8 font glyphs with the CPU after native DMA\nsynchronization, retaining the general blitter fallback. Matched draw cost falls\n{saving:.2f}% ({a-b:.3f} ms). All twelve performance pairs pass mean/p95\nno-regression, with exact state, frames, pixels/CCR primitive oracles, elapsed,\ncontrols, lifecycle, legacy and signature-failure checks. See RENDERING_PLAN.md\nfor the measured results and scope. IRQ ownership is unchanged.\n\nThe current source independently builds to {build['bytes']:,} bytes, SHA256\n`{build['slave_sha256']}`. CUSTOM2 remains default-off and RC2 is unchanged.\nB8-PAL cleanup and successor packaging are separate work; human full races and\nreal hardware remain deferred.\n''';p.write_text(s)
p=r/'manifest/project.json';j=json.loads(p.read_text());j.pop('render_h5_status',None);j['rendering_h5_status']='Passed: bounded CPU 8x8 live-font glyphs; exact pixels/CCR, states/frames, elapsed,12 performance pairs, controls/lifecycle/legacy/fault gates. See render-h5-validation.json.';j['rendering_h5']='tmp/dev/manifest/render-h5-validation.json';j['next_steps']=['B8-PAL: remove inherited unconditional COLOR00 diagnostic pulse in separate cleanup before successor package.','Successor packaging/release qualification when requested; RC2 LHA unchanged.','Human full-race playtesting and real Amiga hardware remain deferred.'];p.write_text(json.dumps(j,indent=2)+'\n')
print('Documented H5 acceptance')
