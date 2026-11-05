# Ferrari Formula One performance plan

Improve visible motion and input response on the A500 through accelerated AGA
machines while preserving the game's handling, race rules and season timing.
Aim for one new presentation per display field where the measured workload
allows it; this is a target, not a prediction of 50 FPS. A higher drawing rate
must not make the car, opponents, fuel consumption or clocks run faster.

Follow this plan in order. Each step has an exit condition. The structure follows
Hard Drivin' `H/HardDrivin/usr/source/PERFORMANCE_PLAN.md`, but its addresses,
measured rates and chosen simulation design do not apply to Ferrari.

## Current status and source references

Steps 1-4 and the selected S0-S3/B3-B8/C1-C4 implementation are complete in their
documented scopes. Production integration now passes on SPS 0481 PAL A500,
A500+Fast, chip-only 020 and 020+Fast. See the closure at the end of
STEP5_CAPACITY.md and manifest/production-integration.json. The authoritative
slave includes the default-off engines; the frozen v1.01 release is a baseline.
The selected intervals are 200 ms / native 100 ms / 20 ms player with native
100 ms opponents, respectively. The user's no-fallback decision and matched-
workload no-regression C4 gate supersede earlier fallback proposals below.
Calibrated030/040/060 analysis and Step-7 emulator release qualification now
pass; see manifest/release-qualification.json and the final capacity closure.
Human playtesting, including full races, and real Amiga hardware are deferred
by the user. The local opt-in RC1 is reproducible and unpublished. C4-T01 remains
an optional optimization shortfall. The historical work plan below is retained.

Read these before implementation:

- Repository `AGENTS.md` and `tmp/manifest/project.json`.
- Authoritative source `src/FerrariFormulaOne_WHD.s`.
- The preserved installer's `ReadMe` and `Manual` under
  `tmp/installer/FerrariFormulaOne/FerrariFormulaOne_Install/`.
- AmigaXDev `docs/playbooks/new-game-playbook-stingray.md`,
  `docs/playbooks/fixed-time-simulation.md`,
  `docs/playbooks/simulation-and-presentation.md`, and
  `docs/reference/measurement-method.md`.

Stay on `ferrariformulaone`. Keep source modules game-prefixed in `Games/`;
keep tools, captures, private disassembly, game data and builds in ignored
`tmp/dev/`. All paths below are relative to the worktree root. Do not copy
another game's source offsets, state comparator or timing constants unchanged.

## What the existing slave establishes

The v1.01 slave boots through KickEmu 1.3 and loads `racemenu` using DOS LoadSeg.
The ReadMe identifies overlay hunks and C code. The slave requests 512 KiB chip
memory and zero expansion memory; this does not establish the placement of all
DOS allocations or the total WHDLoad memory requirement. The ReadMe specifies
another 1.1 MB for preload and the Kickstart ROM.

`DEBUG` is defined in the published source. It changes the data directory and
banner and adds an RMB wait in the SPS race hook. `CACHE` is commented out.
Actual cache state must be read from the running configuration, not inferred
from that one directive. The header already has `slv_Version = 17` and a config
string. CUSTOM1 is occupied: **1 disables the existing timing fix**.

The source supplies these anchors. `load:` means an offset in the loader region
addressed by its patch list; verify its hunk identity during mapping. `race:`
means an offset from the runtime `a1` base in `.patchhunk`. These are not file
offsets or permanent Amiga addresses.

| Anchor | SPS 0481 | Irek version | Purpose shown in source |
| --- | --- | --- | --- |
| `racemenu` file length | 199368 | 199500 | Version selection |
| `load:$02e6` | Patched | Patched | Calls the overlay patch hook |
| Delay skips | `load:$07aa`, `$0864` | `load:$0816`, `$08d0` | Skip existing delay instructions |
| `fixdelay` replacement | `load:$2236` | `load:$22a2` | Shifts `d0.w` left by two and calls `resload_Delay` |
| Race discriminator | `race:$6662 = $2250` | Same expression | Identifies a race overlay candidate |
| Screen pointer fix | `race:$0ab0` | Not installed | Sign-extends `d1` before original use |
| Wrong blit fix | `race:$6652` | Not installed | Changes long subtraction to word subtraction |
| `fixtiming` call | `race:$589c` | Same expression | Installed unless CUSTOM1 is set |

`fixtiming` preserves the displaced `asl.w`, `ext.l` and `move.l` work, then
loads `graphics.library` through Exec `$9c` and calls WaitTOF (vector `-270`)
twice, saving `d0-a6` around the calls. Step 1 verified the live library name
and the shared NDK vector definition. Two calls alone do not prove two fields per
rendered frame or a 25 FPS ceiling: establish call frequency and phase first.

The Irek hook's comment names a different hunk start, while the timing patch
uses the same subtraction as SPS. Preserve that distinction and verify runtime
bases and bytes; do not mechanically shift every offset. The available local
game is SPS 0481. The Irek version remains unvalidated until supplied locally.

## Step 1 Establish a reproducible baseline build

1. Verify archive, source and executable hashes against the manifests. Confirm
   `tmp/dev/` is ignored and the working tree has no unrelated edits. Keep the
   pristine extracted drawer read-only in practice; run disposable copies.
2. Prepare `tmp/dev/amiga/` and `tools/` from the shared environment.
   Use AmigaXDev's environment variables and shared Python libraries. Give the
   harness its own emulator PID, debugger port and run directory. Quote paths
   containing spaces and stop only this harness's processes.
3. Build the imported source first, resolving `SOURCES:` includes locally to the
   shared WHDLoad/NDK files. Preserve its Latin-1 banner and line endings. Then
   make a separately identified release-equivalent build with DEBUG disabled,
   data directory `data`, and no debug RMB wait. Record every adaptation and
   dependency version. Do not mix these changes with performance patches.
4. Keep shipped, rebuilt release and VERIFY slaves separate. Record their hashes
   in each run and make the launcher fail if the selected slave is missing.
   Explicitly select the slave; never silently fall back to the shipped one.
5. Boot the shipped slave, then the release rebuild, with CUSTOM1=0 and =1.
   Use emulator warp to reach the automatic non-interactive demo without input;
   its long startup is not part of a performance window. Step-1 correctness
   captures may retain warp, as the shared playbook permits; make no performance
   claim from them. For timing captures, turn warp off at a verified demo anchor
   and allow a recorded settling interval first.
   Verify title, menus, demo, entry into driving, leaving the track, return to
   pits and F10 quit. Save files go only to the disposable drawer.
6. Compare loaded game bytes after relocation normalization, stable screens and
   decoded game state at matched events. Once step 2 supplies the state map,
   repeat with per-field and completed-update snapshots. A changed KickEmu can
   change placement and scheduling. If needed, compare a locally padded original
   at the same layout, but retain the ordinary shipped comparison too.

Exit: a documented build/run command in `docs/profiling.md`, identified
build differences, and a release rebuild whose observed equivalence to the
shipped slave has an explicit scope. Unexplained race or timing differences
block using the rebuild as a performance baseline.

## Step 2 Map and validate the automatic demo — complete

Scope clarification: the automatic demo is the performance workload. Interactive
menus, driving tapes and season save/load are deferred until an implementation
needs that coverage. They are not prerequisites for measuring this demo.

1. Trace the loader hook through startup. Catalog HEADER identities, hunks,
   relocations and BSS; decode the active resident/race segment table at the
   settled demo anchor. Treat reused hunk slots as belonging only to their active
   overlay. Preserve startup traces for later lifetime investigations.
2. Locate the race loop, eight-car update return, completed-drawing barrier,
   publication and geometry preparation. Establish the existing timing hook's
   location and task versus interrupt context. Record calibrated addresses and
   overlay-relative identities in `game.md`; resolve again for other profiles.
3. Cross-check visible publication using both bitplane DMA bank changes and
   cropped game-image changes. Keep update, draw-barrier, publication-request
   and actual visible-presentation counts distinct.
4. Record a bounded state inventory for all eight cars, controls, progress,
   clocks and RNG. Retain opaque condition/state blocks without inventing units.
   Exhaustive writer and time-domain semantics belong to step 4.
5. Reach the demo with warp and no input. Anchor by completed updates, switch
   actual emulator warp off, verify readback, and record the settling fields.
   Repeat from fresh boots with the identical slave and machine configuration.
6. Capture completed-update state and field-level DMA/pixels. Require identical
   fresh-boot anchors and field observations. Validate the state comparator with
   a later demo state and a deliberately altered speed byte; normalize only the
   two proven RNG pointers.
7. In a separate diagnostic build, add three WaitTOF calls after the completed
   drawing barrier and before publication. Compare the sampled state at the same
   completed update with the normal demo. Autonomous controls provide the
   no-external-input control; this does not prove elapsed-time correctness.

Exit evidence: `game.md`, `manifest/step2-overlays.json`,
`manifest/step2-state-checks.json`, `manifest/step2-validation.json`, and the
retained fresh-boot demo captures. The first machine's discovery tools remain
explicitly SPS/A500-specific. No guessed offsets are approved for release patches.

## Step 3 Measure the machine matrix and rendering ceiling — complete in focused scope

Completed: 68000, 68020 and 68020 + Fast. The already captured A500 + Fast
baseline is retained as additional evidence. 030/040/060 rows and their MMU
checks below are deferred, including references in later steps, until scope is
expanded. No interactive/contact-specific worst case is claimed by this demo.

1. Define these PAL profiles, recording exact clocks, chipset, memory banks,
   Kickstarts, emulator version, cycle settings and cache flags:

   | Profile | CPU | Memory starting point |
   | --- | --- | --- |
   | A500 | 68000 at PAL stock clock | 512 KiB chip, 1.5 MiB slow |
   | A500 Fast | Same | Same plus 2 MiB Fast |
   | A1200 stock | 68EC020 at stock clock | 2 MiB chip, no Fast |
   | A1200 Fast | Same | 2 MiB chip, 4 MiB Fast |
   | A1200 030 | 68030 at 50 MHz | 2 MiB chip, 8 MiB Fast |
   | A4000 040 | 68040 at 25 MHz, then 40 MHz | 2 MiB chip, 8 MiB Fast |
   | 060 | 68060 at 50 MHz | 2 MiB chip, 8 MiB Fast |

   Verify that each boots with the intended preload policy. If memory is
   insufficient, record the constraint and a separately named runnable profile;
   do not quietly give the baseline Fast RAM. Record actual code/data placement.
2. When the deferred scope resumes, use cycle-exact non-MMU 040/060 profiles for comparative emulator timing, and
   separate MMU-enabled functional runs. Calibrate frequency/chip timing and
   counter behavior for each core. Unsupported instruments produce `unavailable`,
   not a zero. Emulator rates are not claims of measured real-hardware rates.
3. Start with DEMO as the no-input baseline: use warp through startup, disable it
   at the verified demo anchor, then apply the same settling interval in each arm.
   Capture 1,000 settled fields of the automatic DEMO, twice from fresh boots.
   Select a traffic-heavy interval within the demo where available. Add interactive
   DRIVE, CONTACT and SESSION routes only when a proposed change requires them.
   Use a 500-field subset for detailed profiles. State its exact anchor and bounds.
4. Record presented FPS as `new presentations × measured field rate / fields`,
   mean/p50/p95/p99/max frame intervals, render and simulation rates, and work time
   excluding synchronization. Profile self/inclusive routine cost, both timing
   waits, blitter waits, interrupt cost and CPU/blitter/bitplane/copper bus usage
   where supported. Record cycles per completed simulation update, including the
   worst measured contact and dense-traffic updates.
5. Use breakpoint-free timed windows and calibrated in-memory counters or a
   validated read-only observer. Read results outside the window. Use debugger
   breakpoints for discovery/state capture, not as the acceptance timing clock.
   Check trace support and overlay coverage before trusting routine percentages.
6. For each profile measure CUSTOM1=0 and =1. Label CUSTOM1=1 as a diagnostic
   uncapped/native-timing arm until step 4 proves game speed. Measure time spent
   inside `fixtiming`, including scheduling effects, and in `fixdelay` separately.
7. On the fast profiles isolate the ceiling with one VERIFY change at a time:
   existing timing wait bypass; expensive drawing omitted while preserving frame
   bookkeeping; and instant blitter if the emulator exposes a validated setting.
   Keep identical workloads using a fixed simulation trace or matched completed
   updates when the native simulation is frame-coupled. Omission arms estimate
   ceilings only; they are not playable improvements.
8. Rank candidates by measured share and opportunity on each machine. Distinguish
   a wait cap, CPU work, chip-bus traffic and blitter latency. If the wait costs two
   fields per frame, establish whether work overlaps either field before predicting
   the attainable cadence.

Exit: `docs/PERFORMANCE.md` contains the baseline matrix, calibration,
workload hashes, bottlenecks and evidence limits. No numeric Ferrari FPS target
beyond the display ceiling is committed before this step.

## Step 4 Establish the game time model and choose a design — complete in documented analysis scope

1. Audit every time source: VBL, CIA timers, timer.device/OS calls, boot benchmarks,
   loop counters, audio interrupts and scripted time jumps. Measure each clock
   against emulated elapsed time. Resolve the two `fixtiming` calls here if not
   already resolved, including whether another task advances during them.
2. Run the automatic demo first on A500, A500 with delayed drawing and 020 Fast
   (040 deferred); add DRIVE only when input-dependent semantics require it, with both CUSTOM1
   settings. Compare state per completed update with identical consumed input,
   then per elapsed field with field-indexed input. Separate input differences,
   unfinished updates, clock epochs and RNG calls from actual timing defects.
3. Build a units/writers/consumers table for movement, AI, steering ramps, gears,
   boost, fuel, wear, temperature, damage, sound, animations and all clocks.
   Determine which are per-frame, per-update or independently timed. Include
   passenger/demo behavior and any replay feature only if found in the game.
4. Preserve Ferrari's clock domains. The manual says time runs from boot, repair
   and travel are accelerated, and session preparation consumes time. Measure
   the native behavior of menus, ESC pause, garage work, tow, transport, results
   and save/load. Do not impose a blanket rule that all menus freeze world time.
5. Establish the intended simulation rate from independent evidence: stock A500
   behavior, track distance versus indicated speed, lap/session clocks, manual
   expectations and the shipped timing fix. Record uncertainty. Neither the
   two waits nor A500 render FPS alone determines the correct physics rate.
6. Price a simulation update on each machine. For a proposed fixed rate `f`,
   estimate `f × update cycles / available CPU cycles per second`, then include
   drawing, audio and interrupts. Validate capacity with a logic-only experiment
   in both traffic and contact cases. Reject any rate that accumulates unbounded
   debt or leaves the A500 below the agreed rendering floor.
7. Select the smallest design that meets correct speed and smoother presentation:

   | Evidence | Design to evaluate |
   | --- | --- |
   | Simulation already timed independently | Retain it; remove only redundant render pacing and preserve display synchronization |
   | A native fixed update is affordable | Schedule that update by elapsed time; draw independently; evaluate presentation smoothing |
   | Frame-coupled integration with a complete units audit | Evaluate a measured frame-time step with fractional state and bounded substeps |
   | Fine updates unaffordable on 68000 | Keep its validated native/coarse path; use finer updates only on capable profiles |

   Document cadence, latency, collision behavior, precision, CPU cost and fallback
   before choosing. A material handling change needs the user's choice; routine
   measurement and behavior-preserving work can continue independently. Do not
   inherit Hard Drivin's 6.25 Hz or its chosen variable-step design.

Exit: `docs/GAME_TIME.md` contains the state inventory, coupling results,
reference-rate evidence, capacity measurements and chosen design with acceptance
criteria. This is the gate before uncapping normal gameplay.

## Step 5 Implement correct speed and smooth presentation

Design revision (2026-10-12, updated after the step-5 capacity profile): select
the update interval by CPU class **and Fast memory**:

| Machine class | Interval | Opponents |
| --- | --- | --- |
| 68020 or better with Fast memory | **20 ms** | 14 MHz 68020: unchanged native 100 ms step on the pulse quantum (Plan B); 20 ms only after the escalation gate |
| 68020 or better without Fast memory | Coarse path: unchanged native 100 ms step (proposed) | With the player |
| 68000 | Coarse path: native 100 ms first; 200 ms with ×2 conversions only if 100 ms fails and the user agrees | With the player |

Stock 68020 without Fast memory is no longer a 20 ms profile. Detect Fast memory
from WHDLoad's side, not the guest Exec. 030/040/060 follow the same rule but stay
deferred. `STEP5_CAPACITY.md` holds the profile, the cycle budgets and the ordered
steps S0–S3, B3–B8 and C1–C4 with their gates. It supersedes the earlier "20 ms
for all cars on every 68020+" capacity reasoning: eight cars at 20 ms do not fit
on a 14 MHz 68020 even with zero conversion overhead.

Both paths must preserve game-time speed, independently of drawing. On the 20 ms
path, implement the units/timebase conversions below for the player; do not run
an unchanged native tick every 20 ms. The coarse path runs the native step at its
own 100 ms game-time quantum, so it needs no rate conversion. Never slow game time
to fit a CPU. Keep the performance mode default-off until the interval, handling,
clock and drawing-rate gates pass on each advertised profile. Keep native modal
code and validate every touched transition at runtime.

1. Reserve CUSTOM1's existing meaning. Proposed CUSTOM2 enables the new performance
   mode, initially off. With CUSTOM2=0, CUSTOM1=0/1 must reproduce the corresponding
   rebuilt legacy paths, including both SPS bug fixes. With CUSTOM2=1, the new time
   controller owns race pacing; explicitly document that CUSTOM1 controls only the
   legacy path. Keep diagnostic switches VERIFY-only.
2. Add a monotonic elapsed-time source with measured PAL/NTSC rate and fractional
   conversion carry. Track active simulation time separately from live UI/season
   time, using the measured native modal boundaries. Handle wrap, resets, loading,
   save/load and overlay replacement; do not keep stale overlay pointers.
3. Select the interval by CPU class and account for completed, pending and consumed
   time using that interval. Do not change it dynamically to hide overload.
   Apply the input belonging to each logical tick; one-shot commands execute once.
   Bound catch-up batches so input/audio remain serviced. Instrument backlog,
   overflow and any discarded/rebased time. A saturated CPU must not silently
   report correct speed.
4. For both CPU-specific intervals, implement the units audit quantity by
   quantity: integrated increments scale with the step, explicit step-squared
   terms with its square, derivatives with inverse step, and retention with
   `r^step` (20 ms player path; opponents only after escalation). Keep collision impulses, thresholds and corrections distinct from
   continuous forces. Preserve fractional accumulators and update them through
   every reset, pit and contact writer. Analyze original integration order;
   smaller Euler steps change displacement even when final speed matches.
   Bound long steps using measured contact tests and price all required substeps.
5. Convert frame-counted deadlines to elapsed time only where the audit calls for
   it. Keep intended season jumps and accelerated repair/travel semantics. Audit
   opponent updates, RNG consumption and audio separately from player motion.
   Accumulate fractional time for native tenth-second clocks and preserve the
   elapsed-time rate of rotating wear updates and probability trials; do not
   multiply their frequency by five on the 20 ms path.
6. If drawing outpaces simulation, snapshot the inputs actually consumed by the
   cockpit and demo render paths. Blend only render copies. Interpolation adds
   one tick of latency; extrapolation can overshoot contact. Choose explicitly,
   wrap angles/track coordinates correctly and reset at cuts, tow and track loads.
   Verify that intermediate displayed poses change. Skip this cost on a slow CPU
   when it cannot draw more than once per simulation update.
7. Retain a safe display handoff and every required blitter/DMA dependency. Removing
   the timing limiter must not introduce tearing, drawing into a displayed buffer
   or reuse of a bitmap still owned by DMA.
8. Validate before renderer work: native-step/matched-input controls reproduce
   original decoded simulation state; elapsed simulation time is within 1% of
   nominal over at least 60 emulated seconds when capacity permits; clock error
   and pending work stay within the documented scheduling bound. For changed
   integration, define position/heading/braking tolerances from measured units
   before comparing results, and classify all residual differences.
9. Test normal, deliberately slow and fastest drawing; steady acceleration,
   braking, steering reversals, manual gears, boost, contact, off-track recovery,
   traffic, pause, pits, tow and season transitions. Measure input-to-visible
   response as well as FPS. A person should drive the A500 and 68020 paths before
   accepting changed handling.

Exit: correct-speed gameplay with bounded time accounting across the supported
matrix. Proposed A500 gate: no more than 3% loss in presented FPS in each fixed
workload versus the rebuilt legacy baseline, and no new long-frame problem.
Treat this as an engineering acceptance threshold, not a measured result. If
it fails, optimize the blocking work or retain the legacy path for that profile.

## Step 6 Optimize the measured expensive work

Order these candidates by step 3's measurements. They are investigations, not
claims that Ferrari uses a particular polygon, sprite or conversion pipeline.
For each candidate estimate the maximum frame-time saving from its measured
share, build one gated change, and retain it only when an A/B resolves a benefit.
A candidate below roughly 3% of a frame needs a cheap implementation or a clear
reason such as improving the worst frame.

1. **Placement and overlay lifetime.** User requirement: place all eligible code
   and data in public Fast memory when available, not only hot routines or 020+
   code. Inventory resident and overlay code, constants and lookup tables, game
   state, stacks and CPU workspaces. Keep every custom-chip-accessed buffer in
   chip RAM: display bitplanes, copper lists, hardware sprites, audio samples,
   and blitter sources/destinations. Split mixed allocations where references
   and ownership can be preserved; unclassified allocations are not yet cleared
   for relocation. Use MEMF_PUBLIC for eligible allocations and let the allocator
   prefer available Fast memory, with its natural fallback on no-Fast machines;
   do not require MEMF_FAST or add a separate Fast-first allocation scheme.
   Handle allocation failure cleanly. Account for
   WHDLoad/KickEmu memory ownership; the existing guest Exec pool did not expose
   the configured Fast bank. Trace all pointers, absolute and PC-relative
   references, executable writes, overlay reload and deallocation. Prefer proper
   loader relocation over permanent duplicate copies and entry trampolines.
   Validate addresses, memory budget, allocation failures, reloads and decoded
   game state before accepting a placement change. Price placement independently
   from arithmetic changes on the current 68000, stock 68020 and 68020 + Fast
   profiles; keep 030/040/060 deferred. The two-hunk code-only diagnostic is
   evidence for a benefit, not completion of this requirement.
2. **Cache safety.** Audit every executable write, including both `.patchhunk`
   paths and any generated/self-modifying drawing code. The source makes direct
   writes here; establish where cache coherency is currently guaranteed and add
   a flush after the final write when required. Flush each reload, not only boot.
   Test supported cache settings separately and repeat with the 040 MMU enabled.
3. **Drawing inner loops.** Identify the actual dominant road/scene routines from
   traces. If planar spans dominate, test aligned long stores and specialized
   plane paths. If transforms/divisions dominate, consider register allocation,
   precomputation or CPU-specific arithmetic only with identical signed overflow,
   rounding and precision. If conversion dominates, measure changed pixels and
   data movement before replacing the conversion method.
4. **Blitter and bus traffic.** Inventory each expensive blit's inputs, output and
   first consumer. Compare CPU fills versus blitter fills on the matching chipset
   and memory configuration. Overlap work only across proven independent regions;
   keep a barrier at the first dependent read/write. Never delete a wait solely
   because it was cheap or appeared unnecessary in one trace.
5. **Dashboard, scenery and overlays.** If redraw cost is significant, cache static
   content or use per-buffer dirty regions. Account for road/objects behind the
   dashboard, both screen buffers, palette changes, damage displays and menus.
   Confirm invalidation on every overlay and track transition.
6. **Simulation hot spots.** If step 4 found simulation capacity limits, optimize
   the measured player/AI/contact routines with exact arithmetic before raising
   their cadence. Keep the original physics as the comparison oracle.

Every replacement must have whole-instruction hook boundaries, preserved calling
convention/registers/flags, CPU and memory gates, and a named `PERF_RANGE` keyed
by version and overlay. For arithmetic or rasterization, run original and new
routines on captured inputs in VERIFY, compare state or all output planes plus
surviving registers/flags, and guard scratch buffers. Add an independent model
where numerical changes warrant it. Twin/oracle cost is never a release FPS.

After each accepted candidate, run same-build option-off/on comparisons in the
same session and fixed windows on all affected profiles; smoke-test the rest.
Use matched workloads, final-state hashes and cycles per completed call. Repeat
plain-build timing without diagnostic probes. Report frame work time separately
from presented FPS, since a wait may absorb the saving. Reject regressions or
select the winning path at patch time. Do not accumulate unverified changes.

Exit: `PERFORMANCE.md` lists each candidate's measured effect, CPU gate and
accepted/rejected disposition, with updated current matrix figures.

## Step 7 Validate versions and integrate the release

1. Build `check_disabled.py` around version/overlay-specific `PERF_RANGE` records.
   Compare the performance-disabled runtime with the same rebuilt legacy slave
   for both CUSTOM1 values. Existing protection/timing/bug patches are expected;
   compare their bytes with the corresponding baseline, not indiscriminately
   with the pristine game. Verify repeated overlay reloads as well as first load.
2. When the Irek executable is available, map and validate it separately. Require
   stronger verified signatures than the existing single-word race discriminator
   for new patches. If it remains unavailable, retain its existing behavior and
   gate the new mode to SPS; state that limitation. Unknown code must never receive
   speculative performance offsets.
3. Run the final machine matrix, cache variants and MMU functional check. Check
   NTSC only with the actual field rate verified; retain/document any pre-existing
   video-mode restriction rather than claim untested support.
4. Cover F3 and F1 controls, Fiorano, Rio, at least one contrasting track such as
   Monaco, race starts, traffic/contact, lap completion, fuel/wear, pits/tow,
   pause/resume, session transitions, results, season save/load and F10 exit.
   Compare repair/travel jumps and season clocks with the legacy behavior.
   Have a person complete a race on A500 and an accelerated profile.
5. Keep `slv_Version = 17` unless a newly required API/header feature requires more.
   Validate on the stated minimum runtime and the development runtime. Keep new
   performance mode off by default until all its advertised profiles pass. Publish
   explicit CUSTOM1/CUSTOM2 interactions in the release notes and source comments.
6. Audit the normal slave for absence of VERIFY tapes, counters, delays, test
   entrypoints and pinned RNG. Build from authoritative source with a recorded
   toolchain. Keep package generation and any installer ReadMe edits under the
   ignored harness unless deliberately contributed through the upstream workflow.
7. Update the manifest's validation status, local `PERFORMANCE.md`, `GAME_TIME.md`
   and `open-work.md` in place. Put reusable discoveries in AmigaXDev documentation;
   keep Ferrari offsets and state layouts here.

Exit: a reproducible release candidate with correct speed, a proven disabled
path, measured improvements for each advertised profile and clearly stated
version/hardware limitations. Do not claim real-hardware validation without it.

## Commit and evidence rules

This plan and the harness stay in ignored `tmp/dev/`. Future commits contain only
coherent Ferrari source changes, staged by explicit path. Before committing,
verify effective author and committer are Vesa Halttunen <vesuri@jormas.com>,
including environment overrides; signing is disabled for commits, tags and
pushes; and `core.hooksPath` is `/dev/null`. Never run hooks or add attribution
trailers. Verify the Vesuri account before any GitHub operation.

Do not commit game bytes, archives, SDK copies, dumps, input recordings, traces,
screenshots, built slaves or host-specific paths. Keep measured facts, derived
bounds and hypotheses distinct. Each performance result names its build hash,
configuration, cache state, workload, instrument and completed capture window.
