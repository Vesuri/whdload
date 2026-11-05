from pathlib import Path
import json, hashlib, subprocess
r=Path(__file__).resolve().parents[1]; repo=r.parents[1]
def read(p):return json.loads((r/p).read_text())
def sha(p):return hashlib.sha256((r/p).read_bytes()).hexdigest()
evidence={
 'state':'manifest/step5-c2-a1200-native-candidate.json',
 'clock_replay':'manifest/step5-c2-clock-replay.json',
 'elapsed':'tmp/step5/c2-a1200-candidate-elapsed/result.json',
 'fps':'tmp/step5/c2-a1200-candidate-fps300/result.json',
 'contact_state':'manifest/step5-c2-contact-a1200-baseline-candidate.json',
 'division_oracle':'tmp/step5/c2-div-oracle-a1200-1/result.json',
 'exit':'tmp/step5/c2-a1200-exit/result.json',
 'reload':'tmp/step5/c2-a1200-reload/result.json',
 'default_off':'manifest/step5-c2-default-validation.json',
}
for key,p in evidence.items():assert read(p)['status']=='passed',(key,p)
assert read(evidence['state'])['steps']==600
assert read(evidence['contact_state'])['steps']==100
assert read(evidence['exit'])['restored_division_signatures']==60
for arm in ('baseline','omitted'):
 p=f'tmp/step5/c2-a1200-{arm}-profile/audit.json';assert read(p)['status']=='passed';evidence[arm+'_profile']=p
p='tmp/step5/c2-contact-a1200-candidate-profile/audit.json';assert read(p)['status']=='passed';evidence['contact_dma']=p
p='tmp/step5/c2-contact-a1200-candidate-profile/debt.json';debt=read(p);assert debt['passed'];evidence['contact_debt']=p
baseline=read('tmp/step5/c2-a1200-baseline-profile/profile.json');candidate=read('tmp/step5/c2-a1200-omitted-profile/profile.json')
assert baseline['complete_updates']==candidate['complete_updates']==18
ms=candidate['mean_cycles']/14187580*1000;assert ms<=49.6
fps=read(evidence['fps']);assert fps['presented_fps']>=5.54 and fps['presentations']==300 and fps['untraced'] and fps['warp_start']==fps['warp_end']=='warp=0'
elapsed=read(evidence['elapsed']);assert elapsed['simulated_seconds']==60 and elapsed['error_percent']<=1 and elapsed['untraced'] and elapsed['warp_start']==elapsed['warp_end']=='warp=0'
unchanged={
 'tmp/build/step5-c1/020/candidate.slave':'101ae798084b5e647e9557f6c55a69a12eccc5ee24f86f2ceb58d9e6f704e0aa',
 'tmp/build/step5-c1/000/candidate.slave':'f527dc7d370d7681904d2af0de78b2911fa802614081dc55da6b4b4c06870eb8',
 'tmp/build/step5-b8-v3-source/lean/fine.slave':'158403173c1d01ffdf7d13d9d6d13ab453f9afab07336374f4c19a74f0b7c493',
 'tmp/build/release/FerrariFormulaOne.slave':'b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'}
for p,h in unchanged.items():assert sha(p)==h,p
assert hashlib.sha256((repo/'Games/FerrariFormulaOne_WHD.s').read_bytes()).hexdigest()=='88995624ab0cc80974109bfede29ff6aa7434cf9901933b1961cf87eda851761'
commit=subprocess.check_output(['git','rev-parse','134a18b'],cwd=repo,text=True).strip()
saving=100*(1-candidate['mean_cycles']/baseline['mean_cycles'])
metrics=dict(native_control_cycles=baseline['mean_cycles'],candidate_cycles=candidate['mean_cycles'],candidate_ms=ms,physics_saving_percent=saving,physics_gate_ms=49.6,presented_fps=fps['presented_fps'],fps_gate=5.54,presentations=300,fps_elapsed_seconds=fps['elapsed_seconds'],simulated_seconds=60,elapsed_seconds=elapsed['elapsed_seconds'],timing_error_percent=elapsed['error_percent'],contact_max_pending_ms=debt['max_pending_quanta']*100,contact_recovery_steps=debt['post_contact_recovery_steps'])
report=dict(status='passed_candidate',date='2026-10-13',commit=commit,scope='SPS 0481 PAL A1200 14 MHz 68EC020, 2 MiB Chip, no Fast; default-off coarse 100 ms candidate.',metrics=metrics,evidence=evidence,unchanged_artifacts=unchanged,artifact_sha256={v:sha(f'tmp/build/step5-c2/020/{v}.slave') for v in ('candidate','omitted','baseline','baseline-render','native')},limitations=['Physical input and full modal transitions remain outside demo-first candidate acceptance.','Ten forced wall penetrations, eleven native wall-handler entries; bounded observed debt is not a worst-case proof for all crashes.','VERIFY state-copy cost is excluded from lean capacity and FPS measurements. All 27 state blocks remain unchanged.','B7 experimental 768 KiB WHDLoad reservation retained; minimum-memory/production integration remains open.','C3 68000 capacity remains open; 200 ms gameplay fallback is not enabled or authorized. 030/040/060 analysis remains deferred.'])
(r/'manifest/step5-c2-validation.json').write_text(json.dumps(report,indent=2)+'\n')
p=r/'docs/STEP5_CAPACITY.md';doc=p.read_text().replace('11. **C2 – 68020 chip-only acceptance.**','11. **C2 – 68020 chip-only acceptance. Passed (candidate).**',1)
section=f'''

### C2 accepted: chip-only 68020 capacity and real presentation (2026-10-13)

Commit `{commit[:7]}`; aggregate `manifest/step5-c2-validation.json`.
The selected coarse candidate reuses **only B6 stage 1**, the audited 68020
native division call-site substitutions. Positive constant divisors use inline
DIVSL.L; variable divisors use the existing zero/overflow-compatible helper.
The existing signatures prove that outgoing CCR is overwritten before use.
No physics conversion, car-order change, additional B6 stage, or new rendering
optimization was needed. Installation is inside C1's interrupt-excluded patch
transaction and restoration ledger, before cache flush. The host supplies
`FF1_COARSE_NATIVE_EXACT` and `FF1_NATIVE_EXACT=1`; a compile-time guard requires
`FF1_COARSE_020`. The ordinary default remains off (CUSTOM2=0); the C2 runtime
control word exists for an equal-layout A/B. CPU-only allocations remain public.

| Gate / measurement | Equal-layout C1 control | C2 | Required |
|---|---:|---:|---:|
| Native all-car simulation, cycles/update | {baseline['mean_cycles']:.2f} | {candidate['mean_cycles']:.2f} | — |
| Simulation, ms/update at 14.18758 MHz | {baseline['mean_cycles']/14187580*1000:.4f} | {ms:.4f} | ≤49.6 |
| Actual presented FPS, untraced | Not used for the C2 gate | {fps['presented_fps']:.5f} | ≥5.54 |
| Actual elapsed for 60.000 s simulation | — | {elapsed['elapsed_seconds']:.6f} s | Within 1% |

Physics cost falls **{saving:.2f}%** in the matched 18-update capture, with
repeated unsuccessful pacing polls excluded, the first full update dropped,
and the same 125-step native warm-up/RNG control. Total, per-car and classify
analysers agree exactly; raw/normalized trace audits retain all cycle/register
records. The FPS gate counts **300 real publications** across
{fps['elapsed_seconds']:.6f} emulated seconds, at the same post-publication
boundary, warp off at both ends, without CPU trace or intermediate debugger
stops. The screenshot is taken after that window and was visually checked.
The independent 600-update elapsed window has {elapsed['error_percent']:.4f}%
error. VERIFY copying is not used to claim capacity or FPS.

Exact-state/replay: **600 consecutive steps** match an equal-layout unchanged
native full-render control over all **27 blocks / 29,722 bytes per step**.
No masks or exclusions were added. Only the established explicit native hunk
relocations and two RNG pointers are canonicalized. Both calendar and session
clocks advance exactly one tenth at every step. The native division guest oracle
passes **94,720 cases** (quotient/remainder and D2–D5 preservation, all 32 incoming
CCR values); outgoing-CCR equality is intentionally not claimed at these
CCR-dead call sites. Committed-source lean/VERIFY builds reproduce the measured
binaries exactly; both C2-disabled C1 CPU builds reproduce their prior hashes.

Contact gate: the established wall-input fixture applies ten penetrations at
completed steps 11–20; **eleven actual native wall-handler calls** are recorded.
One hundred contact-state records match exactly between native-arithmetic,
drawing-omitted control and optimized full-render candidate. The 100-field
full-render trace contains **17** retained complete updates (9–25), covering
all ten forced inputs and recovery; the ordinary matched A/B contains 18.
Actual producer/snapshot reconstruction gives a maximum completed-step pending
time of **{debt['max_pending_quanta']*100:.4f} ms**, returning below 100 ms
**{debt['post_contact_recovery_steps']} step** after the final forced input.
Every producer increment is retained, with no rebase or debt discard. This is
bounded debt for this observed contact episode, not a universal crash bound.
The full-render DMA audit passes: actual transfers and applicable pointers
remain in Chip memory, retaining the documented line-mode APT exception.

Lifecycle/default-off: native exit after ten steps restores **all 60 division
signature fragments** and releases both ledger owners. The bounded real native
unload/reload fixture moves the primary race allocation from `$186f60` to
`$1890d8`, restores the 1,350-byte ledger, rebinds and runs twenty fresh steps
without runtime errors. Four-profile controlled CUSTOM2=0 remains byte-exact
against the original release at native loops 125/150/175. Original source,
ordinary release and B8 fine artifact remain unchanged. Production integration,
minimum-memory and physical-input/full-modal acceptance remain open; the B7
experimental 768 KiB reservation is unchanged.

Reproduce with `build_step5_c2.py`, `capture_step5_c2_profile.py`, the three
existing profile analysers (`analyze_step5_c2_profiles.py` supplies matched
arguments and trace audit), `capture_step5_c2_fps.py`,
`capture_step5_c2_states.py` / `analyze_step5_c2_states.py`,
`analyze_step5_c2_clocks.py`, and `capture_step5_c2_elapsed.py`.
Contact, division, exit/reload and default-off fixtures have corresponding
`*_step5_c2_*` tools. Paths and hashes are in the aggregate; all harness/build
and measurement files remain ignored.

**Next: C3**, 68000 capacity ≤41.7 ms per native 100 ms update and ≥3.494 FPS.
C4 requires the user's agreement if C3 cannot meet its targets. C2 is complete
as a default-off candidate; step 5 and production integration remain open.
030/040/060 analysis remains deferred.
'''
if '\n### C2 accepted:' in doc:doc=doc.split('\n### C2 accepted:',1)[0].rstrip()
p.write_text(doc+section)
p=r/'manifest/project.json';project=json.loads(p.read_text())
status=f'C2 passed as default-off candidate on chip-only 68020: audited B6 division integration; {ms:.4f} ms/native 100 ms update (gate 49.6), {fps["presented_fps"]:.5f} actual FPS over 300 untraced presentations (gate 5.54). 600 exact native-state/clock records, elapsed error {elapsed["error_percent"]:.4f}%, 100 exact contact records, bounded contact debt, native exit/moved reload and four-profile CUSTOM2=0 pass. C1-disabled binaries, B8 and ordinary release unchanged. Next C3; step 5 and production integration remain open.'
project['step5_c2_status']=status;project['step5_c2_validation']='tmp/dev/manifest/step5-c2-validation.json';project['step5_c2_commit']=commit
project['step5_status']='S0/S2/S3/B3-B8/C1/C2 passed as candidates; S1 CCR diagnostic validated. '+status
project['next_steps'][0]='Step 5: C2 passed. Next C3 68000 capacity and real presented FPS.'
project['next_steps'][2]='C3 68000: <=41.7 ms per native 100 ms step and >=3.494 actual FPS. Re-profile before stacking changes; C4 200 ms fallback only with user agreement.'
project['performance_design']['validation']='B8 fine 020+Fast and C1/C2 coarse chip-only 020 passed as default-off candidates. Native 100 ms 68000 elapsed/state passes C1; C3 performance acceptance remains open. Production, physical-input and full-modal integration remains open.'
p.write_text(json.dumps(project,indent=2)+'\n');print(json.dumps(metrics,indent=2))
