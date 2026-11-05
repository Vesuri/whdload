from pathlib import Path
import json
r=Path(__file__).resolve().parents[1];root=r.parents[1];g=root/'Games/FerrariFormulaOne'
def read(p):return json.loads(p.read_text())
v=read(r/'manifest/render-h4-validation.json');assert v['status']=='passed'
p=read(r/'manifest/render-h4-performance.json');assert len(p['comparisons'])==12
m=read(r/'manifest/render-h4-matched-profile.json');b=read(r/'manifest/render-h4-build-audit.json')
table=['| Emulator / scene | FPS control → H4 | Mean ms control → H4 | p95 ms control → H4 |','|---|---:|---:|---:|']
for row in p['comparisons']:
 a,c=row['arms'].values();table.append(f"| {row['profile']} / {row['scene']} | {a['fps']:.3f} → {c['fps']:.3f} | {a['mean_ms']:.3f} → {c['mean_ms']:.3f} | {a['p95_ms']:.3f} → {c['p95_ms']:.3f} |")
text='''
## H4 accepted: batch demo text and remove duplicate clock writes (2026-10-15)

`RenderText.s` replaces the driving demo's 21 separate glyph operations with
one packed bitmap operation per destination. It predecodes the fixed label's
font columns but rebuilds its pixels from the live font on every draw. The
192-byte CPU workspace is public memory. After WaitBlit, it copies the packed
rows into the existing 1,020-byte Chip colour scratch; native `$24ae0` retains
shifts, masks, foreground/background minterms and first/second buffer order.
A final WaitBlit returns scratch to native ownership. H2's whole-overlay audit
establishes that the completed sprite cookie-cut is its only native data reader.
There is no new allocation, native patch site or interrupt ownership.
Changed label, position, style, view or unsupported font dimensions retain the
native text path.

The clock optimization applies during player driving as well as the demo.
H3 temporarily gives both native HUD pointer views the same back buffer.
`FF1RenderClockDigit` draws each digit once when those pointers are identical;
the native immediate second overwrite has the same source, coordinates and
colours, with no intervening writer. Its masked foreground/background operation
is idempotent. Different destinations and other native display modes retain
`$23288`. This never suppresses a later frame's draw: every clear, buffer swap,
font/value change and re-entry gets fresh pixels. No destination cache needs
to survive a view/menu/reload. The public reset table also clears the workspace.
Flag rendering is unchanged; it remains separate work for the next profile.

Fourteen complete matched endpoint draws cost **60.156836 → 55.786248 ms**,
a **4.370588 ms / 7.27%** reduction. The matched entry interval costs
**64.377998 → 60.080593 ms**. The demo label falls **7.245341 → 1.549847 ms**,
with **126 → 6** BLTSIZE operations. The clock falls **2.091870 → 1.153091 ms**,
with **42 → 21** operations. Beam waiting absorbs some primitive savings;
the reductions must not be summed and presented as additional whole-frame gain.
These endpoint fixtures are not ordinary-demo FPS measurements.

The equal-layout control disables both H4 operations with one immutable preset
byte. All 100 updates match all 27 semantic blocks and private fractions exactly.
Normal, grid and dense each pass 30 complete 754 x 576 RGB comparisons, without
cropping, masks or pixel tolerance. All retained PNG pixels are independently
rehashed. The first normal image run exposed an observer scheduling issue:
its two-field capture allowed the faster arm to skip updates 2, 11 and 27;
all common update images were exact. The corrected normal/dense sampling fixes
30 update numbers (1, 5, 10, …, 145), with no writes to game state and no change
to image equality. Grid's original 30 consecutive samples already passed.

The 48-field paired trace has 15 exact shared interior bitplane-DMA sequences;
the faster arm reaches one additional frame. Shared sequences align at zero,
with every transition retained. Native projection registers, clipping, colour
planes and clear destinations match. Both buffer banks and all observed safe
handover checks pass. All DMA stays Chip. The inherited **B8-PAL** diagnostic
pulse still changes scanline with timing, so identical full transitional RGB
fields are not claimed. H4 makes no palette change; cleanup remains separate.

The independent pixel model passes 400 random live-font/stride cases, and all
32 Boolean cases for clock overwrite idempotence. The complete emulator image
checks provide the native shift/mask check. Both 60-second clock errors remain
below 0.25%; the exact values are recorded below. Native F3 throttle/clutch,
coast/brake/restart/steering, F1 manual gears, and the 040/MMU/32 MiB control
configuration pass. Pause retains exact pending time; tow restores the owned
patch ledger, INTENA remains unchanged, and pit/menu/session re-entry clears
the H3/H4 workspaces before the fresh epoch. Both CUSTOM1 settings pass the
controlled CUSTOM2=0 exact-state gate on all four base profiles. The inherited
signature-failure path rejects a deliberately damaged signature before its hook
is installed. The 000 and chip-only 020 payloads remain byte-identical to H3.

The following are 300 complete warp-off intervals, with census-window boundaries
excluded. All twelve comparisons pass mean and p95 no-regression. These are
fresh H4 equal-layout baselines; do not combine their raw FPS with historical
H3 measurements from a different binary layout. All seven opponents remain in
the grid/dense fixtures and their completeness counter stays zero.

'''+ '\n'.join(table)+'\n\n'
for e in v['elapsed']:text+=f"60 simulated seconds, {e['arm']}: **{e['seconds']:.9f} s**, absolute error **{e['error_percent']:.6f}%**.\n"
text+='''
The accelerated timing profiles use the calibrated observer and explicit
real-frequency cycle settings: 030/50, 040/40 and 060/50, 8 MiB Fast. The
040/060 timing runs have MMU off; the functional 040/MMU/32 MiB check is separate.
These emulator measurements do not establish physical CPU rankings or a
complete human-driven race. The normal high-end target remains two PAL fields
(~25 FPS); the table records the actual outcome, not an assumed target pass.

'''
a=read(r/'tmp/step5/c4-q03-render-profile-a1200-fast-h4-candidate/audit.json')
assert a['start_snapshots_exact'] and a['end_snapshots_exact'] and a['all_dma_counts_and_bitplane_addresses_exact'] and a['field_cycles_exact']
text+='''The independent ordinary trace/census boots have identical complete start/end
Chip/Fast snapshots, scheduler contexts, every field cycle count, DMA counts
and displayed bitplane addresses. Coverage is 99.999993%, with one boundary
cycle unrecorded out of 13,641,792. All DMA addresses stay below $200000.

The fresh post-H4 ordinary trace has 12 complete draws averaging **59.186521 ms**
in its own scene; this is H5 input, not a paired saving against the older
ordinary captures. Remaining scene/HUD costs **17.330322 ms**, road
**13.460200 ms**, optional scene **7.901218 ms**, clear **5.289644 ms** and
beam wait **3.246725 ms**. The label is **1.868465 ms**, clock **1.177270 ms**.
There are **303.58 WaitBlit calls/draw** (1,340 busy / 2,303 idle across the
window), 78,396 CIA reads and **24.010989 ms/draw** inclusive waits. These wait
costs overlap the stage totals. Large caller totals are clear `$6b082` 3.037 ms,
bitmap `$24c28` 2.592 ms, road `$6ac16` 2.536 ms / `$6ac42` 2.303 ms and
bitmap `$24dc6` 2.300 ms. H5 should histogram actual primitive work and choose
bounded CPU alternatives; H1's discarded dispatch-only change stays removed.
'''

text+=f'''
The independently reproduced slave is {b['bytes']:,} bytes, SHA256
`{b['candidate_sha256']}`.
CUSTOM2 remains default-off. The delivered RC2 LHA is unchanged. Human full
races and real hardware remain deferred. **H5 is next**, using the fresh post-H4
profile for primitive selection; **B8-PAL** remains separate pre-package cleanup.

Local evidence: `tmp/dev/manifest/render-h4-validation.json`,
`render-h4-performance.json`, `render-h4-matched-profile.json`,
`render-h4-source-audit.json`, `render-h4-build-audit.json`,
`render-h4-text-model.json`, `render-h4-dma.json` and `render-h4-traces.json`.
Raw traces are compressed with verified decompressed hashes; harnesses and
fixture builds remain ignored. The earlier demo-only iteration and observer
sampling diagnostic remain separately labelled, not reused as final acceptance.
'''
q=g/'RENDERING_PLAN.md';s=q.read_text();assert '## H4 accepted:' not in s;s=s.replace('4. **H4 — Reduce repeated text/instrument bitmap work.**','4. **H4 — Reduce repeated text/instrument bitmap work: accepted.**').replace('**Next optimization: H4.**','**Next at the H3 checkpoint: H4 (now completed below).**');q.write_text(s+text)
summary=f'''\nH4 batches the demo label (126 → 6 blits) and removes the clock's immediate\nduplicate back-buffer overwrite (42 → 21 blits, including player driving).\nMatched draw cost falls 7.27% (4.371 ms). All twelve 300-presentation performance\npairs pass no-regression, with exact state/private fractions, 90 complete RGB\ncomparisons, elapsed, native controls, lifecycle, legacy and failure checks.\nSee RENDERING_PLAN.md for the FPS table and the inherited B8-PAL limitation.\n\nThe current H4 source independently builds to {b['bytes']:,} bytes, SHA256\n`{b['candidate_sha256']}`.\nCUSTOM2 remains default-off and RC2 remains unchanged. H5 is next; human races\nand physical hardware testing remain deferred.\n'''
q=g/'README.md';s=q.read_text().replace('The current H3 source','The accepted H3 source').replace('next optimization; human full races','next optimization at that checkpoint; human full races');q.write_text(s+summary)
q=r/'docs/STEP5_CAPACITY.md';q.write_text(q.read_text()+text)
q=r/'manifest/project.json';j=read(q);j['rendering_h4_status']='Passed: matched draw -4.370588 ms (7.27%), demo text 126 to 6 blits, duplicate clock 42 to 21; all 12 performance pairs, exact state/RGB, elapsed, controls/lifecycle, legacy and failure gates pass. B8-PAL remains separate; RC2 unchanged.';j['rendering_h4']='tmp/dev/manifest/render-h4-validation.json';j['next_steps']=['H5: choose measured CPU/blitter primitives from fresh post-H4 profile, then reassess IRQs.','B8-PAL: remove inherited unconditional COLOR00 diagnostic pulse in separate cleanup before successor package.','Human full-race playtesting and real hardware deferred; RC2 archive unchanged.'];q.write_text(json.dumps(j,indent=2)+'\n')
print('Documented H4')
