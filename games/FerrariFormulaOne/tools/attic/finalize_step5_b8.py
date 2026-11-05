from pathlib import Path
import json,hashlib,subprocess
r=Path(__file__).resolve().parents[1]
def read(p):return json.loads((r/p).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
refs={
 'state':'manifest/step5-b8-v3-state-validation.json',
 'elapsed':'manifest/step5-b8-v3-elapsed-validation.json',
 'replay':'manifest/step5-b8-v3-replay-validation.json',
 'pose':'tmp/step5/b8-pose-a1200-fast/result.json',
 'history':'tmp/step5/b8-history-a1200-fast/result.json',
 'ownership':'tmp/step5/b8-ownership-a1200-fast/result.json',
 'tow':'tmp/step5/a1200-fast-b8-v3-tow/result.json',
 'reload':'tmp/step5/b8-v3-reload-a1200-fast/result.json',
 'default_off':'manifest/step5-b8-default-validation.json',
 'logic':'tmp/step5/a1200-fast-b8-v3-control-profile/audit.json',
 'render_dma':'tmp/step5/a1200-fast-b8-v3-render-profile/audit.json',
 'fps100':'tmp/step5/a1200-fast-b8-v3-fps/result.json',
 'fps300':'tmp/step5/a1200-fast-b8-v3-fps300/result.json',
}
evidence={k:read(v) for k,v in refs.items()}
assert all(v['status']=='passed' for v in evidence.values())
debt=read('tmp/step5/a1200-fast-b8-v3-render-profile/debt.json');assert debt['passed']
logic=evidence['logic'];assert logic['cycle_gate'] and logic['worst_five']<=145600 and logic['peak']<=283750
fps=evidence['fps300'];assert fps['presented_fps']>=5.54 and fps['elapsed_seconds']>=20 and fps['untraced']
repo=r.parents[1];source=repo/'Games/FerrariFormulaOne_WHD.s';release=r/'tmp/build/release/FerrariFormulaOne.slave'
assert sha(source)=='88995624ab0cc80974109bfede29ff6aa7434cf9901933b1961cf87eda851761'
assert sha(release)=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
assert (r/'tmp/build/step5-b8-disabled/lean/fine.slave').read_bytes()==(r/'tmp/build/step5-b7-v3/lean/fine.slave').read_bytes()
commits=['81562229fba1d8430e29648a5f703f548abbd928','38b2c6150b277b4213dff3a32dce84cdf510adfc']
report=dict(status='passed_candidate',date='2026-10-13',scope='B8 default-off SPS 0481 candidate, 14.19 MHz 68020 + 4 MiB Fast, no-input demo. Full native drawing, 100 ms opponent-only render history, and unchanged 20 ms player/100 ms opponent simulation design. Step 5 is not complete.',commits=commits,evidence=refs,
 artifacts={v:dict(path=f'tmp/build/step5-b8-v3/{v}/fine.slave',sha256=sha(r/f'tmp/build/step5-b8-v3/{v}/fine.slave')) for v in ('lean','verify','lean-padded')},
 logic=dict(mean_cycles=logic['mean_cycles'],mean_ms=logic['mean_cycles']/14187580*1000,worst_five=logic['worst_five'],peak=logic['peak'],mean_gate=100000,five_gate=145600,peak_gate=283750,prior_b7_mean=51546.3,scope='Rendering omitted in the equal-layout control, history and all simulation-owned state work included; CPU tracing only observes the lean candidate, with no VERIFY guest records.'),
 presentation=dict(fps=fps['presented_fps'],mean_frame_ms=1000/fps['presented_fps'],frames=fps['presentations'],fields=fps['elapsed_fields'],elapsed_seconds=fps['elapsed_seconds'],gate_fps=5.54,untraced=True,warp=False,simulated_to_elapsed=(fps['end']['schedule_completed']-fps['start']['schedule_completed'])*.02/fps['elapsed_seconds'],max_recovery_quanta=max(x['quanta_to_below_one'] for x in debt['pulses'])),
 state_gate='Same 26 blocks, plus eight pit flags and all existing player fractional state: 101 checkpoints, omitted control/VERIFY/padded lean exact. B8 corrects omitted native wheel-rate/view/pit ownership in both arms; no new exclusion or masking. This is drawing independence, not preservation of the old B7 stale instrument rates.',
 dma=evidence['render_dma']['dma'],
 limitations=['Controlled step-1 RNG/countdown startup fixture remains in diagnostic candidates.','Candidate remains default-off; ordinary source/release unchanged. Experimental B7 768 KiB WHDLoad reservation remains.','Native tow-entry and unload/reload are bounded guest fixtures, not manual pit/save/load acceptance. Physical input and full modal acceptance remain pending.','Coarse C1-C3 and production integration remain open. 68000 200 ms fallback requires user agreement. 030/040/060 remain deferred.'])
(r/'manifest/step5-b8-validation.json').write_text(json.dumps(report,indent=2)+'\n')
p=r/'docs/STEP5_CAPACITY.md';s=p.read_text().replace('9. **B8 – Presentation.**','9. **B8 – Presentation. Passed (candidate).**',1)
s+='''

### B8 accepted: complete drawing and opponent render history (2026-10-13)

Commits `8156222` and `38b2c61`; aggregate:
`manifest/step5-b8-validation.json`. Ordinary source/release unchanged. The new
path remains default-off and confined to the selected 020 + Fast profile.

`FerrariFormulaOne_RenderPose.s` and `RenderHistory.s` retain two native 100 ms
opponent endpoints, then blend private render copies using elapsed sub-pulse
phase. Adjacent forward/backward section changes rotate the old endpoint into
the current section's basis using the native Q15 table; lap and heading wrapping
are handled explicitly. The player uses current state without this 100 ms delay.
Native projection writes only its usual rendering scratch; it never overwrites
live simulation poses. All new CPU data/code remain in the B7 public allocation.

`FullPresentation.s` retains the native road, cars, cockpit, instruments, text,
blitter waits and buffer publication. It includes the complete original slave
screen-pointer repair. Drawing runs only after simulation has caught up; it does
not discard debt. Native buffer-pointer views are saved/restored across each
presentation, allowing the existing broad exact-state inventory to remain exact.

The full-body audit completed S3 ownership: native wheel-rate calculation,
view-direction/recovery flag and pit-range flags now run in simulation, while
pit messages draw separately. Both B8 matched arms contain those corrections.
This is not a claim that B7's stale instrument rates were preserved. The exact
state gate has **no new exclusion or mask**: all prior 26 blocks plus eight pit
flags and all player fractional state agree at all 101 checkpoints for the
omitted control, VERIFY and equal-allocation lean arms.

Validated:
- 462 guest pose cases (signed limits, angles, curved sections, lap boundaries,
  alpha endpoints and source immutability); 288 wheel/view/pit ownership cases.
- History fixtures cover the 100 ms endpoints, intermediate blend, player bypass,
  explicit cut/tow invalidation, epoch changes and reseeding after reset.
- The installed native `$69496` tow hook clears populated history before its
  original position-writing body. Demo takeover changes `$1bee8/$1c1c2/$1c1c4`
  at resident `$236e8..$236fc`; the adapter detects that epoch change, including
  its following grid reset. New races/load clear private history through B7's
  explicit reset spans.
- Real native unload/reload with a deliberately moved race allocation
  (`$568970 -> $56ac80`): history becomes invalid before reload and is seeded
  again after re-entry; 130 native updates, no patch/binding/fallback errors.
- The unchanged elapsed/replay oracles pass: 100 updates, 20 native pulses,
  exactly 2.0 simulated seconds; 2.04325 elapsed seconds at the final checkpoint
  includes 43.25 ms pending after a drawing pass. No rebase or time loss.
- CUSTOM2=0 is exact against the original release under step-1 RNG/countdown
  control on 68000, A500 + Fast, chip-only 020 and 020 + Fast. Reservation and
  allocation size are matched. B8-disabled build is byte-identical to B7.

Matched lean simulation-only profile (same loop-132 anchor; 48 fields, first
complete update dropped, twenty updates retained): **52,650.25 cycles/update =
3.7110 ms**, vs B7 51,546.3. Worst rolling five **54,530.2**, peak **138,287**.
All retained gates pass. Player segment 21,003.15 cycles; its conversion helpers
3,637.4. Per-car, category and total analysers agree exactly. Raw/normalized
trace audit preserves all costs/registers across 3,826,795 instructions.
The approximately 1,104-cycle increase buys history capture and the missing
native state ownership; no abort threshold is reached.

Actual presentation gate: **300 buffer publications in 1,137 PAL fields =
22.77626 seconds: 13.17161 FPS / 75.92085 ms per frame**, exceeding 5.54 FPS.
Warp is off; no CPU trace or intervening debugger stop in this window. Endpoints
are the same instruction immediately after native buffer publication. 1,138
20 ms updates occur in that window (99.9286% simulated/elapsed ratio). The
shorter independent 100-publication capture measured 13.20646 FPS. Screenshots
at both endpoints show complete road, opponent cars and cockpit drawing.

A separate 48-field **full drawing** trace checks actual DMA, with 909,271 blitter
transfers plus copper/audio/sprite/bitplane transfers: all real DMA addresses and
applicable pointer registers remain Chip (maximum sampled pointer 368,310).
Raw/normalized costs/registers agree across 1,428,510 instructions; all three
analysers agree. Its combined simulation-plus-drawing cycles are not substituted
for the simulation-only gates; real presentation is gated by the measurement
above. Debt falls below one quantum within **1–3** completed simulation updates
of every sampled native pulse, without rebasing.

Two analyser assumptions were corrected for this new workload, with original
results retained as `*-initial-analyser.json`: line-mode BLTAPT is the signed
Bresenham error accumulator, not an address (confirmed by the local emulator's
blitter implementation); A/B are not DMA pointer checks in that mode. Every
actual DMA transfer is still checked. Debt is evaluated at completed simulation
before the optional drawing callback, retaining the next native-loop debt
separately: immediately starting another frame can add debt after catch-up.
Neither correction changes execution or relaxes the logic/FPS thresholds.

Rejected bring-up: v1 omitted the original repair's `EXT.L D1`, causing a bad
screen pointer on a later frame. v2 repaired that, then identified the two
presentation buffer-pointer views in the unchanged state inventory. v3 saves
and restores them and passes the full comparison. These failures are retained
separately; their measurements are not acceptance evidence.

Reproduction uses `build_step5_b8_source.py` (same bytes as frozen v3),
`capture_step5_b7_v2.py` for the matched checkpoint protocol,
`capture_step5_b8_profile.py` / `capture_step5_b8_render_profile.py` with the
existing total/per-car/classify tools, `debt_step5_b8.py`, and
`capture_step5_b8_fps300.py`. The precise paths/hashes and additional fixtures
are in the aggregate manifest. All harness/data/build products remain ignored.

**Next: C1**, native coarse 100 ms elapsed scheduling; then C2 chip-only 020 and
C3 68000 capacity. B8 is complete as a candidate; step 5, production integration,
physical-input/full-modal acceptance remain open. The 68000 200 ms fallback still
requires user agreement; 030/040/060 remain deferred.
'''
p.write_text(s)
p=r/'manifest/project.json';d=json.loads(p.read_text());status=f'B8 passed as default-off candidate. Full native drawing with opponent-only 100 ms render history; unchanged 26-block state gate plus pit flags, elapsed/replay, 462 pose and 288 ownership cases, tow/epoch/load reset, moved native unload/reload and four-profile controlled CUSTOM2=0 pass. Logic {logic["mean_cycles"]:.2f} cycles/update (3.7110 ms), worst five 54530.2, peak 138287. Actual untraced 300-presentation window: {fps["presented_fps"]:.5f} FPS / {1000/fps["presented_fps"]:.5f} ms, above 5.54 floor. Full-render DMA stays Chip and debt clears in 1–3 updates. Ordinary source/release unchanged. Next C1-C3; step 5 not complete.'
d['step5_b8_status']=status;d['step5_b8_validation']='tmp/dev/manifest/step5-b8-validation.json';d['step5_b8_commits']=commits;d['step5_status']='S0/S2/S3/B3/B4/B5/B6/B7/B8 passed as candidates; S1 CCR diagnostic validated. '+status
d['next_steps'][0]='Step 5: B8 passed. Next C1 native coarse 100 ms elapsed scheduling, then C2 chip-only 68020 and C3 68000 capacity.'
d['next_steps'][1]='020 + Fast presentation candidate passed; keep it default-off until production integration and remaining step-5 acceptance. Retain all exact-state, elapsed/replay, DMA and cycle/FPS gates.'
d['performance_design']['opponents']+=' B8 candidate now renders private interpolated opponent poses with 100 ms history, while the player uses current state; no authoritative pose swaps.'
p.write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(dict(status=report['status'],logic=report['logic'],presentation=report['presentation']),indent=2))
