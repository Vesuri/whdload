# Profiling Battlehawks 1942

How to run, drive and trace the original game, and the measurements so far. Method:
`Test Drive 2'sdocs/new-game-playbook.md`. Every number here names its instrument.

## TL;DR

```sh
source amiga/env.sh
make -C whdload original                 # reconstruction == shipped slave (byte compare)
tools/fixed_window.sh tmp/prof/turn      # VERIFY build: 100 fields from flight frame 90, in a left circle
SLAVE=tmp/prof/turn/slave.slave python3 tools/bh_report.py tmp/prof/turn/trace.bin tmp/prof/turn/code.bin
SLAVE=tmp/prof/turn/slave.slave python3 tools/frames.py tmp/prof/turn/trace.bin tmp/prof/turn/code.bin 0x200000
SLAVE=tmp/prof/turn/slave.slave python3 tools/c2p_stats.py tmp/prof/turn/trace.bin tmp/prof/turn/code.bin 0x200000
python3 tools/compare_traces.py tmp/prof/turn/trace.bin tmp/prof/turn2/trace.bin
STATE_ONLY=1 SKIP_FRAMES=8 tools/fixed_window.sh tmp/prof/state-a   # memory at flight frame 8
python3 tools/compare_state.py tmp/prof/state-a tmp/prof/state-b
```

A capture takes about 10 minutes (one boot, ~4800 fields to the window in warp) and ~520 MB.

## 1. The game and the slave

| | |
|---|---|
| Archive | `Battlehawks1942_v1.0_0053.lha` (Retroplay), SHA-256s in `tmp/archive.sha256` |
| Game | PAL v1.0, three AmigaDOS OFS disks: `Disk.1` "BHawk1" (boot, `BH`, sounds), `Disk.2` "BHawk2" (screens, `FDAT/` plane data), `Disk.3` "BHPilots" (pilot records) |
| Code | `BH` on `Disk.1` (167 936 bytes), Aztec C (`link a5` prologues, `jsr d16(a4)` jump table, small data `a4` = data hunk + `$7FFE`). Hunk 0 code `$1C794` bytes at file `$28` (3 relocs); hunk 1 data `$A664` file-backed / `$F1EC` allocated (2146 relocs); hunk 2 BSS 4 bytes. `Disk.1:s/startup-sequence` is just `BH`. |
| Shipped slave | Galahad of Fairlight v1.0 (12/05/03), 1512 bytes, WHDLoad v15 header, no source. `ws_BaseMemSize` `$80000`, `ws_ExpMem` `$40000` (exactly the Kickstart image), flags `NoError\|EmulPriv`, quit F10. The archive is the "SLOW" slave (no fast RAM); the ReadMe mentions a "FAST" one, not included. |
| Reconstruction | `whdload/original/Battlehawks1942.s` rebuilds the shipped slave byte-identically. Old-style Kick 1.3 boot: `resload_LoadKick` into ExpMem, a `resload_Patch` list on the Kickstart image (trackdisk → `Disk.N` via `resload_DiskLoad`, disk change, copper, a dos `LoadSeg` hook), and in the hook one patch to `BH`. Decode its list with `tools/patchlist.py SLAVE 0x206`. |
| Game patch | The manual check ("Recognition Test", shown before the first flight): `bh:025be move.b (0,a0,d1.l),d2; cmp.w d2,d0; beq.s` becomes `jsr fix; bra.s` — any answer passes, but Return must still be pressed. |
| Built slave | `whdload/Battlehawks1942.s`: WHDLoad 20 KickEmu (`whdload/whdload/kick13.s`, vendored verbatim with the 20.0 headers in `whdload/include/`). 512 KB chip **plus 512 KB fast memory** (v1.0: chip only), `DISKSONBOOT`, `NUMDRIVES=3` (no swaps), `WPDRIVES=%1111` (as v1.0), the same `BH` patch via `_cb_dosLoadSeg` + `resload_PatchSeg`. `make verify` adds `tape.s`; `make c2pfull` the c2p experiment (`docs/c2p.md`). |

**Memory.** Only what DMA needs is in chip RAM. `BH`'s three hunks are "any" memory; it
allocates the sample data of its sound resources `MEMF_CHIP` (`bh:157d6`: resource id + 1000,
flags 2) and everything else `MEMF_ANY` (the chunky buffers, 2 × 12,544 bytes, `bh:3c08`;
two small `MEMF_CHIP|MEMF_CLEAR` blocks); bitplanes come from the OS (Intuition screens).
With the slave's fast memory, code, data and chunky buffers are in fast RAM with no patch to
`BH` (v1.0 had no fast memory, so everything was in chip). On the capture machine `BH`, the
relocated Kickstart image and the running slave are all in the 8 MB at `$200000` (where
exactly moves with the slave's size).
`tools/bh_report.py` finds `BH` in chip RAM or in the dump (byte-match voting with a quorum,
then LoadSeg's BPTR chain to the data hunk), the relocated Kickstart, and the *running* slave
(the copy with `WHDLOADS` and no `$3F3` hunk header in front; WHDLoad also keeps the file).
Anything read inside the slave (the tape counter) is searched for from the running copy.

## 2. The machine

68000, 512 KB chip, **8 MB Zorro II fast RAM** (`CHIP_KB=512 FAST_KB=8192`, no slow RAM),
cycle exact, PAL, host Kickstart 3.1 + Workbench 2.04 floppy booting `DH0`, WHDLoad 20.0 on `DH1`
(`amiga/run.sh`; kick13 needs `kick34005.A500` + `.RTB`, the RTB is in
`~/.local/share/amiga/Kickstarts/`). `fixed_window.sh` sets all of this. The fast RAM holds
the slave's fast memory and lets `PRELOAD` cache all three disk images; with only 1.5 MB of
slow RAM it could not, and every disk read became a WHDLoad OS switch (the screen blinks
through the boot, and loads slowed enough to break the tape). The first baseline (§6, "chip
only") used the old A500-equivalent: `FAST_KB=0 EXTRA_ARGS=--slow_memory=1536`, chip-only slave.

## 3. Driving: `tools/bh.py` and the input tape

`bh.py serve` boots (`DEBUG=1 amiga/run.sh`), attaches gdb within the stub's 20 s window,
and serves `stop/cont/gdb/shot/profile/wait/until/quit` on `amiga/.run/bh.sock`. The
profiler's PC window is fixed per capture by one lldb attach (`LLDB_FIX`, link-time
`0x32dea04`, unchanged FS-UAE binary; ~35 s).

**There is no attract demo**, and posted host key events never reach FS-UAE. Two ways were tried:

1. **FS-UAE input recordings do not replay in this build.** `RECORD=` works, and synthetic
   events can be spliced in (`tools/splice_rec.py`; `KEY_RETURN` = 164 in this binary's
   event table, 48-byte entries, `JOY2_LEFT` = 60 and `SPC_STATESAVE1` = 378 agree with
   TD2), but FS-UAE itself emits two events at startup (2263, 2272: joystick-port mode
   actions, sent whatever `JOY0/JOY1` are). During playback recording any event truncates the
   recording at the play position, so playback always ends at position 0. `PLAYBACK=` is kept
   in `run.sh` in case a fixed FS-UAE turns up. The recordings also showed that the host
   mouse feeds port 0 when `JOY0=mouse`, even with input grab off.
2. **The VERIFY input tape (`whdload/tape.s`) — used.** `_cb_dosLoadSeg` starts an Exec task
   (TCB, stack and I/O blocks inside the slave, so the game's allocations do not move) that
   counts fields with `WaitTOF` and sends `IECLASS_RAWKEY` events through `input.device`
   `IND_WRITEEVENT`: Return at fields 3000, 3505, 4010, 4515 after BH's LoadSeg, then the
   left circle (below). The screens:
   title, credits (both by themselves), main menu (Return: Select Training), Select Training
   Mission (Return: first mission), Ready Room (Return: Begin Flight), Recognition Test
   (Return) → the flight. The menu is up by field ~2800 (KickEmu slave, 68000); the v1.0
   slave reached the screens on a different schedule, so retime the tape when the slave or
   the boot changes. After the tape the task sits in `Wait(0)`.
   It publishes `"BHTAPE!!"`, its field count and the field of its last Return;
   `fixed_window.sh` polls the count read-only.

**How BH reads input** (it matters for scripting): its input handler only adds `RAWMOUSE`
deltas into `25188/25190(a4)` (`bh:19a86`); once per frame `bh:3e98` takes the accumulated
mouse movement (clamped to ±192/±128) and *one* IDCMP message from its window: a RAWKEY
becomes one character (cursor keys 1–4: up, down, left = 3, right), mouse buttons set
`25192/25194(a4)`. The controller (`bh:7f30`) sets the stick from that frame's input: mouse
movement × 128, or ±10240 for one frame per cursor character. So one key press is one frame of
full aileron: the bank grows with the number of presses (a real keyboard's auto-repeat sends
many), and the plane levels its wings by itself afterwards. BH has no joystick or CIA reads.

**The benchmark scene: a left turn** (the user's choice: level flight over the flat-shaded
sea barely changes the picture). In flight the VERIFY slave hands BH its keys **inside the
frame loop**: `pl_bh` hooks the loop's call of the key reader (`bh:75be`, `tape.s`
`tape_key`); when no real key is waiting, the flight tape gives a Left character on the frame
numbers it lists (BH's frame counter `26292(a4)`): 8 of them 3 frames apart from frame 30
(about 10° of bank), then one every 10 frames. The bank is not stable in this flight model
(small banks level out by themselves, larger ones tighten into a descending spiral), so by
the window (frame 90) the plane is in a steep turn. Because the game steps once per frame,
this gives the same flight on every CPU and in every run. Two earlier versions did not:
keys typed through `input.device` at fixed fields put the 68020's frame 90 before the bank,
and the tape task polling the frame counter once per field let a press slip a frame when the
debugger's stops (which are not cycle-transparent) shifted the frame/field phase.

**Anchor.** `fixed_window.sh` boots once with no breakpoint (a breakpoint armed from reset
made warp too slow to reach field ~4600 in 5 minutes), finds `BH` and the tape counter with
the emulator held (searching an 8 MB dump takes seconds, and warp left running got thousands of
fields past the arming point), polls the counter in 0.05 s steps until 1000 fields before the
last Return (a 0.2 s step in warp overshot a 300-field margin), runs to the next `bh:1a2c2` (the 3D view's
c2p pass: one per frame, never run by the menus), reads BH's **frame counter** (`26292(a4)`,
counted up at `bh:6e52` once per flight-loop pass) and runs on to the c2p pass of flight frame
`SKIP_FRAMES` (default 90). gdb holding the CPU stops emulated time, so polling does not
change the run, but the poll's overshoot is not deterministic: with fast memory the flight
starts before the poll arms the anchor, and "the first c2p seen" came out one frame apart in
two captures. Counting by BH's own counter removes that. The window is 100 fields from there
(Gunnery Fundamentals, the first training flight, in a left circle).

## 4. Reading a trace

- `bh_report.py`: regions, contexts (SP ranges), self/inclusive time per routine (function
  starts = Aztec `link a5` prologues + traced call targets), hottest instructions, call edges.
  The game's top level was entered before the trace, so inclusive times above `bh:06eea`
  show as `[top]`.
- `frames.py`: frames, STOP idle, level-3 interrupts (through the live `$6C` vector), DMA slots.
- `swap_fields.py`: the same frame count from read-only breakpoints (`SWAP_ONLY=1`), for the
  68030 backend that records no instructions. Validated against the circle trace on the
  68000: the per-field pattern is identical for the first 26 fields, then drifts (breakpoint
  stops in this FS-UAE are not cycle-transparent, and the tape's field-timed keys then land on
  other frames): 18 frames in 91 fields (9.9 fps) against the trace's 19 in 92 (10.3 fps).
  Good for a ceiling to within a frame, not for exact comparisons.
- `c2p_stats.py`: the c2p's compare/convert split and change rate per pass (`docs/c2p.md`).
- `compare_state.py`: BH's data hunk between two `STATE_ONLY` dumps (§9).
- `fixed_window.sh` writes `armed.txt` (the tape field the anchor was armed at) and
  `anchor.txt` (the frame counter when the window opened).
- `hotspots.py`, `disd.py`, `dis.sh`: instruction-level views (`HUNKBASE` = the `bh` region).
- Disassemble `BH` without a dump: `tools/adf.py tmp/game/Battlehawks1942/Disk.1 BH tmp/BH`,
  then hunk 0 is file `$28`..`$28+$1C794`.

## 5. Display and frame counting

The 3D view is rendered by the CPU into a chunky buffer and converted by **`bh:1a2c2`, a delta
chunky-to-planar pass**: it compares the new chunky frame with the previous one a long at a
time (`cmpm.l (a5)+,(a6)+; dbne d7` at `bh:1a30e`, the hottest instruction) and converts only
the changed longs into the 4 bitplanes (details and the Kalms c2p question: `docs/c2p.md`).
The two chunky buffers alternate (allocated `MEMF_ANY`: fast RAM with the slave's fast
memory); the bitplanes do not — **there is one displayed buffer**, written while it
is shown (no swap, no beam sync). So one c2p pass is one new frame, and that is the frame
counter (`bh_report.C2P`). The renderer never touches the blitter (no `$DFF040..58`
references, no `btst #6`; one `OwnBlitter` call in BH), so there is no blitter wait.

No graphics.library calls run during flight. The game installs its own level-3 handler,
`bh:1ac26` (a per-VBL sound sequencer that drives the audio registers and then jumps into the
Kickstart handler past its prologue, `kick:fc0d18`).

## 6. Baselines

### Current: the left turn on the 8 MB fast-RAM machine (2026-10-07)

`tools/fixed_window.sh tmp/prof/turn` (68000, 512 KB chip + 8 MB fast, slave with 512 KB fast
memory, flight frame 90, 100 fields; flight input injected on frame numbers, §3).
`tmp/prof/turn2` is the same capture again, armed at another tape field: `compare_traces.py`
prints `identical`.

- **9.2 fps**: 17 frames in 92 fields, 5.41 fields/frame.
- CPU never stops (0.0 % STOP). Contexts: BH 93.6 %, two OS tasks 4.2 % and 1.6 % (the tape
  task is idle by now: it only types the menu keys).
- Regions: `bh` 94.0 %, Kickstart 5.5 %, slave 0.2 %, `bh-data` 0.2 %.
- DMA slots: free 75.0 %, bitplane 22.5 %, refresh 1.8 %, CPU 0.4 % (code and data are in fast
  RAM; the CPU touches chip RAM only for the bitplanes it writes), copper 0.2 %, audio 0.1 %.
- c2p (`c2p_stats.py`): 1.1 % of the longs change per frame; 14.5 % of all cycles = compare
  11.7 % + convert 1.6 % + 1.1 %.

| % self | routine | calls | note |
|---:|---|---:|---|
| 14.5 | `bh:1a2c2` | 18 | delta c2p; mostly its `cmpm.l`/`dbne` pair |
| 12.8 | `bh:15cb6` | 19 | |
| 7.6 | `bh:161ec` | 18 | |
| 6.8 | `bh:16bca` | 323 | |
| 5.2 | `bh:0aec8` | 19 | called from the flight loop (simulation) |
| 4.2 | `bh:1719c` | 76 | |
| 4.1 | `bh:11142` | 19 | |
| 4.1 | `bh:1a3d6` | 1856 | plots one pixel into the four planes (next to the c2p) |
| 3.5 | `bh:19ba8` | 72 | planar drawing (plane pointers `26224(a4)`..) |
| 2.5 | `bh:08266` | 19 | flight loop (simulation) |

Inclusive: `bh:06eea` (3D view) 58.6 %, `bh:1a2c2` 14.5 %, `bh:15cb6` 14.2 %, `bh:0ab0e`
12.0 % (76 calls: per object). Rendering (3D view + c2p) is about three quarters of the frame;
the simulation calls of the flight loop are most of the rest.

Same scene, other configurations (frames.py; the turn, flight frame 90, 100 fields):

| machine | slave | fps | fields/frame |
|---|---|---:|---:|
| 68000, 512 KB chip + 8 MB fast | fast memory (default) | **9.2** | 5.41 |
| 68000, 512 KB chip + 8 MB fast | chip only (`-DFASTMEMSIZE=0`, like v1.0) | 8.8 | 5.69 |
| 68020 (A1200, 2 MB chip + 8 MB fast) | fast memory | **28.8** | 1.74 |

`AMIGA_MODEL=A1200 KICKSTART=~/.local/share/amiga/Kickstarts/kick40068.A1200 CHIP_KB=2048
CPU=68020`. Fast memory is worth 5 % on the 68000 (no bitplane contention on code, data and
chunky reads); the 68020 is 3.1 times the 68000. Every such speed-up also speeds the game up
(§9). Not yet measured: the 68030 ceiling (a `SWAP_ONLY` run at 50 MHz found the flight at
frame 1539 when the anchor was armed, so that machine reaches the screens on another schedule;
the tape needs checking there first).

### First baseline: level flight, chip-only (2026-10-07)

The first 100 fields of the flight, no input, chip-only slave on the A500-equivalent
(`FAST_KB=0 --slow_memory=1536`), `tmp/prof/r1` (= `r2`, identical): **9.7 fps** (18 frames in
93 fields). c2p 15.6 % of all cycles (compare 12.8 %), 1.0 % of the longs changing per frame;
DMA slots: free 34.9 %, CPU 40.6 %, bitplane 22.5 %. (Before the port-mode fix, `base`: 9.6 fps,
94 fields.) Not comparable with the circle: other scene, other machine.

## 7. Reproducibility

`DETERMINISTIC=1`, `JOY0=none JOY1=none`, the tape as the only input. BH has no
`VHPOSR`/`VPOSR`/CIA reads (custom-chip references are only DMACON and the audio registers).
Its `rand()` (Aztec LCG 1103515245/12345, state `9180(a4)`, `bh:1adb6`, seeded by `bh:1adea`)
has not been traced to its seed.

Two captures (`tmp/prof/base`, `base2`, chip-only machine) first differed in registers and
DMA records from the Kickstart's first gameport read: **JOY0DAT** read `$0000` in one boot
and `$0101` in the other. FS-UAE's `joystick_port_0=none` only unplugs the host device; the
port's mode stays `mouse` (the default for port 0) and the host mouse still moves the
counters. `run.sh` now also passes `--joystick_port_N_mode=nothing` for `JOYN=none`, and two
fresh captures (`tmp/prof/r1`, `r2`) compared **`identical`**: every field's instruction
records (PCs, costs, registers), DMA records and screenshot, and the chip snapshot.

With fast memory the window first came out one frame apart in two captures (see the anchor
in §3); anchored on BH's frame counter, see §6 for the comparison on the current machine.
A touched emulator window is input: people watching can move the mouse over it.

## 8. Traps

- `fixed_window.sh` uses `bh until`, which blocks until the anchor is hit. If the tape no
  longer reaches the flight (retimed boot, another slave), kill your own emulator by
  `amiga/.run/fsuae.pid` and check with `shot`s against the tape counter.
- Don't `pkill -f` broad patterns: other sessions' command lines can match.
- Don't edit `fixed_window.sh` (or any script) while a capture runs it: bash reads scripts as
  it executes, and the run continues from a shifted offset (`h: command not found`).

## 9. Game time

**Verdict: one simulation step per rendered frame; nothing measures time.** Game speed is
proportional to the frame rate (6–11 fps on the A500, depending on the scene).

**But the step has a size: `T = 10184(a4)`**, the same design as Their Finest Hour's T
(`Their Finest Hour'sdocs/profiling.md` §10), except that BH does not benchmark it.
The mission setup (`bh:132cc`, at `bh:1341c`) sets `T = 10182(a4) × b / 16`, minimum 3, where
`10182(a4) = 7` is a constant (`bh:054a`) and `b` is byte 16 of the mission's 17-byte record
(table `-16984(a4)`, index `9835(a4)`). Over the first 40 records b is 12, 14, 15, 16 or 20,
so T is 5–8 (7 in the turn window; 7 in both the 68000 and 68020 dumps). Derived at the same
time: `10186(a4) = T/8 + 1`; `bh:1351e` picks 16 instead of 8 when `T > 10`.
- 25 `divu.w 10184(a4)` sites scale per-step quantities: the stick from the controller
  (`bh:7934`..`797a`, `bh:800e`..`8056`) and sites in `bh:c9f2`, `bh:11152`..`bh:12bf0`.
  Other sites read T for multiplying or adding (for example `bh:e7b2`, `bh:e7d8`).
- Timers are counted in units of T: `bh:0246` loads a countdown with `T/2` frames.
- Two busy-wait delays are counted in CPU loops scaled by T (`bh:030a`: 1000 × T × n
  iterations; `bh:12b8`: `10182(a4)` × n × 1000), so they shorten on faster CPUs.
- **Working model:** a step is 1/T seconds, and T is the designers' estimate of each
  mission's frame rate on an A500. The coverage test below supports it for the flight model.

**Coverage test** (2026-10-08, `make tscale TSCALE=2 [STICKREF=1]`, `tools/tscale_compare.py`):
the VERIFY slave multiplies T by 2 at `bh:1344e` (14 in the turn mission) and the tape gives
each press at frame 2F instead of F, so frame 2N is the game time of frame N at T = 7.
`STATE_ONLY` dumps at T = 7 frames 60/120/240 and T = 14 frames 120/240; the world arrays are
144 slots of longs, x `10908(a4)`, y `11484(a4)`, z `12060(a4)` (slot 0 the player).
- **Drones** (slots 1–8): over game time 60→120 they move the same distance at T = 14 as at
  T = 7 (major-axis ratios 0.98–1.02, two outliers 1.06 and 1.18 on short axes). At the same
  number of steps they are elsewhere. Their motion goes through T.
- **Countdowns** set from T follow it (`10320(a4)`: 3 at T = 7, 7 at T = 14).
- **The pool at slot 128** (`bh:1351e`, 8 slots for T ≤ 10, else 16) is full at both T;
  its objects respawn, so displacement does not compare. 16 slots is all there is (the arrays
  end at slot 143), so at T = 50 these objects would recycle early. To find: what they are.
- **The stick does not follow T.** `bh:0110` sets `10308(a4)` per frame: mouse counts since
  the last frame × 128, or for a key −2112 (Left) for one step, ramping by 4096 when the same
  key repeats within T/2 frames. `bh:7920` divides it by T into `28506(a4)`, which the
  attitude integrator `bh:79f0` adds per step. A mouse count per frame is already a rate, and
  a key press lasts one step whatever its length, so dividing by T again makes response fall
  as T rises (TFH has the same: its fix scales the stick by T/8). With the doubled tape the
  second press ramped, and the player's displacement over game time 60→120 was 46.5 % off.
- **With `STICKREF`** the four stick divisions (`bh:7934`..`797a`) divide by the reference
  T 7 instead, and the tape gives one press per original press (at 2F): the player's
  displacement over game time 60→120 is within **4.1 %** of T = 7 (25,025 units), attitude
  word `14328(a4)` within 348/65,536.
- Not explained: a few hundred data words that follow steps, not time (`tscale_compare.py`
  output; render scratch and the sound sequencer among them, unnamed so far) and words that
  differ only at T = 14 (tables or the larger pool).

Evidence:
- **No time source.** BH's OS calls (by library base and LVO, all `movea.l N(a4),a6; jmp
  -LVO(a6)` stubs): exec (memory, signals, devices), dos (files), intuition (screens,
  windows), graphics (`LoadRGB4`, `SetRast`, `SetRGB4`, `SetAPen`, ...), icon. No
  `DateStamp`, `CurrentTime`, `VBeamPos`, timer.device or `ReadEClock`; no beam or CIA reads;
  the only `$6C` handler (`bh:1ac26`) runs the sound sequencer (envelopes, audio registers)
  and keeps no counter the game reads.
- **The flight loop** `bh:6e48` (called from `bh:00d8`), per pass: quit check
  (`10200(a4)`), frame counter `26292(a4)` + 1, `bh:75ba` (key commands; `bh:3e98` reads the
  input of this frame), `bh:422a`, `bh:8266`, `bh:c366`, `bh:aec8`, `bh:d106`, `bh:e28e`,
  `bh:de16` and a few jump-table calls (the simulation), `bh:6ec6` (swap chunky buffers),
  `bh:6eea` (render the 3D view), the c2p through `10252(a4)` (or `10248(a4)`), `bh:8862`
  (instruments), and round again. No wait anywhere: the CPU never idles (0 % STOP).
- **Input per frame.** The controller `bh:7f30` sets the stick from the mouse movement since
  the last frame or one cursor character (§3): the same hand movement gives the same stick
  per frame whatever the frame rate, but each frame is one step, so control response also
  scales with the frame rate.
- **Coupling test** (`STATE_ONLY=1 SKIP_FRAMES=120`, flight input injected on frame
  numbers): the normal VERIFY slave (~5.4 fields per frame) against `make c2pfull` (the slow
  full-frame c2p, ~9 fields per frame), BH's data hunk at the c2p entry of flight frame 120
  (`tools/compare_state.py tmp/prof/state-a tmp/prof/state-b`): **3 bytes of 61,932 differ**,
  the original c2p's scratch byte `+6609(a4)` and one word of the per-field sound sequencer
  (`+29008(a4)`). Position, attitude, the drones, both random generators, the frame counter:
  identical after about twice as many fields. **The simulation advances exactly one step per
  frame.** (Earlier runs with keys typed at fixed fields differed in a few hundred bytes: the
  presses reached the game on different frames. That was the tape, not the game.)
- **Across CPUs** the same test is not yet clean: the 68000 and the 68020 at frame 120 differ
  in 1059 bytes. Likely cause: BH's second random generator, a 16-step shift register
  (`bh:15bf8`, state `-6070/-6068(a4)`, called by the 3D view driver), is not reseeded for the
  flight (`bh:15c1c` seeds it; only the replay camera's save/restore was seen touching it,
  `bh:77b8`/`bh:8ee0`), so its state at the first flight frame depends on how often it ran in
  the title and menus, which run at CPU speed. The slowed renderer does not change the menus,
  hence the clean result above. To compare CPUs, seed it in the VERIFY build at flight start.
  The Aztec `rand()` (`9180(a4)`) is still at its initial value 1 in flight.

What this means for faster machines, and the possible designs: `docs/open-work.md`.

