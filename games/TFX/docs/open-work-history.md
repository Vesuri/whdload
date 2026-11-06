# Open-work history

Handoffs in reverse order, kept for reference. The current state is in `open-work.md`.

## Note: step 3d not implemented (2026-10-21)

Probe tools/cockpit_probe.py PROBE_SIZES=1 (adds the mask_sprite8_040 entry and image size
headers; drops 3D breakpoints because the stub takes ~20) -> tmp/step3d/probe{,150}. Exact
skip of persistent sprite rows: 18-24% of mask work, net ~0.3-0.6% est after tracking.
Recorded in the plan (36b55dd4). Production unchanged (b99c3ca8).

## Note: step 3c not implemented (2026-10-21)

Re-assessed from tmp/step3/probe-copy: ~805 units/frame skippable but 1-2 still change
(stale post-panel writes in the shadow's frame), net ~0.25% after span overhead. Recorded
in the plan (011fe90d). Production unchanged (b99c3ca8).

## Current handoff: step 9 done (2026-10-21)

Production b99c3ca8 (tmp/build/release/TFX.Slave == tmp/prof20/sqrt-verified.slave).
Step 9: isqrt_040 at $4bdca (@SquareRoot enters unrolled iterations at the highest
power of 4 <= D0 via BFFFO). Twins 4,922 + 5 controls (tools/opt20_sqrt_test.py), gates,
scenes pass; tools/sqrt_suite.sh, PATCH_KIND=sqrt, SQRT_OFF. Accepted by cycle count
(fewer instr/cycles on every input): routine net -4.8k est, -8.5k emu per frame; the
frame pair 746 -> 731 is scene divergence (ScanFillDown calls +4%), as in step 7
(tmp/sqrt9/sqrt-ab.json). Tail ceilings recorded in the plan (xTranslate: no gain,
MULS.L needs per-product floors; others < 0.4%). PITFALL: TFXHD.s is CRLF; Python
text-mode writes drop the CRs (write bytes). Next: Apollo (step 1 default, step 10
validation), step 12 palette.

## Current handoff: step 5 rejected (2026-10-21)

Production unchanged: a9b21fbb (tmp/build/release/TFX.Slave == tmp/prof20/sfd-verified.slave).
Step 5 (poly_fill_040 at $60d92: edges + runs in one pass) passed twins (194,
tools/opt20_poly_test.py), gates, scenes and a poison build, but the pair lost:
746 -> 743, est -0.33%, emu +0.4% (tmp/poly5/poly-ab.json). Only ~8k instr/frame of
~71k overhead saved; edge arithmetic equals GenLeft/GenRight. Rejected source:
tmp/poly5/poly-rejected.{s,diff}; tools/poly_suite.sh, poly_poison.py; PATCH_KIND=poly,
POLY_OFF, gate check (only when the listing has poly_fill_040). Pitfalls: edge tables
hold 17 records per chain (n <= 17 safe); Gouraud/texture fills read stale end-record
fractions, so poison only bytes the original writes. Next: 9/10 re-profile.

## Current handoff: step 4 done (2026-10-21)

Production a9b21fbb (tmp/build/release/TFX.Slave == tmp/prof20/sfd-verified.slave).
Step 4: sfd_span_040 at $6c514 (ScanFillDown lines from per-x offset/mask tables;
edge longs via PlotColour, no BFINS). Pair 708 -> 746, est -8.3% (1.69 M/frame, below
the 2.0 M target), emu -5.1% (tmp/sfd4/sfd-ab.json); matched on first start.
D1-D6/A1/A6 differ at exit (dead; poison build sfd-poison.slave proves it in scenes).
Twins tools/opt20_sfd_test.py (187 calls); tools/sfd_suite.sh; PATCH_KIND=sfd, SFD_OFF.
Pitfall: poison only after restoring kept registers; poison scenes need their own
DELTA_LISTING. Next: step 5 (fused edge walking) or 9/10 re-profile.

## Current handoff: step 8 done (2026-10-21)

Production: see git log (tmp/build/release/TFX.Slave == tmp/prof20/rot-verified.slave).
Step 8: rot_delta2_040 at $59748, a (delta, matrix)-keyed table (4 slots x 256 x 32 B,
allocated with the copy shadow). Flight hit rate 84%. Pair 689 -> 708, est -1.3%,
emu -2.7% (tmp/rot8/rot-ab.json). Twins 220 + 4 controls (tools/opt20_rot_test.py:
owns dispatch entries 254/255; entry 104 is NOT stable at run time). tools/rot_suite.sh
(DEBUG_PORT=2611: another project's emulator held 2462). Startup mismatches now also
in hunks 0/1 beyond the clocks (6 retries); investigate before the next pair.
Refinement idea: An-addressed entries, per-object matrix check. Next: step 4.

## Current handoff: step 7 done (2026-10-21)

Production is 617899c7 (tmp/build/release/TFX.Slave == tmp/prof20/fade-verified.slave).
Step 7: fade_cols_040 at $249a. Factor 50 (call $2ad0) is a byte copy; 0-49 (call
$3244, in place, lighting) uses the exact reciprocal |n|*5243>>18; others/wrap run the
original. Accepted on cycle count by the user (cannot be slower on any in-flight call):
the copy-only frame A/B lost (699 vs 686, est +0.9%) to scene divergence (+4% fill
calls) while the routine saved 26k est/frame. Twins 216 + 5 controls
(tools/opt20_fade_test.py), gates, scenes pass. tools/fade_suite.sh; PATCH_KIND=fade,
FADE_OFF. Evidence tmp/fade7/. Frame A/B noise from divergence is large for small
changes: judge small steps by routine-level cost. Next: step 4 or 8.

## Current handoff: step 6 done (2026-10-21)

Production is b66a0657 (tmp/build/release/TFX.Slave == tmp/prof20/copy-verified.slave).
Step 6: copy_changed_blocks compares one 32-byte line per DBF with per-position
handlers (no rewind), dest addressed via D4 = dest - src, 150-byte COPY_SLOT.
Balanced pair 671 -> 700/2,000, est-040 -3.7%, emu -4.1% (tmp/copy6/copy-ab.json).
New baseline for later A/Bs: 700/2,000. Rejected first version (rewind per line, est
+2.5%): tmp/copy6/copy-rewind-rejected.s. Harness: COPY_DONOR/COPY_LEN in
opt20_balanced_profile.py and opt20_scene.py; long tfxmem writes are chunked (~90-byte
limit); opt20_gate.py expects original scan/panel bytes unless the slave has step 3.
tools/step6_suite.sh (LATE_ONLY=1 skips twins/gates). Note tmp/step6 is the ORIGINAL
plan's Ghidra step 6, unrelated. Next: step 7 (palette blend) or step 4.

## Current handoff: step 3 rejected (2026-10-21)

Source is clean at 02b67bbf (plan record only); production slave unchanged from 78330582.
Step 3b tried twice, both exact, both slower in clock-normalized balanced pairs:
per-line clipping 650 vs 671 (est +2.3%, clip-ab.json), whole-call skip 663 vs 671
(est +0.3%, skip-ab.json). Hidden pixels are cheap (unrolled plot table); hidden calls
are small (36k of 376k fill cycles). Sources: tmp/step3/clip-perline-rejected.s,
skip-rejected.s, step3b-rejected.diff. 3c/3d not implemented (ceilings ~2%).
HARNESS: CLOCK_NORMALIZE=1 in opt20_balanced_profile.py fixes startup mismatches (boot
jitter of 1-4 vblanks in _vblank_clock $4d884 + 4 copies); use it on both sides of every
new pair (control must be rerun with it). tools/skip_suite.sh is the full suite template.
Next: step 6 (copy compare unroll).

## Current handoff: step 1 switch built (2026-10-21)

Production is 78330582 (tmp/build/release/TFX.Slave == tmp/prof20/intproj-verified.slave).
Step 1: project_int_040 behind CUSTOM1 (C1:B), default FPU. Balanced pair intproj-fpu
671 vs intproj-int-1 644/2,000: emu +4.2%, est-040 -3.9% cycles/frame (intproj-ab.json).
Decide the default on the Apollo (calib040 + both settings). PITFALL: the seed's dh0.hdf
bakes the WHDLoad command line, so TEST_SEED runs boot with the control's CUSTOM
arguments; select variants with a same-length patch write (PROJECT_SYMBOL in
opt20_balanced_profile.py). tmp/prof20/invalid/ holds three runs that hit this.
Scripts: tools/intproj_gates.sh, tools/intproj_ab.sh. Next: step 3a measurement, step 4.

## Current handoff: steps 0 and 2 done (2026-10-21)

Production is 9ae51bb3 (tmp/build/release/TFX.Slave == tmp/prof20/mask-verified.slave).
Step 0: views fixture (464/2,000), prof20_ab.py, PATCH_KIND=mask, calib040 (waiting
for the Apollo; user does not have it now). Step 2: mask_sprite8_040, balanced pair
606 -> 671/2,000 (16.78 nominal fps), est-040 -7.2%. Details in profile-20fps.md and
PERFORMANCE_PLAN.md. Next by plan order: step 1 (needs hardware to decide; can be
built behind a switch), step 3a measurement, step 4. Re-profile first: the new
baseline is tmp/prof20/mask-on-2.

## Current handoff: 20 fps action plan (2026-10-21)

Fresh profile of production e0cd1fe7: tmp/prof20/current, 608/2,000 (15.2 nominal
fps), CPU-bound, zero FPSP. Analysis: profile-20fps.md. New precise plan appended to
PERFORMANCE_PLAN.md ("20 fps action plan"); it supersedes the paused projection
recheck below. Key finding: emulator 040 timing is a flat ~2.84 cycles/instruction
(FDIV/MULS.L/BFINS undercharged ~10x; DIVS.W 48, MULS.W 20, chip write ~31), so use
prof20_cost040.py alongside emulator A/B. Next: plan step 0, then step 1/2.

## Current handoff: paused at user request (2026-10-21)

Production code is e0cd1fe7; current tmp/build/release/TFX.Slave is byte-identical
to tmp/opt20/delta-eight-verified.slave. No experimental source is active.
Best corrected extended result: 607/2,000 PAL fields (15.175 nominal fps), short
81/250 (16.2). Hardware 20 fps remains unverified and measurements postponed.

Cache-balanced edge recheck is complete: recheck-edge-off/on-2 confirms 598 ->
601/2,000, short 80/250 both, zero FPSP/cache flushes in the measured window.
Manifest hashes, all entry hunks except tested instructions, and reported CPU
registers match. recheck-edge-summary.json records verification. The first on
attempt was rejected before timing. Projection control recheck-project-off is
563/2,000; recheck-project-on was rejected with [false,false,true,true]. Preserve
these rejected starts. Next action on resume: retry the projection enabled path
against that control with symmetric cache setup and MATCH_ENTRY; do not weaken
the startup guard. No further optimization was started for the pause.

The following chronological notes include superseded active-work instructions;
this handoff takes precedence. Harness/evidence remain ignored and local; only
tracked source/plan changes are committed and pushed.

# TFX

Initial setup is complete. Branch `tfx` starts at upstream commit
`ce5a2a25e7f8443da5502d9755b6b1ae01080862`; local master, origin/master and
upstream/master matched when fetched.

The installer and full installed game are retained and extracted with SHA-256
manifests. All development inputs and notes are ignored by Git.

See `development.md` for locations and provenance.

## Goal (from the user)

Plan: `docs/PERFORMANCE_PLAN.md`. Fastest possible 68040 version with native 040 FPU maths, and fix development-leftover
palette glitches seen on A1200/68040. Executable survey: `executables.md` — no intact
68040-specific build is known; `tfx.020` (Dec 1997) is the newest intact FPU build.

## Plan progress

- Step 1 (build) done: see `development.md` Build/Run. Makefile fix committed (04a5dd8) in
  `src/Makefile` (fpsp040/fpsp060 targets). 

- Step 2 complete (user accepted the specific clock-origin mismatch on 2026-10-20).
  Harness implemented and exercised on 040, 020, 030+68882 and 060:
  `tools/replay_flight.py`, `tools/flight.tape.json`, `tools/compare_flight.py`.
  See `replay-flight.md` for commands, evidence, machine settings and pitfalls.
  Two cold boots give identical screenshots at swap checkpoints 1, 10, 20 and 30
  on all four configurations; recorded right joystick visibly banks the aircraft.
  040/060 also match every captured game-hunk byte. On 020/030, five absolute timer
  values differ by one vblank; every byte matches after translating that clock
  origin. This specific difference is accepted; use `--clock-relative` for the
  accepted baseline and retain raw results. Other state differences remain failures.
- Deterministic directory-drive startup hangs with indirect UAE I/O; disposable
  HDF seeds fix that while retaining target CPU caches. 040 now has an explicit
  40 MHz override and exactly 32 MB fast RAM; 030 explicitly adds its 68882.
- Step 3 complete: see `frame-counter.md`. Read-only publication/vblank breakpoints
  agree with a full target-040 MMU instruction trace: eight publications, 16 vblanks
  in the fixed neutral window. All eight bitplanes use the published buffer on the
  next field. Tools: `count_frames.py`, `check_frames.py`, and the local-only
  `build_trace_emulator.sh`/`040-dispatch-trace.patch`.
  Publication is tfx.020:$4c474, vblank increment $4d2de. Swap entry $019fc can
  precede publication by a vblank. Count vblank hits rather than reading raw cached
  clock RAM. The trace build records instruction order, with zero cost values;
  it does not solve step 5's instruction-cost measurement.
- Step 4 complete: see `baseline-matrix.md`, `tools/baseline_matrix.py`,
  `tools/run_baseline_matrix.sh` and `tools/report_baseline.py`. Evidence in
  `tmp/step4-matrix/`: two cold boots per measured row, fixed [2,252) vblank window.
  Nominal PAL emulator rates: 040 TFX new 11.8, original 6.8, tfx.020 11.4,
  TFX.FPU 14.6, installed TFX.040 beta 14.6; 020 TFX 3.6. Forced tfx.020
  without an FPU aborts at $50f4c and has no performance result.
  Corrected naming: the installed 599152-byte beta is usable in this window;
  it is distinct from the damaged 040-named candidates and is not native-040.
  Keep tfx.020 as base: 3.5% more throughput matches plain TFX in this fixture.
  MMU timing ignores frequency. Performance rows use the playbook's frequency-
  sensitive NOMMU backend, with actual CPU/cache metadata from a local read-only
  observer build. These are A/B figures, not Apollo FPS. Repeated totals/images
  match; small cadence differences and additional raw-state differences remain
  explicitly reported, with no new equivalence waiver.
- Step 5 complete: see `profile-040.md`. The private NOMMU observer accounts for
  100% of fixed-window scheduler time, with per-PC costs, routine regions, chip
  accesses, FPSP opcode/site counts and cache calls. Two strict profiles are
  byte-identical; disabling the observer gives identical events, images and all
  captured game-hunk bytes. Evidence: `tmp/step5/`.
  Important correction: step 4 allowed unsupported FPU operations in the emulator.
  Use `--uae_fpu_no_unimplemented=true` for future 040 profiling. Strict tfx.020
  remains 57 publications, but now enters FPSP 2,394 times (42/frame, six
  transcendental sites). Other FPU matrix rows need strict remeasurement before
  comparing their rankings. No FINTRZ/FMOVECR traps or cache flushes in this window.
  Dominant regions: ScanFillDown, screen copy, masked sprites and geometry.
  Costs include synthetic emulator padding, not hardware-accurate FPU latencies.
  Small unclassified regions remain explicit; no new state mismatch was waived.
- Step 6 complete: see `symbol-map.md`, evidence `tmp/step6/`. Accepted map covers
  all 30 hot regions and all 60 active rows (57 distinct sites) in the plain-TFX
  main/060 patch lists. 723 unique relocation-masked complete symbol spans;
  semantic matches and local names remain explicitly separate. Ghidra/shared
  exporters audit 37 selected entries. No code changed and no new speed claim.
  Sort hooks: $5efbe/$5f03e; depth $5bf16, count $5bf10. Duplicate-fire site:
  $4e080, branch destination $4e0a6. Sort replacement bytes match the plain build.
  GouraudFill ($4f840) has a different ABI; frame limit is MOVEQ at $1abfe;
  delta time moved to A4-$ba4. No blind copy of the rendering/uncapped patches.
  The six FPSP sites are @tan/@sin/@cos/@atan2/@atan/@asin wrappers.
- Step 7 correctness exit complete: see `correctness-fixes.md` and
  `tmp/step7/validation.json`. Sort `7a9ea96` and duplicate-fire `18f4c42` are
  committed. The full-array baseline corrupts guarded arrays; all 39 candidate
  boundary/insertion/ABI cases pass on 040/030+FPU/060. Actual distinct missile
  allocations change from two per joystick press to one, while Space and original
  rendering continue to work. No game/FPSP/shared-emulator inputs changed.
  Strict 040 throughput remains 57 publications/250 vblanks. Sort-only same-seed
  repeats match events, image and all hunks; final NOMMU repeats match events but
  differ in dynamic state after a one-vblank clock-origin difference at entry.
  Additional shared-emulator replay pairs repeat all images. 020/060 match raw
  state exactly; 040 has only five clock-value differences; 030 also has audio
  queue differences. Full-state gates remain failed, with no new waiver.
- Step 8 complete: `a539348` moves the new-rendering 040 path's merged data/BSS
  to fast RAM and copies only DMA objects into a 141,152-byte chip allocation.
  62 relocation sites are complete; 156 CPU-only references remain in fast RAM.
  Palette snapshots, sprite pointer tables and screen selectors are CPU-only.
  See `chip-placement.md` and `tmp/step8/validation.json`.
  Strict 040 fixed-window throughput improves from 57 to 73 publications/250
  vblanks (+28.07%, emulator A/B only). Two candidate runs match events, final
  image and all three hunk dumps. Five controlled baseline/candidate screenshots
  match exactly with fixed timesteps, resolved-latch input and CPU-held capture
  after actual publication. Earlier fixture failures remain documented.
  Two normal replays per CPU repeat all images. 020/040/060 also match raw hunk
  state; 030 differs by a two-vblank origin only (clock-relative equal, no new
  waiver). Old step-7 versus new 020/030 images can differ. Original rendering
  retains chip placement; 020/030/060 placement and the shared emulator are
  unchanged. Both FPSP binaries and pristine inputs are unchanged.
- Step 9 complete: `ee06330` covers all 146 FINTRZ and 93 FMOVECR sites on 040;
  `29a6c7e` replaces the six hot transcendental sites with native arithmetic.
  See `native-fpu.md` and `tmp/step9/validation.json`. The post-step-8 baseline
  has 3,066 FPSP entries; two native timing runs have zero. Throughput remains
  73 publications/250 vblanks (14.6 nominal PAL fps, emulator A/B only).
  1,147 static cases plus 1,147 FPCR-mode cases match FPSP exactly. All 5,196
  transcendental cases pass the independent 80-digit oracle (max scaled error
  2.54e-16); broad tests retain 28 original-FPSP outliers outside gameplay.
  Five baseline/candidate controlled screenshots match. Same-build CUSTOM5
  on/off end states differ only in intentional patches, four clock fields and
  20 low-order double values (max accumulated absolute difference 7.276e-12).
  All remaining game-hunk bytes match. FPSP remains installed for exceptional
  and unobserved operations. 060 FPU sites are byte-identical to step 8.
  Ordinary pairs: 020 raw/image equality; 030/060 image equality with one-vblank
  origin differences; 040 MMU first three images match but swap 30 differs after
  a three-vblank origin shift. That full replay gate is not passed or waived.
- Step 10 complete: `fb0137f` ports 040 Gouraud/texture fills; `94fb17c` ports
  uncapped/one-frame options; `e006c99` fixes line endpoint/stipple equivalence;
  `6ec951e` restores one-pixel-wide boxes. See `rendering-port.md` and
  `tmp/step10/validation.json`. The equivalent generic flat-fill port measured
  slower (72 versus 73 publications), so original ScanFillDown is retained.
  Existing fast render-buffer/start_frame/C2P integration is preserved and verified.
  Final selected fills pass 180 cases, lines 592, boxes 259, option helpers 41;
  earlier full fill comparison covers 436 cases including flat. Independent pixel
  models prevent untouched-buffer false positives. All five original-renderer
  scenes match bitplanes and PNGs exactly. Default/uncapped/one-frame timing pairs
  all have 73 publications/250 vblanks and zero FPSP; no measured fps improvement.
  Default repeats all raw state. Other modes retain explained clock/audio-tail
  differences, with no new waiver. All four ordinary CPU pairs repeat every image
  and captured hunk byte; four CPU/combined-option gates pass. 060 FPU sites are
  unchanged. Normal/CHIP_ONLY builds and the retained exit checker pass.
- Step 11 complete (`d031a0a`) with no retained code change. See `tuning-040.md` and
  `tmp/step11/validation.json`. Fresh baseline exactly repeats step 10's profile,
  final image and all game-hunk bytes. Copyback is already requested; zero cache
  flushes occur. Three same-build 040 copy A/B pairs (MOVE16, MOVEM, longer
  longword unroll) all measure 73 publications/250 vblanks, zero FPSP. All are
  rejected; uncontrolled final images/state differ and equivalence is not claimed.
  `step11_report.py` uses current listing anchors with independent code guards;
  three negative controls pass. Explicit boundary residual is 512 scheduler ticks.
  Final slave and FPSPs are byte-identical to the verified step-10 release.
- Step 12 investigated, **not complete**: see `palette-investigation.md` and
  `tmp/step12/`. No yellow glitch reproduced in enrolment, menus, training intro,
  aircraft/loadout selection or sampled flight views. 18 stable palette samples
  (4,608 RGB entries) match hardware; two complete traced 040 SetPal calls
  (512 entries) have correct CPU operands/banks/nibbles. No root cause/fix claimed.
  Some 020 view requests and the full mission-briefing route are unverified.
  Need a more specific trigger or hardware capture to direct further diagnosis.
  User follow-up: also unable to reproduce; possibly a debug executable, but
  the affected build is unknown. Keep palette code unchanged pending reproduction.
  Step 12 left the slave and FPSPs byte-identical to step 11.
- Step 13 complete (`adbfde4` record): selector `b0a1139` chooses newest tfx.020 automatically on
  full 040+FPU. Explicit choices and 020/030/060 selection stay unchanged.
  See `selection-regression.md` and `tmp/step13/validation.json`: eight baseline
  selections, 49 supported flight/option cases (three publications each), and
  16 startup cases pass. The seven unchanged automatic choices repeat their
  baseline PNG; no full-state equivalence or new timing result is claimed.
  All 239 static FPU replacements are present on automatic 040; CUSTOM5 restores
  the originals. All 245 inspected 060 FPU sites are unchanged. Normal and
  CHIP_ONLY builds pass, and both FPSPs remain byte-identical to the baseline.
  Forced FPU builds on the no-FPU 020 give the expected Line 1111 exceptions;
  those three unsupported combinations are explicitly excluded from passing boots.
  Step 14 (real hardware validation and release) has not started.

- Further optimization toward a 20 fps average is active (plan ff094922).
  See optimization-20fps.md and tmp/opt20/. Fresh baseline is 73/250.
  Two masked-sprite experiments show no throughput gain and are discarded.
  Shadow-based screen copy is verified: final same-build 2,000-field pair
  improves 546 to 578 frames (+5.86%); original prefix 73 to 77. 80 native cases,
  ten displayed-buffer/image comparisons, 114 in-game copy checks, CPU gates and
  normal/CHIP_ONLY builds pass. 060 FPU sites stay unchanged. Committed as 4b81b5ff.
  The extended flight's FETOX at $51682 now has a bounded native 040 helper.
  1,248 independent-oracle and 726 exact non-default-mode cases pass. A controlled
  400-update flight executes 440 calls with seven identical displayed images;
  rounding differences in two double cells and five clock changes are documented.
  The 2,000-field run remains 578 frames, now with zero FPSP traps (was 142).
  CPU/CUSTOM5 gates and both builds pass; all 246 inspected 060 sites unchanged.
  Committed as 91eb7410. Current tmp/build contains this verified helper;
  exp-final.slave freezes it.
  Hardware measurements are postponed because the Amiga is unavailable.
  The 20 fps target is not reached or hardware-verified. Continue with measured
  wide flat spans/geometry bottlenecks; avoid repeating rejected sprite/MOVEM work.
  The two-block flat-span unroll is also rejected: extended same-build timing
  regresses 578 to 567 frames. Source restored; see optimization-20fps.md.





Harness, recordings and evidence remain ignored; accepted status is recorded in the tracked plan.

## Native projection accepted (275fc83f)

The 040 new-renderer Project replacement is verified and committed. It uses
native FPU division with exact integer truncation, preserves the final point's
original packed return registers, and saves/restores FP0, FPCR/FPSR/FPIAR.
CUSTOM5 and original rendering retain original Project; 060 is unchanged.
That verified build is frozen as `tmp/opt20/project-verified.slave` with
its source and listing; see the newer build below.

275 native full-array/GPR/CCR/FP-state comparisons pass, including recorded
operands, boundaries and wrapping translations. An independent integer oracle
and four negative controls pass. Seven full displayed buffers and PNGs match
through 400 controlled updates. Final whole-game state is not bit-identical:
clocks, an interrupt-updated audio period and an inactive queue record differ;
all other state matches apart from the patch. Details are explicitly recorded in
optimization-20fps.md and project-scene-comparison.json (strict equality false).

Final timing uses identical build/emulator/seed and all three entry hunks match
except the six-byte Project switch: 563 -> 598 frames/2,000 fields (+6.22%,
14.075 -> 14.95 nominal fps), prefix 76 -> 80 (15.2 -> 16.0). Both paths have zero
FPSP traps/cache flushes. Historical pre-projection 578 is a separate build/state
comparison, not the matched control. CPU/CUSTOM5/original-renderer/060 gates and
normal/CHIP_ONLY builds pass; both FPSPs and 246 inspected 060 sites are unchanged.

No emulator remains active. Worktree is committed. Goal remains active: 20 fps
is neither reached nor hardware-verified. Hardware measurements are postponed.
Continue measured exact-output renderer work; do not repeat rejected masked-
sprite, MOVEM-copy or two-block flat-loop unroll candidates. ScanFillDown remains
about 17.4% of this profile; masked sprite merge about 11.4%; rotation about 8.9%.
Use exact symbol spans, not broad SetColor attribution. Native projection is now
in the slave, so broad Project bucket no longer describes its cost.

## Latest retained build: edge extraction (3fafdb93)

Current tmp/build is committed and verified, frozen as flat-edge-verified.slave
with source/listing in tmp/opt20/. In-place BFEXTU replaces two mask operations
on the 040 new-renderer path. 65,536 native edge-word pairs, independent oracle,
four negative controls, five complete displayed-buffer/PNG comparisons and
CPU/render-option/build checks pass. 060 instructions and FPSP binaries remain
unchanged. A common-state matched pair gives 598 -> 601/2,000 fields (+0.50%,
14.95 -> 15.025 nominal fps), with unchanged 80/250 short prefix. Zero measured
FPSP entries/cache flushes. No hardware-speed claim. Initial startup mismatches
and the provenance of the accepted common state are retained, not normalized away.

No emulator session is active; worktree is committed. The 20 fps objective stays
active and unverified. Renderer costs remain dominant. Avoid repeating the
rejected two-block unroll, sprite or MOVEM-copy candidates. Continue from the
latest profile flat-edge-match-on and its exact flat-edge.lst symbol addresses.

Latest rejected trial: word-granularity shadow copy. Saved coherent frames
suggested 40-55% fewer chip longword writes, and 80 native history/guard/pointer
cases passed. With every other slave byte unchanged, the matched-start extended
pair measured 601 old vs 600 candidate, so it is discarded. No new tracked change.
Evidence: delta-word-timing-summary.json, rejected source/slave and tools under
opt20. Production source/build remains 3fafdb93; no emulator remains active.

## Latest retained build: 8-byte copy (e0cd1fe7)

Current source/tmp/build is committed and verified, frozen as
`tmp/opt20/delta-eight-verified.slave` with source/listing. It uses 8-byte changed
units, retaining first-use initialization and shadow invalidation. Only the old
90-byte copy-loop span differs from flat-edge-verified; padding keeps every other
code/data byte and address unchanged. 80 native history/guard/pointer cases, four
negative controls, five displayed-buffer/PNG comparisons, CPU/render-option gates
and normal/CHIP_ONLY builds pass. Both FPSPs are unchanged.

Corrected balanced-eight-off/on: 601 -> 607/2,000 fields (+1.0%, 15.025 -> 15.175
nominal fps), short prefix 80 -> 81 (16.0 -> 16.2). Chip writes 3,110,105 ->
2,139,708; zero measured FPSP entries/cache flushes. Both sides perform exactly
one same-address/length code write (same cache flush), then match every starting
game-hunk byte and reported CPU register. No startup rejection was needed.

Benchmark-method audit is committed as 46d3e676. Earlier optional-off writes
flushed caches asymmetrically. Native correctness/image checks remain valid, but
precise historical performance attribution needs symmetric revalidation. Do this
next, before further optimization:
- Edge: PROFILE_SLAVE=tmp/opt20/flat-edge-verified.slave, PATCH_KIND=edge.
- Projection: PROFILE_SLAVE=tmp/opt20/project-verified.slave, PATCH_KIND=project.
Use absolute PROFILE_SLAVE paths from the game directory; replay_flight.py now supports
this optional frozen-artifact selection without changing tmp/build. Defaults are
unchanged. opt20_balanced_profile.py CONTROL=1 OUT creates the control; enabled
uses its TEST_SEED and MATCH_ENTRY, omitting CONTROL. It checks all game hunks
(mask only the tested game instruction bytes) and reported CPU registers.
Keep the current production build intact during historical revalidation.

No emulator session remains active; tracked worktree is clean. Goal remains
active: 20 fps is unreached/unverified on the Apollo. Hardware remains unavailable.
The 4-byte trial stays archived; its speed also needs symmetric setup before any
hardware recommendation. Avoid repeating already rejected sprite/MOVEM/unroll
experiments. Another possible renderer lead, not yet implemented, is reusing the
original colour-specialized narrow-span AND/OR table for the two edges of a
wide span instead of its per-plane BFINS loop; inspect/trace before patching.
