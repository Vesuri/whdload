from pathlib import Path
import json,hashlib,subprocess
r=Path(__file__).resolve().parents[1];repo=r.parents[1]
def read(p):return json.loads((r/p).read_text())
def sha(p):return hashlib.sha256((r/p).read_bytes()).hexdigest()
evidence={};metrics={}
for profile in ('a1200','a500'):
 checks={
 'timer':f'tmp/step5/c1-time-{profile}/result.json',
 'state':f'manifest/step5-c1-{profile}-native-candidate.json',
 'elapsed':f'tmp/step5/c1-{profile}-candidate-elapsed/result.json',
 'exit':f'tmp/step5/c1-{profile}-exit/result.json',
 'reload':f'tmp/step5/c1-{profile}-reload/result.json'}
 for k,p in checks.items():assert read(p)['status']=='passed',(profile,k,read(p).get('status'))
 assert read(checks['state'])['steps']==600
 e=read(checks['elapsed']);assert e['untraced'] and e['warp_start']==e['warp_end']=='warp=0' and e['error_percent']<=1
 profiles={}
 for arm in ('control','omitted','candidate'):
  p=f'tmp/step5/c1-{profile}-{arm}-profile'
  audit=read(p+'/audit.json');assert audit['status']=='passed' and audit['analyzer_totals_agree']
  profiles[arm]=read(p+'/profile.json');checks['profile_'+arm]=p+'/audit.json'
 for arm in ('omitted','candidate'):
  p=f'tmp/step5/c1-{profile}-{arm}-profile/debt.json';assert read(p)['passed'];checks['debt_'+arm]=p
 clock=7093790 if profile=='a500' else 14187580
 metrics[profile]=dict(simulated_seconds=e['simulated_seconds'],elapsed_seconds=e['elapsed_seconds'],error_percent=e['error_percent'],native_control_cycles=profiles['control']['mean_cycles'],scheduled_cycles=profiles['omitted']['mean_cycles'],scheduled_ms=profiles['omitted']['mean_cycles']/clock*1000,overhead_cycles=profiles['omitted']['mean_cycles']-profiles['control']['mean_cycles'])
 evidence[profile]=checks
assert read('manifest/step5-c1-default-validation.json')['status']=='passed'
assert read('manifest/step5-c1-clock-replay.json')['status']=='passed'
assert sha('tmp/build/release/FerrariFormulaOne.slave')=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
assert sha('tmp/build/step5-b8-v3-source/lean/fine.slave')=='158403173c1d01ffdf7d13d9d6d13ab453f9afab07336374f4c19a74f0b7c493'
commits=subprocess.check_output(['git','log','-3','--format=%H'],cwd=repo,text=True).splitlines()[::-1]
report=dict(status='passed_candidate',scope='SPS 0481 PAL no-input demo, native 100 ms step on chip-only 68020 and 68000. Separate CPU-specific default-off candidate artifacts; production integration and C2/C3 FPS/capacity remain open.',commits=commits,metrics=metrics,evidence=evidence,default_off='manifest/step5-c1-default-validation.json',clock_replay='manifest/step5-c1-clock-replay.json',artifacts={f'{arch}/{v}':sha(f'tmp/build/step5-c1/{arch}/{v}.slave') for arch in ('000','020') for v in ('candidate','omitted','control','native')},limitations=['Physical input and full modal workflows remain outside this demo-first acceptance; pause consumer hooks preserve timer debt and use the existing tested time module.','Native exit and moved unload/reload are bounded guest fixtures, not complete manual workflows.','WHDLoad reservation remains the B7 experimental 768 KiB; this does not establish the ordinary release minimum footprint.','VERIFY copies all 27 retained state blocks and is not used for capacity/timing measurements. No new state masks or exclusions.','C2/C3 frame-rate and capacity gates are not C1 acceptance. No 200 ms fallback or 030/040/060 analysis is enabled.'])
(r/'manifest/step5-c1-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(metrics,indent=2))

p=r/'docs/STEP5_CAPACITY.md';doc=p.read_text();doc=doc.replace('10. **C1 – Elapsed native step.**','10. **C1 – Elapsed native step. Passed (candidate).**',1)
section="""

### C1 accepted: elapsed native 100 ms stepping (2026-10-13)

Commits `{commits}`; aggregate `manifest/step5-c1-validation.json`.
The isolated candidate schedules the unchanged all-car native step at 100 ms,
with a native tenth pulse on every completed update. Physics/rates are not
converted. Admission is before the native input head, so each admitted step
retains native input sampling. Service remains bounded through the native loop;
drawing is skipped while another tick is due, and outstanding time is never
rebased or discarded to catch up. The private two-update service counter wraps
without dropping debt or bypassing native input.

`FerrariFormulaOne_Coarse.s` and `CoarseInstall.s` reuse the time module, S3/B8
simulation ownership, complete native renderer, and B7 public loader/bindings
and patch ledger. The time module's 100 ms branch is opt-in. Presentation uses
68000-safe calls/addressing in the coarse build; flags save with SR on 68000,
CCR on 68020. Both CPU-specific harness builds are candidates; a shipping
combined slave is still production integration. The ordinary source/release
are unchanged, and the B8 fine binary remains exactly
`158403173c1d01ffdf7d13d9d6d13ab453f9afab07336374f4c19a74f0b7c493`.

The existing matched protocol retains 125 native warm-up steps and the step-1
RNG/countdown control before activation. All gates below apply after activation,
not to title/menu startup. The timer producer cannot run until its context has been initialized; the
installation transaction keeps interrupts disabled until then. Reversible native pause edges use Pause/Resume; native
race exit and unload restore the patch ledger before overlay memory is freed.
CPU-only code, state, stack and ledger allocations retain MEMF_PUBLIC ownership;
original DMA resources remain Chip.

| Profile | Simulated | Actual emulated elapsed | Difference | Gate |
|---|---:|---:|---:|---:|
| Chip-only 68020 | 60.000 s | {e020:.6f} s | {p020:.4f}% | ≤1% |
| A500 68000 | 60.000 s | {e000:.6f} s | {p000:.4f}% | ≤1% |

These lean windows contain 600 updates, with real drawing, warp confirmed off at
both matched endpoints, no CPU trace and no intermediate debugger stops. A
single-field screenshot is taken only after the A1200 window. The first A1200
attempt was rejected because warp-off was still queued at its initial endpoint;
the accepted rerun advances to the next checkpoint and verifies warp=0 before
starting. Its simulated/elapsed gate is unchanged.

State/replay: on **both** CPUs, all **600 consecutive steps** agree with an
equal-layout native full-render control across the unchanged 26-block inventory
**plus all eight pit flags**. The verifier records 29,722 bytes per step; its
copying cost is excluded from the lean timing/profile gates. No block, byte or
new mask was removed. Address normalization uses the same explicit native hunk
relocations and two RNG pointers as B7. Both calendar and session clocks advance
exactly one tenth on every sampled step (599 tenths between records 1 and 600).

The initial comparison exposed only native buffer-pointer views and the native
drawing flag. C1 preserves their per-step values while physical publication
remains presentation-owned; the full exact-state gate then passes. Initial
failed evidence is retained under `c1-a1200-*-initial`. A separate short omitted
control comparison also passes; the final full native control is the stronger
gate and preserves native arithmetic, RNG order and all-car ordering.

| Matched lean simulation, eighteen retained updates | Native-step control | Elapsed scheduler | Elapsed ms/update |
|---|---:|---:|---:|
| Chip-only 68020 | {c020:.2f} cycles | {s020:.2f} cycles | {m020:.4f} |
| A500 68000 | {c000:.2f} cycles | {s000:.2f} cycles | {m000:.4f} |

Profiles use the same post-warm-up anchor and 100-field captures, with repeated
unsuccessful pacing polls excluded and the first complete update dropped.
`analyze_step5_profile.py`, `percar_step5_profile.py` and
`classify_step5_profile.py` agree exactly. Raw/normalized trace audits preserve
every cost/register record. Separate full-render traces check actual DMA and
applicable pointer registers (including the documented line-mode APT rule).
Debt is measured from actual timer snapshots at completed simulation, before
rendering; the final reports retain both that debt and next-loop debt.
These numbers establish C1 scheduling overhead, **not C2/C3 acceptance**. Those
phases still require their own capacity, contact and real presented-FPS gates.

Additional checks:
- Eleven time-module cases on both CPUs, including 100 ms service, wrap, early
  consume rejection, and the retained 20/200 ms arithmetic regressions. The
  200 ms arithmetic test does not enable or authorize a gameplay fallback.
- Real native exit after ten candidate steps restores code and releases both
  ledger owners. Bounded actual native unload/reload forces the primary race
  allocation to move; binding, fresh time initialization and twenty resumed
  coarse updates succeed with zero runtime errors, on both CPUs.
- Four-profile CUSTOM2=0 is exact against the original release at native loops
  125/150/175 with equal reservation/allocation and the established RNG control.
- B8 reproduction remains byte-exact. All local harness/build/data evidence is
  intentionally ignored; only the reviewed source modules are committed.

Scope limits remain: B7's experimental 768 KiB WHDLoad reservation; no minimum
memory or physical-input claim; pause edges are wired to the existing tested
timer but full interactive modal workflows remain open. 030/040/060 remain
deferred. The new mode remains **default-off**.

**Next: C2** chip-only 68020 capacity/FPS, then C3 68000 capacity/FPS. C1 is
complete within this candidate scope; step 5 and production integration remain
open. The 68000 200 ms fallback still requires the user's agreement.
""".format(commits=', '.join(x[:7] for x in commits),e020=metrics['a1200']['elapsed_seconds'],p020=metrics['a1200']['error_percent'],e000=metrics['a500']['elapsed_seconds'],p000=metrics['a500']['error_percent'],c020=metrics['a1200']['native_control_cycles'],s020=metrics['a1200']['scheduled_cycles'],m020=metrics['a1200']['scheduled_ms'],c000=metrics['a500']['native_control_cycles'],s000=metrics['a500']['scheduled_cycles'],m000=metrics['a500']['scheduled_ms'])
if '\n### C1 accepted:' in doc:doc=doc.split('\n### C1 accepted:',1)[0].rstrip()
p.write_text(doc+section)
p=r/'manifest/project.json';project=json.loads(p.read_text());status='C1 passed as default-off candidate: unchanged all-car 100 ms stepping, 600 consecutive exact native-state/clock records on A500 and chip-only 020; 60-second lean timing errors {:.4f}% / {:.4f}%; matched profile, DMA, exit/moved reload and four-profile CUSTOM2=0 pass. B8 binary and ordinary release unchanged. C2/C3 and production integration remain open.'.format(metrics['a500']['error_percent'],metrics['a1200']['error_percent'])
project['step5_c1_status']=status;project['step5_c1_validation']='tmp/dev/manifest/step5-c1-validation.json';project['step5_c1_commits']=commits;project['step5_status']='S0/S2/S3/B3-B8/C1 passed as candidates. '+status
project['next_steps'][0]='Step 5: C1 passed. Next C2 chip-only 68020 capacity/FPS, then C3 68000 capacity/FPS.'
project['next_steps'][2]='C2 chip-only 68020: <=49.6 ms per native 100 ms step and >=5.54 actual FPS; C3 68000: <=41.7 ms and >=3.494 FPS. C4 200 ms fallback only with user agreement.'
p.write_text(json.dumps(project,indent=2)+'\n')
