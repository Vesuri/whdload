# Open work — Test Drive II: separate the simulation from rendering speed

> **Handoff document.** Read this first, then `docs/profiling.md` (tools, traps) and
> `docs/optimisation-plan.md` (performance ranking). Everything here was measured or read from
> the binary on 2026-10-04; each claim says which. Do the work items **in order**.

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

Only now. One patch per commit, each with a `fixed_window.sh` A/B and the W1 reproducibility
check showing the simulation trajectory (W2 variables per field) is unchanged where it must be.

### W6. Then, and only then, rendering speed

Follow `docs/optimisation-plan.md` §1–§3, **largest structural item first**: let the CPU run while
the blitter works (`duel:0f114` shapes, `duel:0f91a` lines), then the span fill and back-buffer
clear (`duel:0789c`, `duel:0844e`) as blitter or long-word operations, then projection. Measure each
with `fixed_window.sh` on the reproducible slave. Skip anything worth < 3% of a frame unless it
is free. Do not touch the slave's `set_copper` beam wait (JOTD's flicker fix) without testing a
68020/68030 configuration for tearing.

### Tooling debts (fix when they bite, not before)

- `fixed_window.sh` anchors on the first `duel:0789c` entry, not the race start (W1 fixes it).
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
