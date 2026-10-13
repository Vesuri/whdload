# Open work

## Current state

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
with steady/changing rates and explicit runtime/instrument gaps. Phase 8 pricing
is in progress; the user chooses the design before phase 9.

The user accepted the practical baseline with documented gaps on 2026-10-12.
General routine self/inclusive attribution, complete interrupt and blitter-wait
accounting, unaccepted callback controls and a broader drawing ceiling are
explicitly deferred. These are not claimed complete. Revisit a gap when a future
change requires that evidence; do not expand the matrix merely to fill it.

The executable uses the Manx/Aztec C runtime and a View/copper display path with
two eight-plane buffers. The original slave explicitly requests cache settings.
Its normal c2p limiter waits two CIA-A TOD increments; that is not an intended-rate
measurement. `Custom5=4` selects the original blitter c2p path, not Akiko. These
findings refine the implementation assumptions below; the intended-rate and design
decisions still wait for the later gates. The OCS version remains unanalysed.

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
- **Design.** A fixed tick with only presentation interpolation is rejected. The
  choice between designs B, C and D remains the user's phase-8 decision. The flight
  time model and framerate audit are available; performance pricing remains deferred.
- **PC reference.** Use the supplied 86Box/eXoDOS recording as a practical external
  pace reference alongside the Amiga time sources and music. It represents the
  recorded experience, not proof of an original design rate or identical port code.

## Intended speed: working estimate

**Flight-unit anchor: 10 world updates per second.** Phase 7 verifies that a
displayed 200 kps corresponds to 20 km per update. This supersedes the unmeasured
15/s prior. No timing fix is installed, and this rate does not establish every
animation/AI cadence. Do not transfer intro evidence to flight.

**Intro phase 5 candidate: approximately 15 native ship updates/s** (roughly
15–17/s from the short projected-motion comparison). The unmodified ship loop
updates twice per picture, so this is about 7.5 pictures/s, not a 15 FPS cap.
The PC clip shows about 14–15 visible ship/explosion advances/s and a faster
20–25/s asteroid cadence. Asteroids update once per Amiga draw; their cross-port
native-step equivalence remains unproved. These are separate motion targets for
the user's decision, not a silently installed universal rate. Keep music and
text deadlines unchanged. See the phase 5 findings in `internals.md`.

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

### Phase 5 — Game-time model for the intro (analysis complete; rate choice pending)

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
the asteroid native-step mapping is an explicit limit. The user subsequently authorised phase 6 and deferred further timing
investigation to gameplay. Preserve the existing limiter and record remaining
frame coupling; do not install the candidate rates as established facts.

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

### Phase 9 — Decoupled simulation (chosen design)

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

### Phase 10 — Presentation between updates (C and D)

Needed where frames are shorter than a simulation update: world objects under D,
everything under C below the display rate. Not needed under B.

1. Snapshot the renderer's native inputs at the update's common exit: ship poses,
   projectiles, starfield/debris, cockpit indicators where they animate.
2. Interpolate or predict positions, and orientations by a method that stays
   orthonormal; snap at cuts, jumps, autopilot and view changes. Keep renderer copies
   apart from the authoritative state.
3. Validate on real flight, not only on the intro: frames within one update must move,
   and predictions are checked against the next update.

### Phase 11 — Rendering, second pass (flight scope)

Profile-driven: the hot routines found in phase 7 (ship bitmap scaling, polygon or span
drawing, starfield, cockpit and HUD redraw, text). Cockpit-aware c2p (convert only the
view area and changed HUD regions), drawing directly into fast RAM, removal of
redundant clears. Each change measured and validated like phase 6.

### Phase 12 — Definitive-edition polish and release

Known defects (to be collected), controls (CD32 pad, keyboard, mouse), NTSC/60 Hz
behaviour, save/load and nonvolatile storage, options in the slave, the ReadMe, and a
release archive per AmigaXDev's playbook. Final play-test by the user on real hardware
if available.

### Phase 13 — OCS version

Repeat from phase 1 for the OCS disk version as a separate variant: different
executable, display, c2p (none expected) and timing. Reuse designs, not assumptions.

## Decisions pending

- Intended intro/flight rates, deferred to the in-game timing investigation.
- Decoupling design B, C or D, after phase 8's pricing.
