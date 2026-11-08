# Open work

State of the setup against the playbook's "ready to improve" list (§12), and what comes next.
Read `docs/profiling.md` for how each item was measured. The goal (the user's): gameplay that
does not depend on the frame rate, and 50 fps on faster Amigas.

## Done

2026-10-06/07, first pass:
- Repo, rules (`AGENTS.md`, the repository root's), `tmp/` ignored; game, Kickstart, WHDLoad bytes and captures local only.
- Game, version, slave type and the slave's patches documented (profiling.md §1). The slave
  had no source: reconstructed byte-identically (`src/original/`, `make build BUILD=original`).
- A WHDLoad 20 KickEmu slave (`src/Battlehawks1942.s`) and a VERIFY build with an input
  tape that reaches the first training flight.
- `bh_report.py` names every hot region; traces have PCs. Frame counter: c2p passes.

2026-10-07, second pass:
- **Reproducibility fixed.** The JOY0DAT difference between boots was FS-UAE: with
  `joystick_port_0=none` the port's mode stays `mouse` and the host mouse still moves the
  counters. The shared `fsuae_common.sh` (under `common/run.sh`) now also sets `joystick_port_N_mode=nothing` for `JOYN=none`; two
  captures then compared `identical` (every register, DMA record and screenshot).
- **Memory: only DMA data in chip RAM** (the user's rule). The slave gives 512 KB of fast
  memory; BH's hunks are "any" memory and BH allocates sample data `MEMF_CHIP` and everything
  else `MEMF_ANY` (bitplanes come from the OS), so code, data and chunky buffers moved to fast
  memory with no patch to BH. The capture machine is now 68000 + 512 KB chip + **8 MB fast**
  (room for the fast memory and PRELOAD of all three disks; without PRELOAD every disk read was
  a WHDLoad OS switch: blinking, and a boot too slow for the tape).
- **Benchmark scene: a left turn** (the user's choice). In flight the VERIFY slave feeds Left
  characters straight into BH's frame loop on listed frame numbers (8 from frame 30, then
  one every 10 frames); the plane ends up in a steep, descending turn (the flight model
  levels small banks and tightens large ones). The window is 100 fields from **flight frame
  90 by BH's own frame counter** (`26292(a4)`). Two captures armed at different tape fields:
  `identical`.
- **Kalms c2p: measured, rejected** (`docs/c2p.md`). The game's c2p is a delta pass and only
  1–13 % of the view changes per frame; a full-frame Kalms-style merge c2p dropped the A500
  from 9.7 to 5.7 fps.
- **Game time: one simulation step per rendered frame** (profiling.md §9). No time source at
  all; the flight loop `bh:6e48` runs input, simulation, render and c2p once per pass. Coupling
  test: at flight frame 120 the normal slave and a slowed renderer (~9 instead of ~5.4 fields
  per frame) leave identical game state but for 3 bytes (c2p scratch, sound sequencer).
- **T coverage** (2026-10-08): with T doubled and the stick divided by the reference T,
  player and drones cover the same ground in the same game time (4.1 %, 1–2 %).
- **Baselines, the turn:** 68000 9.2 fps (chip-only slave 8.8), 68020 28.8 fps (§6).

## What Their Finest Hour's work gives this one

The work here paused for Their Finest Hour (`games/TheirFinestHour`, the same Lucasfilm
engine family: Aztec C, small-data `a4` globals, a step divisor T, a chunky buffer and a delta
c2p). That work is finished (Enhanced framerate, `CUSTOM2=1`, released as 2.0b). Its
`docs/internals.md` ("Game time", "The slave's changes") and `docs/framerate-audit.md` hold
the details. What carries over, untested on BH:

- **The design: T per frame (E above).** TFH sets T at the top of the flight loop from the
  measured average frame length (moving 1/8 of the way per frame, clamped to 4..field rate),
  carries the time owed between frames, ignores frames of more than 25 fields (pauses, disk
  loads), and starts each flight from the boot T. BH needs the same, from its own field
  counter (it has none, item 3) and from the mission T at `bh:1341c`.
- **Countdowns set as multiples of T** last their time only while T stays put; TFH's fix is
  the averaged T, and its audit (FR-01..FR-28) replaced frame-counted timers with elapsed
  time one system at a time. Its list (debris, group timers, effects, world clock, projectile
  life, flak, gun reloads, bomb salvos and guidance, damage, AI decisions and aim, script
  waits, mission waits, messages, replay and camera, field-based input, audio envelopes, fuel)
  is the checklist for BH's 25 `divu.w 10184(a4)` sites and the timers in units of T.
- **The stick:** TFH scales the counts by T/8 (its reference T) at the end of its input
  routine; BH's `STICKREF` experiment (divide by the reference T 7) is the same fix.
- **Fractions at large T:** at T = 50 per-step increments truncate to nothing; TFH carries
  16.16 fractions per object for position, the player's rates and the AI turn. BH's
  integrators (`bh:79f0`, the world arrays at `10908/11484/12060(a4)`) will need the same.
- **The method:** native CPU checks of single routines under Unicorn (68000 and 68040) from
  a flight snapshot, comparing equal elapsed game time at T = 8/25/50/60 and changing T;
  input tapes and pinned RNG in the VERIFY build only (item 1); every change behind one
  `CUSTOM` option with the original bytes untouched when it is off (item 6).
- **Not directly:** TFH's frame pacing waits for the buffer swap; BH has one displayed
  bitplane buffer and no swap (profiling.md §5). TFH's merge c2p converts only changed
  groups of 32 pixels, unlike the full-frame merge rejected here (`docs/c2p.md`); whether a
  delta merge pays on BH is unmeasured.

## Not done yet, in order

1. **Seed BH's second random generator at flight start** in the VERIFY build (shift register
   `bh:15bf8`, state `-6070/-6068(a4)`), then re-run the cross-CPU state comparison
   (68000 vs 68020 at frame 120 now differs in 1059 bytes; profiling.md §9). With that, game
   state can be compared between any two machines frame by frame: the tool for checking a
   decoupling design.
2. **The 68030 ceiling.** A 50 MHz `SWAP_ONLY` run found the flight already at frame 1539 when
   the anchor was armed: map that machine's screens against the tape first.
3. **Dynamic T for BH**, now that Their Finest Hour's version is finished (its Enhanced
   framerate, below; the lessons are in AmigaXDev `docs/playbooks/fixed-time-simulation.md`): the coverage test (profiling.md §9) shows the flight
   model and the drones follow T and the stick needs the reference-T division. BH also needs
   its own field counter (no VBL count exists), T restored at mission setup (`bh:1341c`),
   `10186(a4)` and countdowns recomputed, the slot-128 pool sized for T = 50 (16 slots is all
   there is), the two T-scaled busy-wait delays replaced with field waits, and TFH's
   truncation work at large T.
4. **The state map** for the flight model (position `10908/11484/12060(a4)`, attitude
   `14328/14952(a4)` integrated at `bh:79f0`, speed, the drones), from `STATE_ONLY` dumps.
5. **v1.0 vs this slave.** v1.0 was chip-only by design ("too fast" with fast RAM); compare
   the two on the same window by game state once a step-rate design exists.
6. **CUSTOM gating** for the first patch, declared in `slv_config`, with a disabled-bytes
   checker (AmigaXDev `docs/playbooks/new-game-playbook.md` §10; Test Drive 2 has one).

## Decision for the user

Game time is coupled to the frame rate, so a faster renderer, fast RAM or a faster CPU makes
the whole game faster: on a 68020 the turn runs at 28.8 fps, so the whole game runs 3.1 times
as fast as on the 68000. That is why Galahad shipped a chip-only slave, and the fast memory
now in this slave speeds the game up too (5 % on the 68000). Possible designs:

- **A. Fixed-rate simulation, catch-up.** Run the simulation calls of the flight loop
  (`bh:75ba`..`bh:de16`) at a fixed rate S from a field counter, as many steps per rendered
  frame as are due, then render once. Game speed is constant and slow machines catch up, but
  motion is only as smooth as S. Small patch (the loop is one function); S would be the
  intended step rate (item 3; guess: near the A500's 6–11 fps), so 50 fps would show
  repeated frames.
- **B. Scaled step (dt).** Make every per-step increment proportional to the time since the
  last frame: integrations of position, attitude, speed, timers, AI, sound triggers. Smooth
  50 fps, but every rate in the simulation must be found and scaled, with fixed-point care.
  Large reverse-engineering job; needs the state map first.
- **C. A + interpolation.** Simulate at S, render at the display rate by interpolating object
  and camera positions between the last two steps. Smooth 50 fps without touching the
  simulation's rates, but the renderer must take interpolated inputs (camera, objects).
- **E. Dynamic T** (the user's question, 2026-10-07): set `10184(a4)` each frame from the
  measured fields per frame, one step per rendered frame as now. B with the plumbing already
  in the game, if item 3 shows T reaches everything. Its variant: **fixed T with fixed
  steps** (T = 50 or 25, one step per elapsed field or two, as in Stunt Car Racer and Revs).
- **D. Cap only.** Limit the frame rate to the A500's (e.g. 10 fps) so fast machines play at
  the original speed. Trivial, but not the goal.

Until then, keep the slave's fast memory? It follows the user's memory rule but changes game
speed on fast machines; a `slv_MemConfig` alternative (chip-only, like v1.0) could keep the old
behaviour selectable.
