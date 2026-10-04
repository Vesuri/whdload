# Open work — Test Drive II: separate the simulation from rendering speed

> **Handoff document.** Read this first, then `docs/profiling.md` (tools, traps) and
> `docs/optimisation-plan.md` (performance ranking). Everything here was measured or read from
> the binary on 2026-10-04; each claim says which. Do the work items **in order**.

**Current status:** W1–W6 complete, including the user-requested one-field
refinement (2026-10-04). The original handoff and three-field measurements remain
as historical context; the one-field completion records below describe this release.

## The goal

Make the game **advance at the same speed regardless of the CPU it runs on**: game time
(car motion, opponents, clock, sounds) tied to real time, while rendering runs as fast as the
machine allows. Shipped as **WHDLoad slave patches** (`whdload/TestDrive2HD.s`, `resload_PatchSeg`
list `pl_main_v1`), for `duel` v1 only.

Speeding up the renderer is a **secondary** goal and only matters once the timing architecture
is understood: a faster renderer is worthless if it also speeds up the game, and pointless if the
simulation only moves things 8 times a second (see below).

## ⚠ Working rules (read twice)

1. **Architecture before instructions.** Do not optimise any routine, shave cycles off a loop,
   rewrite Aztec C in asm, reorder blitter waits, or remove interrupts until W1–W4 are done and
   the user has picked a design (W4). A 2% win in a loop is not progress on this goal; a correct
   statement of how game time advances is.
2. **No claim without a measurement**, and no measurement from the wrong instrument:
   - A/B frame rates only from `tools/fixed_window.sh` (never two `tools/profile_demo.sh` runs —
     the demo content differs per run; a sign scene runs at 4.3 fps, open road at 7.2).
   - **Screenshots do not prove game speed**: different machines/boots land in different demos
     (W3 explains why). Compare **game-state variables** (W2), not pictures.
   - Treat a ±0.15 fps difference as noise (three boots of the shipped slave: 6.9, 6.9, 7.1 fps).
3. **Every change is a slave patch**, behind a WHDLoad tooltype, built with `make -C whdload`,
   run with `SLAVE=$PWD/whdload/TestDrive2.slave`. Never commit game, Kickstart or WHDLoad bytes,
   traces, dumps or screenshots (`tmp/` is ignored). Commits: author
   Vesa Halttunen <vesuri@jormas.com>, unsigned, no Co-Authored-By, one commit per coherent
   feature. Never `pkill fs-uae`.
4. **Addresses**: `duel:XXXXX` is an offset into `duel`'s root code hunk (hunk 0) — the same
   numbering as the slave's patch lists. A file offset is hunk offset + `$28`
   (`m68k-amiga-elf-objdump -b binary` on the file prints file offsets). Kickstart addresses are
   ROM addresses (`kick:FCxxxx`); kickemu copies the ROM into RAM, the tools translate.

## What is known

### Machine and tools (working, committed)

`amiga/run.sh` boots the WHDLoad install; `tools/td2.py serve` holds gdb on FS-UAE's Barto stub
(`shot`, `profile N file`, `until ADDR`, `gdb CMD`, `stop`/`cont`, `quit`); the stub is
**read-only** (no memory/register writes). `tools/fixed_window.sh OUT [SLAVE]` traces 100 fields
from the first entry to `duel:0789c` after a deterministic boot; `CPU=68020 FAST_KB=4096
CHIP_KB=1024 EXTRA_ARGS=` selects another machine. `tools/frames.py` prints swaps per field,
fps, blitter waits, interrupts and DMA use. `tools/td2_report.py` gives per-context self and
inclusive times. All in `docs/profiling.md`.

### Frame structure (measured, one 994 724-cycle frame, A500-equivalent, `w3` window)

Main game task (stack ≈ `$D1E000` on the A500-equivalent machine), inclusive % of the frame:

```
[outer main loop, entered before the trace]
├── duel:06432   74.5%
│   ├── duel:06c0c   64.3%   render
│   │   ├── duel:0844e   20.5%   road/ground spans (calls duel:0789c) + movem back-buffer clear
│   │   ├── duel:079c6   12.3%
│   │   ├── duel:08f40   10.2%   objects (shape blits, duel:0f114)
│   │   ├── duel:07370    8.6%   projection (muls)
│   │   ├── duel:0876a    4.7%
│   │   ├── duel:08c82    4.3%
│   │   └── duel:0766c    2.8%
│   └── duel:0ab60    9.5%   → duel:0973c 9.1% (calls the masked copy duel:09588)
└── duel:01bb0    2.2%   → duel:05872: buffer swap, contains the slave's set_copper patch (duel:0588a)
23% of the frame is not the main task: interrupts (~15%) and a second game task (~7%).
```

No routine in the main task looks like physics: its children are all drawing. **Where the game
state is advanced is not yet proven** — see the second task.

### The second game task (measured)

A second task running `duel` code (stack ≈ `$CFD000` on the A500-equivalent machine, ≈ `$57D000`
on the 68020/fast machine) runs:

- **every field**: a light slice of ~3 000 cycles (code in the `duel:10d00`… and `duel:0ea00`…
  pages; the latter holds the RNG `duel:0e9e2` and the joystick read the slave hooks with
  `PL_PS $00EAA2,read_joydat` — slave patch offsets are hunk offsets, verified: file `$EACA` is
  `move.w $dff00c,d0`);
- **every 6 fields exactly**: a heavy slice of ~41 000–47 000 cycles (code in `duel:0dd00`…,
  `duel:0d800`…, `duel:08800`…; `duel:0d6ae` is the hottest routine of this task).

The 6-field period is **the same on both machines while the render rate is not**:

| Machine | render | heavy task-2 step |
|---|---|---|
| A500-equivalent (68000, 512K chip + 1.5M slow) | 7.0 fields/frame (7.1 fps) | fields 5, 11, 17, 23, 29, 35… |
| 68020 + 4 MB fast | 4.95 fields/frame (10.1 fps) | fields 4, 10, 16, 22, 28, 34… |

The heavy step is not synchronised with the buffer swaps (swaps at fields 3, 10, 17, 24…).

**Hypothesis H1 (strong, unproven):** the game simulation runs in this second task at a fixed
50/6 ≈ **8.33 Hz**, paced by the vertical blank (graphics.library `WaitTOF`: the game's stub
for graphics `-270` is at file `$1151A` = `duel:114f2`, graphics base in `-12964(a4)`), and the
main task renders the latest state as fast as it can. If true, **game speed is already
independent of the CPU** and the real problem is different: motion updates only 8.33 times a
second, so rendering faster than that shows repeated states.

### Time sources in `duel` (read from the binary, file offsets → hunk = file − `$28`)

| What | Where (hunk) | Notes |
|---|---|---|
| VBL counter `-$30E2(a4)` (long) | incremented at `duel:02330` in the game's VBL server (`duel:0231c`, interrupt context); cleared `duel:01fa2` | read only at `duel:021d2`, `duel:022ec`, `duel:0235e` — all audio-channel timers in the VBL server |
| RNG | `duel:0e9e2`: `seed = (seed*6907 + 130253) ^ VHPOSR`, seed `-18632(a4)` | **mixes the beam position** — any timing change changes the random sequence |
| CIA timers / TOD | none read | only CIA port/ICR accesses (keyboard, disk, fire buttons) |
| timer.device, DateStamp | not opened / not called | devices opened: trackdisk, input, console |
| `WaitTOF` | stub `duel:114f2` | the likely 50 Hz pacing of the second task |
| exec `Wait`/`Signal` | `duel:02756` / `duel:02818` | belong to the custom disk loader (DSKSYNC `$4489`, disk-block interrupt) — not the simulation |
| exec `AddTask` | call at `duel:11264` (stub from `duel:11256`) | how the second task is created |

### Why runs differ (measured + explained)

- Two boots with FS-UAE `--deterministic=1` and the same slave reach the same demo start but
  with different traffic/roadside objects: the RNG mixes in VHPOSR (above).
- A 68020 boot lands in a **different demo** (trees, 5.4 miles) than the 68000 (desert,
  2.5 miles) in the same window: the attract sequence's choice is timing-dependent.
- `fixed_window.sh`'s anchor (first entry to `duel:0789c`) is **not** the demo's race start:
  both windows began with the race clock already at 0:07–0:08.

### Performance facts that matter for the architecture (measured)

- CPU never idles; ~7 fps on the A500-equivalent machine; the CPU stops for every blit
  (11–14% polling BBUSY, 21% with the blitter interrupt disabled). Blitter-finished interrupts
  (~150/frame) mostly overlap those waits: disabling them gains only 6.9–7.1 → 7.2 fps.
- Fast RAM barely helps the 68000; a 68020 with fast RAM renders 10.1 fps.
- If H1 holds, the render rate on a stock A500 (7 fps) is **below** the simulation rate
  (8.33 Hz): some simulation steps are never displayed; on a 68020 (10 fps) some are displayed
  twice.

## Open work — in this order

### W1. Make runs reproducible (infrastructure; required by everything else)

**DONE (2026-10-04).** `make -C whdload verify` includes the v1-only RNG beam-mix
patch, gated by WHDLoad `CUSTOM3=1`. Normal builds and v2 retain the original RNG.
The patch replaces `duel:0e9f0` with `moveq #0,d1; nop; nop`, preserving the following XOR.

The dashboard clock is `-$27A2(a4)` / `-10146(a4)`, long. Its reset writer is
`duel:0bbf8` (`move.l #1,...`); a read-only gdb watchpoint observed 0 → 1, stopping at
`duel:0bc00`. Raw 1 displays as 0:00 (the HUD divides by 600, 100 and 10).
The final window starts at `duel:05a4c`, after setup has drawn the dashboard and before
the gameplay loop starts; the clock is still 1. Starting immediately at the reset mostly
traces setup, so it is not a useful simulation window.

Two deterministic 68000 boots (`tmp/prof/verify-race-a`, `verify-race-b`) gave identical
`barto.Field.shot` MD5s: field 0 `a2c31ccefeec8a15fd78c56c9234405d`, field 99
`412e6285e23e5199a419ae933ab2dc56`. Both start at raw clock 1 and select stage 2 (trees,
5.9 miles). `fixed_window.sh` measured 5.9 fps in each window; this is a new scene/window,
not an A/B performance improvement over the old desert capture.

**Another timing input was in the harness, not the game:** the one-second host poll in
warp can miss the first race on the 68020. An initial 68020 capture's reset watchpoint
reported 1365 → 1, proving it captured a later race. Discard it (`verify-race-020`).
`td2.py serve` now accepts `BOOT_BREAK`, armed while the emulated CPU is still at reset;
`fixed_window.sh` calibrates the loaded hunk address, caches it by machine/arguments/slave,
and reboots to capture the first reset. It validates the loaded hunk against that address.
`BOOT_HUNK` can supply a calibrated address explicitly.

The corrected 68020 first-race capture (`verify-first-020`, 1 MB chip/4 MB fast) observes
0 → 1, selects the same stage 2, and has the same post-setup RNG seed `$E940` as the
68000. It measured 9.3 fps. Its different rendered fields do not establish game speed.
The reset seed `$DE3C` becomes `$E940` during setup on both CPUs; comparing a pre-setup
seed with a post-setup seed would falsely suggest another RNG input.

Run (source the environment in the same shell):
```
source amiga/env.sh
make -C whdload verify
WHD_ARGS=CUSTOM3=1 SLAVE="$PWD/whdload/TestDrive2.slave" tools/fixed_window.sh tmp/prof/check "$PWD/whdload/TestDrive2.slave"
```


**Do:** add a `VERIFY` assembly option to the slave that patches the RNG's VHPOSR mix
(`duel:0e9f0`, `move.w $dff006,d1` / `eor.w d1,d0` — 6 + 2 bytes) to a constant (e.g. replace
the `move.w $dff006,d1` with `moveq #0,d1` + `nop`s via `PL_W`/`PL_NOP`), and anchor the
benchmark on the **race start** instead of the first `duel:0789c` entry (find the routine that
zeroes the race clock — W2 gives the variable; break on its writer with a gdb `watch`, which the
stub supports for writes).

**Done when:** two deterministic boots of the `VERIFY` slave produce byte-identical screenshots at
field 0 and field 99 of the window (`md5` of `barto.Field.shot`), on the A500-equivalent machine,
and the window starts with the race clock at 0:00. If they are still not identical, find the next
timing-dependent input (do not paper over it) and record it in this doc.

Then check whether a 68020 boot of the `VERIFY` slave reaches the **same** demo: if not, the
attract sequence's choice has another timing input; find it the same way.

### W2. Map the game state

**DONE (2026-10-04).** `tools/state_fields.py` reads the allocated data hunk at successive
entries to `duel:0231c`; `state_report.py` reports raw values and change fields.
`state_writers.py` correlates executed simple destination EAs with task stacks. It is not a
complete instruction emulator; absence from its report is not proof of no writes.
`state_watch.py` independently verifies candidate stores with constant-address hardware write
watchpoints. All capture files remain in ignored `tmp/`.

**Data-hunk correction:** the file's hunk-1 payload is `$3A38`, but its allocation in the
HUNK_HEADER is `$1E9C` longs = `$7A70` bytes. Most mutable state is in the zero-filled tail.
Follow the BPTR at `hunk0−4` to get hunk 1's segment link, then add 4 for its data address.
Do not byte-search for it: that can find WHDLoad's PRELOAD copy. In this VERIFY 68000 boot,
hunk 0 = `$CFF0A8`, hunk 1 = `$D10620`, a4 = hunk 1 + `$7FFE` = `$D1861E`.
`td2_report.regions` now includes the full allocated `duel-data` region.

| State | a4 displacement | Size / meaning | Update schedule | Observed writer (duel hunk offset) |
|---|---|---|---|---|
| Player longitudinal position | `-$4356` / -17238 | long, 16.16 road units | six-field step | `0b2a6` (integration); `05a88`, `05aec` temporarily borrow/restore it for demo AI |
| Player speed | `-$33E2` / -13282 | long, 16.16; integer word feeds MPH needle | six-field step | `0a8e6` (add increment); `0a754`, `0a828`, `0a8fa`; `05a9a`, `05ad8` demo borrow/restore |
| Race clock | `-$27A2` / -10146 | long, nominal tenths; initial 1 displays 0:00 | six-field step after movement starts | `05b90` (+1); reset `0bbf8`; finish/penalty path `05c58`, `05eea` |
| Opponent longitudinal position | `-$342C` / -13356 | long, 16.16 road units | six-field step | `0de3e` stores to `2(a5)` with a5 = a4−13358 |
| Opponent longitudinal increment | `-$3424` / -13348 | long, road units per step, player-speed scale /64 | six-field step | `0dd6e` stores to `10(a5)` |
| Same-direction traffic origin | `-$349E` / -13470 | long, 16.16, wraps at road length | six-field step | `0e0f6` |
| Oncoming traffic origin | `-$349A` / -13466 | long, 16.16, wraps at road length | six-field step | `0e1b4`, wrap `0e1be` |
| Render/camera position snapshot | `-$3452` / -13394 | long, copy of player position | once per rendered frame | `06442` |
| MILES display | camera above + `-$4358` / -17240 | derived; road length is word | display recomputed per rendered frame | `08fba` onward reads `road length−camera integer`, ×100 /4325, then decimal digits; no separate continuously accumulated miles counter |
| Gameplay field clock | `-$4340` / -17216 | long | every video field | `01abc` adds 1 through `(a1)` in VBL callback |
| Step deadline | `-$433C` / -17212 | long, field clock units | advances by 6 per heavy step | `05c12`; `-$6CD6` / -27862 is the word constant 6 |
| RPM | `-$3384` / -13188 | long, 16.16 | six-field step | `0a6f0`, `0a750`, `0a7e2`, `0a836` |
| Engine audio period | `-$0AE8` / -2792 | word, computed from RPM | six-field step | `0d156` |
| Fuel | `-$2A46` / -10822 | word | six-field step | `0ade6` |
| Two dashboard animation phases | `-$0BC0` / -3008, `-$0BBE` / -3006 | words | six-field step | `0ae04`, `0ae34` |
| Needle redraw caches (speed/RPM) | `-$6048` / -24648, `-$604C` / -24652 | words, sampled values | once per rendered frame | `0ad6e`, `0ad1e`, helper `0b45a` |
| Four visual/background phases | `-$0C30` / -3120, `-$0C2C` / -3116, `-$0C28` / -3112, `-$0C24` / -3108 | longs; +4000/+5000/+6000/+7000 | **once per rendered frame** | `08cd0`, `08cd8`, `08ce0`, `08ce8` |

In `state-000`, 300 VBL snapshots: clock and opponent position first change at sample 78,
then every six samples through 294 (37 changes). This particular attract demo waits before
moving; a changing word is not necessarily an additional clock. The camera cache changes at
85, 94, 103… with the slower render schedule. In the following 100-field trace (relative
fields 300–399), all listed core writers run at trace fields 5,11,…95 on stack page `$CFC`,
while the camera/phase writers use renderer stack page `$D1D` (camera at 3,14,…91).

Hardware write watchpoints in `state-watch/state/watchpoints.txt` confirmed:
player position 2576994 → 2620780 at `0b2a6`; speed 2802353 → 2902475 at `0a8e6`;
clock 23 → 24 at `05b90`; opponent position 1429220 → 1462868 at `0de3e`.
All four use the second game task's `$CFCxxx` stack.

**Sampling trap:** the demo temporarily substitutes opponent values into the player globals
inside the heavy step. A VBL can interrupt this transaction (sample 0 caught player position
1114112 instead of committed 2031616). Compare initial anchor values and committed values;
classify any isolated mismatch by its PC before calling it a gameplay-speed difference.

**W3 audit already has a concrete target:** the four visual phase accumulators really advance
per render; needle/camera caches merely sample fixed-step inputs. The engine period writer is
in the heavy task. W3 must distinguish visual clock dependence from gameplay dependence.


**Do:** find, in `duel`'s data hunk (hunk 1, `$3A38` bytes; located like hunk 0 — see
`td2_report.regions`, add hunk 1), the variables for: player distance/position along the road,
player speed, the race clock, the "MILES" display value, opponent/traffic positions. Method:
`td2.py gdb "dump binary memory /tmp/d.bin START END"` of hunk 1 at successive fields (stop with
`td2.py until` on a per-field address, e.g. the VBL server `duel:0231c`, or `profile 1`), diff,
classify each changing long/word by **when** it changes: every field, every 6th field (task 2's
heavy step), or once per rendered frame (main task). For each candidate, find its writer with a gdb
write watchpoint (`td2.py gdb "watch *(int*)ADDR"` then `gdb continue`; the PC tells which routine
and therefore which task).

**Done when:** a table in this doc lists each state variable with its `-x(a4)` offset (Aztec C
addresses globals off a4), size, update rate (field / 6-field step / render frame), and writer
routine, for at least distance, speed, clock and one opponent position.

### W3. Prove or refute H1

**DONE (2026-10-04). Measured verdict: H1 holds for the core six-field simulation in the
windows tested, but is partial as a description of the whole game.** Drawing has
its own time-dependent visual state and consumes the simulation's shared RNG.
A faster renderer does not make the measured car/clock/opponents progress faster;
it does change visual animation rates and the subsequent random sequence.

All runs use the first race, stage 2, post-setup seed `$E940`, `CUSTOM3=1`, and the
same relative VBL indices. The first 1,000 samples cover approximately 20 PAL seconds;
the following fixed-window traces cover relative fields 1000–1099:

| Configuration | Render fps (fixed_window only) | Deadline changes / spacing | Clock changes / spacing |
|---|---:|---|---|
| 68000, 512K chip + 1.5M slow (`state-000-long`) | 4.3 | 166 changes; all 165 intervals = 6 fields | 154 changes; all 153 intervals = 6 fields |
| 68020, 1M chip + 4M fast (`state-020-long`) | 6.8 | same | same |
| 68000 + drawing delay (`state-000-slow`) | 2.7 | same | same |

The delay is a VERIFY-only, v1-only `CUSTOM4=1` patch at `duel:0588a`: save d0,
65,536 DBF iterations, restore d0, enter the existing copper hook. Interrupts and
scheduling remain enabled. This is an instrument explicitly allowed by W3; no
rendering optimisation or shipping timing design has been implemented.

At sample 999, all three machines have these exact raw values:

| Player position (16.16) | Speed (16.16) | Clock | Opponent position (16.16) |
|---:|---:|---:|---:|
| 15390991 | 8828952 | 155 | 15894051 |

Every sample 1–999 matches exactly for position, speed, clock, opponent position and
increment, both traffic origins, RPM, fuel, engine period and both dashboard phases.
The few sample-0 differences are the W2 borrowed-state/first-step transaction; initial
anchor values match. Normalised field counter/deadline phases match 1000/1000.
Camera/needle differences are the ages of drawing caches, not accumulated motion.
The slow renderer skips displayed steps while the simulation continues on schedule.
In each subsequent trace the clock/deadline writers execute at fields 1,7,…97,
including at 2.7 fps. No missed or late six-field interval was observed.

**Priority evidence:** `tools/task_state.py CODE.bin BASE` reads the actual Exec
nodes from the full dump. On all three machines the simulation context is the
original `Initial CLI` process (type 13, priority **4**, saved SP `$CFC41C` / `$57C41C`),
while drawing is the separate `Road Drawer` task (type 1, priority **−1**, SP in
`$D1Dxxx` / `$59Dxxx`). Thus “main task” and “second task” in the initial profile
were context labels, not creation order: the created task is the renderer.
This priority relationship explains the measured preemption, but the measurements
establish robustness only for these tested loads, not arbitrary interrupt starvation.

**Extended check:** `state-000-3000` and `state-020-3000` use the current VERIFY
slave with CUSTOM4 off, sampling 3,000 fields (~60 seconds). Position, speed, clock,
opponent position/increment, traffic, RPM, fuel and engine period match **3000/3000**;
the two dashboard phases match 2999/3000 with only the known first-step difference.
Normalised field counter/deadline phases match 3000/3000. Each run has 499 deadline
changes (498 intervals of six fields) and 487 clock changes (486 intervals of six).
At sample 2999 both have position **75909113**, speed **12979580**, clock **488**,
and opponent position **80651103**. No later physical trajectory divergence was
observed, despite RNG divergence. These state-only captures use FIELDS=1 and provide
no additional fps evidence. Comparing the older and current 68020 builds' overlapping
1,000 samples gives 1000/1000 for every core variable, including RNG: the added test
instrument is inert with CUSTOM4 off.

Both `make -C whdload` and `make -C whdload verify` assemble successfully. The current
local slave is the VERIFY build; its instruments remain off unless their tooltypes
are set. Only `pl_main_v1` has the optional patches.

**Remaining dependencies, measured and read from code:**

- Four visual phases at `-$0C30/-$0C2C/-$0C28/-$0C24(a4)` accumulate per drawn frame
  at `duel:08cd0/08cd8/08ce0/08ce8`. At sample 999 phase 1 is **384000 / 600000 /
  236000** on 68000 / 68020 / delayed 68000. They are autonomous visual clocks.
- A rare visual-effect path tests speed ≥95 MPH, then calls RNG once per drawn frame
  at `duel:08db6`; extra calls at `08dc4`, `08dd4`, `08e26` initialise/select shapes.
  Its y/animation counters also advance per draw (`08e06`, `08e0a`). The spawn flag
  is `-7640(a4)`, y is `-7636(a4)`, countdown is `-7626(a4)`.
- RNG's central writer `duel:0e9f8`, seed `-18632(a4)`, runs on **both** task stacks.
  In the fields 1000–1099 trace it is called 105 times in the simulation on all
  machines, plus **9 / 14 / 5** times by drawing. The two normal CPUs first disagree
  at sample **564** (seeds 46036 vs 54697); delayed drawing first disagrees with the
  baseline at 583. Removing VHPOSR alone does not decouple random state from drawing.
  The shared generator also feeds simulation/collision/object-selection paths, so
  matching core variables in a finite window does not prove all future race outcomes
  independent of render rate. Fuel in this demo is distance-derived, not RNG-derived.
- Clock starts at 1 and first advances at sample 78, then 84,…996. Once running,
  ten nominal tenths require **60 PAL fields = 1.2 real seconds**: the dashboard runs
  at **5/6 = 0.8333 displayed seconds per real second**. CPU independence and a
  correctly calibrated real-time clock are separate requirements. These are PAL
  measurements; NTSC has not been tested.

Reproduce state comparisons with `tools/compare_state.py A/state B/state`; it reports
raw values and separately normalises absolute boot field counts. Dumps and traces
are local ignored evidence under `tmp/prof/`; no game bytes are committed.


**Do:** with the W1 slave and the W2 variables, run the same window on the A500-equivalent
machine and on `CPU=68020 FAST_KB=4096` (and a third, slower configuration if available, e.g.
the A500-equivalent with an artificial busy loop added to `set_copper` via a test slave). Record
the state variables at fixed **field** numbers.

**Done when:** a verdict, with numbers:
- **H1 true** if distance/clock/opponents advance identically per field on all machines (same
  values at the same field, given the same demo) and only in the 6-field step;
- **H1 false / partial** if anything that affects gameplay advances per **rendered frame** in the
  main task (list each such variable and its writer — those are what a fixed-timestep patch has
  to move). Pay particular attention to the camera/road scroll, animation counters, the
  speedometer/tachometer needles and sound pitch: they may be renderer-side per frame even if
  physics is per step.

Also answer: **what happens when the renderer is slower than the simulation** (A500: 7 fps vs
8.33 Hz) — does task 2 always get its step (priority), or does it slip? Measure the heavy-step
period over a long window in the heaviest scene you can catch (the vector-font sign scene ran
4.3 fps): if the period stays 6 fields, the simulation is robust to slow rendering.

### W4. Choose the design with the user (stop here and ask)

**DONE (2026-10-04): the user selected option 3:** “We want higher-rate simulation
independent from the frame rate.” Implement a higher-rate fixed simulation step,
scaling per-step quantities and keeping rendering independent. W5 is now authorised.

**Evidence governing the design:** W3 shows an existing preemptible fixed-step
simulation, so wrapping the entire drawing loop in a new physics loop is not justified.
All candidate designs must address the remaining visual clocks, drawing's shared-RNG
consumption/beam entropy, and the PAL dashboard clock calibration:

1. **Minimal correction (recommended for the stated goal):** retain the original
   six-field physics and motion pace; make the remaining animation/random updates
   follow fields rather than drawing, and make elapsed race time track real time.
   Drawing still samples the latest state. Above 8.33 fps, motion remains stepped.
2. **Interpolation:** do the same corrections, then render between snapshots of
   fixed-step simulation state. Preserve physics/AI cadence; improve smoothness on
   faster machines. Requires auditing all moving drawing inputs and adds latency.
3. **Higher-rate simulation:** shorten the interval and scale every per-step physics,
   AI, timer and animation quantity. More responsive movement, substantially greater
   risk of changing handling and race balance; W2 is only the starting map.

The user chose the higher-rate simulation design. Preserve the existing motion pace
where possible, correct elapsed race time to real time, and measure any handling
change caused by finer integration. The exact rate is an implementation choice;
start with a three-field step (16.67 Hz PAL) and scale the old six-field quantities.
Do not start W6 until W5 is validated. The original conditional options below remain background
for the decision; the measured partial verdict above takes precedence.


Write up the options with the W3 evidence and **ask the user**. The options depend on W3:

- **If H1 is true** (simulation fixed at 8.33 Hz, CPU-independent already): the remaining issue is
  smoothness. Options:
  a. *Leave the simulation alone*; only speed up rendering. Above 8.33 fps nothing moves more
     smoothly; worth it only up to ~8 fps on an A500.
  b. *Run the simulation step more often with a scaled time step* (e.g. every 3 fields with every
     per-step increment halved). Requires finding **every** per-step constant in task 2
     (integration of speed into distance, AI, timers, the clock) — incomplete scaling changes the
     game. High risk, high value; W2's writer table is the starting point.
  c. *Interpolate in the renderer* between the last two simulation states (snapshot the state
     variables at each step in the slave, render from `prev + (now−prev)·phase`). Keeps the
     simulation byte-exact; needs every renderer input that moves to be interpolated.
- **If H1 is false**: the classic fixed-timestep loop in the slave: hook the main loop
  (`duel:06432`'s caller) so the per-frame update runs `n` times per elapsed simulation tick
  (VBL count from the game's own counter `-$30E2(a4)`), and render once.

**Done when:** the user has chosen; record the decision here.

### W5. Implement the chosen design

**Follow-up authorised (2026-10-04):** the user requested six one-sixth-sized
substeps per original step, following the Revs/SCR elapsed-time approach, with
appropriate tests and all improvements finished. Retain the independent existing
simulation task; use one PAL field per physical step. Require signed fractional
carries, original-cadence bookkeeping, original-mode handling fixtures, cross-CPU
and slow-drawing state checks, recovery/terminal checks, and new release benchmarks.
The user also reported demo off-road behaviour. The first prototype exposed
unscaled gear-lever travel (early clutch release). Its gear-hook return adjustment
then landed two bytes before the intended instruction; the exception at $D08012
identified that error. The correction has an assembly return-boundary regression
fixture. A 6,000-field normal-demo capture reproduced an early crash and showed that
the demo AI record is a full-step predictor: its speed/distance outputs are discarded,
so they must not be scaled as physical rates. The completed validation is recorded below.

**One-field W5 refinement DONE (2026-10-04).** The v1 optional simulation now
runs once per PAL video field (50 Hz), retaining the existing independent tasks.
Signed word/long rates have fractional carries; physical AI records have independent
carries. Player/AI displacement receives a modified-Euler constant-force correction,
and heading/yaw/clutch relaxation uses Q16 sixth roots. Coupled free-RPM rise and
decay compose to the original map within one word unit. Gear decisions/lever travel
and script counters retain six-field cadence. A gear command preserves the entire
six-field player-physics hold that the original skipped. The demo record retains
full-step prediction speed/distance; only its applied lane movement is fractional.

The corrected hooks pass `audit_simulation.py`: 63 hooks, no errors. VERIFY has
59 assembly assertions, covering signed endpoints, separate car carries, clocks,
counters, relaxations, coupled RPM, constant-force acceleration/braking travel,
gear holds and the prediction distinction. The return-boundary test has a sentinel
at site+54: deliberately restoring the erroneous $36 return adjustment produces
five failures; the correct $38 passes 59/59 (`six-gear-regression-bad/good`).
The bad build captured only one field, before driving, and is not shipped.

`six-validated-drive-000/020/slow` compares all **35 core variables 1800/1800**,
including sample 0, across the 68000, 68020/fast RAM and artificially slow drawing.
`six-validated-damage-000/020/slow` does the same for forced engine damage.
`six-validated-fatal-000/020` matches core state **1200/1200**: fatal code 17
at field 900 overrides an existing recovery, lives reach zero and the race clock
freezes while VBL continues. Deadline checks end at that terminal event; later
menu deadline differences are not active physics. All nonterminal checks show
one-field pacing, deadline lag exactly zero and nominal PAL elapsed race time.

Ordinary demo captures `six-holds-demo-000` / `six-validated-demo-020` match all
35 variables **6000/6000**, through one complete recovery. The same game patches
ship in the normal build: `six-release-state-000/020` match **6000/6000**, and
normal/VERIFY trajectories also match **6000/6000**. Camera and needle snapshots
can differ because drawing samples at different times. The normal trainer run
`six-release-trainer` passes 4000-field timing and a full 240-field idle recovery:
one penalty of 200, lives stay 5. The normal slave is 10008 bytes, SHA-256
`ac3d955a3639a5c12b2a49fa8f624272335431d2b766e7a3eea14cd34193aed8`.

With simulation off, `six-validated-disabled` confirms original v1 bytes at all
67 checked non-RNG ranges (including alternative fixture ranges). VERIFY input
fixtures can now run the original controller too, providing a real handling
baseline rather than a different attract driver. The straight fixture intentionally
has no road-following steering and must not be mistaken for the demo.

**Measured handling limits:** the original ordinary demo first crashes at field
3474; the uncorrected fractional predictor crashed at 1092. The final full-horizon
build crashes at **3457**, 17 fields earlier than original. At field 999 original
speed/distance are 8828952/15390991, versus 8929273/15621755: about +1.14% speed,
+1.73% travel measured from the common start position 2031616. The straight
acceleration fixture at field 399 has about +2.57% speed and +3.04% travel; its
stopped position after braking is +3.27% farther from the start. These changes
are finer-integration/decision effects, not CPU divergence. Six constant-rate
updates preserve an old increment; arbitrary nonlinear races are not byte-exact
coarse-step replicas. PAL is validated; NTSC and natural police pursuit are not.

The completed three-field release below is historical evidence, not validation of
the new one-field build.

**DONE (2026-10-04).** The optional v1 `CUSTOM2` patch uses a three-field PAL
step (16.67 Hz), halves continuous rates, retains road-unit operations and event
impulses, and carries 3/5 fractions for clocks and average-speed sums. Visual
phases move to simulation ticks; the renderer's rare event uses a private RNG.
The unmodified mode is still the default. Both normal and VERIFY builds assemble.

The first prototype stalled because a hook displaced a shared input-check entry;
expanded hooks also had branches into their overwritten tails. The corrected
layout passes `tools/audit_simulation.py tmp/game/TestDrive2/data/duel` (31 hooks,
no boundary, overlap or direct incoming-branch errors). The tool excludes data
outside the root code hunk and documents its limits for indirect calls and helper
return adjustments. Rendering work began only after the completed W5 checks below.

A corrected pre-recovery prototype matched 68000/68020 driving state through the
first crash, which begins at relative field 1068. It then exposed another timing
dependency: blocking crash animation, drawing and automatic acknowledgement run
inside the simulation process. The 20-second penalty appeared at field 1312 on
the 68020 and later on the 68000. Restarted motion then diverged. Evidence:
`tmp/prof/sim-000-long`, `sim-020-long`, `sim-000-slow`. These runs do **not**
prove W5 complete. They motivated a field-timed recovery state, keeping opponents
and the clock running while the renderer shows the penalty. The field-timed replacement now matches 68000, 68020/fast RAM and deliberately
slow drawing over 1,800 fields. Capture checks verify one life loss (or none with
CUSTOM1), one penalty and 240 stationary fields at idle engine pitch. Engine
damage uses the same original blocking path and now receives timed recovery too.
The fatal-event fixture exposed a terminal-precedence defect during an existing
recovery; fatal crashes now override it. It also needed to clear the race frame's
cached attract flag before it could exercise the original player death path.
`fatal-player-000/020` now match all core state 1200/1200: fatal code 17 at field
900, lives zero by field 903, one additional crash counted, race clock frozen and
VBL continuing. Active pacing/clock checks stop at the terminal event, not the
later menu animation.

With CUSTOM2 off, `check_disabled.py w5-original-mode` verifies original bytes
at all 57 non-RNG simulation patch ranges. Motion, clock and opponent state match
the original 1000-field run; transient first-step RPM/lane/period samples and
original renderer-driven RNG differences are the known W3 behaviour.

Two higher-rate boots (`w5-repeat-a/b`, VERIFY + CUSTOM2/CUSTOM3) have identical
field-0 and field-99 images: MD5 **9fb8e78911ccb9c21432cbe39e09347e** and
**813cba1a17bd8cb91634dc959a0f7614**. Each fixed window measures 10 frames in
89 fields, **5.6 fps**, with 17.1% polling. This is the W6 baseline in the new
simulation mode; the original-mode 5.9 fps has a different simulation trajectory.
The normal build (`w5-normal-build/020`, CUSTOM2 only) passes 1,800 fields on
both CPUs, including one full recovery. All core variables match at samples
1..1799; sample 0 can interrupt the initial demo borrow/audio transaction.
Clock, speed, opponents, traffic, RNG, life loss and penalty match 1800/1800.
`w5-recovery-view` confirms the normal renderer displays the complete penalty
message during a stopped-player recovery; the 1,200-field state capture still
passes pacing/clock checks. The terminal trace shows the original GAME OVER
presentation without the timed-recovery overlay. Screens are visual QA only;
all game-time claims above come from state measurements.

A measurement correction accompanies this work: `td2_report.regions` now reads
`SLAVE` when supplied, rather than always using the installed slave's smaller
size. Otherwise the copper write beyond the old region end was missed, producing
zero counted frames despite active drawing. Recounting the existing fixed-window
trace with its actual slave found 7 frames in 88 fields, 4.0 fps, at relative
fields 3000–3099. This is a different trajectory from the original simulation;
it is not a rendering optimisation A/B result.

The state map now also includes lane, heading, yaw, heat, gear, clutch, police
counters, crash code, gear envelope, opponent clock and average-speed sums.
They are compared alongside longitudinal position. `unit-final-000/020` match
motion, clocks, opponents, steering, gears, random state and average-speed sums
1800/1800; only the two animation phases differ at the known first interrupt
sample. `damage-final-000/020/slow` exercise engine damage: all core quantities
match from sample 1 through 1799, and all motion/time/life/penalty quantities match
1800/1800. Their clocks track PAL field time from field 69 with one 200-unit
penalty. The VERIFY assembly invariants pass 18 cases, including signed rounding,
heat rates and police counters. Natural police pursuit has not been captured.

The earlier `drive-020-extended` trainer run held three-field pacing for 6,000
fields through eight recoveries. It predates the idle-pitch and engine-damage
fixes; it supports pacing through repeated recovery, not validation of those later
changes. `docs/simulation-design.md` records rates, recovery behaviour and the
measured handling change (~+5.4% distance, +3.4% speed at field 999).

Only now. One patch per commit, each with a `fixed_window.sh` A/B and the W1 reproducibility
check showing the simulation trajectory (W2 variables per field) is unchanged where it must be.

### Additional machine validation (2026-10-04)

The user requested A1200 and A4000/general-68030 testing. All new captures use
normal shipping slave SHA256
`ac3d955a3639a5c12b2a49fa8f624272335431d2b766e7a3eea14cd34193aed8`,
`CUSTOM2=3`, normal attract driving, and no VERIFY fixtures or trainer.
The harness now selects the machine model explicitly and isolates emulator logs.

Expanded A1200: FS-UAE A1200 model, 68EC020, host Kickstart 3.1 A1200,
2 MB chip RAM, 4 MB fast RAM, no slow RAM. Effective log confirms real CPU speed,
approximate cycle timing, 24-bit addressing and JIT disabled.
`a1200-state` matches all 35 core gameplay variables against
`six-release-state-000` at every sample 0..5999. Timing checks pass 6,000
consecutive one-field deadlines with zero lag; the clock follows elapsed PAL
fields from field 73 plus the single 200-unit penalty. Recovery checks confirm
one lost life, one penalty, and a complete 240-field stationary idle recovery.

Two separate fresh-boot 100-field windows, `a1200-fps-a/b`, both measure
30 frames over 93 fields = **16.1 fps**, with identical swap patterns, 38.7%
blitter polling, 0 BLIT interrupts and 100 VBL interrupts. Their full raw first
and last trace screenshots are byte-identical across boots. These windows
start immediately at the race anchor, not after the long state study.

The general 68030 configuration retains that A1200 model/ROM/RAM and sets
CPU=68030, real speed, cycle timing enabled, multiplier zero and frequency
25,000,000 Hz. This is an accelerated A1200 setup; no local A4000 ROM was
available. These are emulator measurements, not measured physical hardware FPS.
`030-state` also matches all 35 gameplay variables at every sample 0..5999;
the one-field pacing, elapsed clock and complete recovery checks pass with the
same event timing as the 68000 and 68EC020. The retained effective configuration
confirms CPU=68030, the requested 25 MHz frequency with multiplier zero,
approximate cycle timing, no FPU, MMU=68030 and JIT disabled.
The 68030 instruction profiler emitted zero instruction bytes over 100 fields
(`030-fps-a`), so that capture is rejected as an FPS instrument. The harness's
new `SWAP_ONLY=1` mode counts COP1LC writes at read-only debugger breakpoints
over 100 complete VBL intervals. `a1200-swaps` reproduces the **exact** swap
pattern and 16.1 fps of both ordinary A1200 traces, validating this alternate
instrument's field boundaries before using it on the 68030.

Two fresh-boot `030-swaps-a/b` windows both give an identical alternating swap
pattern: **49 frames in 98 fields = 25.0 fps**. Both use the same shipping slave,
settings and race anchor. No 68030 polling/interrupt percentages are claimed
from its empty CPU trace. Physics/state checks remain independent of drawing.

| Emulated setup, CUSTOM2=3 | Fixed-window FPS, two boots | Gameplay state vs 68000 |
|---|---|---|
| Expanded A1200 / 68EC020, 2 MB chip + 4 MB fast | 16.1 / 16.1 | 35 variables × 6,000 fields, exact |
| A1200 / 68030 at requested 25 MHz, same RAM | 25.0 / 25.0 | 35 variables × 6,000 fields, exact |

Commands and effective configuration evidence are described in `docs/profiling.md`.

### W6. Then, and only then, rendering speed

Follow `docs/optimisation-plan.md` §1–§3, **largest structural item first**: let the CPU run while
the blitter works (`duel:0f114` shapes, `duel:0f91a` lines), then the span fill and back-buffer
clear (`duel:0789c`, `duel:0844e`) as blitter or long-word operations, then projection. Measure each
with `fixed_window.sh` on the reproducible slave. Skip anything worth < 3% of a frame unless it
is free. Do not touch the slave's `set_copper` beam wait (JOTD's flicker fix) without testing a
68020/68030 configuration for tearing.

**One-field W6 revalidation DONE (2026-10-04).** No additional rendering
algorithm is shipping. The existing v1 unused-blitter-interrupt option is
revalidated against the final 50 Hz simulation. Four normal-build fixed windows
(`six-release-serial-a/b`, `six-release-irq-a/b`) use the identical 10008-byte slave:

| Arm | Both repeats | Polling | BLIT / VBL interrupts per 100 fields |
|---|---|---:|---:|
| CUSTOM2=1 | 7 frames / 78 fields = 4.5 fps | 12.7% | 1955 / 100 |
| CUSTOM2=3 | 9 frames / 87 fields = 5.2 fps | 14.2% | 0 / 100 |

That is **15.3% more frames per second / 13.2% less time per frame** in this
window, above the noise and 3% thresholds. It compares the same 50 Hz physics in
both arms. The extra physics updates cost CPU time: the historical three-field
mode drew faster (6.5 fps with IRQ suppression). This refinement improves update
frequency and handling fidelity, not rendering speed relative to that old mode.

The recommended CUSTOM2=3 arm passes the complete, uncropped W1 image repeat:
first/last MD5s **9fb8e78911ccb9c21432cbe39e09347e** /
**4eb34ff6e3c47aee3361d16718fd8371** in both boots. The serial baseline's raw
images fail the byte repeat: 6140 differing pixels, confined to outer capture
columns 751–753 and rows 568–575. Its complete game viewport (x=74..713,
y=37..436) matches exactly at both endpoints. No images were cropped or
normalised, and the serial arm is not claimed to pass the full raw check.
Frame counts repeat exactly; game-speed evidence comes from state, not images.

`six-validated-irq-on-state` matches all 35 driving variables 1800/1800 with
IRQ suppression on/off. Damage plus slow drawing also matches 1800/1800.
Runtime shape twins (`six-validated-twin-000/020`) complete **18 / 33 checks**
with zero pixel/carry mismatches; both retain one-field scheduling in their
300-field state windows. Their deliberately expensive oracle has no useful
fps result and is excluded from performance claims. The normal `six-release-render-only` capture independently verifies original
instructions at all 67 simulation ranges with CUSTOM2=2. Normal release state,
trainer, recovery and terminal proofs are recorded in the W5 completion above.
All original blitter waits, ownership barriers and JOTD's display fix remain.

The previous three-field rendering results below are historical.

**DONE (2026-10-04).** The accepted rendering change is v1 CUSTOM2 bit 1,
suppression of unused blitter-finished interrupts. The first v1 rendering prototype moved shape
waits before the next plane and moved the common final wait to ownership/CPU
writer/display barriers. The original line routine already waits before each
plane; it was incorrectly described as wait-after-start in the original plan.
JOTD's beam wait was retained throughout.

Four same-build fixed windows (`w6-serial-a/b`, `w6-async-a/b`) give 5.6 fps
serial and 5.4 fps asynchronous. A second same-build experiment
(`w6-irq-serial-a/b`, `w6-irq-async-a/b`) gives 5.6 fps serial and 6.2 fps
with asynchronous drawing plus disabled blitter IRQs. IRQ removal alone
(`w6-irq-only-a`) gives 6.5 fps in that exact second build; `w6-irq-only-b`
repeats 6.5 fps but includes the pixel-verifier code and has a different size,
so it is supporting evidence, not a same-build repeat. The slower asynchronous
prototype has been removed. No changed blitter wait is shipping.

The shipping patch retains every original wait/ownership/display contract and
suppresses only INTENA BLIT, restoring its original enable on a normal return.
Only the v1 Control call reads the option. All game graphics call stubs were
checked: none calls QBlit (-276) or QBSBlit (-294). A VERIFY shape twin copies
the original routine at runtime before PatchSeg, relocates its external clip
call, and compares complete destination planes plus clipping carry with IRQs
on/off from identical pixels and register inputs. It runs only during racing:
checking introductory full-screen drawing prevented a timely anchored boot.
The final VERIFY build passes six completed shape twins on the 68000 and nine
on the 68020, with zero pixel/carry mismatches (`w6-irq-long-twin-000/020`).
Its own four same-build windows (`w6-final-serial-a/b`, `w6-final-irq-a/b`)
repeat 5.6 versus 6.5 fps. One VERIFY repeat's trace images differ only in three
rightmost columns outside the game viewport; all game pixels match. No images
were cropped or normalised to claim the raw W1 check.

The **normal shipping build**, 8,506 code bytes / 8,544-byte file, independently
repeats both arms (`w6-release-serial-a/b`, `w6-release-irq-a/b`): 10 frames in
90 fields = 5.6 fps with CUSTOM2=1; 11 in 85 = 6.5 fps with CUSTOM2=3. This is
about **16.5% more frames per second / 14.1% less time per frame** in this scene,
not a claim for every scene. Polling rises from 17.0% to 19.5%; BLIT interrupts
fall from 2,438 to zero, and VBL interrupts remain 100/100. All four use one
exact build, with no VERIFY code or fixture arguments.

Both normal arms pass the full, uncropped W1 check: serial field-0/99 MD5s are
`a2c31ccefeec8a15fd78c56c9234405d` / `098da8eea96c1f2f427e5c496a8be614`;
IRQ-off MD5s are `9fb8e78911ccb9c21432cbe39e09347e` /
`10e8f27815ee07997fac5604266a4219`, identical between the two boots of each arm.
Screens are reproducibility/visual checks, not game-speed evidence.

VERIFY driving (`w6-state-000/020/slow`) matches all **35 core variables
1800/1800**, including sample 0, against the W5 trainer tape and across both
CPUs plus slow drawing. Pacing is three fields, deadline lag 0..2, and the
clock follows nominal PAL elapsed fields from field 69 with one penalty of 200.
All three complete a 240-field stationary recovery at idle pitch; the 18 rate
invariants still pass. `w6-fatal` matches W5's player fatal fixture through
1200 fields: fatal 17 at field 900, exhausted lives, frozen race clock and
continuing VBL. Terminal checks stop active pacing at that event.

Normal `w6-release-state-000/020` also matches all 35 core variables 1800/1800
across CPUs, with one full recovery. Against W5's normal capture all core state
matches at samples 1..1799; sample 0 differs in the documented borrowed-demo
transaction (distance, lane, RPM, engine period and two visual phases), not in
subsequent trajectory. Normal `CUSTOM2=2` (`w6-release-render-only`) verifies
original bytes at all 57 non-RNG simulation ranges, demonstrating independent
bit gating. `w6-release-trainer` completes the normal-build trainer-on check: 1,800 fields,
three-field pacing, correct elapsed clock, one penalty, no lost life, and one
complete 240-field idle recovery. The normal release has no VERIFY fixtures.

The next candidates were inspected after that structural experiment. The span,
MOVEM clear and both projection passes already use register-held loop state; the proposed C-to-assembly rewrites do not apply. In the IRQ-only
100-field capture, span stores plus DBF cost about 3.5% of all cycles. Pairing
stores saves only one quarter of the stores and half the DBF cost before added
setup, below the 3% frame threshold. More complex edge specialisation or early
DMA clearing would need a separate measured prototype and pixel oracle; they
are not established wins. Projection accumulator caching was quantified: all four affected instructions
together cost 0.346% of the IRQ-only fixed window, before mandatory output writes.
The real clear kernel costs 3.809%; mandatory writes leave less than 0.87%
recoverable by any CPU-loop rewrite. These candidates were skipped under the
3% rule; larger new algorithms remain unmeasured future experiments.

### Fast-CPU study: the 25 fps ceiling (2026-10-04)

**Game speed is CPU-independent (re-verified):** normal slave, CUSTOM2=3, 1,500
fields: the 68000 (`review-state-000`, ~5 fps) and an emulated 100 MHz 68030
(`review-state-030-100`, 25 fps) match all 35 core variables 1500/1500; pacing is
one field with zero lag and the clock follows PAL time. **Rendering is capped at
25.0 fps** on 68030/25 MHz, 68030/100 MHz and 68020/100 MHz with blitter
priority: the chip bus (blitter + five-bitplane display), not the CPU, limits a
frame. Details, per-blit costs and the measurements below are in
`optimisation-plan.md` ("Fast-CPU ceiling").

- CUSTOM2 bit 2 (blitter priority, shipping): A500 5.2 → 5.4, A1200 16.1 → 16.7,
  68020/100 MHz 21.1 → 25.0 fps. A500 state with bit 2 (`pri-state-a500-c3/c7`)
  matches all 35 core variables at samples 1..1499; sample 0 differs only in the
  documented initial transaction (RPM, engine period, two animation phases).
- CPU shape drawing (`make cpushapes`, bit 3): pixel-exact against the blitter
  (18 twins, 0 mismatches) but slower on every machine tested. Not shipped.
- Next candidate, needing the user's decision: a fast-RAM back buffer with all
  blitter users replaced by CPU code and a viewport copy to chip (68030+).
  Unmeasured; it is a renderer redesign, not a patch.

The 100 MHz emulated boots need longer than the harness's 180 s server wait:
use `SERVE_WAIT=1700`.

### Tooling debts (fix when they bite, not before)

- Race anchoring and boot polling are fixed by W1; see its calibration-cache trap above.
- `td2_report.py` names self time by nearest preceding `link a5`/call target; functions without
  `link` merge into their predecessor. Check with `hotspots.py` before trusting a big self number.
- The trace format holds no fast-RAM snapshot; the scripts dump the code region separately with
  gdb. A trace is ~5.4 MB per field; `monitor profile` caps at 100 fields.
- The lldb fix of the profiler window (`docs/profiling.md` §3) is tied to this FS-UAE binary's
  addresses.

## Files

| Path | What |
|---|---|
| `docs/profiling.md` | how to run, drive, trace and read; traps; baseline |
| `docs/optimisation-plan.md` | rendering cost centres and the order to attack them (W6) |
| `whdload/TestDrive2HD.s` | the slave (JOTD v1.5 + `NOBLITIRQ` experiment flag) |
| `tools/` | harness, tracer, reports (README table) |
| `tmp/prof/w3/`, `tmp/prof/f020/` | the A500-equivalent and 68020 windows quoted above (local only) |
