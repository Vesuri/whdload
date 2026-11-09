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
  list; without it `pl_bh` is v1.0's manual-check patch and the cache flush (`tools/pl_check.py`, in
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

2026-11-09, plan step 3 (below):
- **Timers and combat** (`src/combat.s`): what the game counted in steps lasts its time in
  seconds at any T. The routines pass their Unicorn checks at T 4/7/25/50, and with T
  changing, on the 68000 and 68040 (`tools/combat_check.py`, in `make check`).
- The tape's spiral now descends alike on the 68000 and the 68030/50: altitude lost by
  20 s differs by 1.2% (it was 13%).
- Flight records (rectime, `CUSTOM2=1`): game time / real time from the second second on is
  1.0010 on the A500 and 1.0000 on the 68030/50, and both machines fly the tape to its end.
  The A500 rendered 12.4 fps against 12.9 at step 2 (one record each; another step-3 run
  gave 12.2), so step 3 costs about 4%. Not profiled.

2026-11-09, the 68040 (reported from `make run SETUP=a1200-040`, `CUSTOM2=1`):
- **BH writes code, and the caches did not see it.** `bh:18360` (from the view setup,
  `bh:170e8`) rewrites the opcodes (`and.b`/`or.b dN,d16(a1)`) and displacements of the
  unrolled plane writes `bh:18478..19a7e` whenever the view's angle changes, and the span
  loop (`bh:1734c`, `bh:173aa`) ends each span by writing an `rts` into that code at the
  span's last row, calling it at the first row and restoring the word. With `CACHE` the
  68040's instruction cache ran stale code (its copyback data cache held the writes): spans
  past their end (stray lines, a grey band from a drone along the horizon), then a span
  entered mid-instruction (Illegal Instruction at `bh:18c90`, WHDLoad `COREDUMP`; earlier an
  Access Fault in Intuition). Original mode did the same; `NOCACHE` did not. Found by
  comparing BH's code hunk in a flight dump with the file (only the relocations, the
  slave's patches and those blocks differ) and from the core dump, where the `rts` sat in
  the block. The slave flushes the caches after the generator when it rewrote the code
  (`gen_flush`, `pl_bh`) and, on a 68040 or 68060, between each span's `rts` and its call
  (`pl_span`). A 68020's or 68030's instruction cache is direct-mapped (the 68020's 64
  lines of 4 bytes indexed by address bits 2-7, the 68030's 16 lines of 16 bytes by bits
  4-7), so there only the lines of the two written words are replaced: after each write
  the slave calls an `rts` at the same bits 2-7 in a 256-byte block of `rts` allocated at
  install (`pl_span_evict`, `sled_alloc`; without the memory, the flush). Chosen from
  WHDLoad's attention flags; both modes. The flush per span cost the 68020 12% of its frame rate: 33.09 fps
  against 37.56 with the eviction (rectime, `CUSTOM2=1`, fields 50..1750 of one flight
  each). Checked with the `spancheck` build (VERIFY): before each span it sets the end
  row's byte to the span colour's complement and afterwards counts the spans whose end
  row's nibble changed. Without the flush on the 68040: 45983 of 91707 spans ran past
  their end; with it 0. A build whose spans never get their `rts` was counted at 32962 of
  33043, so the check sees a span that runs on. The eviction gave 0 on the 68020, 68030
  and 68040 (where it flushes). On the 68020 and 68030, FS-UAE also gave 0 with no
  flush or eviction at all, so the emulator does not show stale code there, and the
  eviction rests on the caches' documented organisation, not on a measurement. TFH's later engine does
  not write code (its generator `bob:2cd7a` fills a table of offsets and its span loop
  reads it), so TFH needed nothing.

- **The main menu's selection raced** on fast machines. T is 0 until a mission is chosen
  (`bh:1e34`, `bh:2198` load it), so every `bh:30a` pause before that was none, among them
  the one after each selection move (`bh:28e2`); only the A500's slow redraw held the
  selection back. With `CUSTOM2=1`, `dt_delay` times these pauses with BH's base T
  (`10182(a4)` = 7, `bh:54a`), as after a flight. That made the selection sluggish (12.6
  fields a step), so its pause (`bh:2934`, n = 4) is 2: 6.3 fields, 8 steps a second. Original
  mode keeps v1.0's behaviour.

- **Mouse up raised the nose, as mouse down did** (`CUSTOM2=1`, every machine). BH keeps the
  pitch rate `28508(a4)` as |stick| / T (`bh:795a..797e` negate the stick but not the
  quotient; the roll rate is signed) and its readers (`bh:7a24`, `bh:7b44`) take the
  direction from the stick. `dt_stick` gave it the stick's sign, negated twice for up.
  Found with the `mouse` build's flight records (pitch against mouse down, still, up; the
  68030 in original mode went the other way) and `timing_check.py`'s new pitch check, which
  runs BH's attitude step `bh:79f0..7a72` original against patched for both signs. TFH's
  stick fix scales the input (`muls`) and leaves the game's rate code alone: not affected.

2026-11-09, plan step 4 (below):
- **Rendering** (`src/render.s`, `CUSTOM2=1` only): the point transform `bh:16bca` (TFH's
  arithmetic in registers; `mulu.l` on the 68020, 68030 and 68040), the horizon row fill
  `bh:160ba` and `bh:15ea2..15ece`, and the run-length overlay `bh:161ec`. They leave
  everything the originals leave, on the 68000, 68020 and 68030 (`tools/render_check.py`,
  in `make check`). Flight records (rectime, `CUSTOM2=1`, fields 50..1750 of one flight
  each), before step 4 and now: A500 9.50 and 9.88 fps, 68020 31.21 and 37.56 (with the
  span eviction above), 68030/50 50.0 and 50.0.

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
   `tools/pl_check.py` (pl_bh is the manual-check patch and the cache flush) and `tools/timing_check.py`.
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
   - 16.16 with carried fractions: the stick rates (the pitch rate a magnitude, as BH's)
     and the turn (`bh:79fe`), the object step
     and polar split (`bh:8290`; `831c`, `839e`, `842a`, `855c`, `8622`), the AI turn
     (`bh:11e50`, `11ee2`), all ported from TFH with BH's globals and 144 slots;
   - the busy waits `bh:30a` and `bh:12ac` wait their 68000 length in fields;
   - the slot-128 pool is set up once from the mission's T (profiling.md §9): nothing to do
     here; its animation is the effects cadence (step 3).
   The descent in the tape's spiral, which differed by 13% between machines after this step,
   was the attitude code (FR-15, step 3).
3. **Timers and combat** — **done** (`src/combat.s`, included by timing.s; its state is in
   timing.s's buffer, cleared at each flight's start; `FASTMEMSIZE` grew by $17000 for its
   85 KB). The policy: a rate per second divides by the live T and carries its fraction. A
   quantity the original counted in steps is kept as it was at the mission's T (tm, what
   the A500 was tuned for) and timed in seconds, for example a T/3 reload = floor(tm/3)/tm
   s. A countdown set as k·T lasts k s, whatever T does meanwhile. Each has a check in
   `tools/combat_check.py`.

   | BH system | BH sites | TFH item | Change |
   |---|---|---|---|
   | attitude | `11238`..`11d90` | FR-15 | rates with carried fractions per plane and channel; pole reflection; the climb loss tm·max(1, floor(r/tm)) a second and the sink 16·tm a second |
   | fuel | `111dc` | FR-28 | the fraction carried |
   | guns, bursts | `c36c`, `c388`, `c70c`, `c76a` | FR-07 | Q24 reload clocks of floor(tm/3)/tm s, armed once a shot (the fire code runs once per barrel); bursts count shots, so they follow |
   | release wait, object lives | `ce34`, `c958`, `ce02`, `cf26`, `8408`, `d542`, `83ea`, `8512`, `8588`, `ebd2` | FR-05, 08 | countdowns in seconds beside the count, which is rewritten each step as ceil(seconds·T) |
   | falling objects | `8440`, `8470` | FR-01 | gravity tm·max(1, floor(11/tm)) a second; the height moves by the step's mean speed, fractions carried (a 5 s drop is the same at every T; the original at T 7 fell 2% further) |
   | effects, aircraft and ship damage | `aec8`, `de16`, `e28e` | FR-03, 10, 11 | Q24 clocks at tm/(floor(tm/8)+1), tm/(floor(tm/3)+1), tm/(4tm+1) Hz |
   | flak | `e7b2`, `e9d4`..`eb40`, `e580` | FR-06 | delay limited to a word; jitter × T/tm; the delay becomes a timer when the burst is made; the aim point (`e7d8`, velocity × (delay + T) steps) is consistent already |
   | AI decisions | `f010`, `f074`, `12d14`, `12d22` | FR-12, 14 | every 2 s for each eligible object, the earliest due first (the original served one object a step) |
   | AI and gunner lead | `cac6`, `caf2`, `cb1e` | FR-13 | n steps at tm = n/tm s of the target's motion; the AI lead `12b22` is consistent already |
   | hit test | `dae6` | — | TFH's swept test with BH's 400 box |
   | mission waits | `ecd0`, `ed12`, `ef12` | FR-20 | (40tm+1)/tm and (4tm+1)/tm s |
   | messages | `8858`, `886c` | FR-21 | 80 steps at tm (11.4 s at T 7) |
   | replay | `77a2`, `8eae`, `78aa`, `7902`, `371a`, `377a` | FR-22, reduced | the film in the buffer: 7680 steps or 128 s, each step's T kept and replayed (`dt_frame`); timing.s's state saved and restored with the game's two states |

   Corrections to the plan's table: BH has no bomb guidance (`bh:ecaa` is the mission scan,
   FR-20; `bh:8742` clamps a position); `bh:10200` (script waits) is an empty stub; contact
   (`bh:d106`, FR-19) uses no T and keeps no count. Also consistent already: the slot-128
   pool (`bh:13524`, the mission's T), `bh:12404` (dz·T·3), the decelerator `bh:1207c`
   (it carries its own fraction in 15984), the drag's speed loss `bh:83fa` (once per drag
   interval, now a timer), and the AI script counters 16688 (counted per decision). The AI
   muzzle offset `bh:c9f2` (2000/T) is left as it is. Every remaining step-counted
   countdown was listed (`subq`/`addq` on globals and tables); the rest count events,
   statistics, menus or frames.

   Closed as absent or already covered:
   - FR-02 (group timer): BH has no group scheduler. Overflow audit: every stored multiple
     of T is a word, the largest at T 50 is 180T = 9000; the one overflow was the flak
     delay, now limited.
   - Not in BH: FR-04 (no world clock or daylight), FR-18 (no drift terms), FR-25 (input
     arrives through `input.device` events).
   - FR-16 (attitude recovery), FR-17 (ground steering) and FR-24 (gunner aim): BH has no
     T site or step count for them beyond those above (all 67 uses of 10184/10186 were
     listed); the player's recovery is the attitude code (FR-15).
   - Covered by step 2: FR-23 (the replay camera, `bh:7982`, goes through the view
     controller `bh:7f30`, which step 2 changed).
   - FR-26 (audio envelopes) matters only on NTSC.

   A patch must not cover a branch target. The release wait's first patch (`bh:c372`)
   overwrote `bh:c376`, the target of the `beq` before it; the guns check crashed on it. All
   94 patch sites were then checked against every branch target in the disassembly.
4. **Rendering** — **done** (`src/render.s`, from timing.s's patch list; done when the
   68030/50 holds 50 fps in the turn and the A500 is no slower than before). A 68020
   profile of the turn (flight frame 90, 100 fields, caches on, `CUSTOM2=1`) put these
   routines' self time at or above 5% of the frame: c2p `bh:1a2c2` 14.6%, the polygon fill
   `bh:15cb6` 9.6% (with its row fill `bh:160ba` 3.4%), the overlay `bh:161ec` 6.8%, the
   transform `bh:16bca` 5.4% and the span loop `bh:1719c` 5.4%.
   Cycles per call on the 68020, original and now, from traces: transform 2006 and 1307,
   polygon fill 83430 and 54214, overlay 36606 and 33765 (68000: 3597 and 3013, 106185 and
   86214, 59986 and 53858).

   | Routine | Change |
   |---|---|
   | transform `bh:16bca` | TFH's register version of the same arithmetic: differences, signs and partial sums in registers instead of data-hunk globals (only 568, 570, 572 and 576 are read outside it); each matrix term one 64-bit `mulu.l` on the 68020..68040; the 68060 traps that form, so it takes the 68000 version. The perspective divide `bh:16f6e` is still BH's. |
   | row fill `bh:160ba`, `bh:15ea2..15ece` | each run of longs a jump into 32 `move.l` instead of `move.l`/`dbf` |
   | overlay `bh:161ec` | a whole byte inside a run is `c<<4 \| c` whatever it held, so one `move.b`; only the odd first and last pixels are merged |
   | span loop `bh:1719c` | its own code unchanged; the flush after each span's `rts` (in the slave) replaced by the cache-line eviction on the 68020 and 68030 (above; both modes) |

   Not changed: the c2p (TFH's merge c2p is a full-frame conversion; BH's is a delta c2p
   and the full-frame one was 40% slower, `docs/c2p.md`), TFH's projection routines (BH's
   `bh:16cd8`..`16f58` counterparts are not 5% of the frame), and the pixel plot
   `bh:1a3d6` (2.2%).
5. **Release:** Galahad's installer (`BattleHawks1942.lha`) with both `(SLOW)` and `(FAST)`
   replaced by the release slave, `CUSTOM2=1` in its three icons, a ReadMe entry above
   Galahad's; then play-testing on real machines.
