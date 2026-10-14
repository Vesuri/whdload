# Open work

## Current state

**Phase 13 investigation, P13A1–P13A4, P13B1–P13B3 and P13C1–P13C4 are complete.** The OCS loader, four-plane blitter
conversion, memory ownership and timing anchors are mapped in
[internals](internals.md#phase-13-ocs-static-investigation). The
[ordered OCS work items P13A1–P13E3](ocs-plan.md) cover shared CD32 mechanisms,
68000 safety, measured blitter/CPU selection and Amiga 500/Fast RAM acceptance.
The OCS slave rebuilds byte for byte with input/revision and displaced-site
guards. The isolated native display/pixel and allocation/ownership checks pass.
The explicit OCS launcher and live locator pass matched original/rebuilt boots
through intro, menu, simulator and visible name entry on the nominated A500.
The short calibrated stock-clock A500 baseline measures 5.79 displayed pictures/s
in asteroid credits and 5.39 during simulator flight/fire. Native publication and
actual display counters agree; observer-off state/pixels match at eight checkpoints.
Normal OCS builds retain native conversion; C2 runtime arms remain diagnostic-only. Compile-time variant maps
and explicit build/analysis selection now preserve all checked CD32 binaries and
original OCS bytes. The shared 68000 ISA alternatives pass arithmetic, flags and
wrapper checks; full OCS linking and native ABI integration remain later gates.
Shared instrumentation now distinguishes world ticks, rendered sources and actual
OCS display changes, with strict state/pixel/allocation/ownership checks. The
callable OCS recorder passes CPU/replay checks; live guest hooks and their overhead
remain later integration. The retained native observer-off control remains exact.
Experimental Kalms word/longword converters now pass native/oracle pixel and
bounds checks with shared checkerboard adaptation and explicit native fallback.
C2 now measures the full adapters, matched source images and actual display changes.
Native wins the measured 68000 and no-Fast 68020 profiles; CPU/Fast longword wins
the measured 14 MHz 68020/Fast profile. Flight requires rebasing compositor shadow
rows and copy-command pointers as well as the primary source. Normal builds are
unchanged. See the [C2 gate](internals.md#p13c2-measured-ocs-converter-crossover).
C3 selection and explicit native/CPU override pass the bounded live gate, with
pre-move memory fallback, once-only selection and unchanged cache policy.
A separate C4 candidate now installs allocation/conversion hooks at startup,
chooses source ownership before compositor aliases, and safely unwinds partial
setup. Controlled native display teardown passes on both backends, with no stale
DMA reads after release. The combined Chip workspace remains available for
fallback. The tested launcher floor is 512 KiB Chip plus 4 MiB Fast.
See the [C4 ownership gate](internals.md#p13c4-backend-specific-memory-ownership).
See the [C3 gate](internals.md#p13c3-conservative-backend-selection).
P13C5 publication acceptance is next; CD32 E1 and phase 12 remain
paused. See the [P13A4 baseline](internals.md#p13a4-short-native-ocs-baseline) and
[P13B3 scope and checks](internals.md#p13b3-shared-instrumentation-and-validation-interfaces).

The following completed implementation results concern **CD32**:

Phases 1–3 are complete. The reconstructed slave is byte-identical. Original
and reconstructed English boots match all four live game hunks and every screenshot
pixel at the menu and simulator/name prompt for Custom5=0–3. VERIFY off/on marker
checks and equal-size control comparisons pass at both endpoints.
Derived source, executable bytes, disassemblies and captures remain under `tmp/`.
The unskipped intro has 31 identical milestone captures across two fresh boots.
The publication ledger, full traces and independent SWAP_ONLY check agree. The
stock 020 multiplier and numeric-frequency scaling are calibrated for the emulator.
**Phase 4 is complete under the user-approved practical-baseline scope.**
The eleven-configuration scene baseline, cache audits, source-change census,
DMA/STOP idle controls and matched c2p, instant-blitter and scoped bitmap-drawing
ceilings are recorded. Eight configurations pass combined callback validation.
All phase 4 captures and consolidation jobs are terminal. Phase 5 analysis is
complete, using the supplied PC video for visible motion cadence and displacement.
Phase 6 rendering work is complete: measured converter selection, native/live
output checks, cache-preserving gating and display-end publication are recorded.
The user deferred further timing investigation to gameplay; exact scene-duration
neutrality remains an explicit gap. Phase 7 gameplay timing and state investigation is complete: reproducible flight
windows, representative costs/source changes, state cadence and render coupling
are documented. The native flight-unit anchor is 10 updates/s. Phase 7b is complete:
the world-update dispatch inventory, FR-01–FR-23 and B/C/D audit costs are recorded
in [the framerate audit](framerate-audit.md). Native 68000/68040 reproductions pass
with steady/changing rates and explicit runtime/instrument gaps. Phase 8 is
complete: the user selected D on 2026-10-13, with the explicit pricing gaps in
[the design comparison](timing-design.md). Phase 9 is complete: the gated 10 Hz
world, responsive player/camera path and required clock owners pass the scoped
[native/live gate](internals.md#phase-9-decoupled-simulation-gate). Phase 10 is complete: bounded renderer-only prediction, transient allocation
isolation and real-flight validation pass the [presentation gate](internals.md#phase-10-renderer-only-prediction-gate).
Phase 11 is complete: changed-block flight conversion passes native/live output,
measured conversion-time and PAL/NTSC timing gates. Phase 11b frame-rate
recovery is required before release. A1/A3 measured the frame budget:
Psygore's default limiter caps flight at 25 FPS, the emulated machines reach
40–50 with it off, and no credible 040 model exists yet (A2). Phase 12
release polish is paused behind it; OCS implementation is planned separately. B1 is complete:
public CUSTOM5=0 enables uncapped English flight, 1–4 retain Psygore's modes,
and CUSTOM1 selects language only. The cached 030 model reaches 49.920 pictures/s;
the uncalibrated cycle-exact 040 core reaches 39.953 at the B1 gate.
B2 is complete: queued early-VBL swaps and pre-conversion ownership waits retain
two buffers. Both PAL model gates now report 49.920 displayed pictures/s; the
030 NTSC gate reports 59.826. The cached-040 horizontal-row corruption is traced
to FS-UAE using read-ATC cache attributes for write-ATC hits; the local emulator
correction preserves both caches and the B2 slave. See the
[CPU/DMA pixel evidence](internals.md#cached-040-display-corruption-emulator-mmu-write-attributes).
C1 is complete: render prediction includes both the upcoming publication and
pending swap. PAL/NTSC display ledgers match every forecast to its actual field.
C2 is complete: controlled player velocity/position advance per field, with zero
world-tick position corrections in the steady and turning gates. C3 is complete:
heading-aware ship forecasts retain native inertia, with p95 0.255 km and maximum
6.348 km error on the retained hard-turn world-ship sample. Constant-velocity
classes stay exact. C4 confirms one displayed picture per field in steady flight
on both required models, with no scheduler change needed. D1’s practical model
profile is complete: geometry, cockpit composition and comparison overhead
justify the D2–D4 investigations. D2 is complete: selective pose backups and
unchanged-input geometry retain 49.920 frames/s in both steady gates and improve
the 040 held turn to 42.087. Calibrated 040 profiling remains blocked on A2.
D3 is complete: native view-region clear/composition keeps exact pixels and
49.920 frames/s in both steady gates; the 040 held turn reaches 42.493.
D4’s practical comparison-cost gate is complete: compact full-image comparisons
reduce the 040 model’s residual cost by 0.84 ms per picture, with 43.424 frames/s
in its held-turn window. Drawing-based dirty rectangles remain deferred.
D5 is complete on the current models with unchanged converter selection.
The user excludes real-hardware validation at this stage; A2 remains separate
follow-up work. Stop before E1. Held-turn frame-budget misses remain; campaign and hardware
visual acceptance remain open.

The user accepted the practical baseline with documented gaps on 2026-10-12.
General routine self/inclusive attribution, complete interrupt and blitter-wait
accounting, unaccepted callback controls and a broader drawing ceiling are
explicitly deferred. These are not claimed complete. Revisit a gap when a future
change requires that evidence; do not expand the matrix merely to fill it.

The executable uses the Manx/Aztec C runtime and a View/copper display path with
two eight-plane buffers. The original slave explicitly requests cache settings.
Its normal c2p limiter waits two CIA-A TOD increments; that is not an intended-rate
measurement. In the original slave, `Custom5=4` selects the blitter c2p path, not Akiko.
The public-option candidate removes it and uses 4 for Psygore slow. These
findings refine the implementation assumptions below; flight now uses the selected
10 Hz design, including the English ship/title and asteroid intro. Native and
model gates pass; music and credit deadlines remain native. See the
[intro gate](internals.md#intro-10-hz-world-and-extrapolated-presentation).
The separate Origin logo remains native. OCS static findings and pending
implementation are recorded under phase 13.

## Goal

A definitive CD32 edition, OCS afterwards and separately:

1. Game time independent of rendering: the game plays at the intended speed on every
   supported CPU, and fast CPUs show more frames rather than a faster game.
2. Rendering as fast as the hardware allows: Kalms c2p, chunky and drawing work in
   fast RAM, FMODE 3 fetch, CPU caches, sensible buffering and frame pacing.
3. No regressions in faithfulness: original behaviour stays reachable (CUSTOM gating),
   every change is measured and validated against the original.

## Decisions made

- **Hardware envelope.** Fast RAM is required; a stock CD32 or an A1200 without fast
  RAM is not a target. Akiko support and the existing `Custom5=4` option are to be removed.
  Phase 1 identifies the latter as the original blitter path in the existing
  slave; it must not be used as an Akiko baseline.
- **Caches (future slave policy).** Leave cache state to WHDLoad and its user
  options. The original slave explicitly calls SetCPU (phase 1 finding). Every
  measurement records the hardware cache state (`CACR`) it ran under.
- **Design.** The user selected D on 2026-10-13: a 10 Hz world, responsive
  per-render player orientation/camera and bounded world-object extrapolation
  as the initial presentation approach to validate. A fixed tick with only
  presentation smoothing remains rejected. The flight time model, framerate
  audit, eleven-cell pricing and ownership contract are in
  [the design comparison](timing-design.md).
- **PC reference.** Use the supplied 86Box/eXoDOS recording as a practical external
  pace reference alongside the Amiga time sources and music. It represents the
  recorded experience, not proof of an original design rate or identical port code.
- **Frame-rate recovery (user, 2026-10-13).** Under D the enhanced modes render as
  fast as they can with vsync on and no frame cap; game logic stays at its own rate.
  Psygore's `Custom5` limiter is retained only in Psygore's modes. The player's
  translation, not only orientation, advances every field. Other objects are
  extrapolated (not interpolated), along their predicted heading. See phase 11b.

## Intended speed: working estimate

**Flight-unit anchor: 10 world updates per second.** Phase 7 verifies that a
displayed 200 kps corresponds to 20 km per update. This supersedes the unmeasured
15/s prior. The experimental timing build uses this rate; it does not establish every
animation/AI cadence. Do not transfer intro evidence to flight.

**Intro decision: 10 native world updates per second**, matching flight, with
bounded renderer-only extrapolation between updates. The user selected this
working target; it is not independent proof of the historical intro rate.
Do not scale native displacement toward the earlier PC-derived 15/s estimate.
The PC recording is a secondary visual reference. Preserve native music and
credit-text deadlines. Implementation and validation are now in progress.

Rate choices use the following evidence before implementation:

- **Intro against music.** The music player runs from an interrupt at a fixed rate;
  phase 5 confirms music-anchored holds but also per-pass movement inside them.
  Music alone does not uniquely determine that movement rate. Use the supplied
  PC ship/explosion/asteroid cadence **and displacement**, not credit durations.
- **Flight units.** The HUD shows speed in kps and target range. The tick rate at
  which displayed range closes at the displayed speed is the rate the designers'
  units assume.
- **Psygore's `Custom5=0` limiter.** What "normal" limits to records the speed the
  existing slave considers correct.

If these disagree, all of them are recorded and the user chooses.

## Plan

Each phase ends with a gate. Do not start the next phase until its gate passes and
its results are in `docs/internals.md` (state) and `docs/development.md` (commands).
AmigaXDev's playbooks are the method; this list says what applies to Wing Commander.

### Phase 1 — Identify the CD32 install (static only; gate complete)

1. Identify `wing.english`: hunk layout, packing/compression, compiler and runtime
   (library usage, startup code), symbols if any. Compare with `wing.german`.
2. Disassemble Psygore's `WingCommanderCD32.Slave`: memory configuration, KickEmu
   version and options, cache settings, every patch (patch list with game-hunk
   offsets), the software c2p, the `Custom5` limiter, Akiko and
   `lowlevel`/`nonvolatile` replacements, and the quit key.
3. Find, by static search, every time source the game can use: VBL/`$6C` handlers,
   CIA timers (all registers, including any the music driver programs), `timer.device`,
   `graphics.library` waits (`WaitTOF`, `WaitBlit`), beam reads (`VPOSR`/`VHPOSR`) and
   the `lowlevel` timing calls.
4. Find the display path: OS screens (`OpenScreen`/`AllocBitMap`/`ChangeVPBitMap`) or
   custom copper lists; bitplane count, size and alignment; `FMODE` and `BPLCON` writes;
   how many buffers; where chunky buffers are allocated (`AllocMem` flags).

Gate: a written description of the slave and the executable, with the time sources and
display path listed as hypotheses to confirm at run time.

### Phase 2 — Harness and a reconstructed slave (gate complete)

1. Take the harness from Legends of Valour (OS game, KickEmu, no slave source, Kalms
   c2p with CPU-selected renderer patches, state-tape waits, A/B driver), retargeted to
   KickEmu 3.1 and an A1200-class machine with fast RAM. Use the shared
   `fsuae_common.sh` launcher, `amigaxdev` trace/disassembly/gdb-server tools and the
   shared debugger input route.
2. Reconstruct `WingCommanderCD32.Slave` as source and build it with vasm. Prove it
   equivalent to Psygore's (byte-identical if possible; otherwise identical patches and
   matched boots). Add CUSTOM gating and a VERIFY build that is option-disabled
   byte-equivalent.
3. First boots of the original slave on an A1200 with fast RAM, windowed and real
   speed, through `Custom5` settings 0–3.

Gate: original and reconstructed slaves boot to the main menu with identical screenshots
and state at matched points. The authorised extension also passes through the
simulator to the first pilot-name input prompt, without entering a name.

### Phase 3 — The intro window and a trusted frame counter (gate complete)

1. Define the window: boot, Origin logo, the fight/credits sequence, title, main menu.
   Mark its milestones by game state (scene/script index), not by field number.
2. Make it reproducible across boots without input (the intro must not be skipped).
   If any step needs input, use state-tape waits.
3. Find the frame publication point (buffer swap) and validate a frame counter: a full
   trace and `SWAP_ONLY` agree.
4. Record per scene: fields per frame, frames per scene, scene duration in emulated
   seconds, and music position at each scene cut.

Gate: two boots give the same milestone sequence, same screenshots at milestones,
and frame counts that match between instruments.

### Phase 4 — Practical baseline on the machine matrix (gate complete)

Scope approved by the user on 2026-10-12: finish with the practical baseline and
documented gaps, rather than exhaustive routine/interrupt accounting in every cell.

1. Retain the A1200 fast-RAM, 030/50 WHDLoad MMU/NoMMU, 040/25 NOMMU and
   060/50 NOMMU matrix, including distinct cache options. Record VERIFY `CACR`
   audits and effective emulator settings behind each configuration.
2. Record per-scene publication rates and source-change census, validated DMA
   slots and STOP idle accounting; use validated representative routine and
   callback measurements to identify major costs. State coverage and uncertainty.
3. Record matched fastest-cell c2p, instant-blitter and scoped bitmap-drawing
   ceiling experiments. Exclude the invalid blanket-clear bypass and retain its
   failure as a limitation; do not claim a complete drawing ceiling.
4. Document reproducible commands, instrument failures and deferred accounting.
   Cockpit change rates, intended game speed and rendering implementation remain
   later-phase work.

Gate passed: the measured baseline and representative bottlenecks are recorded in
`internals.md`, with commands in `development.md`. General routine self/inclusive
costs, full interrupt/blitter-wait accounting, unresolved callback-control
failures and broader drawing bounds remain explicit gaps, not gate blockers
under this approved scope. Accelerated figures describe the emulator model.
Phase 5 analysis is complete; phase 6 is now authorised.

### Phase 5 — Game-time model for the intro (analysis complete; 10 Hz selected)

1. Confirm the time sources from phase 1 with traces.
2. Coupling test: the same window on several CPUs and with VERIFY-only slowed drawing.
   Compare scene durations in emulated seconds and music position at scene cuts.
   A scene whose duration scales with draw time is frame-coupled; a scene that stays in
   step with the music is clocked.
3. Establish motion-rate candidates using the music anchor and the supplied PC
   video. Per the user's clarification, measure moving ships, explosions and
   asteroids, including displacement per advance; preserve music/text timing.
4. Document what the main loop does per frame: input, update, draw, wait, publish.

Gate reached: the mixed time model, measured motion references and a ship-update
rate candidate are documented. A uniform rate is not established by the video;
the asteroid native-step mapping is an explicit limit. The user subsequently
selected the flight-derived 10 Hz working target for the intro. The PC-derived
candidates are not installed as established facts.

### Phase 6 — Rendering, first pass (rendering complete; timing gap documented)

All rendering changes are CUSTOM-gated and retain the original path. Results and
reproducible commands are in `internals.md` and `development.md`.

1. **FAST RAM:** verified active chunky sources, loaded game hunks and the 128 KiB
   workspace in FAST in the 8 MiB setup; planar buffers remain aligned CHIP.
   Avoid a broad allocation patch where the observed placement is already right.
2. **c2p:** immutable, bit-exact Kalms specialisations; select the 030 family on
   cached 020/030. Both Kalms candidates regressed on the measured 040/060 setups,
   and Kalms 030 regressed on uncached 020, so retain the existing converter there.
   Conservative original selection covers unmeasured configurations. The enabled
   renderer rejects `Custom5=4`, the old blitter path; no Akiko path was found.
3. **Display fetch:** FMODE 3, eight-byte alignment and the corresponding modulos
   already exist in the observed copper lists. No fetch patch or freed-slot claim.
4. **Buffering:** WaitBOVP before the existing swap protects old-buffer reuse;
   retain two buffers and one publication per completed frame.
5. **Caches:** preserve WHDLoad's policy, using a zero-change-mask startup query
   for selection. No converter SMC or per-frame cache manipulation.

Rendering checkpoint: native store-level checks, live twin comparisons, the
intro state/publication ledger and matched converter measurements pass in the
recorded configurations. Rejected candidates are not selected automatically.
Fresh speed measurements for every retained-original cache cell, optional 060
cache/setup combinations and real hardware remain unclaimed.

**Timing part of the original gate is deferred**, following the user's request
to investigate timing further in-game. The existing limiter and music/text
thresholds are retained, but CPU-bound scene durations can change. The final
020 reset-to-menu window is 0.631 s longer; no universal intended rate or exact
duration neutrality is claimed. Stop here; do not start phase 7 automatically.

### Phase 7 — Gameplay windows (gate complete)

1. Use the slave's cheat options (`Custom2`, `Custom3` system, `Custom4` mission) to
   enter a chosen mission directly; build a reproducible flight window with an input
   tape on the shared debugger input route.
2. Repeat phases 3–5 for flight: frame counter, matrix profile, change rate (the
   cockpit is mostly static), and the flight game-time model.
3. State map: player ship (position, orientation, velocity, set/actual speed,
   afterburner, energy, shields, armour), other ships, AI state, projectiles and
   missiles, lock/targeting, comms video and message timers, cockpit animation,
   explosions, RNG, mission clock, autopilot and landing.
4. Writers and cadence of every state item: classify each as per-frame, clocked, or
   modal (menus, comms, pause, briefing, landing).
5. Calibrate the flight anchor (kps against range).

Gate passed: the flight time model, state-family writer/cadence map and matched
CPU/drawing coupling test are recorded. The repeated coast, independent full-trace
counter, observer control, firing/turning/afterburner and pause checks pass.
Comms, missile locking, ordinary damage, autopilot, landing and full mission
progression retain explicit runtime gaps; their map is static classification.
The phase-7b audit below adds the complete world/dispatch inventory and native
reproductions; it does not close these live-coverage gaps.

### Phase 7b — Framerate dependency audit (gate complete)

Their Finest Hour's `docs/framerate-audit.md` and FR-01..FR-27 are the template; its
gameplay is expected to be more complex than Wing Commander's, but the kinds of
defect will recur.

1. Start at the world update, follow every call, decode every dispatch table entry
   (ship classes, projectile/missile types, effects), and list each clock: counters
   decremented once per update, countdowns set to frame counts, per-frame increments
   without fraction carry, sampled thresholds (overshoot, tunnelling of fast guns and
   missiles), RNG draws per update, byte-wide counters that overflow at other rates,
   input and replay boundaries. Searching only for arithmetic misses byte accesses
   and counters initialised elsewhere.
2. Open one stable item (`FR-nn`) per concept in `docs/framerate-audit.md`, labelled
   reproduced, static finding or candidate. A candidate can close as verified
   unaffected, with its tested scope.
3. Reproduce each item with a native-routine check (Their Finest Hour
   `timing_audit_check.py` style: original routines executed on Unicorn 68000 and
   68040 models from a local live dump, controlled fixtures, several step rates and
   changing rates). Flip each check from asserting the defect to asserting equal
   elapsed-time outcomes when its fix lands.
4. Record, per system, which clock policies are possible: fixed-rate sub-clock
   (Their Finest Hour's 64 Hz debris, 8 Hz effects), elapsed-time countdown with
   carried remainder, step-scaled increment with carried fraction, or render-rate
   presentation only.

Gate complete: [FR-01–FR-23](framerate-audit.md) record the world-root closure,
54 dispatch tables / 625 entries, every classified subsystem boundary, clock
initialisers/consumers and each item's B/C/D implementation cost. Original-code
checks pass on Unicorn 68000/68040 at four steady rates and both directions of a
mid-run rate change. All entries, 104 bounds checks and rejecting negative controls
pass. Native slices, complete routines and static/live gaps are distinguished.
No new emulator run, timing fix or phase-8 performance pricing was performed.
Stop at phase 7b.

### Phase 8 — Choose the decoupling design (user decision)

Inputs: phases 7 and 7b. For each design, price the simulation (Red Baron): cycles per
update in a busy dogfight on each matrix cell, simulation-only utilisation and the
render rate left, and the number and kind of FR items it must close.

- **B. Variable step.** Every per-frame system advances by the elapsed time of the
  rendered frame (Their Finest Hour). Simulation cost stays one update per frame and
  latency is minimal. Wing Commander presumably assumes a fixed step, so each
  integrator, timer and AI decision needs a step value introduced, not only smoothed.
  Needs a smoothed, clamped frame length and fraction carry.
- **C. Finer fixed tick.** The world runs at a fixed rate above the intended one,
  several updates per frame when drawing is slow (Stunt Car Racer), with constants
  rescaled per quantity. Deterministic; the cost multiplies with the rate, and the
  handling changes unless the rescaling preserves it.
- **D. Hybrid.** The world runs at the intended fixed tick; the player's orientation,
  camera and other control-critical systems advance per rendered frame with an
  elapsed-time step, and other world objects are presented between ticks. Smaller
  audit than B; needs a defined hand-off where the player meets the world tick (gun
  and missile launch, collisions, targeting).

Gate: a priced recommendation with the evidence; **the user chooses**.

Pricing is ready in [the design comparison](timing-design.md). It records the
eleven-cell busy-combat root costs, B/C20/C25/C50/D10 budgets, FR item counts and
the proposed D ownership contract. Full exclusive IRQ subtraction and new-code
overhead remain explicit gaps; elapsed world reservations are not exclusive CPU
utilisation or measured shipping frame rates. A fresh 020 repeat is identical.
**Gate complete: the user selected D on 2026-10-13.**
The world rate is the inferred 10 updates/s pace, not an existing native timer.
Try bounded extrapolation for world-object presentation; validate prediction
errors without changing authoritative collision, damage or lifecycle state.

### Phase 9 — Decoupled simulation (D; complete)

Common to every design:

1. Split the main loop at the native boundary between update and draw. Keep modal
   states (menus, comms video, briefings, landing) on their native timing; they must
   not accumulate simulation debt.
2. Elapsed time from a real-time source in emulated time, measured rather than assuming
   PAL; bounded debt or clamped steps (drop and count beyond it in VERIFY).
3. Input per update: joystick/joypad, keyboard (one-shot commands exactly once, held
   controls on every update they cover), mouse if used.
4. Close the FR items the design requires, each with its own evidence.
5. Acceptance (Red Baron gate): completed world time within ±1% of nominal for every
   render schedule (normal, slowed, one field) where the simulation fits the CPU;
   game speed independent of render time; pause and menus rebase without catch-up;
   option off is the original bytes. Compare equal elapsed time with identical input;
   record residual differences rather than demanding byte identity.

Design-specific: B introduces and smooths the step value and carries fractions per
object; C runs bounded batches of fixed updates and rescales by quantity (what
integrates over the step, timers by where they run); D runs the world from a fixed-tick
accumulator and the player path per frame.

**Gate complete.** The separate `--timing` build gates D with `CUSTOM1=3`.
Completed world rates are 9.962–10.017 updates/s in the final captures, with no
input-history overflow. Normal/slow/one-field held-fire comparisons match ship,
weapon, target, damage and gameplay-RNG state; cosmetic debris and draw counts
are recorded residuals. PAL and NTSC pause tests rebase without catch-up. The
030 run demonstrates 540 between-tick responsive player/camera publications.
[FR closure](framerate-audit.md#phase-9-d-closure) records each item's policy and
limits. Full modal/campaign and physical-device play-throughs, the original
point-sampled collision limitation, and combined-renderer release validation remain
explicit gaps. Phase 10 closes the presentation boundary below.

### Phase 10 — Presentation between updates (D; complete)

Needed where frames are shorter than a simulation update: world objects under D,
everything under C below the display rate. Not needed under B.

1. Snapshot the renderer's native inputs at the update's common exit: ship poses,
   projectiles, starfield/debris, cockpit indicators where they animate.
2. Interpolate or predict positions, and orientations by a method that stays
   orthonormal; snap at cuts, jumps, autopilot and view changes. Keep renderer copies
   apart from the authoritative state.
3. Validate on real flight, not only on the intro: frames within one update must move,
   and predictions are checked against the next update.

**Gate complete.** The experimental timing build predicts for at most one world
interval, uses native basis reconstruction, snaps at discontinuities and restores
all staged poses/allocation fields before gameplay. Two real-flight gates include
240 pictures, 916 between-tick projected moves, exact post-draw restoration,
next-update error measurements and PAL pause. Hard turning reached an 8.982 km
full-tick positional forecast error; corrections snap rather than feed back into
simulation. Discrete effect/indicator frames remain world-clocked. Full model,
scripted-camera and hardware play-tests remain release coverage. The phase-11
flight conversion gate is recorded below.

### Phase 11 — Rendering, second pass (flight scope)

**Complete.** The phase-7 profile selected c2p (64–66% of representative 020 cost)
as the useful target. The timing build now compares 32-pixel source blocks against
separate histories for each planar buffer, converting changed view/cockpit/HUD
blocks. First use, changed buffers and nonflight/geometry transitions are handled
conservatively; history needs 128000 bytes of FAST RAM with original-converter
fallback if allocation fails. The original limiter remains.

Native complete-output and live original/candidate twin gates pass. Same-picture
CHIP-to-CHIP destination comparisons measure 80.0% less mean conversion time on
030 firing and 66.5% on 020 turning. Normal 030 PAL/NTSC flights retain the 10 Hz
world, pause and presentation restoration, with roughly 25/30 publications/s.
These are scoped emulator conversion savings, not an FPS or hardware claim.
See [the phase-11 gate](internals.md#phase-11-flight-rendering-gate) and
[reproducible commands](development.md#phase-11-flight-conversion).

Flight chunky drawing already targets FAST RAM. Smaller drawing/math buckets do
not justify speculative ship, polygon/span, starfield, HUD or text rewrites, and
the earlier blanket-clear bypass was unsafe. Those native routines and clears are
retained. Dense screen changes may reduce or reverse the conversion saving;
all-scene/cache/hardware performance, every model/camera/transition and small-memory
coverage remain explicit release gaps. Stop before phase 12.

### Phase 11b — Frame-rate recovery (required before release)

The user's emulated 040 with the release build's default pacing showed under 25 FPS.
Diagnosis (2026-10-13):

- `Custom5` is Psygore's original option: 0 waits for two CIA-A TOD ticks (fields)
  per conversion, 1 never waits, 2 waits three, 3 waits five, 4 the blitter path.
  The labels "Standard/Unlimited/Relaxed/Slow" were added by the release work. The
  flight converter still calls the wait `S:17b8`, so the default caps at 25 FPS PAL.
  Phase 9–11 gates measured 24.97 publications/s, exactly this cap.
- Phase 8's render remainder `R` on fast CPUs is mostly limiter wait: 030
  `S+R` = 40.07 ms, two PAL fields. True render cost on fast CPUs is unmeasured.
- The emulated 040/060 cells do not represent those CPUs: the 040 world update is
  slower than the 030 (4.11 vs 2.23 ms) and 060 results ignore cache state. Phase 6
  rejected Kalms 040 on that model. Phases 9–11 never ran the timing build on a 040.
- Both renderers call WaitBOVP after every conversion, before publication, idling
  the CPU every frame.
- Phase 9 advanced only player orientation per field. Player position is
  extrapolated from the last tick's velocity, other objects in a straight line
  (hard-turn error up to 9 km, snapping at 10 Hz), and the prediction targets
  render start rather than the displayed field.
- World ticks and catch-up land whole in single frames; drawing, clears, cockpit,
  HUD and prediction save/restore were never profiled on a fast CPU.
- No gate required an end-to-end frame rate.

Work items, in order. Every item's gate reports end-to-end frames/s and the
fields-per-frame histogram on the 030 model and the calibrated 040 (A2).

**A. Measurement** — A1 and A3 done; A2 is blocked on a real-hardware reference.
Results are in [internals](internals.md#phase-11b-measured-frame-budget-a1a3).
With the limiter off, the emulated 030/040/060 reach 40–50 pictures/s.
`Custom5=0` holds every one at 24.96. The remaining drops are world-tick frames
(cycle-exact 040: 26.6 ms with a tick, 15.7 ms without) and the post-conversion
display wait (6–7 ms of idle per frame).


- **A1.** Frame instrument in a diagnostic build: per published frame its display
  field and the time in input/player, world, prediction save/restore, drawing,
  conversion and waits. Output frames/s, a fields-per-frame histogram and the
  per-part times. Gate: agrees with the existing observer within one field on 030.
- **A2.** Credible 040 reference: calibrate an emulator 040/25 configuration
  (CPU model, cache emulation, speed) against published 040/25 figures or the
  user's hardware, within 10% on the same window. No 040/060 claims before this.
  Status: no emulator configuration here models those CPUs. The non-cycle-exact
  040 and 060 match each other, and the cycle-exact 040 ignores cache state. The
  recorder runs unchanged on real hardware (`NOWRITECACHE`); a real 040 capture
  is the remaining step. Psygore's cache request leaves a 040 at CACR 0 unless
  the user adds `DCache`.
- **A3.** Baseline the release build with `Custom5=1` (limiter off) on 030 and
  calibrated 040: Nav-1 held fire, hard turn, afterburner. This is the real budget.

**B. Pacing and buffering**

- **B1 — complete.** Remove the limiter call from both enhanced renderers and make the mode a
  `Custom5` choice (user, 2026-10-13): 0 enhanced (default; WHDLoad's unset value),
  1–4 Psygore normal/unlimited/relaxed/slow (his 0–3, shifted; his blitter option is
  dropped). `Custom1` selects only the language. German with 0 falls back to Psygore
  normal until the German port exists. The clocked ship/title and asteroid intro
  now also bypasses the limiter; remaining scenes keep normal pacing. The ReadMe states both and the
  changed numbering. Psygore's modes stay for now.
  Native option/pacing/output gates and the required frame-rate reports pass;
  see [B1 evidence](internals.md#phase-11b-public-modes-and-uncapped-flight-b1-gate-complete).
  B2 replaces the flight display-end wait below; the cached-040 row glitch is fixed in the local emulator (evidence above).
- **B2 — complete.** Vsync without idle: publish immediately after conversion, swaps take
  effect at vertical blank, and wait only before converting into a buffer whose
  swap-away has not yet been displayed. Drawing into the FAST chunky buffer overlaps.
  Native queue/retirement and original-path tests, complete converter output,
  independent displayed-frame counts, ownership and PAL/NTSC copper audits pass.
  See [B2 evidence](internals.md#phase-11b-deferred-buffer-reuse-b2-gate-complete).
  C1 display-time prediction is complete below; subjective visual acceptance remains open.
- **B3.** No triple buffering (user, 2026-10-13): keep two buffers; B2 removes
  the idle wait instead.

**C. Smoothness**

- **C1 — complete.** Predict to the queued picture's display field, including the
  pending swap. Gate: all 661 PAL pictures on each required model and 665 NTSC
  pictures have exactly matching display-time fractions and no missed targets;
  independent A1 and buffer-ownership checks pass. The bounded renderer horizon
  includes up to two queued fields beyond one tick. See
  [C1 evidence](internals.md#phase-11b-display-time-prediction-c1-gate-complete).
- **C2 — complete.** Player translation per field: identify the native player velocity model
  (thrust, afterburner, speed ramps), advance velocity and position every field with
  carried fractions, exclude the player from the world position step `E:80b6`, and
  commit at the tick as rotation already does. Gate: zero camera-position correction
  at ticks in steady flight and turns; fuel, speed and world state match within
  documented tolerance; collisions use the committed authoritative pose. All four
  live windows pass, with 656 checked ticks and zero player/camera corrections.
  Native field arithmetic, world bookkeeping, fallbacks and render restoration
  pass. See [C2 evidence and tolerances](internals.md#phase-11b-player-translation-c2-gate-complete).
- **C3 — complete.** Heading-aware extrapolation: direct each object's predicted velocity
  along its predicted orientation, using the existing angular-step prediction.
  Gate: hard-turn full-tick forecast error well below the phase-10 p95 4.357 km /
  max 8.982 km; constant-velocity classes stay exact. The 149 world-ship
  comparisons now give p95 0.255 km / max 6.348 km (94% / 29% lower); all 441
  constant-velocity comparisons are exact. Native thrust toward predicted heading
  preserves inertia. AI speed changes remain unpredictable; this is a scoped
  one-tick gate, not a universal correction bound. Native isolation and two live
  frame-rate gates pass; see [C3 evidence](internals.md#phase-11b-heading-aware-extrapolation-c3-gate-complete).
- **C4 — steady-flight gate complete.** Measure displayed intervals separately
  from internal work intervals around world ticks and catch-up batches. Both
  current PAL models show 639/639 measured intervals of one field: median and
  p95 both 20.032 ms, including 128 intervals containing a world tick. B2's
  queue already absorbs the work spikes; no additional tick-placement or
  simulation change is needed for this gate. No multi-tick catch-up interval
  occurred in these windows; forced-stall cadence remains unmeasured.
  The held-turn control still has two/three-field intervals and 119/656 missed
  prediction targets. This is not a global smoothness or C1 deadline pass;
  the remaining heavy-scene overruns carry into D1–D5 and E1. See the
  [C4 evidence](internals.md#phase-11b-frame-time-spikes-c4-steady-flight-gate-complete).
  D1 records the remaining rendering costs below.

**D. Rendering cost (driven by A3/D1)**

- **D1 — model profile complete; calibrated follow-up blocked on A2.** The unchanged
  release candidate is profiled on the current 030/040 models: clear, stars,
  native object bitmap/scaling/rotation paths, cockpit composition, HUD, glyphs,
  comparison/loop/history, prediction/backup/restore and geometry. Read-only
  observer controls preserve both ledgers byte for byte. Geometry, cockpit
  composition and comparison overhead justify D2–D4; no optimisation is applied.
  Steady flight remains 49.920 pictures/s on both models; the 040 held turn stays
  41.535 with 119/656 prediction misses. Hardware timing, exclusive attribution
  and wider workload coverage remain explicit gaps. See the
  [D1 profile](internals.md#phase-11b-rendering-costs-d1-model-profile-complete).
- **D2 — complete on current models.** Save/restore occupied slots and camera
  scratch, with lazy backup of native render allocations. Unchanged pad queues
  skip one geometry rebuild while preserving native range history. Whole-data
  and input-transition checks pass. Steady PAL flight retains 49.920 frames/s
  on 030 and cycle-exact 040; the 040 held turn improves from 41.535 to 42.087,
  with 118/656 prediction misses still open. Calibrated 040 remains blocked on A2.
  See [D2 evidence](internals.md#phase-11b-prediction-overhead-d2-complete).
- **D3 — complete on current models.** The native split-row/aperture map already
  preserves the cockpit. Faster exact-region clears and cached-030 span copies
  retain all pixels needed by later reads; other shapes and 040 composition use
  native fallbacks. Pixel/installer/buffer gates pass. Steady flight stays at
  49.920 frames/s on both models; the 040 held turn reaches 42.493 versus 42.087
  for its same-size native-path control, with 112/657 prediction misses remaining.
  See [D3 evidence](internals.md#phase-11b-view-regions-d3-complete).
- **D4 — practical comparison-cost gate complete; dirty rectangles deferred.**
  D1 confirms the overhead matters. A compact `CMPM` loop retains complete source
  coverage and both buffer histories, reducing 040 held-turn comparison/loop/history
  mean cost from 4.143 to 3.304 ms. Native and live pixels match; both steady
  models retain 49.920 frames/s, and the held-turn window reports 43.424 versus
  42.493 for the unchanged D3 control. This implements a smaller optimization
  than the proposed drawing-based dirty rectangles, which are not implemented or
  claimed disproved: native clears rewrite the view, and tracking all writers plus
  two-buffer invalidation needs a separate correctness contract. See
  [D4 evidence and limits](internals.md#phase-11b-comparison-cost-d4-practical-gate-complete).
  D5 follows below.
- **D5 — complete on current models.**
  Five equal-layout arms compare current/040 changed blocks and original/030/040
  full conversion. Both families pass native and live pixel checks. Changed-block
  FPS is 47.533 versus 47.604 on 030, 43.424 versus 43.255 on the 040 core: no
  meaningful gain from the 040 family. Kalms 030 improves sustained full conversion
  on 030, but every full arm trails changed blocks; neither full Kalms family beats
  the original on the 040 model. Retain release bytes and selection unchanged.
  See [D5 results and limits](internals.md#phase-11b-kalms-families-d5-model-evaluation-complete).
  Per the user’s scope decision, real-hardware validation is not required to
  close D5. A2 remains separate follow-up; no physical 040 performance claim
  follows from these model results. Stop before E1.

**Spawn prediction fix — complete.** Completed native player/AI weapon
constructors certify new projectile identities for their first presentation
interval. Constructor-recorded shooter cooldowns no longer trigger false view
cuts. Slot reuse, death, view cuts and modal rebasing retain protection; native
simulation and firing cadence remain unchanged. Native checks cover 44
constructors, 220 render samples, simultaneous mounts and 56 rejecting controls.
Short held-fire gates measure 49.92 frames/s on 030 and 48.03 on the cycle-exact
040 model, with recorder/observer agreement and correct buffer ownership. See
[spawn fix and limits](internals.md#cannon-spawn-first-interval-prediction-hold).
Hardware acceptance is still separate; stop before E1 and keep phase 12 paused.

**E. Acceptance**

- **E1.** Calibrated 040/25 with fast RAM, Nav-1 combat: at least 25 frames/s at
  p95, 50 in light scenes; 030/50 at least 25. World 10 Hz ±1%; the view advances
  every published frame. Numbers to be confirmed with the user after A3.
- **E2.** User play-test with the A1 counter, emulator and real hardware if available.

### Phase 12 — Definitive-edition polish and release

Known defects (to be collected), controls (CD32 pad, keyboard, mouse), NTSC/60 Hz
behaviour, save/load and nonvolatile storage, options in the slave, the ReadMe, and a
release archive per AmigaXDev's playbook. Final play-test by the user on real hardware
if available.

Deferred local work: the pre-existing save/load length guard and native checks
are preserved in stash `5237ca28782a8e1fd1f615c91232c80b2fd93391`
(`Phase 12: deferred save-load length guard and native checks`). It contains only
`whdload/release.s`, `tools/reconstruct.py` and `tools/release_check.py`: reject
missing or wrong-sized save files before loading, install the load detour, and
test valid/invalid lengths. This work is not part of the accepted C1 build and
still needs phase-12 review and validation. Restore when phase 12 resumes with
`git stash apply 5237ca28782a8e1fd1f615c91232c80b2fd93391`, then review the diff;
keep the stash until the work is safely committed. This stash is local to this
checkout and is not transferred by pushing the documentation commit.

### Phase 13 — OCS investigation and implementation plan (complete)

The investigation deliverable is the [ordered OCS plan](ocs-plan.md):

- **P13A1–P13A4:** reconstruction, native display/memory contract, launcher and baseline.
- **P13B1–P13B3:** shared variant definitions, 68000-safe mechanisms and instrumentation.
- **P13C1–P13C6:** four-plane candidates, measured blitter/CPU/memory crossover,
  selection, memory ownership, publication and optional changed-block conversion.
- **P13D1–P13D4:** OCS timing audit, 10 Hz world clock, responsive presentation,
  projectile prediction and the 15-page intro.
- **P13E1–P13E3:** focused A500 performance work, compatibility and later release hand-off.

P13A1–P13A4, P13B1–P13B3 and P13C1–P13C3 are complete; P13C4–P13E3 remain pending. The native converter **uses the blitter**;
keep it where measured end-to-end performance wins, including potentially 68000
and no-Fast 68020 systems. A 68000 CPU converter and the proposed 68020+ longword
path are alternatives to compare, not a reason to remove the blitter. CPU type
alone does not establish the crossover. See the [static evidence and limits](internals.md#phase-13-ocs-static-investigation)
and [reproducible commands](development.md#phase-13-ocs-static-investigation).
Stop at P13C2; no backend selection or resumption of CD32 release work.

## Decisions pending

- Release play-testing must judge visible hard-turn corrections and all model/camera paths;
  the implemented presentation policy predicts to display time with authoritative
  snaps and a bound of one tick plus two queued display fields.
