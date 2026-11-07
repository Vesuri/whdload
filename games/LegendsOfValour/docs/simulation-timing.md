# 25 Hz simulation (developer CUSTOM2 bit 6)

Read this before changing `src/simulation*.s`, the game's clock/input paths, or anything
that runs between rendered frames.

## What it does

The original game advances the world once per rendered frame and scales movement by a
frame-time compensation table (step written to `h12:0cdd6`, capped at 12 fields per frame).
Below 25 fps, world speed, AI, combat, animation and input sampling all couple to rendering
speed. Bit 6 replaces that with **fixed world ticks of 2 PAL fields (25 ticks/s)** driven by an
elapsed-field accumulator:

- Each overdue tick runs the original per-tick logic (player, actors, clocks, projectiles) in
  the original order with the original small steps. Catch-up ticks skip wall/sprite drawing,
  C2P and display; one tick per output frame draws.
- The native 25 fps frame cap (`h12:05e2a`), the display dispatch (`h12:05ea6`) and the beam
  wait (`h12:063ce`) stay unpatched.
- The movement step is the constant 10 (the original value at 25 fps), set in every
  compensation-table entry.
- Combat keeps its native minimum cadence: one combat step per 4 fields (two world ticks).
- Bit 6 is independent of the rendering patches (W1–W6), mouse precision (bit 7) and click
  inputs (bit 8) in developer builds. Release builds have no separate timing option: Enhanced
  frame rate (any nonzero CUSTOM2, `CUSTOM2=1` in the installed icon) turns it on with the
  other enhancements, and `CUSTOM2=0` runs the original game.

It **changes gameplay speed** on machines that rendered below 25 fps: the world now runs at
the 25 fps reference. It also **costs CPU**: on the A500 catch-up ticks take rendering time
(see “Cost” below).

## Design

**Clocks.** `_sim_vbl` (hooked at the VBL's game-clock add, `h12:06412`) counts *active*
fields in `_sim_fields`, separately from the saved native game clock `h11:004d6`.

- Active fields accumulate only while the main loop runs, the native pause gate `h12:0a0c3`
  (also published at `h11:05ff8`) is open, and no private suspension is active.
- The main loop (`_sim_loop` at `h1:02496`, `_sim_end_tick` at `h1:02714`) consumes 2 fields
  per tick into `_sim_consumed`. Debt is `_sim_fields − _sim_consumed`.
- The native game clock stays VBL-driven, so deliberate jumps (rest, load: `h2:04ecc`,
  `h2:05da4`) remain jumps and are never replayed as catch-up.
- **Never use differences of `h11:004d6` as the accumulator.**

**Logical time for gameplay readers** (`simulation_clock.s`). Gameplay clock readers see
the native clock minus outstanding debt. The patched readers are:

- calendar and periodic events: `h12:173b2/173c4/173d8`;
- weapon/projectile cooldown: `h5:01a1a`;
- timed player state: `h1:01112/01140`;
- the periodic world update fed by `h11:00006`, at `h1:029ea` → `h2:0411c`.

Menus and modal loops keep the live clock; they use `h11:004d6` for their own deadlines.

Day boundaries: the VBL's day producer (`h12:06430`) is unchanged, because modal loops read
the real pending-day count at `h2:00796/00a54/00d7c/0109c`. The guarded hook at `h1:0265a`
lets the main loop's consume loop (`h1:0265a–0266e`) take only the days whose logical
boundary is due.

**Renderer ownership.** `_sim_renderer` patches `h12:027c4`, the renderer's per-frame actor
update and 16-frame periodic call. Inside a tick, the actors (`h12:140e6`, 56 records of 128
bytes at `h12:0a2f0`, mapped to render records at `h11:08c44`) and the periodic work
(`h12:15b1a`) advance once per tick.

Renderer calls outside the main tick only redraw and never advance AI. These are:
- `h1:00690/006d6`;
- `h9:00226`;
- modal redraws;
- object-builder redraws (`h5:0135c`), which project projectiles without moving them.

**Historical input** (`simulation_input.s`, `simulation_mouse.s`).
- *Pointer and buttons.* At the VBL tail (`h12:06484`), after native debounce or the VERIFY
  tape, the pointer position and buttons go into a 512-slot × 16-byte ring
  (`_sim_input_ring`). Each tick reads the sample for its own logical field.
- *Relative mouse.* Motion is accumulated at the original JOYDAT delta code (`h12:06460`) as
  cumulative positions, and each tick consumes the difference once. The adapter at
  `h5:01e64` (caller `h1:02aaa`) reproduces the heading ADD and its signed **BGE** internally.
- *Mouse-look entry.* Entering mouse look clears the current delta, as the native code does.
- *Clicks.* With click inputs (bit 8), `_sim_input_pointer` and `_sim_combat_pointer` pass
  their historical buttons through `_click_filter`; samples whose buttons the live UI already
  consumed (see "Modal and pause boundaries") bypass it (`docs/click-inputs.md`).
- *History loss.* A tick older than the retained history rebases explicitly: it samples
  current input, resynchronises consumed time, drops accumulated motion and increments
  `input_recoveries`. Unrecoverable time is abandoned, not replayed. Every validation run
  requires **zero recoveries**.

**Keyboard collector** (`simulation_keyboard.s`). A task-context worker owns the game's single
console `CMD_READ` for its whole lifetime:
- *Lifetime.* The game opens the read at `h1:01ee0`, submits at `h1:01e56` and closes at
  `h1:01f30`. The readers are `h1:01e86` (blocking) and `h1:01eb6` (non-blocking); the
  main-loop callers are `h1:0258a` and `h1:025ae`.
- *VBL never calls console.device.* It only signals the task.
- *Timestamps.* Completed bytes go into a 512-slot FIFO, tagged with an arrival field and a
  clock domain (world or combat).
- *Consumption.* Gameplay polls consume bytes up to the tick's historical cutoff. Blocking and
  UI readers consume immediately, with no cutoff.
- *Backpressure.* When the queue is full, the worker keeps the completed byte and its
  timestamp, waits for space, then resubmits. Bytes are never dropped and the worker never
  aborts.
- *Shutdown.* It cancels and waits for pending IO, restores the port owner and removes the
  worker before freeing its memory, then continues the native console close.

**Modal and pause boundaries.** The options panel (command 37: `h5:01cf8` / `h5:0266e` →
`h2:04678`) and the item panel are wrapped in a private suspension depth:
- The item panel is `h2:01ca0`, called from `h2:024d0`; its sole normal epilogue is
  `h2:0222e`. The adapter in `simulation_modal.s` keeps the original LINK and stack frame.
- During a suspension, the native clock and native input keep running, but private fields and
  input history stop.
- On leaving the outermost suspension, historical samples up to that boundary keep their
  time, pointer and motion but **lose their buttons**, because the live UI has already handled
  them. Without this, stale clicks reopen the options panel after save/load.
- Combat's epilogue applies the same rule.

**Combat** (`simulation_combat.s`). The native caller `h12:10b8c` closes the world gate,
calls `h2:0506a` → `h9:000e6`, then reopens the gate at `h12:10bdc`. World time therefore
stays frozen in combat, and combat runs on its own clock:
- *Deadline.* The native per-iteration deadline at `h9:001b2` resets to "now + 4". The patch
  replaces it with a separate elapsed-field deadline that advances by exactly 4 fields per
  iteration, starting after combat setup.
- *Catch-up.* Overdue iterations skip only the h9-local drawing calls: world `h9:00642`,
  sprites `0062a`, enemy frame `005fa`, overlay `00000` and display `0064e`. Attack scripts,
  RNG, damage and sound keep their order.
- *Input.* Combat has its own 512 × 12-byte pointer/button history (`h9:00408`) that keeps
  running while the world is paused. Console bytes are cut off at the combat deadline
  (`h9:005ac`).

**Visual cadence** (`simulation_feel.s`). These run at their own pace, apart from the world
step:
- the texture phase (`h12:06b54`) and the actor fractional animation (`h12:14224`) advance on
  every second tick (`SIM_VISUAL_DIVISOR`);
- the shared sprite phase (`h5:01934`, read at `h5:02264`) has pacing 8;
- button turns use 5° in every view (`h1:0021a/0024a/0027a`; native is 15° for large and 10°
  for medium/small).

The `h5:01934` adapter performs the CMP and signed branch internally, then resumes at
`h5:01942` (advance) or `h5:01954` (hold). Returning through a pushed continuation would
destroy the flags.

## Constants (`src/simulation.s`, keep together)

`SIM_FIELDS_PER_TICK = 2`, `SIM_MOVEMENT_STEP = 10`, `SIM_ANIMATION_PACING = 8`,
`SIM_VISUAL_DIVISOR = 2`, `SIM_TURN_STEP = 5`, `SIM_FIRE_TICKS = 4`,
`SIM_INPUT_SLOTS = 512` (`simulation_input.s`), `SIM_KEYS_SLOTS = 512`
(`simulation_keyboard.s`), and `SIM_COMBAT_FIELDS = 2 × SIM_FIELDS_PER_TICK`.

The integer field interval supports only rates that divide 50; any other rate needs a
fractional accumulator. Changing the rate means reviewing the movement step and animation
pacing with it, then rerunning all the checks below.

## Invariants a change must keep

- **Install guards.** `_sim_install` returns before any check or write when bit 6 is off or
  CUSTOM1 selects character creation. Every hook is guarded by an opcode or relocation check
  (failure → `_sim_bad`). Continuations come from the hunk table, never from fixed addresses.
  Installers flush the cache.
- **Disabled-option checks.** Every patched range carries a `; PERF_RANGE hN:OFF LEN bit=6`
  comment. `tools/check_disabled.py` uses these to prove the bytes stay original when bit 6
  is off. Keep the comments accurate when adding hooks.
- **Native pacing stays native.** The frame cap, display dispatch and beam wait stay
  original: `check_disabled.py --display-timing` compares `h12:05e2a–05e79`,
  `h12:05ea6–05eb1` and `h12:063ce–063ef`. The compensation table (`h12:05e7a`) changes only
  when bit 6 is on.
- **No world advance outside the main tick.** Modal callers, out-of-loop renderer calls and
  combat must not advance the world.
- **Fixed per-tick order.** Do not scale a whole frame's displacement: player x/y carry 6
  fractional cell bits, actors use 4× player units with replacement fractions, and collisions
  and countdowns depend on per-tick order.
- **Flags across adapters.** Adapters with branch-dependent results branch inside the
  adapter. Clock readers use ADDA/SUBA so that X is preserved where the original preserved it.
- **Device IO stays in task context.** No device IO from VBL. Collector records are published
  only after initialisation.
- **Fixtures stay out of release builds.** Normal builds must not contain the tape, drawing
  delays, observers or input-device fixtures. All code must stay 68000/PIC-clean: the build is
  `-m68000 -pic` (`game.conf` `VASM_FLAGS`).

Actor speeds are also frame-clock dependent at creation. `h12:14b64`, called from
`h12:14c56`, stores (step + random(−3..1)) in actor fields 28/30. The other readers of the
step word are `h12:10a80/10abc` (scripted motion). With bit 6 on they all see the constant
10.

## Build switches

| Switch | Status |
|---|---|
| `SIM_KEYBOARD_EXPERIMENT`, `SIM_COMBAT_EXPERIMENT` | Historical names, **default on** in every build (`LegendsOfValourHD.s`); runtime bit 6 gates them. Leave them defined. |
| `SIM_FIRE_EXPERIMENT` | Off. Private cosmetic RNG for the scenery random choices (`h5:002dc/002fc/00310` via `h5:02698`). Never exercised at runtime; not part of the feature. Dead unless revived. |
| `SIM_KEYS_SLOTS` | VERIFY only: override the collector ring size (2 exercises backpressure). |
| `TIMING_STUDY` | VERIFY only: `timing_study.s` instruments (drawing delay, input fixtures, observers). Includes `timing_panel.s`, `timing_keys.s`, `timing_combat.s`. |
| `TIMING_MODE_TEST` | With `TIMING_STUDY`: hardware-counter mouse fixture for the mode matrix. |
| `TIMING_PROJECTILE`, `TIMING_THROW` | With `TIMING_STUDY`: native spell launch (`h5:019aa`, type 130) or item-55 throw (`h5:0195c`). |
| `TIMING_KEYS_TEXT` | With `TIMING_STUDY`: native save-name editor input (`h8:00800` poll). |
| `VERIFY_WAIT_RESCUE` | VERIFY: rescue pulses for blind waits (needed on A500 in the load route). |

The `TIMING_STUDY` CUSTOM5 bits are:
- tape options: bit 0 tape, bit 1 wait rescue;
- bit 8: 8-field drawing delay before each renderer entry after the anchor (the tape flag
  `D` on the anchor selects the same delay);
- bits 9/10: button pulse / legacy-input control;
- bits 11/14: synthetic positive / negative mouse X;
- bit 12: time jump to `$fff0`, with dismissal of the resulting message;
- bit 13: 600-field item-panel hold;
- bit 16: 600-field main-task stall (recovery test);
- bits 24/25/26/27: key events / blocking read / native exit / ANSI;
- bits 28/29/30: combat observer / manual combat presses / combat space key.

## Verification

All captures go through `tools/fixed_window.sh`, which runs as `INSTANCE=cap` with
`JOY0=none`, one capture at a time. Machines:
- **A500:** `AMIGA_MODEL=A500 CPU=68000 CHIP_KB=512 FAST_KB=0 EXTRA_ARGS=--slow_memory=1536`,
  base `0xc00000`;
- **020:** `AMIGA_MODEL=A1200 KICKSTART=$KICKSTART_A1200 CPU=68EC020 CHIP_KB=2048
  FAST_KB=4096 EXTRA_ARGS=--slow_memory=0`, base `0x200000`.

Build a VERIFY slave with the flags a check needs (`make verify VASM_EXTRA='-DTIMING_STUDY=1 ...'`),
copy `tmp/build/verify/LegendsOfValour.{Slave,lst}` into each `OUT` as
`slave.slave`/`slave.lst`, and use `KEEP_SLAVE=1`, so that both members of a pair run the
identical slave. A normal/delayed pair differs only in the final anchor flag: `A` versus
`AD`.

**Sampling modes:**
- `STATE_TICKS=N`: `lov_timing_fields.py --ticks` samples N+1 completed ticks at
  `_sim_tick_complete`.
- `STATE_FIELDS=N`: samples N+1 VBLs.
- `lov_timing_state.py` decodes the samples.

| Check | How |
|---|---|
| Repeated input modes, W1 off/on, both CPUs (the main determinism gate) | `tools/timing_modes_validate.sh PREFIX` (VERIFY `-DTIMING_STUDY=1 -DTIMING_MODE_TEST=1`, tapes `timing-modes-{normal,delayed}.txt`, CUSTOM2 126/127, CUSTOM5 2049, `STATE_TICKS=120`); it runs `lov_modes_check.py NORMAL DELAYED` itself |
| Equal elapsed fields | same build and tapes, `STATE_FIELDS=240`, then `lov_elapsed_check.py NORMAL DELAYED` |
| Save/load round trip | ordinary VERIFY + `VERIFY_WAIT_RESCUE`, CUSTOM2=255, CUSTOM5=1, `TAPE_CHECKPOINTS="before-save before-load" STATE_TICKS=40 STATE_ONLY=1`, tape `timing-load.txt`; then `lov_load_check.py OUT --base BASE` and `lov_animation_check.py OUT` |
| Native save-name editing | VERIFY `TIMING_STUDY TIMING_KEYS_TEXT`, tape `timing-text.txt`, CUSTOM2=127, CUSTOM5=16777217, `STATE_ONLY=1 STATE_TICKS=80`; `lov_text_check.py OUT --base BASE` |
| Keyboard transport | VERIFY `TIMING_STUDY`, CUSTOM2=127, `STATE_ONLY=1 STATE_TICKS=80`, CUSTOM5 16777217 (events) / 150994945 (ANSI) / 50331649 (blocking); `lov_keyboard_check.py OUT --base BASE [--ansi] [--blocking] [--compare OTHER]`. Backpressure: add `-DSIM_KEYS_SLOTS=2`, check with `--ansi --slots 2 --require-full` |
| Keyboard teardown | CUSTOM5=83886081, `KEYBOARD_EXIT=1` (runs `lov_keyboard_exit.py`) |
| Combat | VERIFY `TIMING_STUDY`, CUSTOM2=127, `STATE_ONLY=1 STATE_TICKS=30`, CUSTOM5=1895825409 (observer + manual presses + space exit); `lov_combat_report.py OUT --base BASE --scheduled --manual --keyboard-exit` |
| Projectiles | VERIFY `TIMING_STUDY TIMING_PROJECTILE` (`+TIMING_THROW` for the arc), CUSTOM2=127, CUSTOM5=1, `STATE_TICKS=80` (50 for the throw); `lov_projectile_check.py NORMAL [--thrown] --compare DELAYED` |
| Pair state comparison | `lov_timing_compare.py NORMAL DELAYED [--ticks]` |
| Disabled and native ranges | `check_disabled.py OUT --base BASE --custom2 MASK --display-timing` |
| Cost | `lov_simulation_cost.py OUT --base BASE` on a traced window; spin/wall A/B with `tools/ab_window.sh PREFIX 63 127 timing-perf-spin` / `timing-perf-wall-clear` and `PROFILE_WINDOW=guest`, `FSUAE="$HOME/.local/share/amiga/fs-uae-arm/fs-uae"` |

The stationary normal/delayed pairs (keyboard, combat, projectile) use the large-view
stationary route. Take `timing-perf-wall-clear.txt` and copy it with the final `A` changed to
`AD` for the delayed member. The perf tapes add long runs of EXIT pulses so that the
townsman's conversation is closed before the window starts. Reject any window that shows no
display steps.

## Known limits (final measurements)

- **Determinism holds for completed ticks, not for wall-clock instants.**
  - *Completed ticks.* In the mode matrix (8 captures, both CPUs, W1 off/on), every decoded
    logical state matches within each normal/delayed pair, and 120 ticks consume exactly
    240 logical fields.
  - *Wall-clock instants.* At equal elapsed fields, actor records differ in 226/241 (020) and
    195/241 (A500) samples, because drawing temporarily blocks ticks that then catch up. The
    completed-tick gap ranges from −1 to +5 (020) and −7 to +11 (A500).
  - The renderer is not preemptible, and input latency is not zero.
- **Maximum observed debt** is 27 fields (540 ms) on the A500 with deliberate 8-field
  drawing delay and W1 off. Without the delay it is 20 fields. This is a finite-window
  observation, not a bound.
- **History is finite:** 512 fields of world input and 512 of combat input; longer stalls
  rebase and lose time.
- **The keyboard FIFO is bounded:** under backpressure, bytes arrive later. Native console
  buffering limits still apply.
- **Cost.** Fixed windows, W1–W6 on, CUSTOM2 63 → 127:

  | Route | A500 fps | 020 fps |
  |---|---|---|
  | spin | 3.3 → 1.2 | 16.2 → 15.2 |
  | wall | 3.3 → 1.3 | 15.5 → 13.4 |

  Catch-up ticks cost ~150k main-task cycles on the A500 and ~70–76k on the 020. Drawing
  ticks cost ~2.2M cycles on the A500 and ~0.87–0.97M on the 020. Poses differ within each
  pair because the world now advances differently, so these are total-cost figures, not
  matched-scene rendering comparisons.
- **Untested.** Text-entry UIs other than the save-name editor have no runtime coverage.
  Scenery random choices still use the native per-render RNG, because `SIM_FIRE_EXPERIMENT`
  is off.
