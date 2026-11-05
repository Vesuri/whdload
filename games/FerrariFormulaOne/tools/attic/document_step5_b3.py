from pathlib import Path
import json
r=Path(__file__).resolve().parents[1];a=json.loads((r/'manifest/step5-b3-validation.json').read_text());assert a['status']=='passed'
p=r/'docs/STEP5_CAPACITY.md';s=p.read_text();s=s.replace('4. **B3 – Opponent bypass.**','4. **B3 – Opponent bypass. Passed (candidate).**')
s=s.replace('Every player hook gets a ≤ 8-cycle `tst.w $32fbc`\n   early-out to native code for opponents.','Player hooks use a `tst.w $32fbc`\n   native early-out for opponents (actual Chip-bus-inclusive guard cost is recorded below).')
fast=a['cycle_results']['a1200-fast'];chip=a['cycle_results']['a1200'];guard=a['schedule_audits']['a1200-fast']['mean_current_car_tst_cycles']
section=f'''

### B3 accepted: native opponents on the 100 ms pulse

**B3 passed as a default-off candidate.** Aggregate:
`manifest/step5-b3-validation.json`. Tracked implementation:
`Games/FerrariFormulaOne_Opponents.s` and the conditional `FF1_PLAN_B` paths in
`Games/FerrariFormulaOne_UpdateHooks.s`. The host must install the opponent
selector after the existing installers and flush the instruction cache.
The ordinary slave does not include or activate these modules.

On the selected 020 + Fast path, car 0 retains its converted 20 ms update.
Cars 7..1 execute native arithmetic in native order only on each fifth quantum.
The seven player/opponent pairs run every quantum; the 21 opponent/opponent
pairs run on that fifth quantum. Pointer-based cold writers use the actual
recipient rather than the stale loop index. Mixed contact resets the player's
longitudinal position/velocity/speed fractions from the native opponent value;
native lateral impulses retain the player's fractional tail. Opponent shadows
are neither consumed nor changed. Repair/refill and contact-counter callbacks
bypass player fractional work for opponents.

| Profile | S3 all-car cycles/quantum | B3 cycles/quantum | Saving | B3 active time |
| --- | ---: | ---: | ---: | ---: |
| 020, chip only (diagnostic) | {chip['s3_cycles']:,.2f} | **{chip['b3_cycles']:,.2f}** | {chip['saving_percent']:.2f}% | {chip['b3_cycles']/14187.58:.3f} ms |
| 020 + Fast (gating profile) | {fast['s3_cycles']:,.2f} | **{fast['b3_cycles']:,.2f}** | {fast['saving_percent']:.2f}% | {fast['b3_cycles']/14187.58:.3f} ms |

Fast worst rolling five-quantum average: **{fast['worst_rolling_five']:,.1f}**
against **200,000**; peak/pulse quantum: **{fast['peak']:,}** against **400,000**.
No abort threshold is exceeded. These pass B3, not B6's pulse/debt gate or B8's
rendered FPS gate. Chip-only measurements are diagnostic; its selected design
remains the native 100 ms coarse path.

Matched A/B: `capture_step5_profile.py` with the same pre-activation state at
completed loop 125, warp off. Exclude the first complete interval containing
installation, then compare 20 complete quanta (four native pulse periods).
The before/after trajectories necessarily differ after B3 activation; the
unchanged semantic inventory is exact at their common starting point. Run the
ownership, per-car and classify analysers on identical windows; all three
per-quantum totals agree exactly. Captures:
`tmp/step5/{{a1200,a1200-fast}}-b3-v4-matched-{{s3,b3}}`.

Unlike the old all-car diagnostic, B3 can reach the pacing wait. The analysers
now optionally exclude **only repeated unsuccessful scheduler polls**, retaining
the final successful due check and the rest of the loop. No simulation work is
removed. Guest VERIFY is off for capacity measurements; the emulator's
instruction trace supplies cycle attribution. The instruction audit confirms
7..0 on pulse quanta, only car 0 otherwise, exactly 28/7 pair bodies, no opponent
conversion/context helper calls, and zero native simulation blits.

The original ≤8-cycle TST figure was an instruction-cost estimate, **not the
observed elapsed cost**: `$32fbc` remains in Chip RAM. The final Fast trace
measures a mean **{guard:.2f} cycles** for that instruction including bus waits;
the distribution is retained in the schedule audit. The prescribed TST early-out
is implemented, and these costs are included in the unchanged 200,000/400,000
aggregate gates. B4 still owns player hook/context consolidation.

Final semantic gates, both profiles:

- VERIFY, lean and a separate native-instruction control agree at **101 exact
  checkpoints**, including all **20 opponent pulses**, across the full existing
  semantic inventory, gear, instrument phase/rates and flag counter. All seven
  fractional buffers agree too. No comparison masks were relaxed.
- The control saves native instruction windows before conversion installation,
  restores them while opponents execute, and reinstalls player hooks before
  car 0. Thus opponents execute the original code independently of the new
  bypass trampolines. It replays the same player trajectory; exact per-quantum
  comparison verifies that trajectory as well as every opponent's state.
- Final VERIFY arithmetic replay passes for 100 player updates: velocity,
  scalar feedback, position, heading, steering, wear/fuel, events, clocks,
  counters, boost/audio/gear and healthy recovery. Elapsed oracles confirm
  **2.000 simulated seconds, 100 quanta and 20 native pulses**.
- **112 forced contact cases per profile** cover all 28 pairs, both directions
  and both pulse phases. Native position, longitudinal/lateral velocity and
  speed results are exact against the native control. Only player fractions
  change; non-due opponent pairs are skipped. Lateral impulses are measured
  explicitly, preserving their fractional tails.
- **1,008 recovery/refill cases per profile**, including signed states, gates,
  race/session modes and 0/1/3 presentation passes, pass. Native opponent
  repairs leave dormant fractional wear/fuel slots unchanged.
- **128 contact-counter cases per profile** verify native opponent decrements
  and pulse-gated player decrements, without opponent trace callbacks.

The initial large native control exceeded chip-only loader memory: its boot
screen explicitly reported AmigaDOS error 103 before the game started. The
accepted control removes unused trace histories, retaining the same native
instruction restoration and state comparison. Failed boot evidence remains in
`a1200-b3-matrix-control-fine` and `a1200-b3-control-boot-diagnostic`. The first
contact oracle omitted the native lateral impulse; the corrected fixture records
and compares that field rather than masking it. Earlier captures are retained;
final acceptance uses v4 builds/captures and their recorded SHA-256 values.

With `FF1_PLAN_B` undefined, all six S3 VERIFY/lean 0/1/3 presentation binaries
remain byte-identical. Ordinary source/release hashes are unchanged, the mode
stays default-off, and ordinary CUSTOM2=0 remains legacy-exact. No full renderer,
physical-input, modal, rendered-FPS, 68000/coarse or 030/040/060 acceptance is
claimed here. Next: **B4**, player hook consolidation (player segment ≤50,000
Fast; re-profile rather than stacking changes at the stated abort threshold).
'''
marker='\n\n### B3 accepted: native opponents on the 100 ms pulse'
if marker in s:s=s[:s.index(marker)]
p.write_text(s+section)
p=r/'manifest/project.json';d=json.loads(p.read_text());status=f"B3 passed as default-off candidate. Fast {fast['s3_cycles']:.1f} -> {fast['b3_cycles']:.1f} cycles/quantum ({fast['saving_percent']:.2f}% saving); worst rolling five {fast['worst_rolling_five']:.1f}, peak {fast['peak']}. Both profiles pass exact 101-checkpoint native-opponent/VERIFY/lean comparison, elapsed/player replay, 112 contact, 1008 recovery and 128 counter cases. Ordinary source/release unchanged. Chip-only B3 is diagnostic only; selected coarse path unchanged. Next B4."
d['step5_b3_status']=status;d['step5_status']='S0/S2/S3/B3 passed as candidates; S1 CCR diagnostic validated. '+status;d['step5_b3_validation']='tmp/dev/manifest/step5-b3-validation.json';d['next_steps'][0]='Step 5: B3 passed. Next STEP5_CAPACITY.md B4 player hook consolidation on 020 + Fast (player segment <= 50,000 cycles; abort/re-profile if > 58,000).'
d['next_steps'][1]='20 ms path: B4 player hook consolidation, B5 020 helpers, B6 native exact-output work, B7 MEMF_PUBLIC placement, B8 opponent interpolation. Retain per-phase gates and matched oracles.'
p.write_text(json.dumps(d,indent=2)+'\n');print('Updated capacity plan and project manifest')
