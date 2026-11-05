from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parents[1];repo=r.parents[1]
def read(p):return json.loads((r/p).read_text())
def write(p,j):(r/p).write_text(json.dumps(j,indent=2)+'\n')
profiles=['a500','a500-fast','a1200','a1200-fast']
b=read('tmp/build/production/build.json');sha=b['sha256']
timing={p:read(f'tmp/step5/c4-q03-production-timing-{p}-candidate/result.json') for p in profiles}
modal={p:read(f'tmp/step5/c4-q03-production-live-{p}-candidate/result.json') for p in ['a500','a1200-fast']}
options={p:read(f'tmp/step5/c4-q03-production-custom1-zero-{p}-candidate/result.json') for p in ['a500','a1200','a1200-fast']}
faults={p:read(f'tmp/step5/c4-q03-production-fault-{p}-candidate/result.json') for p in ['a500','a1200-fast']}
for group in [timing,modal,options,faults]:
 for v in group.values():assert v['status']=='passed'
for group in [timing,modal,options]:
 for v in group.values():assert v['slave_sha256']==sha
state={p:read(f'manifest/production-state-{p}.json') for p in profiles};assert all(v['status']=='passed' for v in state.values())
frames=read('manifest/production-frames.json');assert all(v['exact'] for v in frames.values())
assert read('manifest/production-coarse-identity.json')['status']=='passed'
assert read('manifest/step5-production-default-validation.json')['status']=='passed'
assert read('manifest/production-build-audit.json')['status']=='passed'
pal=read('tmp/step5/production-pal-gate/result.json');assert pal['status']=='passed' and pal['slave_sha256']==sha
cycles={a:read(f'tmp/step5/c4-q03-production-profile-{a}-a1200-fast-candidate/audit.json') for a in ['accepted','production']};assert all(v['status']=='passed' and v['cycle_gate'] for v in cycles.values());assert cycles['production']['worst_five']<=145600
p='manifest/production-integration.json';j=read(p);j.update(status='passed',phase='Production integration accepted in the documented SPS 0481 PAL emulator scope',gates_remaining=[],slave_sha256=sha,bytes=b['bytes'],timing=timing,matched_state=state,frames=frames,modal=modal,custom1_zero=options,failure_routes=faults,pal_rejection=pal,cycles=cycles,build_audit='manifest/production-build-audit.json',coarse_identity='manifest/production-coarse-identity.json',disabled_gate='manifest/step5-production-default-validation.json',release_ready=False)
j['limitations']=['Default-off CUSTOM2=0; enabled SPS 0481 PAL only. Irek retains original route but is not runtime qualified.','Minimum memory, both CUSTOM1 disabled-mode option variants/reloads, wider tracks/gameplay/save-load, runtime versions/cache variants and human/hardware handling remain release qualification.','030/040/060 analysis deferred. C4-T01 micro targets remain unmet; P01/P02 accepted under user-selected same-workload no-regression gate.','Combined 260292-byte slave reserves 768 KiB expansion plus Chip and host overhead; original minimum-memory equivalence is not claimed.']
j['evidence_scope']={'state':'100 updates x 27 complete blocks on all four profiles, plus fine fractions. Final coarse payloads identical to the passing fixture except explicit host linkage immediates; fine rerun on final source. No state-field masking.','frames':'30 exact whole RGB images per engine; fine endpoint poses controlled equally. Fine complete second scanout resolves partial-field differences without debugger writes or pixel masking.','cycles':'48-field lean simulation-only matched traces, 20 complete updates after dropping installation interval. All raw/normalized costs, registers and DMA unchanged; per-car/classify totals agree. Disabled trap-address range is not proof of zero traps. Emitted 020 SR-save search is separately clear.','fps':'300 presentations with warp off and no CPU trace/intervening stops. Unmodified production, immediate activation and uncontrolled native demo RNG; these are current profile figures, not a matched original-release speedup.','reuse':'Existing R3g grid/dense and Q01/Q02 semantic gates remain attached to unchanged coarse engine bytes; no claim of new production grid/dense measurements.'}
write(p,j)
rows='\n'.join(f'| {p} | {v["fps"]:.6f} | {v["elapsed_seconds"]:.6f} s | {v["error_percent"]:.4f}% |' for p,v in timing.items())
text=f'''\n### Production integration closure (2026-10-14)\n\nPassed in the documented SPS 0481 PAL emulator scope. A single tracked build now\ncombines the accepted C4 68000, C2 chip-only 020 and B8 020+Fast engines.\n`Games/FerrariFormulaOne/build.py` builds the authoritative WHD source and three\n68000/020 payloads from tracked inputs plus the checksum-verified original game.\nNo game data or generated artifacts are committed. Binary: {b['bytes']} bytes,\nSHA256 `{sha}`; an independent rebuild is identical.\n\nMode remains default-off. CUSTOM2=0 retains the original loop and CUSTOM1 meaning;\nCUSTOM2=1 supersedes the original timing callback for both CUSTOM1 settings.\nIntervals remain 200 ms on 68000 (including Fast), native 100 ms on chip-only 020,\nand 20 ms player / native 100 ms opponents on WHDLoad-qualified 020+Fast.\nActual Fast hunk/stack ownership is still verified. No performance-triggered A500\nfallback is added. CPU allocations use MEMF_PUBLIC and DMA remains Chip.\nProduction activates on driving entry, without diagnostic RNG or warmup.\n\nIntegration fixes include excluding host offsets from native relocation binding,\nfine pause/resume time exclusion, and restoring the patch ledger at the actual\nK-tow cleanup edge ($65f48), which bypasses the ordinary loop-head exit check.\nFine B8 cache setup is retained. Runtime invariant/patch failures take the normal\nWHDLoad error route instead of diagnostic spins. Actual NTSC startup reaches\nTDREASON_MUSTPAL before public activation. Irek retains its original route.\n\nAcceptance evidence (`manifest/production-integration.json`):\n\n- Four-profile 100-update exact-state comparisons (27 full blocks), fine private\n  fractions, and final coarse byte identity apart from host linkage immediates.\n- Final four-profile controlled CUSTOM2=0 comparison against v1.01: unchanged\n  26-block gate at native loops 125/150/175. Equal layout and step-1 RNG control\n  isolate the known startup-timing divergence. CUSTOM1=0; both disabled-option\n  variants and repeated overlays remain the broader Step-7 matrix.\n- All three enabled engines complete error-free updates with CUSTOM1=0; the\n  60-second measurements use CUSTOM1=1. Public patch installation passes a\n  constant replacement mode, independent of the original timing-disable option.\n- 30 exact RGB frames per engine. Fine capture uses equal endpoint poses and\n  the complete second scanout. Four initial one-field images captured partial\n  updates; no pixels are excluded. An intermediate attempted debugger hold is\n  not relied upon; the passing final capture performs no debugger writes.\n- Final A500 and fine actual device-input/modal replays: exact paused debt,\n  full ledger restoration, native menu/session time exclusion, and 21 fresh\n  driving updates after Jerez qualifying selection. Prior Q03 A500+Fast coverage\n  and Q01/Q02 semantics remain attached to the unchanged coarse engine.\n- Forced zero-capacity patch ledger reaches the production abort on 000 and fine.\n  Bad build-input checksum is rejected. Both 020 listings have no emitted SR saves.\n\n| Profile | Presented FPS | Elapsed for 60 simulated seconds | Clock error |\n| --- | ---: | ---: | ---: |\n{rows}\n\nThese are 300-presentation untraced production measurements, warp disabled, with\nimmediate activation and the native uncontrolled demo seed. They are not a\nmatched speedup comparison with the original release. All clock errors are <1%.\nExisting matched R3g grid/dense acceptance remains valid through engine identity;\nno new production grid/dense figure is claimed.\n\nFine matched simulation-only audit: reference mean 51,744.7 / worst-five 52,946 /\npeak 134,889 cycles; production 53,747.8 / 58,122.2 / 141,613. Mean rises 3.87%,\nbut all agreed gates pass (worst-five <=145,600, peak <=283,750; also B7 mean\n<=100,000). All four observed opponent pulses return below one quantum within\nthe same update. Per-car and classification totals agree. Raw/normalized traces\npreserve every cycle, register and DMA record; live DMA pointers remain Chip.\nTrace trap ranges were disabled, so zero classified trap cycles are not a trap\naudit. Lossless verified trace archives retain the evidence without large raw\nfiles.\n\nThe combined slave reserves 768 KiB expansion (256 KiB Kickstart + 512 KiB public\npool), plus 512 KiB Chip and host/slave overhead. Tested A500: 512 KiB Chip +\n1.5 MiB Slow, optionally 2 MiB Fast; 020: 2 MiB Chip, optionally 4 MiB Fast.\nOriginal minimum-memory equivalence is not claimed.\n\nProduction integration is closed; broader release qualification is not. Keep\nminimum-memory/runtime/cache variants, wider tracks/controls/season save-load,\nIrek, human handling and real hardware explicit. Enabled NTSC is deliberately\nunsupported. 030/040/060 analysis remains deferred. C4-T01 micro targets remain\nunmet; the user's same-workload P01/P02 gate remains satisfied.\n'''
f=r/'docs/STEP5_CAPACITY.md';assert '### Production integration closure (2026-10-14)' not in f.read_text();f.write_text(f.read_text()+text)
p='manifest/project.json';x=read(p);x.setdefault('original_source_sha256',x['source_sha256']);x['source_sha256']=hashlib.sha256((repo/x['source']).read_bytes()).hexdigest();x['slave_version']='1.02 opt-in production build (unreleased)';x['validation']='Production integration passed in documented SPS 0481 PAL emulator scope. C4 performance/correctness and combined engine acceptance pass; broader release and human/hardware qualification remain. Default-off; 030/040/060 analysis deferred.';x['production_integration_status']='Passed; see production-integration.json for exact state/frame, disabled-path, elapsed, cycle/DMA, options, lifecycle and failure evidence.';x['step5_status']='Implementation and production integration accepted in documented emulator scope. C4 P01/P02 and Q01-Q03 closed; C4-T01 remains an unmet optimization target. Human handling and broader release matrix remain. Default-off, no A500 performance fallback.';x['performance_design']['validation']=x['validation'];x['performance_design']['68000_selection']='User-selected converted 200 ms C4, including A500+Fast; integrated default-off, no performance-triggered legacy fallback.';x['build_caveats']=['Use tracked Games/FerrariFormulaOne/build.py; authoritative source now integrates the engines with DEBUG disabled and BOOTDOS conditional fixed. Original frozen release remains a baseline.','Build requires verified SPS 0481 relocation metadata; generated files/game data stay ignored. Combined slave reserves 768 KiB expansion plus Chip and host overhead; minimum-memory qualification remains open.','Installed debugger writes are not trusted without readback. Final exact-frame fixtures perform no debugger writes.'];x['next_steps']=['Complete broader Step-7 release matrix: both disabled CUSTOM1 variants/reloads, runtime/minimum-memory/cache variants, wider controls/tracks/season save-load and human/hardware handling.','Keep C4-T01 target shortfalls explicit; optional measured optimization is separate. 030/040/060 analysis deferred; enabled NTSC unsupported, Irek retains original route pending qualification.'];write(p,x)
readme=repo/'Games/FerrariFormulaOne/README.md';s=readme.read_text();a=s.index('Integration acceptance is in progress.');s=s[:a]+'''Integration acceptance passed for SPS 0481 PAL on the four documented emulator
profiles. Controlled exact-state comparisons, 30 exact frames per engine,
CUSTOM2=0 legacy comparisons, 60-second clocks, enabled CUSTOM1 options,
pause/menu/re-entry, failure routes and reproducible builds pass. Fine-path
cycle/debt and DMA audits pass. The current untraced 300-presentation figures
are 4.56 / 4.75 / 6.65 / 13.30 FPS for A500 / A500+Fast / chip-only 020 / 020+Fast;
all 60-second clock errors are below 0.23%. These are current demo measurements,
not matched speedup claims against the original release.

Fine simulation averages 53,747.8 cycles/update; worst rolling five is 58,122.2,
against the 145,600 gate. Peak is 141,613 against 283,750. The matched reference
averages 51,744.7: integration costs about 3.9%, with substantial capacity margin.
Actual tow restores 902 fine-path patch words before native cleanup; pause and
menu/session time do not enter driving debt. Full local evidence is indexed by
`tmp/dev/manifest/production-integration.json` and `tmp/dev/docs/STEP5_CAPACITY.md`.

This is an unreleased, opt-in production integration. Minimum-memory/runtime
qualification, the full disabled-option/reload matrix, broader tracks/controls/
season save-load, Irek, cache variants, real hardware and human handling remain
release work. Enabled NTSC is rejected. 030/040/060 analysis is deferred.
C4-T01 micro targets remain documented shortfalls; the user-selected C4 matched-
workload no-regression gate has passed. There is no A500 performance fallback.
''';readme.write_text(s)
(r/'docs/open-work.md').write_text('''# Ferrari Formula One current work

Production integration is complete for the documented SPS 0481 PAL emulator
profiles. Use the tracked Games/FerrariFormulaOne/build.py build; output is a
single default-off slave. CUSTOM2=1 selects 200 ms 68000, 100 ms chip-only 020,
or 20 ms player / 100 ms opponents on qualified 020+Fast. CUSTOM1 is superseded
only in enabled mode. CPU-only memory is public; DMA remains Chip.

C4-P01/P02 and Q01/Q02/Q03 are closed in their documented scopes. C4-T01 remains
an unmet micro-optimization target, not a performance fallback trigger.
Production exact-state, frames, legacy, elapsed, capacity, option, lifecycle,
failure and reproducibility gates pass. See manifest/production-integration.json
and the final section of STEP5_CAPACITY.md; tracked findings are in
Games/FerrariFormulaOne/README.md.

Remaining work is broader release qualification: minimum-memory and runtime
versions, both disabled CUSTOM1 variants across repeated overlay loads, cache
variants, wider tracks/controls/races/season save-load, human handling and real
hardware. Irek retains its original route but is not runtime qualified here.
Enabled NTSC is unsupported and rejected. 030/040/060 analysis remains deferred.
Further Step-6 optimization is optional measured work, not unfinished integration.

Combined memory reservation is 768 KiB expansion plus Chip and host/slave overhead;
the original release's minimum-memory equivalence is not claimed. No package has
been published. Use warp through startup and the automatic demo for measurement.
''')
plan=r/'docs/PERFORMANCE_PLAN.md';s=plan.read_text();a=s.index('Steps 1 and 2 are complete');z=s.index('Read these before implementation:',a);s=s[:a]+'''Steps 1-4 and the selected S0-S3/B3-B8/C1-C4 implementation are complete in their
documented scopes. Production integration now passes on SPS 0481 PAL A500,
A500+Fast, chip-only 020 and 020+Fast. See the closure at the end of
STEP5_CAPACITY.md and manifest/production-integration.json. The authoritative
slave includes the default-off engines; the frozen v1.01 release is a baseline.
The selected intervals are 200 ms / native 100 ms / 20 ms player with native
100 ms opponents, respectively. The user's no-fallback decision and matched-
workload no-regression C4 gate supersede earlier fallback proposals below.
030/040/060 analysis is deferred. Broader Step-7 release qualification, including
human handling, remains; production integration does not establish hardware or
full-season acceptance. C4-T01 remains a documented optimization shortfall.

'''+s[z:];plan.write_text(s)
step=r/'docs/STEP5.md';s=step.read_text();a=s.index('Status:');z=s.index('## Live VBL',a);s=s[:a]+'''Current status: production integration passed in documented SPS 0481 PAL emulator
scope; see STEP5_CAPACITY.md's final closure and manifest/production-integration.json.
The authoritative source now includes the opt-in combined engines. Human handling
and broader release qualification remain. The sections below are historical
implementation checkpoints, not the current integration status.

'''+s[z:];step.write_text(s)
for name in ['PERFORMANCE.md','GAME_TIME.md']:
 f=r/'docs'/name;s=f.read_text();line=s.index('\n');s=s[:line+1]+'\nCurrent integration (2026-10-14): see the production closure in STEP5_CAPACITY.md\nand manifest/production-integration.json. The default-off combined build is\naccepted in documented PAL emulator scope; measurements below retain their\noriginal historical scope. Broader release/human handling remains.\n'+s[line+1:];f.write_text(s)
a=repo/'AGENTS.md';s=a.read_text();start=s.index('Work on branch `ferrariformulaone`.');s=s[:start]+'''Work on branch `ferrariformulaone`. The authoritative source is
`Games/FerrariFormulaOne_WHD.s`; the tracked `Games/FerrariFormulaOne/build.py`
now builds the default-off combined performance slave. Read
`tmp/dev/manifest/project.json` before continuing and the production closure at
the end of `tmp/dev/docs/STEP5_CAPACITY.md` for current evidence and scope.
Keep archives, game data, builds and the local harness ignored. Production
integration passes on the documented SPS 0481 PAL emulator profiles; broader
release and human/hardware qualification remain. The frozen v1.01 source/release
is the historical baseline. DEBUG is disabled in production. Build instructions
and committed acceptance findings are in `Games/FerrariFormulaOne/README.md`.
''';a.write_text(s)
print('All integration gates passed; documentation updated')
