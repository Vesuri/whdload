from pathlib import Path
import json
p=Path('src/HardDrivinPhase.s')
Path('tmp/phase-p3-e1-candidate.s').write_bytes(p.read_bytes())
p.write_bytes(Path('tmp/phase-p3-before.s').read_bytes())
p=Path('docs/STEP4_COST_PLAN.md');s=p.read_text();s=s.replace('both below 0.3 ms. P3 is next. The combined G1 gate and step-4 closure remain open.','both below 0.3 ms. P3 E1 has been evaluated and fails its entry-rate limits; its\ncandidate is retained only in the ignored harness. P3, the combined G1 gate and\nstep-4 closure remain open. The runtime remains at the accepted P2 implementation.')
s=s.replace('### P3 Native engine runs: target ≤ phases started + 0.1 per frame (now 2.53 / 2.36)','### P3 Native engine runs: target ≤ phases started + 0.1 per frame (open)')
marker='### P4 Slave physics helpers:'
i=s.index(marker)
section='''#### E1 evaluation: correctness passes, performance fails

The exact-memoisation candidate is **not retained in the runtime**. It passed the
checks below but does not meet P3's limits or offer the expected engine-cost saving.
The accepted P2 runtime has 2.432 / 1.879 engine entries per complete frame in A/B;
the original 2.53 / 2.36 figures above the work list predate P1/P2.

Matched final runs are `p3-final-{a,b}-{off,on}`, each 500 PAL fields
(10.015943522 seconds). Each off/on pair uses an identical slave and listing:
`p3-check-a` uses constant accelerator, `p3-check-b` the frozen DRIVE tape.
Both start at the prescribed fields, including B's full preceding tape.
`p3-summary.json`, per-run `frame-budget.json` and `engine-cache.json` retain
full metrics. Probe runs precede a companion-state correction and are not final evidence.

| Metric | A | B |
|---|---:|---:|
| Engine entries / complete frame, candidate | 2.324324 | 1.982759 |
| P3 limit | ≤1.75 | ≤1.25 |
| P3 result | **FAIL** | **FAIL** |
| Cache hits / eligible segments, whole capture | 3 / 90 | 0 / 98 |
| Cache hit rate | 3.333% | 0% |
| Miss: new phase | 60 | 57 |
| Miss: changed throttle | 25 | 41 |
| Miss: changed pitch sine | 2 | 0 |
| Physics ms/frame, P2 → candidate | 15.487410 → 15.454362 | 10.985855 → 11.374694 |

Cache counts cover the whole capture, whereas frame metrics average only complete
swap intervals and also include engine calls through the fallback path. Do not
subtract the former directly from the latter. Phase starts must evaluate a new
anchor; changed throttle/pitch must miss under E1's exact-input rule. Thus the
assumed roughly one reusable evaluation per frame is absent from these windows.
B has no cache hits and its extra comparisons/bookkeeping are unproductive.

For G2 reporting only, CUSTOM1 off/on means are A 260.956033 / 252.293329 ms
(38 / 38 swaps; 57.756757 / 55.378378 polygons per complete frame), and
B 119.947041 / 169.925478 ms (83 / 59 swaps; 13.780488 / 27.689655 polygons).
**B is a scene mismatch.** These are the complete experimental stack against
CUSTOM1 off, not an isolated E1 FPS gain. No combined G1 or step-4 pass is claimed.

The candidate caches only the native `$0b678..$0b904` speed/RPM endpoint within
one phase. Its key includes both full Q16 anchors, gear, throttle, brake, contact
mask, skid, road, turning, grade-disable, engine-disable, automatic flag and
pitch sine. Gear-ratio/math tables are immutable; anchor preparation derives the
engine-speed input and clears scalar carries before every attempt.

Side effects were audited before reuse:

- Off-road throttle retention executes separately on every hit, with current
  throttle carry and `PH_DT`; these affect the decay side effect, not the already
  computed endpoint. The original signed >30 threshold remains intact.
- Native scalar LAST values are saved verbatim. RPM LAST can precede the native
  zero clamp, so reconstructing it from the clamped endpoint is not equivalent.
- `$0b904` onward runs every segment: fractional phase integration, automatic
  gear decisions only at phase completion, gear pointer updates, MPH and engine
  speed publication, brake clearing, and the existing final-segment audio gate.
- Position, spin decay and skid exit still run once per outer frame. Power/root
  memo tables are pure implementation caches; bypassed diagnostic hit counts
  are not gameplay side effects. Reset/new-phase paths cannot reuse a stale endpoint.

Verification of the final candidate:

- `check_p3_cache.py`: 6,000 actual-68000 comparisons against forced native
  evaluation, including 3,567 hits and 2,433 misses. All native globals, phase
  state, scalar companions, gear pointer, pitch/audio call count, preserved
  registers and stack match. Only the private audio body is replaced by a call
  counter; native pitch calculation and its gate execute unchanged.
- The existing 128 native endpoints and 1,440 input-partition comparisons pass.
- All five `analyse_phase_*` checkers pass: `p3-motion-a500` 17 steady-throttle
  returns, `p3-brake-a500` 46 braking returns, `p3-steer-a500` 9 steering returns,
  `p3-offroad-a500` 29 off-road-test returns, and `p3-skid-a500` / `p3-skid-020`
  43 / 188 grounded skid/slope returns. The skid checks stop explicitly at first
  unsupported airborne input, fields 519 / 574; they do not validate flight.
- `p3-native` matches all 108 reference states; `p3-disabled` passes 163 ranges;
  the branch audit passes 141 ranges. Normal, DRIVE and ATTRACT builds remain
  byte-identical to their established baselines.

**Next decision:** P3 remains open. D3 permits E1 only at this point; E2 is
conditional on results after P1–P6, so it has not been enabled. Reconsider the
ordering/conditional fallback or propose another exact optimisation before
claiming P3 complete. Its numeric limits and the accepted physics policy have
not been relaxed. The candidate source, binaries, checkers and verified compressed
traces remain under ignored `tmp/` for follow-up.

'''
s=s[:i]+section+s[i:];p.write_text(s)
p=Path('docs/GAME_TIME.md');s=p.read_text();s+='''

### Engine endpoint reuse: P3 evaluation

P3's exact endpoint-cache candidate passed native/phase equivalence checks but
failed the performance gate: 2.324 engine entries/frame in A (limit 1.75),
1.983 in B (limit 1.25). Only 3 of 90 eligible segments in A and none of 98 in B
reused an endpoint. Changed throttle accounts for 25 / 41 misses, changed pitch
for another 2 in A; other misses start a new phase. These traces do not support
the plan's expected roughly one saved engine call per frame.

The candidate is retained only in the ignored harness; `HardDrivinPhase.s`
continues evaluating the native engine every segment. No input latching or
physics-cadence change was introduced. `STEP4_COST_PLAN.md` P3 records the full
side-effect audit, exact-check evidence, matched ten-second profiles and the
unmet limits. P3 remains open under the existing D3 decision.
''';p.write_text(s)
p=Path('docs/open-work.md');s=p.read_text();s=s.replace('Next P3 exact engine memoization. CombinedG1 and step4closure remainopen.','''P3 E1 evaluated: correctness passes, performance FAIL. Candidate NOT retained in
runtime; source remains P2. Final p3-final-{a,b}-{off,on} 500field traces show
2.324324 / 1.982759 engine entries per frame against1.75/1.25 limits. Cache3/90
and0/98; misses newphase60/57, throttle25/41,pitch2/0. Candidate physics15.454362 /
11.374694 ms; P2 15.487410/10.985855. B nohits and extraoverhead.
Source candidate tmp/phase-p3-e1-candidate.s; exactbuilds p3-check-a/b +listings.
check_p3_cache6000cases3567hits2433misses exact allnativeglobals,phase/scalars,
gearpointer,audio-count/pitch,regs/stack. Preserve nativeRPM LAST beforezero clamp;
firstprobe missedthis, finalcandidate corrected. Current checker loads actualpatched
image from p3-check-motion, matchingp3-check-a.lst. CacheHDENGC01state40bytes:
valid.w0,key22bytes2,endpoint.l24,nativeLASTs.l28,hits.l32,misses.l36.
Allanalyse_phase_* pass: motion17,brake46,steer9,offroad29,skid43/020188; latterstop
firstairfield519/574, noflightclaim. 128endpoints/1440partitionspass. Native108exact,
disabled163pass,branches141pass,normal/drive/attractbyteidentical. No E2; D3 defers
untilafterP1-P6. Asked user whether to retainE1-onlydecision or allowE2now; noanswer
yet. P3 cannotbeclaimedcomplete. Needordering/fallbackdecision oranotherexactapproach.
CombinedG1 and step4closure remainopen.''');p.write_text(s)
