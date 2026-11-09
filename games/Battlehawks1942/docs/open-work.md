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

2026-11-09, Enhanced framerate plan steps 0–2 (below):
- **`tools/xmatch.py`**: TFH's `bob` against BH, matched runs, sites, globals, constants,
  BH's jump table.
- **Scaffolding:** `C2:B:Enhanced framerate` (`CUSTOM2=1`) applies timing.s's own patch
  list; without it `pl_bh` is v1.0's manual-check patch alone (`tools/pl_check.py`, in
  `make check`). Caches on (`CACHE`). The tape presses Return until the flight, on every
  CPU. Fractions in a buffer allocated at install (none: no patches), `FASTMEMSIZE`
  `$81000`. Flight records (`tools/record.sh`, `tools/speed.py`, the `rectime` build).
  Original-mode baselines of the turn, caches on: 68000 9.0, 68020 28.4, 68030/50 55.6 fps
  (profiling.md §6).
- **Decoupling** (`src/timing.s`): game time follows real time from the flight's second
  second on within 0.05% on the 68000, 68020 and 68030/50 (12.4, 39.5 and 50.0 fps), and the
  same input in real time flies the same turn on all three (heading rate per roll within 1%).
  The routines pass their Unicorn checks at T 4/7/25/50 on the 68000 and 68040
  (`tools/timing_check.py`, in `make check`).

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
  counter (it has none; plan step 2) and from the mission T at `bh:1341c`.
- **Countdowns set as multiples of T** last their time only while T stays put; TFH's fix is
  the averaged T, and its audit (FR-01..FR-28) replaced frame-counted timers with elapsed
  time one system at a time. Its list (debris, group timers, effects, world clock, projectile
  life, flak, gun reloads, bomb salvos and guidance, damage, AI decisions and aim, script
  waits, mission waits, messages, replay and camera, field-based input, audio envelopes, fuel)
  is the checklist for BH's 25 `divu.w 10184(a4)` sites and the timers in units of T.
- **The stick:** TFH scales the counts by T/8 (its reference T) at the end of its input
  routine; BH's `STICKREF` experiment (divide by the reference T 7) is the same fix (done:
  BH divides by the mission's T, plan step 2).
- **Fractions at large T:** at T = 50 per-step increments truncate to nothing; TFH carries
  16.16 fractions per object for position, the player's rates and the AI turn. BH's
  integrators (`bh:79f0`, the world arrays at `10908/11484/12060(a4)`) will need the same.
- **The method:** native CPU checks of single routines under Unicorn (68000 and 68040) from
  a flight snapshot, comparing equal elapsed game time at T = 8/25/50/60 and changing T;
  input tapes and pinned RNG in the VERIFY build only; every change behind one
  `CUSTOM` option with the original bytes untouched when it is off (plan step 1).
- **Not directly:** TFH's frame pacing waits for the buffer swap; BH has one displayed
  bitplane buffer and no swap (profiling.md §5). TFH's merge c2p converts only changed
  groups of 32 pixels, unlike the full-frame merge rejected here (`docs/c2p.md`); whether a
  delta merge pays on BH is unmeasured.

## How much of TFH's code BH shares (2026-11-09)

Matched by normalised instruction runs (12 or more instructions, addresses, offsets and
large immediates masked; `tools/xmatch.py`):

- 40% of BH's hunk 0 equals TFH's `bob`. 602 TFH data globals pair with BH's: T
  `11700`→`10184(a4)`, T/8+1 `11702`→`10186`, heading `18162`→`14328`, roll `19198`→`15240`,
  object life `20798`→`16816`.
- 48 of TFH's 162 game-patch sites (not counting NOPs) lie in matched code: object step and
  polar split (`bh:8290`, `831c`, `842a`, `855c`, `8622`), AI turn (`bh:11e50`/`11ee2`), swept hit
  (`bh:da6e`), shot life (`bh:c958`, `8588`), flak (`bh:e556`..`ebb6`), effects (`bh:aec8`),
  ship damage (`bh:e28e`), AI lead (`bh:12b22`, `ca76`), script waits (`bh:10200`), AI attitude
  (`bh:11238`..`11d90`), bombs (`bh:8742`, `ecaa`), debris (`bh:ce02`, `cf26`), sound
  (`bh:1ac6e`, `1acbe`). About 14 more match closely: c2p `bh:1a2c2`, fuel `bh:111e2`, aircraft
  damage `bh:de16`, object loop `bh:8266`/`86b0`, replay camera `bh:784a`/`77f8`/`7982`.
- BH's own T sites are the patterns TFH's audit fixed: gun reload T/3 (`bh:c70c`/`c76a`),
  aircraft damage T/3 (`bh:de2c`), ship clock 4T (`bh:e2a2`), drag 5T (`bh:8408`), mission
  wait 40T (`bh:ed02`), and BH's 180T (`bh:d542`).
- Constants differ inside matched code (TFH's bomb slots end at 52, BH's at 28; hit
  tolerance 500 against 400; native replay snapshot 195 fields against 112): ports take BH's.
- BH-specific: no field counter (the level-3 handler `bh:1ac26` can count); one displayed
  bitplane buffer (TFH's swap pacing and tear fix do not apply, a one-frame-per-field cap
  does); input through `input.device` (no JOY0DAT wrap fix); no time acceleration; T from the
  mission record; simpler player rates (`bh:7920`..`7a6e`); the transform `bh:16bca` is
  TFH's `bob:2f4ae` arithmetic behind a C entry with an early cull; the c2p is TFH's original
  without the cockpit mask.
- The slave does not define KickEmu's `CACHE`, so `kick13.s` turns all caches off: the 68020
  baseline (28.8 fps) is with caches off.

## Plan: Enhanced framerate (the user's request, 2026-11-09)

Simulation speed separate from the frame rate and rendering as fast as possible on faster
machines, every change behind one option, with the least effort by reusing TFH's work. This
replaces the earlier open items (the RNG seed: routine checks need no cross-CPU equality;
the state map: the global map gives it; the 68030 ceiling: step 1; dynamic T: step 2;
gating: step 1) and decides the design question: TFH's dynamic T (E).

Defaults (the user may override):
1. `C2:B:Enhanced framerate` (`CUSTOM2=1`, as TFH); off leaves BH's bytes original.
2. Game speed is real time, as TFH. The original ran the turn at 1.3x real time on the A500,
   so it feels about a quarter slower there.
3. The stick divides by the mission's original T instead of the live T: in the original the
   mouse's response per real second depends on T only, not on the frame rate, so this keeps
   its feel. No sensitivity option at first.
4. `CACHE` always on, as TFH; TFH's one-shot sound fix too (BH's sound routine equals
   TFH's), if BH shows the bug.

Machines: 68000 + 512 KB chip + 8 MB fast (the capture machine: slow reference, traces);
68020 A1200 + 8 MB fast (traces of the fast path); 68030/50 + 8 MB fast (50 fps ceiling and
the cap, frame counts only); Unicorn 68000 and 68040 (routine checks). PAL only.

0. **Translation tool** `tools/xmatch.py` — **done.** `runs`, `sites` (TFH's patch lists:
   48 sites exact, 14 GOOD, 31 WEAK, 81 NONE), `site`, `globals`, `consts`, `jt` (BH's
   `jsr d16(a4)` table from its data hunk's relocations), `dis`. It extracts `BH` from
   `Disk.1` and reads TFH's installed `data/BOB`, both checked by SHA-256.
1. **Scaffolding** — **done.** `CUSTOM2` through `resload_Control` in `_cb_dosLoadSeg`;
   `timing_patch` applies `_pl_timing` only then, after allocating its fractions (1160
   bytes, `MEMF_PUBLIC|MEMF_CLEAR`; without them nothing is patched). `make check`:
   `tools/pl_check.py` (pl_bh is the manual-check patch alone) and `tools/timing_check.py`.
   `CACHE` in both modes. The tape presses Return every 300 fields from field 3000 until the
   first flight frame. Baselines: profiling.md §6 (original mode, caches on).
2. **Decoupling** — **done** (`src/timing.s`, the core of TFH's timing.s):
   - a VERTB server (`AddIntServer`) counts fields; `dt_rate` as TFH;
   - `dt_frame` at `bh:6e52` sets `10184`/`10186` as TFH, with two changes found by the
     flight records: the game may run up to 4 fields ahead of real time, not one (at BH's
     3–6 fields per frame on the 68000 the integer T swings the time owed by about a field,
     and TFH's limit cut the swings off: 1% fast), and the frame average starts at the first
     frame measured (from the mission's T, 1/8 at a time, the 68030 ran 0.9 s ahead in the
     flight's first half second, which at T 50 the game cannot give back);
   - the mission's T saved at `bh:1344e`, restored at the flight start (`bh:6b1c`) and when
     the flight loop ends (`bh:6eb6`: the menus use T too);
   - at most one c2p per field (`bh:6e8e`);
   - the stick (`bh:7920`) and the view controller (`bh:800c`..`8054`) divide by the
     mission's T: mouse counts and key presses both arrive per event, not per frame; the
     mouse limit (`bh:3eb0`) scales by mission T / T in flight only (`bh:3e98` reads the
     menus' input as well);
   - 16.16 with carried fractions: the stick rates and the turn (`bh:79fe`), the object step
     and polar split (`bh:8290`; `831c`, `839e`, `842a`, `855c`, `8622`), the AI turn
     (`bh:11e50`, `11ee2`), all ported from TFH with BH's globals and 144 slots;
   - the busy waits `bh:30a` and `bh:12ac` wait their 68000 length in fields;
   - the slot-128 pool is set up once from the mission's T (profiling.md §9): nothing to do
     here; its animation is the effects cadence (step 3).
   Not yet agreeing between machines: the descent in the tape's spiral (at 20 s the 68000
   has lost 13% more altitude than the 68030/50). Probably the attitude code TFH fixed as
   FR-15 (`bh:11238`..`11d90`); step 3 starts there.
3. **Timers and combat** (TFH's FR-01..FR-28, retargeted with BH's constants, each with its
   check at T 2/4/7/25/50 and changing T on Unicorn 68000/68040):

   | BH system | BH sites | TFH item |
   |---|---|---|
   | guns: reload, bursts | `c366`, `c70c`, `c76a` | FR-07 |
   | bullets: life, damage age, swept hit | `c958`, `8588`, `da6e` | FR-05, hit test |
   | bombs and torpedoes | `c378`, `8742`, `ecaa` (slots 20–27) | FR-08, FR-09 |
   | debris | `ce02`, `cf26`, `8408`..`8480` | FR-01 |
   | effects (T/8+1 cadence) | `aec8`, `aedc`, `6d2e` | FR-03 |
   | damage: aircraft, ships, sinking 180T, flak | `de16`, `e28e`, `d542`, `e556`..`ebb6` | FR-10, 11, 06 |
   | AI: decisions, aim, script waits, attitude | `f074`, `12b22`, `ca76`, `10200`, `11238`..`11d90` | FR-12..15 |
   | mission waits, messages, contact, fuel | `ed02`, ~`8850`, `d106`, `111e2` | FR-20, 21, 19, 28 |
   | replay camera | `78aa`, `3772`, `37ca` | FR-22, reduced |

   The replay camera has a 1023-step in-memory film and no files: store each step's T in an
   allocated buffer, size the film for 128 s, replay with the recorded T. Plus: every stored
   multiple of T must fit its byte or word at T 50 (TFH's FR-02). Probably absent, to confirm
   and close: FR-02, 04, 16, 17, 18, 23, 24, 25; FR-26 matters only on NTSC.
4. **Rendering** (after a 68020 profile of the turn, caches on): TFH's register point
   transform (`mulu.l` on 68020+) at `bh:16bca`, keeping BH's entry and cull; BH's
   counterparts of TFH's projection routines (near `bh:16cd8`..`16f58`); TFH's merge c2p
   without the mask, kept only if faster (BH's c2p has no masked byte merges, most of TFH's
   gain); BH-only hot spots if each is at least 5% of the 68020 frame (`bh:15cb6` polygon
   fill, `bh:161ec` overlay, `bh:1a3d6` pixel plot); each checked against the original with
   TFH's equivalence checks. Done when the 68030/50 holds 50 fps in the turn and the A500 is
   no slower than its step 1 baseline.
5. **Release:** Galahad's installer (`BattleHawks1942.lha`) with both `(SLOW)` and `(FAST)`
   replaced by the release slave, `CUSTOM2=1` in its three icons, a ReadMe entry above
   Galahad's; then play-testing on real machines.
