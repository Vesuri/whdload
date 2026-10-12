# Open work

## Current state

Phases 1–3 are complete. The reconstructed slave is byte-identical. Original
and reconstructed English boots match all four live game hunks and every screenshot
pixel at the menu and simulator/name prompt for Custom5=0–3. VERIFY off/on marker
checks and equal-size control comparisons pass at both endpoints.
Derived source, executable bytes, disassemblies and captures remain under `tmp/`.
The unskipped intro has 31 identical milestone captures across two fresh boots.
The publication ledger, full traces and independent SWAP_ONLY check agree. The
stock 020 multiplier is verified; numeric-frequency presets require calibration.
**Phase 4 is authorised and in progress; its complete accounting gate remains open.**
Phase 5 is not authorised. The CPU/cache scene baseline, source-change census,
cache audits and matched c2p, instant-blitter and scoped bitmap-drawing ceilings
are recorded. Blanket clear bypass is invalid and excluded.

Consolidated instrument checks pass on 020 default/NoCache and 030 MMU
default/NoCache: exact idle and DMA neutrality, raw-source recomputation, callback
neutrality and independent beam calibration. This validates only DMA slots,
stopped-CPU idle and three callback elapsed scopes. It does not validate general
routine self/inclusive time or interrupt entry/dispatch. A 040 default beam check
and a 060 default callback-neutrality check failed; those measurements remain
unaccepted. Remaining acquisitions already in flight are not proof of completion.

The immediate work is to consolidate existing evidence and use short,
representative profiles for unresolved costs that affect the next engineering
decision. Do not expand or repeat the full matrix while developing instruments.
The exhaustive accounting requirement below remains unfulfilled; this change in
working approach does not declare that gate passed.

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
  choice between designs B, C and D (phase 8) waits for the flight time model and the
  framerate audit.
- **No PC reference.** No particular 386 defines the intended experience, so a DOS
  measurement would only move the guess. The intended rate comes from the game's own
  evidence.

## Intended speed: working estimate

**Working estimate: 15 game ticks per second** in space flight and in the intro's
animated sequences. This is a prior, not a measurement: the game logic is expected to
advance once per rendered frame, no contemporary machine sustained a stable rate, and
roughly 15 fps is a plausible design target for the period. The rate will be a
constant so it can change without redesign.

It is replaced by evidence from the game itself before anything depends on it:

- **Intro against music.** The music player runs from an interrupt at a fixed rate;
  the intro's scripted animation was cut to the score. The rate at which picture cues
  line up with musical cues is the intro's intended rate.
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

### Phase 4 — Baseline profile on the machine matrix

1. Matrix: A1200 with fast RAM, cycle-exact 68030/50 with and without WHDLoad `MMU`,
   68040/25 and 68060/50 `-NOMMU`, each under WHDLoad's default cache handling and,
   where it differs, with the user options (`DCache` and similar). Record `CACR` from
   a VERIFY-only audit behind every figure.
2. Per cell: fps per intro scene, CPU share per routine (inclusive and self),
   blitter waits, interrupt handlers and cost, DMA slot shares, idle time.
3. Hard Drivin'-style ceiling on the fastest cell: matched control versus bypassed
   c2p, bypassed drawing and instant blitter.
4. Measure the c2p change rate per scene (and later in the cockpit) before choosing a
   c2p design.

Gate: a measured statement of where frame time goes in each scene and cell, with the
commands that reproduce it.

### Phase 5 — Game-time model for the intro

1. Confirm the time sources from phase 1 with traces.
2. Coupling test: the same window on several CPUs and with VERIFY-only slowed drawing.
   Compare scene durations in emulated seconds and music position at scene cuts.
   A scene whose duration scales with draw time is frame-coupled; a scene that stays in
   step with the music is clocked.
3. Derive the intro's intended rate from the music anchor (above).
4. Document what the main loop does per frame: input, update, draw, wait, publish.

Gate: the intro time model and an intended-rate figure from evidence. **Stop for the
user's decision on the intro's rate.**

### Phase 6 — Rendering, first pass (intro scope, behaviour-neutral)

All changes CUSTOM-gated, measured A/B against the matched control, validated
picture-for-picture against the original.

1. Fast RAM: chunky buffers, drawing workspace and hot tables in fast RAM; keep only
   what DMA reads in chip RAM.
2. c2p: replace Psygore's software c2p with Kalms routines selected by CPU
   (`c2p1x1_8_c5` family for 020/030, the 040/060 variants), full-frame or delta per
   the measured change rate; verify bit-exactly against a reference with every
   destination store hooked. Remove the Akiko path.
3. Display fetch: FMODE 3 with 64-bit aligned bitplanes, adjusted DDF and modulos,
   sprites checked; measure the freed chip-bus slots.
4. Buffering and pacing: one publication per completed frame at the display-end edge,
   triple buffering if memory and measurement justify it.
5. Caches stay as WHDLoad sets them. Where a routine is sensitive to cache state
   (self-modifying code, code copied at run time), make it correct under every state
   rather than changing the state; report results per cache state.

Because game time is still frame-coupled here, a faster renderer also speeds up the
game. Until phase 9 exists, these builds run behind a frame limiter at the intended
rate (as `Custom5=0` does now) so the speed stays correct where the CPU keeps up.

Gate: measured improvement per cell, picture identity with the original in the intro,
and no change in intro scene durations with the limiter on.

### Phase 7 — Gameplay windows

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

Gate: the flight time model with a per-variable classification, and the coupling test.

### Phase 7b — Framerate dependency audit (Their Finest Hour method)

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

Gate: an inventory complete for the world update and its dispatch tables, with each
item's cost under designs B, C and D.

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

- The intro's intended rate, after phase 5; flight's, after phase 7.
- Decoupling design B, C or D, after phase 8's pricing.
