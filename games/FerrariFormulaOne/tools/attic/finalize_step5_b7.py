from pathlib import Path
import json,hashlib,subprocess
r=Path(__file__).resolve().parents[1];repo=r.parents[1]
def read(p):return json.loads((r/p).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for p in ('step5-b7-v3-state-validation.json','step5-b7-v3-elapsed-validation.json','step5-b7-v3-replay-validation.json','step5-b7-default-validation.json'):
 j=read('manifest/'+p);assert j['status']=='passed',(p,j.get('status'))
audit=read('tmp/step5/a1200-fast-b7-v3-profile/audit.json');assert audit['status']=='passed' and audit['cycle_gate'] and audit['every_update_total_agrees']
baseline=read('tmp/step5/a1200-fast-b7-b6-matched132/profile.json');cycles=baseline['per_update_cycles']
reload=read('tmp/step5/b7-v3-reload-a1200-fast/result.json');assert reload['status']=='passed'
exit=read('tmp/step5/b7-v3-transition-a1200-fast/result.json');assert exit['cleanup']['public_race_returns']==1 and exit['cleanup']['installed']==exit['cleanup']['public_bound']==0
failure=read('tmp/step5/b7-v3-failure-a1200-fast/result.json');assert failure['status']=='passed' and failure['state']['selection_interval']==100 and failure['state']['public_fallbacks']==1
matrix={}
for p in ('a500','a500-fast','a1200','a1200-fast'):
 j=read(f'tmp/step5/b7-v3-smoke-{p}/result.json');assert j['status']=='passed';assert len(j['placements'])==209
 if p.endswith('-fast'):assert all(x['kind']=='Fast' for x in j['placements'] if x['hunk']!=46)
 assert next(x for x in j['placements'] if x['hunk']==46)['kind']=='Chip'
 matrix[p]=dict(report=f'tmp/step5/b7-v3-smoke-{p}/result.json',selection=j['state'],stack_owner=hex(j['stack_owner']),hunk_slots=len(j['placements']))
for p in ('a500','a1200-fast'):assert read(f'tmp/step5/b7-bindings-reload-{p}/result.json')['status']=='passed'
commits=subprocess.check_output(['git','rev-list','--reverse','8fa29e9..HEAD'],cwd=repo,text=True).splitlines();assert len(commits)==7
source=repo/'Games/FerrariFormulaOne_WHD.s';release=r/'tmp/build/release/FerrariFormulaOne.slave'
assert sha(source)=='88995624ab0cc80974109bfede29ff6aa7434cf9901933b1961cf87eda851761'
assert sha(release)=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
report=dict(status='passed_candidate',scope='SPS 0481; default-off public-memory candidate. 68020 + Fast fine path, chip-only 020 / 68000 / A500 + Fast native coarse path. Ordinary source and release unchanged; no rendered-FPS or complete step-5 acceptance.',commits=commits,builds={name:sha(r/'tmp/build'/path/'fine.slave') for name,path in [('lean','step5-b7-v3/lean'),('verify','step5-b7-v3/verify'),('control_verify','step5-b7-v3-control/verify'),('matched_lean','step5-b7-v3/lean-padded'),('failure','step5-b7-v3-failure/lean'),('reload_fixture','step5-b7-v3-reload/lean')]},profiles=matrix,cycles=dict(anchor='loop 132, same capture protocol; first interval dropped, twenty complete updates; only repeated unsuccessful pacing polls excluded',b6=dict(mean=baseline['mean_cycles'],worst_five=max(sum(cycles[i:i+5])/5 for i in range(len(cycles)-4)),peak=max(cycles)),b7={k:audit[k] for k in ('mean_cycles','worst_five','peak')},mean_reduction_percent=100*(1-audit['mean_cycles']/baseline['mean_cycles']),mean_ms=audit['mean_cycles']/14187.58,all_three_analyzers_agree_on_every_update=True,all_trace_costs_and_registers_preserved=audit['normalization'],debt='Below one quantum immediately after all four measured pulse updates'),state='101 checkpoints, unchanged 26-block exact-state inventory and complete player fractions, VERIFY and padded lean versus equal-layout public B6 control. Explicit native hunk/link/relocation pointer normalization only; all 209 live hunk identities refreshed per snapshot, exact 512 KiB canonical snapshot length. Raw memory and pointer-bearing records retained.',validation_reports=['manifest/step5-b7-memory-validation.json','manifest/step5-b7-bindings-validation.json','manifest/step5-b7-stack-validation.json','manifest/step5-b7-patches-validation.json','manifest/step5-b7-cache-validation.json','manifest/step5-b7-v3-state-validation.json','manifest/step5-b7-v3-elapsed-validation.json','manifest/step5-b7-v3-replay-validation.json','manifest/step5-b7-default-validation.json','tmp/step5/a1200-fast-b7-v3-profile/audit.json','tmp/step5/b7-v3-reload-a1200-fast/result.json','tmp/step5/b7-v3-transition-a1200-fast/result.json','tmp/step5/b7-v3-failure-a1200-fast/result.json'],lifecycle=dict(native_unload_reload=reload['scope'],old_race=reload['race'],new_race=reload['race2'],reentered=reload['reentered'],exit_boundary='All fine patches restored, ledger/snapshot owners empty and probe state reset before native cleanup. Subsequent menu executes; automatic second Race entry was not observed in that exit experiment. Different-address reload is covered by the bounded native-loader fixture.'),default_off='Four-profile CUSTOM2=0 versus unchanged release, identical test allocation size/reservation and step-1 RNG/countdown fixture in both arms; all 26 blocks exact at loops 125/150/175. This controls known timing-dependent title RNG consumption; no raw uncontrolled-startup equality claim.',limitations=['Candidate harness reserves 768 KiB through WHDLoad: 256 KiB Kick image plus 512 KiB public pool. The default-off comparison equalizes that reservation and slave allocation size; it does not claim the same minimum memory footprint as the small ordinary release. Guest allocation-failure fallback is tested; inability to satisfy WHDLoad mandatory startup memory remains a loader admission failure.','Full rendering/presented FPS, remaining modal/input acceptance, coarse elapsed scheduling and real hardware remain outside B7. 030/040/060 remain deferred.','The pre-public B6 cycle control matches loop/state progression, but its raw allocation headers, dynamic display/resource pointers and memory-policy values differ from public placement. The unchanged complete exact-state gate uses the matched public-layout control; no fields are masked to make it pass.','Cycle class reports use disabled trap-address ranges; all cycles remain counted, but zero trap-class attribution is not evidence of zero privilege traps.'],source_hashes={str(p.relative_to(repo)):sha(p) for p in sorted((repo/'Games').glob('FerrariFormulaOne_Public*.s'))},ordinary_source_sha256=sha(source),ordinary_release_sha256=sha(release))
(r/'manifest/step5-b7-validation.json').write_text(json.dumps(report,indent=2)+'\n')
p=r/'manifest/project.json';j=json.loads(p.read_text());status='B7 passed as default-off candidate. Matched Fast mean 103957.25 -> 51546.3 cycles/update (50.42% lower, 3.6332 ms); worst five 53305.8, peak 134295, all gates pass. Public CPU hunks/stack, Chip DMA, unchanged exact-state/elapsed/replay, four-profile controlled CUSTOM2=0, allocation-failure coarse fallback and different-address native unload/reload pass. Ordinary release unchanged. Experimental 768 KiB WHDLoad reservation documented; no rendered-FPS claim. Next B8.'
j['step5_b7_status']=status;j['step5_b7_validation']='tmp/dev/manifest/step5-b7-validation.json';j['step5_b7_commits']=commits;j['step5_status']='S0/S2/S3/B3/B4/B5/B6/B7 passed as candidates; S1 CCR diagnostic validated. '+status
j['next_steps'][0]='Step 5: B7 passed. Next B8 presentation and measured displayed FPS; retain matched exact-state, elapsed/replay and cycle gates.'
j['next_steps'][1]='20 ms path remaining: B8 opponent render-pose interpolation and presented FPS; production integration remains default-off until accepted.'
j['performance_design']['memory_placement']='MEMF_PUBLIC for CPU-only allocations; original MEMF_CHIP audio and DMA resources stay Chip. B7 candidate validates public resident/race hunks, stack, binding metadata and patch workspaces on four profiles; bounded real native unload/reload and allocation-failure fallback pass. Candidate harness reservation/minimum-memory scope is documented in step5-b7-validation.json.'
p.write_text(json.dumps(j,indent=2)+'\n')
p=r/'docs/STEP5_CAPACITY.md';p.write_text(p.read_text()+'''

### B7 final acceptance — passed (candidate)

Final candidate: `tmp/build/step5-b7-v3`; full evidence and hashes in
`manifest/step5-b7-validation.json`. Seven cohesive commits, ending with
`80ddb07` (native RAM-file-cache guard) and `013cdf9` (race lifecycle).
Ordinary source and release remain byte-identical; new mode remains default-off.

| 020 + Fast, same loop-132 anchor / 20 complete lean updates | B6 control | B7 | Gate |
|---|---:|---:|---:|
| Mean cycles/update | 103,957.25 | 51,546.3 | ≤100,000 |
| Worst rolling five mean | 106,581.8 | 53,305.8 | ≤145,600 |
| Peak pulse cycles | 277,479 | 134,295 | ≤283,750 |

Mean simulation CPU cost falls **50.42%**, to **3.6332 ms per 20 ms update**.
All four measured pulses end below one quantum immediately. Each of the three
analyzers agrees on every update total. All 3,409,639 trace instruction records
retain identical costs and registers after explicit native PC normalization.
Only unsuccessful repeated pacing polls are removed; guest VERIFY recording is
off in this measurement. These are simulation costs, not displayed-frame times.

All 209 live hunk slots are audited. On both Fast profiles, every CPU-only slot
is Fast; the original 456-byte audio hunk 46 stays Chip. The 32 KiB owned stack
is Fast on those profiles, Slow on A500 without Fast, and Chip on chip-only 020.
CPU allocations use MEMF_PUBLIC, not forced MEMF_FAST. Patch snapshots and
ledgers have explicit owners, exact-size release and rollback. Forty-eight live
display fields have no out-of-Chip copper, bitplane or enabled blitter pointers;
recorded copper/audio/sprite/bitplane DMA addresses also stay in Chip memory.
Full rendering and presented FPS remain B8.

The first A500 + Fast integration exposed the game's redundant RAM: file cache:
its native Fast-memory query enables startup copies, and the run stalls in DOS
Write while copying xport.scn (native return $1b5e6). Disabling the public stack
and reducing the pool do not fix it. A diagnostic hiding the Fast attribute
isolates the cache path but is not adopted. The final hunk-validated patch clears
only the RAM-file-cache initializer; its two readers select copying and RAM:/FF1:
reads. Correct Exec Fast attributes and the native overlay policy remain intact.
WHDLoad retains file caching. All four profiles then reach the native update
checkpoint with correct selection: fine only on 020 + Fast, otherwise 100 ms.
The matrix's historical `loop130` filenames actually stop at the 131st update-end
crossing (first hit plus 129 ignored hits); fine `ticks=131` confirms the count.

VERIFY and padded lean pass the unchanged 26-block inventory at all 101 matched
checkpoints and all player fractions against an equal-layout public B6 control.
No state blocks are removed or masked. Canonicalization follows explicit native
hunk identities, allocation links, relocation fields and declared record pointer
columns; all 209 live identities are refreshed per snapshot and the canonical
size remains exactly 512 KiB. Raw memory/records remain available. The original
pre-public B6 has legitimate allocation/resource-pointer and memory-policy
changes, so it is not claimed byte-identical as a raw memory image.
Elapsed/replay: 100 adapted updates, 20 native pulses, 2.000 simulated seconds,
2.0031887 elapsed seconds; arithmetic, motion, steering, wear, fuel, clocks and
recovery oracles pass. Existing non-demo branch fixtures retain their documented
scope; the ordinary no-input demo remains the measurement workload.

Lifecycle checks cover both boundaries. A guest-set native exit flag restores
all fine patches, clears both ledger owners and resets probe state before native
race cleanup; the game continues in its menu. That experiment does not establish
automatic second-demo entry. A separate bounded fixture invokes the real hooked
native unloader with fine hooks installed, holds the freed 8,568-byte primary
allocation, then uses the native overlay loader. Race moves from **$56d970 to
$56fc80**; rebinding and installation succeed, the temporary owner is released,
and the new race completes **130 updates** with no binding/runtime errors or
fallback. It stops before returning into old native frames. Malformed binding,
changed-base rebinding, overlapping ledger/rollback and stack-return/failure
fixtures also pass on their documented 68000/020 profiles.

A genuine failed ledger allocation selects coarse/100 ms, removes fine hooks
and completes the native update checkpoint. Four-profile CUSTOM2=0 comparison
against the unchanged release passes the full 26-block gate at loops 125/150/175.
Both arms have equal test allocation size/reservation and the step-1 RNG/countdown
control, accounting for the known timing-dependent title RNG consumption.

Memory-scope limit: the experimental harness reserves **768 KiB** through WHDLoad
(256 KiB Kick image + 512 KiB public pool). The default-off comparison equalizes
that reservation and does not prove the same minimum memory footprint as the
ordinary small release. Guest allocation failure is covered; failure to satisfy
mandatory WHDLoad startup memory is an admission failure, not an in-game fallback.
The ordinary release is unchanged. Physical hardware, 030/040/060, remaining
modal/input acceptance and complete rendered-game acceptance remain deferred.

**Next: B8 presentation; then C1–C3 coarse scheduling/capacity.** B7 is complete
within this candidate scope; step 5 as a whole remains open.
''')
print('B7 aggregate, capacity report and project manifest updated')
