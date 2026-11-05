from pathlib import Path
import json,hashlib,subprocess
r=Path(__file__).resolve().parents[1];repo=r.parents[1]
def read(p):return json.loads((r/p).read_text())
def sha(p):return hashlib.sha256((r/p).read_bytes()).hexdigest()
evidence={};stages=[]
for stage in (1,2,3):
 n=600 if stage==3 else 100
 for kind,p in {'state':f'manifest/step5-c3-s{stage}-a500-native-candidate.json','clocks':f'manifest/step5-c3-s{stage}-clock-replay.json','elapsed':f'tmp/step5/c3-s{stage}-a500-candidate-elapsed/result.json'}.items():
  assert read(p)['status']=='passed';evidence[f's{stage}_{kind}']=p
 assert read(evidence[f's{stage}_state'])['steps']==n
 for arm in ('baseline','omitted'):
  p=f'tmp/step5/c3-s{stage}-a500-{arm}-profile/audit.json';assert read(p)['status']=='passed';evidence[f's{stage}_{arm}_audit']=p
 a=read(f'tmp/step5/c3-s{stage}-a500-baseline-profile/profile.json');b=read(f'tmp/step5/c3-s{stage}-a500-omitted-profile/profile.json')
 assert a['complete_updates']==b['complete_updates']==18
 stages.append(dict(stage=stage,before_cycles=a['mean_cycles'],after_cycles=b['mean_cycles'],before_ms=a['mean_cycles']/7093.79,after_ms=b['mean_cycles']/7093.79,saving_percent=100*(1-b['mean_cycles']/a['mean_cycles'])))
checks={'division_oracle':'tmp/step5/c3-div-oracle-a500-0/result.json','lookahead_oracle':'tmp/step5/c3-track-oracle-a500-1/result.json','trig_oracle':'tmp/step5/c3-trig-oracle-a500-1/result.json','contact_state':'manifest/step5-c3-contact-a500-baseline-candidate.json','exit':'tmp/step5/c3-s3-a500-exit/result.json','reload':'tmp/step5/c3-s3-a500-reload/result.json','default_off':'manifest/step5-c3-default-validation.json','contact_dma':'tmp/step5/c3-contact-a500-candidate-profile/audit.json'}
for k,p in checks.items():assert read(p)['status']=='passed',(k,p);evidence[k]=p
assert read(checks['contact_state'])['steps']==100
p='tmp/step5/c3-contact-a500-candidate-profile/debt.json';debt=read(p);assert debt['passed'];evidence['contact_debt']=p
p='tmp/step5/c3-s3-a500-fast-candidate/result.json';smoke=read(p);assert smoke['status']=='complete' and smoke['state']['error']==0 and smoke['state']['C1Completed']==21;evidence['a500_fast_smoke']=p
p='tmp/step5/c3-s3-a500-candidate-fps300/result.json';fps=read(p);evidence['fps']=p
assert fps['untraced'] and fps['warp_start']==fps['warp_end']=='warp=0' and fps['presentations']==300 and fps['end']['error']==0
assert fps['end']['C1Completed']-fps['start']['C1Completed']==300+fps['end']['C1Skipped']-fps['start']['C1Skipped']
assert fps['status']=='failed' and fps['presented_fps']<3.494 and stages[-1]['after_ms']>41.7
elapsed=read(evidence['s3_elapsed']);assert elapsed['untraced'] and elapsed['error_percent']<=1 and elapsed['simulated_seconds']==60
unchanged={'tmp/build/step5-c1/000/candidate.slave':'f527dc7d370d7681904d2af0de78b2911fa802614081dc55da6b4b4c06870eb8','tmp/build/step5-c1/020/candidate.slave':'101ae798084b5e647e9557f6c55a69a12eccc5ee24f86f2ceb58d9e6f704e0aa','tmp/build/step5-c2/020/candidate.slave':'5e30454e84e7d6c4ddb2ea71cb76bd35796c4450231d282cb394bbec52ccfb03','tmp/build/step5-b8-v3-source/lean/fine.slave':'158403173c1d01ffdf7d13d9d6d13ab453f9afab07336374f4c19a74f0b7c493','tmp/build/release/FerrariFormulaOne.slave':'b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'}
for p,h in unchanged.items():assert sha(p)==h,p
commits=[subprocess.check_output(['git','rev-parse',c],cwd=repo,text=True).strip() for c in ('771663c','eb61251','0a9dda0')]
metrics=dict(physics_ms=stages[-1]['after_ms'],physics_gate_ms=41.7,presented_fps=fps['presented_fps'],fps_gate=3.494,elapsed_seconds=elapsed['elapsed_seconds'],timing_error_percent=elapsed['error_percent'],contact_max_pending_ms=debt['max_pending_quanta']*100,contact_recovery_steps=debt['post_contact_recovery_steps'])
report=dict(status='implemented_capacity_not_met',date='2026-10-13',commits=commits,scope='SPS 0481 PAL A500 emulator, 7.09379 MHz 68000, 512 KiB Chip + 1.5 MiB Slow, no Fast. Native 100 ms candidate remains default-off.',stages=stages,metrics=metrics,evidence=evidence,reprofile='manifest/step5-c3-reprofile.json',unchanged_artifacts=unchanged,artifact_sha256={v:sha(f'tmp/build/step5-c3-s3/000/{v}.slave') for v in ('candidate','omitted','baseline','native')},decision='Planned C3 safe optimizations implemented and validated, but both capacity gates fail. Stop and request user agreement before C4; no 200 ms gameplay path has been implemented or enabled.',limitations=['Full physical input/modal and production/minimum-memory acceptance remain open.','B7 experimental 768 KiB WHDLoad reservation retained.','A500+Fast is an active smoke check, not a performance acceptance.','Contact debt is an observed forced wall episode, not a universal crash bound.','VERIFY copying excluded from all timing/FPS claims.','030/040/060 remain deferred.'])
(r/'manifest/step5-c3-validation.json').write_text(json.dumps(report,indent=2)+'\n')
rows='\n'.join(f'| {s["stage"]}: {name} | {s["before_ms"]:.4f} | {s["after_ms"]:.4f} | {s["saving_percent"]:.2f}% |' for s,name in zip(stages,('exact division','register lookahead','sin/cos addressing')))
section=f'''

### C3 implemented: correctness passed, capacity gates not met (2026-10-13)

Commits `{', '.join(c[:7] for c in commits)}`;
aggregate `manifest/step5-c3-validation.json`. **C3 is not performance-accepted.**
The planned 68000-safe work is implemented. Final re-profiling still misses both
targets, so no additional optimization changes or 200 ms conversions were stacked.
The candidate remains default-off; the next decision is user approval for C4.

| Matched stage, 18 native updates | Control ms/update | Candidate ms/update | Saving |
|---|---:|---:|---:|
{rows}

Each row is an equal-layout A/B at the same post-warm-up step count, with the
established RNG/countdown control. Stage 1 compares native arithmetic; stages 2
and 3 compare the preceding stage. Do not subtract across rows as though code
layout/bus phase were identical. Total/per-car/classify analysers agree exactly;
raw trace audits preserve all cycle/register records. Repeated unsuccessful
pacing polls and the first complete update are excluded, as in C1/C2.

The final **{metrics['physics_ms']:.4f} ms** exceeds the **41.7 ms** physics gate.
Actual rendering is **{fps['presented_fps']:.5f} FPS**, below **3.494 FPS**,
over **300 native publications / {fps['elapsed_seconds']:.6f} emulated seconds**.
The untraced window uses matching post-publication endpoints, warp off throughout,
and no intermediate debugger stops. Completed = presented + skipped accounting
is exact, excluding a hidden race reset. Its screenshot was inspected after the
window. This is elapsed 10 Hz physics; the native legacy loop ran physics only
as often as frames were completed. Capacity is therefore not inferred from the
old frame-rate alone.

Implementation:
- Stage 1 installs `FF1Divide000` with the original quotient, remainder, register
  and XNZVC contract, including zero divisor and signed wrap cases. The new
  `FF1_MATH_000_ONLY` option excludes 020 instructions; default math bytes stay
  unchanged. The 68000 guest oracle passes **94,720** comparisons.
- Stage 2 reuses the audited ten-sample register lookahead. Only the inspected
  caller's value contract is changed; alternate mode and count/segment boundary
  cases retain native execution. **1,772** native-value cases pass.
- Stage 3 uses 68000-safe indexed table addressing, with the original final
  shifts, D0, A0 and all CCR bits. **43,520** oracle comparisons pass; the exact
  64-byte tested helper block matches the candidate before explicit relocation.
- Blits remain outside the simulation update through the existing C1/S3 split.
  All new code/data retain public-memory ownership. Complete native signatures
  are checked before mutation; the existing ledger owns restoration and the
  host excludes interrupts and flushes caches around installation.

Every stage passes matched native-state and clock replay plus the 60-second lean
elapsed test before the next stage is applied. Intermediate state windows have
100 steps each; final acceptance testing compares **600 consecutive steps** across
all **27 blocks / 29,722 bytes per step** with the native full-render control.
No state mask/exclusion was added; only the established explicit relocations and
two RNG pointers are canonicalized. Both clocks advance exactly one tenth per
step. Final 60.000 simulated seconds take **{elapsed['elapsed_seconds']:.6f} s**
({elapsed['error_percent']:.4f}% error). VERIFY copying is excluded from capacity.

Contact/lifecycle regressions pass: 100 exact state records through ten forced
wall penetrations, actual native wall-handler entries confirmed; measured pending
time peaks at **{debt['max_pending_quanta']*100:.4f} ms**, returning below one
100 ms quantum {debt['post_contact_recovery_steps']} step(s) after the forced episode.
This reports the observed episode rather than inventing a new capacity gate.
Actual DMA and applicable pointers stay Chip (with the documented line-mode APT
rule). Native exit restores division, lookahead and trig signatures; actual
moved native unload/reload restores ledger ownership and resumes twenty updates.
An A500+Fast active smoke run completes twenty further 100 ms updates without
errors; it is not a separate performance acceptance. Four-profile controlled
CUSTOM2=0 remains exact at loops 125/150/175. C1 (both CPUs), C2, and B8 were
rebuilt and reproduce their accepted binaries exactly. Ordinary source/release
remain unchanged.

`manifest/step5-c3-reprofile.json` records the stop-point cost breakdown. Roughly
58.5k cycles/update remain in exact division helpers, 41.4k in native software
multiply and 53.6k in the car body; the remaining work spans contact, dynamics,
engine and native control code. The final step still needs another **20.46%**
reduction to meet 41.7 ms. No simple remaining item from C3's specified list has
been left unapplied; no universal impossibility claim is made.

Reproduction: `build_step5_c3_s1.py`, `build_step5_c3_s2.py`,
`build_step5_c3_s3.py`; corresponding `capture_step5_c3_s*_profile.py`,
state/clock/elapsed tools, the existing three profile analysers, and
`capture_step5_c3_fps.py`. Contact, helper oracles, exit/reload and default-off
have corresponding `*_step5_c3_*` tools. The aggregate retains paths/hashes;
harness, archives, builds and measurements remain ignored. Historical stage
source is preserved by the three cohesive commits.

**Decision required:** C4's 200 ms fallback may begin only with the user's
agreement. No such gameplay change is present. C3's implementation/evaluation is
finished, but the native 100 ms A500 capacity gate is **failed**, not waived.
Step 5/production acceptance remain open, including minimum-memory, full input
and modal testing. The experimental 768 KiB reservation is unchanged;
030/040/060 analysis remains deferred.
'''
p=r/'docs/STEP5_CAPACITY.md';doc=p.read_text().replace('12. **C3 – 68000 capacity.**','12. **C3 – 68000 capacity. Implemented; capacity gates not met.**',1)
if '\n### C3 implemented:' in doc:doc=doc.split('\n### C3 implemented:',1)[0].rstrip()
p.write_text(doc+section)
p=r/'manifest/project.json';project=json.loads(p.read_text())
status=f'C3 planned 68000-safe work implemented and committed; correctness passed, capacity NOT accepted: {metrics["physics_ms"]:.4f} ms/native 100 ms update >41.7, {fps["presented_fps"]:.5f} FPS <3.494. 600 exact native-state/clock steps, 100 contact steps, elapsed error {elapsed["error_percent"]:.4f}%, helper oracles, DMA, exit/moved reload, A500+Fast smoke and four-profile CUSTOM2=0 pass. Re-profile recorded. Default-off; user decision required before any C4 200 ms gameplay change.'
project['step5_c3_status']=status;project['step5_c3_validation']='tmp/dev/manifest/step5-c3-validation.json';project['step5_c3_commits']=commits
project['step5_status']='S0/S2/S3/B3-B8/C1/C2 passed as candidates; S1 CCR diagnostic validated. '+status+' Step 5 and production integration remain open.'
project['next_steps'][0]='C3 implemented/evaluated; A500 native 100 ms capacity gates failed. Obtain user agreement before C4 200 ms fallback; do not enable it implicitly.'
project['next_steps'][2]='Keep the C3 100 ms candidate default-off. Gates remain <=41.7 ms and >=3.494 FPS. Re-profile is recorded; next interval/design decision belongs to the user.'
project['performance_design']['validation']='B8 fine 020+Fast and C1/C2 coarse chip-only 020 passed as candidates. C3 68000 correctness passes, but 100 ms capacity/FPS gates fail. No 200 ms gameplay implementation/approval. Production, minimum-memory, physical-input/full-modal acceptance remains open.'
p.write_text(json.dumps(project,indent=2)+'\n');print(json.dumps(metrics,indent=2))
