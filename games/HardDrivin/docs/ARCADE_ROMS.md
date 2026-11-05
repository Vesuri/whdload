# Arcade Hard Drivin' ROM analysis (2026-10-20)

Source: `harddriv.zip` (pinned in `inputs.sha256`, in `tmp/archives/`), MAME set `harddriv` (cockpit, rev 7, 1988; self-test
"SOFTWARE VERSION 8.6"). `mame -verifyroms harddriv -rompath tmp/archives` passes (MAME 0.289 on
PATH). Work files are under ignored `tmp/arcade/`.

## Processors and where their code lives

| CPU | Role | Code source |
|---|---|---|
| 68010 @ 8 MHz | game logic, controls, sound/IO, orchestration | ROM pairs 200r/210r @0, 200s/210s @20000, 200w/210w @A0000, 200x/210x @C0000 (200 = even byte) |
| TMS34010 GSP @ 48 MHz | polygon/2D drawing | uploaded by 68010 from ROM image at `$CD35A` (ptr `$CB304`) |
| TMS34010 MSP @ 50 MHz | **vehicle simulation** (double-precision C) | uploaded from ROM image at `$D3D9A` (ptr `$CB308`) |
| ADSP-2100 @ 8 MHz | 3D transforms/lighting | uploaded from ROM image at `$CB336` (ptr `$CB300`); data ROMs 10h/10j/10k/10l (`user1`) |
| sound 68000 + TMS32010 | sound board | 1121.45n/1122.70n, samples 1123..1126 |

`$CB310` holds a checksum, then "Copyright 1988 ATARI GAMES". Files not in the MAME set:
`dump1.bin`, `dump5.bin`, `chargen-15ie.bin`, which are ignored.

## 68010 image (`maincpu.bin`, 1 MB, built by `tools/arcade/build_image.py`)

- `$00000-$15FFF`: boot and self-test ROM (reset `$21C`, diagnostics menus).
- `$16000`: game vector table (reset PC `$3C5E0`); `$16100` jumps to the alternative entries.
- `$16000-~$2C5xx`: game code, compiled C (stack arguments). `$3C5B8-$3FFFF`: runtime library and interrupt handlers.
- `$2C000-$3BFFF`, `$A0000-$DFFFF`: data (strings, tables, tuning constants near `$39630`, track/object data, the three uploaded program images at `$CB336-$DE7B2`).
- IRQs: 1 = MSP done (`$3C796` → `$1893C`), 2 = ADSP, 3 = GSP, 5 = 244.14 Hz tick (`$3D604`, increments `$FFFF8014`), 6 = DUART.
- Inputs sampled by the IRQ5 path: 8-bit ADC channels at `$FFFF8000+ch` (0 gas, 1 clutch, 3/4 shifter), 12-bit at `$FFFF8008+2*ch` (0 steering wheel, 1 brake).
- Force feedback: `$1D4C4` steering angle from the 12-bit wheel (centre `$FF916E`, gain `$FF9178`); `$1D5EC` writes motor torque (±360) to `$B00000`.

## 68010 ↔ MSP interface

- Input block `$FF8ECC` (0x21 words) → MSP bit address `$794000` (`$18BA4`, after `$19D9E` conditions controls). 32-bit fields are word-swapped by `$1C808`.
  Key words (68010 addr → MSP bit addr): `$8EE0` → `$7940A0` ticks since last MSP result (≤12); `$8EE2` → `$7940B0` steering (`$8F28`*2);
  `$8EE4` → `$7940C0` (`$8F16`); `$8EE6` → `$7940D0` brake (`$8F14`); `$8EE8` → `$7940E0` gas 0..`$1000` (`$8F1C`); `$8EEA` → `$7940F0` gear 1..4 (`$8F1A`);
  `$8EFE` → `$794190` steering rate (`$FF9164`).
- Track data: `$1909E` writes 60-byte records to MSP `$7B0000`.
- Results: MSP `$790000` (0x86 words) → `$FF8DC0` (`$18A74`); `$18704` copies them to game state, e.g. `$8E04` → `$FF8F2E` (wheel centring in force feedback). Layout below under "Result block".

## MSP program (`msp/`)

Sections (bit addr, bytes): `$700000` 39,888 (code+const), `$778E80` 3,500 (init data), `$FFFFFC00` vectors (reset `$74C870`).
Disassembly: `msp/msp_code.dis` (MAME 34010 disassembler, `tools/dasm/tms34010dasm`).
MAME's MSP speedup PC `$723B00` is the idle wait in `$723900`.

TI C, software doubles (little-endian) on an operand stack in A14. They are **not IEEE**: there is no hidden
bit (see "MSP vehicle model" below, `tools/tidbl.py`).
`$74B400` a×b, `$74B600` a/b, `$74BA00` b/a, `$74C0A0` a+b, `$74C000` a−b, `$74C400` b−a, `$74DE00` negate,
`$74D260` int→double (A8), `$74CE00` double→int (A8). Compares return 0/1 in A8, so a following JREQ branches
when the comparison is false: `$74D600` a≤b, `$74D620` a<b, `$74D640` a≥b, `$74D660` a>b, `$74DC00` a≠b.
`$749E80` is a table-based square root (about 1%).

Frame step `$7002B0` (main loop `$700000`): inputs and time step `$723900`, crash checks `$708BD0`, drivetrain
`$730490`, chassis `$700F30`, result block `$741CD0`. Details under "MSP vehicle model".
`sec01` is the C `.cinit` table (initial values of globals, `tools/msp_cinit.py`).

## GSP and ADSP programs

GSP sections: `$FFC00000` 15,806 B, `$FFC1EDF0` 1,576, `$FFC21F30` 9,650, vectors. `gsp/gsp_code.dis`; MAME's GSP speedup PC `$FFC00F10` matches.
ADSP: 17 records, 2,714 instruction words up to `$1235`, `adsp/adsp_pgm.bin` (24-bit words in 32-bit BE). Not disassembled yet (MAME `2100dasm.cpp` is downloaded).

## Tools (`tools/arcade/`)

`build_image.py`, `msp_sections.py MAINCPU PTR OUTDIR`, `adsp_image.py`, `tms_calls.py`, `dasm/tms34010dasm IMAGE BASE [START END]`,
the step D tools listed under "MSP vehicle model", the step E models `amiga_units.py`, `handling.py`,
`handling_fx.py` and `handling_check.py` (see ARCADE_HANDLING_PLAN.md, step E),
Ghidra scripts `ghidra/HDSetup.java` and `HDExport.java` (project `ghidra-proj/harddriv`, exports in `ghidra-out/`; set
`JAVA_HOME` to a JDK 21, e.g. Homebrew openjdk@21, since headless Ghidra cannot prompt for one). MAME driver sources are in `mame-src/`.

Plan for using this to make the Amiga handling more arcade-like: `ARCADE_HANDLING_PLAN.md`.
Public sources (Jed Margolin) say the Hard Drivin MSP model has two wheels, i.e. a bicycle model.

## MAME harness (plan step A, 2026-10-20)

Tools in `tools/arcade/mame/`. MAME runs headless at 7–10× real time, so booting to the start line
takes about 3 s of wall time.

- `run.sh RUN_DIR LUA WALL [args]`: runs `harddriv` with `-video none -sound none -nothrottle`.
  - On macOS `-video none` alone still opens a full-screen window. `run.sh` sets
    `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy`, so MAME never reaches the window server
    (`lsappinfo` does not list it), and adds `-window -nomaximize` as a fallback. Logs are
    byte-identical to the earlier windowed runs.
  - It uses `-noreadconfig -noplugins`, turns off every input provider, and keeps all MAME
    directories inside RUN_DIR.
  - `gtimeout` enforces the wall-clock limit, and the PID is written to `RUN_DIR/mame.pid`.
- `session.sh RUN_DIR PLAN`: starts a fresh run directory from the pristine EEPROM and runs `hd.lua`.
  The defaults are `HD_WALL=120` wall seconds and `HD_SECONDS=120` emulated seconds.
- `hd.lua`: works through a timed event plan.
  - Inputs are held and re-applied every frame.
  - Controllers for step C: `ramp` (move an input linearly), `cruise` (hold a speed with the gas
    pedal) and `head` (steer to a heading). `plan.road` makes grass road (see "Feel measurements").
  - Each MSP result is logged when the 68010 writes the last word of the result block
    (`$FF8ECA`).
  - Logs: `tools/hdlog.py`. Snapshots: `tools/snapgrid.py`.
- `plans/start.lua`: boots into a race.
  1. Coin at 16 s.
  2. Key at 19 s, on the transmission screen. This picks automatic and skips the fly-over.
  3. Full gas and clutch at 20–20.5 s, so the pedal auto-calibration learns the whole range.
  4. Hold the key from 21 to 23.5 s. The starter cranks for about a second.
  5. The race starts when the engine runs: the forced brake (`$9816` = 0) is released.

  The car idles on the start line at script time 24.5 s.
- `make_pristine.sh` + `plans/calibrate.lua`: builds `mame/pristine`.
  - Boot once to get the default EEPROM, then break its checksum.
  - The game then runs its own control set-up: pot rest values, steering limits 0x010/0xff0,
    shifter first and fourth, seat, and force brake.
  - The brake is pressed to amount 0xc00. With the default range (0xff0), or a range above
    the learned release level of about 0xffb, every press is full braking.

**Save states cannot be used.** The driver saves none of its own state. After a load the MSP
stops returning results and the game's watchdog fires 2500 ticks later. Every session therefore
boots from power-on with the pristine EEPROM. That is deterministic: two runs of
`plans/a4_repeat.lua`, even run in parallel, give byte-identical logs.

Inputs with the pristine EEPROM (`plans/a3_sweep.lua`), as MSP input words:
- **Steering** `$7940B0`: ≈ (wheel − 0x800) × 2.0, ±4092 at 0x010/0xff0.
  It reads about −20 at centre and jitters by ±20 while driving.
- **Gas** `$7940E0` and **clutch** `$7940C0`: ((raw − 12.75) × 4096 / 242.25), clamped to
  0..4096. That is a 5% dead band.
- **Brake** `$7940D0`: (amount − 100) × 1.42, reaching 4096 at an amount of about 2980.
  The amount is 0xfff minus the 12-bit gauge reading.
- **Gear** `$7940F0`: 2 (D in automatic) while the shifter is left alone. Moving the stick
  changes it: 0 = N, 1, 4.
- **Key** `$794120`: the starter.

Result timing in MAME:
- One result every 14 ms at a standstill and about 16.5 ms while driving.
- Each result covers 3–5 ticks of the 244.14 Hz counter. That count is the dt input (≤12).
- MAME's MSP timing (with its speedups) may not match the hardware.

Leaving the road starts an "OFF ROAD n" countdown that resets the car, so manoeuvres must be
short or stay on the road.

Log row `R time frame tick inputs results adc`:
- `inputs` = MSP `$794000`, 0x21 words. `results` = MSP `$790000`, 0x86 words.
- `adc` = `$FFFF8000..$FFFF8017` as words: the 8-bit channels in byte pairs, then the 12-bit
  channels from word 4 on.
- A `C` row records the calibration RAM when logging starts.

## Result block (plan step B, 2026-10-20)

The block is written by MSP `$741CD0`. Word n is at MSP bit address `$790000 + 16n` and 68010
address `$FF8DC0 + 2n`. The fields below were confirmed with `plans/b2_drive.lua` and
`tools/hdstate.py`.

| Word | 68010 | Field |
|---|---|---|
| 00–08 | `$8DC0–$8DD0` | Rotation matrix, 2.14 fixed point. Each row is a vector with components in (X, Z, Y) order. Row 1 is the car's forward axis, row 0 a side axis, row 2 up. It includes pitch and roll: about 1° of squat under throttle and about 5° of roll in a 0.75 g turn. |
| 09–0e | `$8DD2/$8DD6/$8DDA` | Position X, Y, Z as 32-bit values (MSP little-endian; the 68010 swaps the words), 40 per foot. Y is vertical. It is the CG plus an eye point 2.5 ft above it. |
| 0f–11 | `$8DDE/$8DE0/$8DE2` | World velocity X, Y, Z, 2.56 per model ft/s. Each result moves the position by V × ticks / 16. |
| 12–14 | `$8DE4/$8DE6/$8DE8` | Angular rates, 41.72 per model rad/s (1.373 °/s per unit). `$8DE8` is yaw, positive to the right. |
| 15 | `$8DEA` | Speedometer: 4 per model MPH of the rear wheel's surface speed. With the wheel rolling it is about 1.066 × \|V\|. |
| 16 | `$8DEC` | Engine RPM (engine rad/s × 60/2π). Idle is about 900. The game shows "TURN KEY TO START" below 500. |
| 17 | `$8DEE` | Rises with throttle and goes negative off throttle; probably engine torque. It goes to `$FF8F1E`. |
| 1a–1d | `$8DF4–$8DFA` | One value per gear, relative to the current gear, which reads 0. The automatic shift logic uses it. |
| 21 | `$8E02` | Steering torque for the force-feedback motor: about ±1900 in a 12% turn. |
| 22–23 | `$8E04`, `$8E06` | Force-feedback terms (`$8F2E`, `$8F2C`). |
| 25–26 | `$8E0A`, `$8E0C` | Sound levels: tire squeal (up to about 4200 when braking or cornering) and engine load. |
| 28 | `$8E10` | Track segment index. |
| 29–2a | `$8E12`, `$8E14` | Off-road flags. |
| 2d–2f | `$8E1A–$8E1E` | Dashboard gauges (amps, temperature, oil). |

Conventions used by `hdstate.py`:
- **Heading** = atan2(−fwd.Z, fwd.X), positive to the right.
- **Sideslip** is positive when the velocity points to the right of the heading.

A right turn at 12% lock and 63–77 MPH gives:
- yaw of 13–17 °/s
- about 0.75 g lateral (speed × yaw rate agrees with dV/dt)
- −1.4° to −2° of sideslip

**Time step and units** (corrected by step D):
- **The time step:** `$723900` sets dt = ticks × 0.004 s, clamped to 0.05 s. A tick is a real
  4.096 ms (8 MHz / 32768), so model time runs at 0.9766 of real time. The car covers 2.3% less
  ground per real second than its model speed says, and the speedometer reads 2.3% high against
  real ground speed. (Step B read the factors as 0.0118125 and 0.1125, decoding the MSP's doubles
  as IEEE.)
- **One frame per result:** the MSP reads the tick input twice per frame, and those reads come
  at twice the result rate.
- **Real time is unaffected by MAME's speed:** dt comes from the real tick, so the model covers
  the same ground per real second however fast MAME runs the MSP; only the step size changes.
- **Plausible magnitudes:** measured against emulated time, with speeds from the needle, the
  numbers are physical: a 0.43 g launch in first gear, a 0.04 g coast at 16 MPH, 0.67 g at 68%
  brake, and 0–60 MPH in about 6.5 s. The braking figure was measured on grass. On the road,
  step C measured 0.69 g at 49% and 0.87 g at full pedal.
- **Internal units:** feet, pounds, slugs, radians and model seconds, with gravity 32.2 ft/s².
  The position and velocity doubles (`$74EA20`, `$74E960`) are in feet and ft/s. The result
  block's scale factors are 40 per foot, 40 × 0.004 × 16 = 2.56 per ft/s, and 10430.4 × 0.004
  = 41.72 per rad/s. Step B's IEEE readings of them (104, 0.0118125, 48) were wrong.

**Speed calibration:**
- `tools/needle.py` reads the needle angle from snapshots. The dial is linear: 0 MPH at 225°,
  140 MPH at −90°.
- While coasting, `$8DEA`/MPH = 4.04–4.25. Steps B and C used 4.07, ±3%. The needle lags under
  hard acceleration.
- Exact, from the result-block writer (step D): `$8DEA` = rear wheel rad/s × 1 ft × 30/11, which
  is 4 per model MPH. In real time, ground speed in MPH is `$8DEA` / 4.096 while the rear wheel
  rolls.
- `tools/hdstate.py` uses the exact factors in real time: 40 position words per foot, real ft/s
  = V × 0.9766 / 2.56, and real MPH = `$8DEA` / 4.096. Step C's numbers moved by at most 1%;
  the tables below are updated.

## Feel measurements (plan step C, 2026-10-20)

### Test ground

The road near the start is too short and narrow for steady cornering, and leaving it starts the
off-road countdown. So the manoeuvres run on the grass, with the grass made into road.

- **Road everywhere:** `plan.road = true` in a `hd.lua` plan.
  - The MSP keeps one surface type per wheel: front `$750FB0`, rear `$750FD0`. Each is the 3-bit
    field at offset 0xB of the polygon under that wheel, written at `$73A980` and `$73AA00`.
  - 0 is road and 1 is grass. 6 means a wheel is off the ground. 5 and 7 are not identified.
  - A write tap replaces 1 with 0. The off-road countdown reads the same variables through
    `$8E12/$8E14`, so it stops too.
  - Checked: B2's drive is byte-identical with and without the tap until the first wheel touches
    grass. After that the tap removes the grass drag, 0.3–0.5 g with full throttle.
  - Assumption: the surface type is the only difference between grass and road.
- **Open ground:** probe runs (`plans/c0_probe.lua`, `c0_far.lua`) found the grass behind and to
  the left of the start line flat, at the start line's height of 3.5 ft, for at least 8,000 ft.
  Positions are in feet in `hdstate.py` coordinates.
  - **The hill:** ahead, at X ≈ 5,750–7,200 ft, up to 44 ft high, with a drop on its side.
  - **Objects:** turning right near the start hits one at about (5,260, 4,880). Another, hit
    once in 50 runs, is at about (3,945, 6,040).
- **Approach:** `plans/c.lua`. After the boot, the car turns left onto heading −145° at 25 MPH,
  into the open ground, and holds that heading until the manoeuvre starts.
  - Each manoeuvre is a plan, `plans/c1*.lua`.
  - `tools/mame/c_runs.sh ROOT [SHIFT]` runs all 25, eight sessions at a time. That takes about
    80 s of wall time.
- **Stick shift:** turn the wheel right on the transmission screen and hold it through the key
  press (`start.lua`, `M.plan(after, true)`).
  - The shifter positions (shiftx, shifty) are: 1 = (0,255), 2 = (0,0), 3 = (255,255),
    4 = (255,0), N = (128,128).
  - With the automatic, the stick position is the gear word: 1–4, 0 for neutral, and 2 when
    untouched.

### Analysis

`tools/feel.py` works on the logs:
- `report ROOT [REPEAT_ROOT]` prints every metric (231) and writes SVG plots to `ROOT/plots`.
- `spread NAME DIR...` compares one manoeuvre across runs.
- `trace RUN` prints a sampled trace with trouble flags: height change, wheels off the ground,
  position jump, and collision. A collision is losing more than 3 MPH in 0.1 s without a gear
  change; automatic downshifts while braking also jerk the speed word.

Definitions:
- **Time** is physics time. The tick count logged with one result is the step that produces the
  next result; using it that way cuts the yaw-rate noise from 1.9 to 0.7 °/s.
- **`hdstate.py`'s feet conversion was inverted** before step C (2.73 instead of 39.7 units per
  foot). No step B result used it.
- **Units are real time**, with step D's exact factors (see "Speed calibration"). The nominal
  speeds of the plans are the controller's targets, `$8DEA` / 4.07: "60 MPH" is 59.6 real MPH.
- **Repeat runs:** the whole matrix ran a second time with every manoeuvre 0.37 s later, which
  changes the MSP frame phase and where the car is. The tolerance is 5% of the value or an
  absolute floor, whichever is larger: 0.1 s, 35 ms, 0.03 g, 1 °/s, 0.5° or 1 MPH.
  - 221 of 231 metrics repeat within tolerance.
  - The other 10 were run at seven phase shifts. Seven are timing details of the small steering
    steps (C1d below). The arcade's steering word jitters by ±20, which is up to 15% of a 0.35 g
    step at speed, and a result takes 16 ms.
  - The other three are braking at the limit in a corner (C1e below), which is a genuine tipping
    point.

### Feel table

All manoeuvres turn left, so yaw rates are magnitudes. The **nose-in angle** is the sideslip,
positive when the nose points into the turn relative to the direction of travel. That is the
usual attitude at speed. At low speed the reference point's path runs inside the heading, which
makes the angle negative.

ARCADE_HANDLING_PLAN.md, step F, puts the Amiga's values for the same manoeuvres next to these,
for both the enhanced and the original build.

**Straight line (C1a, C1b)**

| Metric | Value |
|---|---|
| 0–30 / 0–60 / 0–100 MPH, automatic | 3.2 / 6.3 / 13.3 s |
| Launch, first second | 0.32 g |
| Automatic upshifts | at 5,750 rpm: 48, 67, 92 MPH |
| Stick, highest speed per gear | 62, 88, 114, 140 MPH; rev limit about 7,500 rpm |
| Top speed | 140 MPH, after about 40 s |
| Coast-down in neutral | 0.12 g at 130 MPH, 0.09 at 110, 0.07 at 90 (≈ 0.024 g + 5.7·10⁻⁶ g/MPH²) |
| Coast-down in 4th, automatic | 0.20 g at 130 MPH, 0.18 at 110, 0.15 at 90, 0.11 at 70 |
| Full braking | 0.87 g: 143 ft and 4.5 s from 60 MPH; 390 ft and 6.6 s from 100 |
| Brake amount 1500 (input word 1996, 49%) | 0.68 g: 182 ft from 60 MPH; 488 ft from 100 |

**Steady cornering (C1c: constant speed, steering ramped over 16 s)**

| Metric | 30 MPH | 60 MPH | 90 MPH |
|---|---|---|---|
| Yaw gain below 0.4 g (°/s per 1000 steer words) | 31.7 | 43.1 | 45.4 |
| Path curvature gain (1/1000 ft per 1000 words) | 12.6 | 8.6 | 6.0 |
| Maximum lateral | 1.08 g | 1.08 g | 1.06 g |
| Steer word at 95% of the maximum | 1,590 | 745 | 590 |
| Nose-in angle at 0.5 / 0.8 g | −1.3° / −1.9° | 0.3° / 0.9° | 0.6° / 1.4° |
| Nose-in angle past the limit | −1.9° | 1.8° | 2.4° |

**Step steer (C1d: medians of seven runs)**

| Metric | 30 small | 30 large | 60 small | 60 large | 90 small | 90 large |
|---|---|---|---|---|---|---|
| Steer word | 470 | 1,290 | 180 | 490 | 130 | 450 |
| Steady lateral | 0.34 g | 0.84 g | 0.36 g | 0.79 g | 0.36 g | 0.85 g |
| Yaw at 63% | 49 ms | 108 ms | 66 ms | 56 ms | 34 ms | 43 ms |
| Yaw at 90% | 84 ms | 167 ms | 116 ms | 90 ms | 63 ms | 64 ms |
| Yaw overshoot | 14% | 7% | 19% | 25% | 37% | 55% |
| Yaw within 10% after | 0.24 s | 0.16 s | 0.3–1.1 s | 0.48 s | 0.8–1.5 s | 0.6 or 1.4 s |
| Steady nose-in angle | −0.9° | −2.1° | 0.2° | 0.9° | 0.5° | 1.7° |

The response times are at the resolution of one result (16 ms) and of MAME's MSP timing. For the
small steps they range over ±30–50 ms between runs. The run that hit an object (60 MPH, small)
is left out.

**In a corner at 60 MPH (C1e: an action held for 3 s)**

| Action | Corner at 0.7 g | Corner at 0.9 g |
|---|---|---|
| Lift off | yaw +13% at peak, +7% after 2 s; nose-in angle up to 0.9° | +20%, +10%; 1.3° |
| Brake, amount 1500 | yaw spike of +133% to +172% for about 0.3 s; nose-in angle 3.0–4.8° | from −37% to +134% (median +112%); nose-in angle 1.9–9.5° (median 4.5°) |
| Full throttle | yaw −17% as the car speeds up to 74 MPH; nose-in angle ≤ 0.7° | −17% to −20%; ≤ 1.0° |

The brake rows are ranges over seven runs. At 0.9 g the response depends on the frame phase of
the brake application. Sometimes the rear lets go and the car reaches 10° nose-in, then recovers
by itself within about a second.

**Slides (C1f: steering step to 2.5× the grip-limit angle, or the limit angle plus full brake)**

| Metric | 60 MPH | 90 MPH |
|---|---|---|
| Peak nose-in angle / yaw rate | 4.7° / 35 °/s at about 0.8 s | 7.7° / 30 °/s |
| Steering held | settles to 22 °/s and 1.7° | 15 °/s and 2.4° |
| Released after 1 s | settled (\|β\| < 1°, \|r\| < 2 °/s) in 0.4–0.5 s | 0.5–0.6 s |
| Countersteer, half as much, for 1 s | settled in 1.4 s; overshoots to −2.1° | 1.4–1.5 s; −5.2° |
| Limit angle plus full brake | peak yaw 6–7 °/s, then straight on; the wheels lock | 11 °/s, then straight on |

**Low speed (C1g)**

| Metric | Value |
|---|---|
| Path radius at 5 MPH: 25 / 50 / 75 / 100% lock | 64 / 32 / 21 / 14.9 ft (circle fit 68 / 33 / 21.3 / 15.4) |
| Nose-in angle at those locks | −3.8° / −9.2° / −13.5° / −18.7° |
| Full lock at 10 / 16 MPH | 15.7 ft at 0.46 g / 17.4 ft at 0.92 g |
| Full right lock at 5 MPH | 15.1 ft |

### What this means for the Amiga model (step E)

- **Understeer:** it follows the textbook form. The path curvature gain is ≈ κ₀ / (1 + (u / 70
  MPH)²), with κ₀ ≈ 15 per 1000 ft per 1000 steer words. That is also the value at 5 MPH and 25%
  lock. At 5 MPH the curvature stays nearly linear in the steering all the way to full lock:
  15.3–16.3 per 1000 words.
- **Grip:** about 1.08 g at every speed. Past the limit the lateral g stays flat (no drop-off),
  and the car ploughs. Steering alone does not start a lasting slide, even at 2.5× the limit
  angle.
- **Yaw response:** fast (63% within 35–110 ms). The overshoot grows with speed: 7–14% at 30 MPH,
  19–25% at 60 and 37–55% at 90. Yaw damping falls as speed rises.
- **Weight transfer:** it is modelled and noticeable.
  - Lifting off tightens the line a little.
  - Braking in a corner rotates the car hard for about 0.3 s, and at the limit it can start a
    10° slide that recovers by itself.
  - Throttle gives understeer, never oversteer.
- **Braking:** full braking locks the wheels, so there is no steering; half braking keeps it.
- **Low speed:** no mode switch is visible. The nose-in angle changes smoothly from −19° at
  5 MPH and full lock to the attitude at speed.
- **Step D** read the model itself; see "MSP vehicle model" below. Its parameters reproduce
  these measurements, and it explains each of them.

### Caveats

- The road-everywhere tap assumes the surface type is all that differs between grass and road.
  Step D confirmed it: the MSP sees grass only through the surface type.
- MAME's MSP timing, one result every 16 ms, may not match the hardware.
- In the stick coast-down, the engine stalled in neutral at about 86 MPH (rpm fell from idle to
  6). The game then forced the brake (0.44 g), so the coast-down data stops there. Step D: the
  forced stop is a constant 1,500 lb force against the velocity.
- Full-lock turning circles are for the position the result block reports. Step D: that is the
  CG, halfway between the axles, plus an eye point 2.5 ft above it.

## MSP vehicle model (plan step D, 2026-10-20)

Read from the MSP code with a value trace in MAME and a lifter for the compiler's double code.
Units are the model's: feet, pounds, slugs, radians and model seconds (0.004 s per tick, see
"Time step and units"). Addresses are MSP bit addresses.

### Tools

- `tools/tidbl.py`: the double format (below).
- `tools/msp_dis.py START [END]`: prints part of `msp/msp_code.dis`.
- `tools/msp_lift.py FUNC...|all`: turns the A14 stack code into expressions such as
  `g_751280 = dbl(wg_7940A0) * 0.004`, with constants decoded. `msp/lift.txt` holds the whole program.
  It forgets register state at branch targets and prints what it does not understand raw.
- `tools/msp_cinit.py`: the `.cinit` records in `sec01`, which hold the initial values of the globals.
- `tools/mame/ftrace.lua` with `plans/d1_trace.lua`:
  - read taps on the float library's entries and exits log every operation (caller, operands,
    result) during the times in `HD_TRACE`, on top of any plan (`HD_BASE`);
  - `HD_DUMP` dumps MSP RAM `$74DE80–$760000` and the program area;
  - `tools/ftrace.py` prints one frame as `caller: a op b = result` next to the lifted statement;
  - `tools/mspram.py` reads values from the dumps at any bit address.
- `plans/d1_watch.lua`: logs writes to an MSP address range with the PC.

### Double format

The MSP's software doubles look like IEEE (sign, 11-bit exponent with bias 1023, 52-bit mantissa)
but have no hidden bit. The mantissa holds 0.1xxx… with an explicit leading one, so the value is
0.M × 2^(e−1023).
- **Read as IEEE**, every value comes out as v + 2^⌊log₂ v⌋: 1.0 reads as 3.0 and 32.2 as 96.2.
- **Earlier readings:** the constants quoted in steps A–C and in the plan were IEEE readings.
  The "time step 0.0118125" is 0.004, the "gear ratios −6.4 … 1.95" are −2.4 … 0.95, and the
  "9-entry curve" at `$77E900` lies inside a 16-bit sine table.
- **Checked:** 4,690 logged operations in MAME, covering multiply, divide, add, subtract and the
  int conversions. All match except 11 add/subtract cancellations, where the library keeps only
  about 32 mantissa bits.

### Frame

`$7002B0` runs once per result:

| Function | Does |
|---|---|
| `$723900` | Inputs: dt = ticks × 0.004 s (at most 0.05); steering angle, pedals 0..1, brake torques |
| `$708BD0` | Crash checks: sets `$7515C0` on a velocity sum over 300 ft/s, a force spike, yaw over 10 rad/s or surface 7 |
| `$730490` | Drivetrain: engine torque `$735BC0`, gear ratio `$734E70`, automatic shifts `$7346B0`, clutch and engine speed `$730830` |
| `$700F30` | Chassis: wheel contact `$73B170`, wheels and drag `$701210`, moments `$703AB0`, accelerations `$704830`, integration `$705C80` and `$705420` |
| `$741CD0` | Result block |

**Chassis:**
- `$701210` calls the wheel function `$70D590` for the front, then the rear. Each wheel does
  suspension, then the tire `$710D30`, then rotates its force into the body.
- The forces add up with gravity and drag. The moments are r × F about the CG.
- Body velocities follow dv/dt = F/m − ω × v. Only pitch and yaw accelerate (`$7087C0` sets roll
  acceleration to 0).
- **Integration** is explicit Euler: position and orientation from the old velocities, then the
  new velocities.
- **Roll:** the roll in the result matrix is set kinematically in `$705C80` from the wheel contact
  data, not by roll dynamics. It does not affect the handling.

### Parameters

The car's parameter block is at `$753CB0` (`.cinit`; `$72ADB0` copies it into the globals). Two
other blocks at `$754EE0` and `$756110` have the same layout. Values below are from MSP RAM during
a race.

| Quantity | Value | Where |
|---|---|---|
| Mass | 109.47 slug (3,525 lb), gravity 32.2 ft/s² | P+20, `$750730` |
| Inertia: roll, pitch, yaw | 321, 2,000, 2,000 slug·ft² (roll unused) | P+60, P+A0, P+E0 |
| Wheels, from the CG (forward, side, down) | front (5, 0, 1.567) ft, rear (−5, 0, 1.567); wheelbase 10 ft | P+320..460 |
| Suspension, front / rear | springs 3,000 / 3,500 lb/ft, dampers 400 / 500 lb·s/ft | P+120..1E0 |
| Static axle loads | 1,762.5 lb each | wheel +200 |
| Tire radius, wheel inertia | 1 ft, 10 slug·ft² | wheel +0, +1C0 (stored as 1/I = 0.1) |
| Cornering stiffness, front / rear | 32,000 / 64,000 lb/rad at the static load | wheel +C0 |
| Friction μ, front / rear | 1.2 / 1.3 | wheel +100 |
| Tire lateral spring and damper | 8,160 lb/ft, 400 lb·s/ft | wheel +40, +80 |
| Steering | ratio 16, 560° of wheel lock: 35° at full lock | P+220, `$72DA20` |
| Drag | 0.0087 · u² + 105 lb against the forward speed u | P+2A0, P+2E0 + 30 |
| Brake torque, front / rear | 4,653 / 0 lb·ft (1.1 × μ_f × weight × split, split = 1) | `$72C9C0`, P+1030 |
| Engine | inertia 0.4 slug·ft², clutch capacity 600 lb·ft | P+1070, P+10F0 |
| Gearbox | 2.4, 1.7, 1.25, 0.95, reverse −2.4; final drive 3.5 | `$753930`, P+10B0 |

The front wheel struct is at `$74FA90` and the rear at `$750060`. The wheel's angular velocity
is at +500, the tire's lateral deflection at +4C0, the friction torque at +540 and the utilisation
at +580. Each wheel's force vector in body axes (x forward, y lateral, z down, so −N at +80) is at
`$74E3C0` (front) and `$74E480` (rear); their points from the CG are at `$74E540` and `$74E600`,
the drag force at `$74E6C0`, and `$703AB0` sums the moments r × F.

### Equations

**Steering:** δ = 0.6109 rad × (steer + steer rate × ticks / 2) / 4096. The steer word comes from
the 68010, ±4092 at full lock.

**Suspension** (`$70D590`), per wheel. Compression x comes from the ground distance under the wheel
(`$73B170`); a wheel more than 1 ft above the ground is airborne (surface 6). Then:
- N = −(k·x + c·ẋ): the springs are 3,000 or 3,500 lb/ft and c is the damper rate, doubled
  while ẋ > 0.
- N is doubled past 1.5 ft of compression (the bump stop), is 0 when x ≤ 0, and is capped at the
  car's weight.
- **Weight transfer** comes from this. Tire forces act at the wheel points, 1.567 ft below the
  CG, so braking or driving pitches the car and moves load between the axles. Quasi-statically
  that is m·a·1.567/10 per axle, 552 lb per g. There is no lateral transfer.

**Tire** (`$710D30`), per wheel. With u, v the contact patch's forward and lateral velocities, r the
radius and ω the wheel's angular velocity:
- **Wheel spin.** When ω·r ≠ u, the wheel slides: the force is μN against the slip velocity
  (u − ω·r, v), and the wheel's torque balance uses the whole μN·r, ω̇ = (T ∓ μN·r)/I. While
  it rolls, a drive or brake torque T gives Fx = T/r × m·r²/(I + m·r²), with m the whole car's
  mass (`g_750770` = 109.47), so 0.916 of T reaches the road. A torque whose 0.916 share reaches
  μN·r starts wheelspin or lock-up; that step pushes μN along the wheel and nothing sideways.
  So full braking locks the front wheel, and its lateral grip goes with it.
  - **A wheel that has only just started to slide pushes harder sideways.** Its slip velocity
    is then almost all lateral, so nearly all of μN goes sideways, more than the rolling tire
    carried. With a brake torque only just above μN·r, ω stays close to u/r for a while.
  - That is the brake-in-corner yaw spike C measured: half pedal (word 1996) brakes with
    2,076 lb·ft against a front μN of about 2,070.
  - RAM dumps at the onset (C1e, 0.7 g) show the effect: the front ω falls below u/r, the
    utilisation is 1.0, the deflection is frozen, the front's lateral force about doubles,
    and the car slows at only 0.23 g for 0.2 s.
- **Friction circle.** While rolling, the lateral limit is μ' = √(μ² − (Fx/N)²).
- **Slip angle** (`$718990`): α = v/|u|, so the force opposes v either way the car rolls;
  α = v when u = 0, and v/400 when |u| ≥ 400 ft/s.
- **Lateral force curve**, a Fiala brush tire: with C' = C/N_static and z = C'α/(3μ'),
  Fy = −N·μ'·(3z − 3z² + z³) up to α_sl = 3μ'/C', where Fy = μ'N; beyond that it stays flat.
  - Saturation angles at the static load: front 11.4°, rear 6.2°.
  - Grip is proportional to N, so load transfer moves grip between the axles.
- **Tire lag.** The lateral force is a spring and damper on a deflection y:
  - Fy = 8,160·y + 400·ẏ, with ẏ = −v − y·|u|/σ;
  - the relaxation length σ is the curve's secant stiffness N·(Fy/N)/α divided by 8,160. At
    small slip that is C/8,160: 3.9 ft at the front and 7.8 ft at the rear;
  - past α_sl, ẏ = −v and Fy is clamped to μ'N.
  - When |u|/σ × dt ≥ 0.5 (front, above about 83 MPH at a 16 ms step), the lag is skipped and
    Fy takes the curve's value directly.
- **Utilisation** |F| / (μN) goes to wheel +580. It feeds the tire squeal.

**Low speed:** there is no mode switch. At low speed α = v/u grows large and the tire acts as the
lateral spring and damper above. The car then follows the kinematic path of a two-wheel car with
its reference point at the CG. At 35° lock that gives a radius of √((L/tan δ)² + b²) = 15.1 ft and
a nose-in angle of −atan(b·tan δ/L) = −19.3°; C1g measured 14.9 ft and −18.7°.

**Brakes and drag:**
- **Brake torque** is −brake × 4,653 × s(ω) lb·ft, all on the front wheel. s is 0 below
  2 rad/s, 0.05·ω up to 10 rad/s, and 1 above.
- **Drag** is 0.0087·u² + 105 lb.
- **Grass**, which C's road tap removes:
  - with the rear wheel on grass, drag adds 10·u lb and the engine uses its grass torque table;
  - with both wheels on grass, μ and C drop to 80%.
- **The forced stop** (race over, stall) is a constant 1,500 lb force against the velocity.

**Drivetrain** (`$730490`):
- **Engine torque** is a 10 × 12 table over throttle and rpm (`$7529F0`, bilinear), times 1.3 on
  road. At full throttle it is 200, 250, 290, 300, 270, 200 and 100 lb·ft at 1,000–7,000 rpm, 0
  at 8,000, and down to −80 above that. Closed throttle gives −10 to −80 lb·ft of engine braking.
- **Clutch.** The engine speed ω_e integrates (T_engine − T_clutch)/0.4. The clutch transmits at
  most its capacity until it locks; locked, the engine's inertia × ratio² is added to the rear
  wheel.
  - Stick: capacity 600 × (0.8 − pedal) × 1.25 lb·ft.
  - Automatic: the clutch takes up between 1,500 and 3,000 rpm.
- **Automatic shifts:** up at 602·(gas + 3)/4 rad/s (5,750 rpm at full throttle), down at
  366.5·(gas + 3)/4 rad/s.
- The drive torque goes to the rear wheel only.

**Special cases:**
- After any wheel leaves the ground, the front cornering stiffness drops to 50% and returns to
  100% over 1.7 s.
- Surface 5 has its own path in `$708BD0`, not identified.

### Checks against step C

C's numbers are in real time. Model-time speeds are 2.3% higher and accelerations 4.6% higher, so
the second column converts the parameters to real time.

| Quantity | From the parameters, real time | Measured in C |
|---|---|---|
| Understeer characteristic speed √(L/K), K = (m/L)(b/C_f − a/C_r) | 72 MPH | about 70 MPH |
| Low-speed curvature per 1000 steer words, 1/L × 0.149 rad | 14.9 per 1000 ft | κ₀ ≈ 15 |
| Full lock at 5 MPH: radius, nose-in angle | 15.1 ft, −19.3° | 14.9 ft, −18.7° |
| Coast in neutral at 130 MPH: 0.0087·u² + 105 lb | 0.12 g | 0.12 g |
| Coast at low speed, rolling drag only | 0.028 g | about 0.024 g |
| Front grip limit, 2 × μ_f × N_f / weight | 1.14 g, before the rear's drive force and the steered front's drag | 1.06–1.08 g |
| Automatic upshift at full throttle | 5,750 rpm | 5,750 rpm |

### Answers to step C's open questions

- **Tire curve past the peak:** flat, at both axles: a Fiala curve saturating at μ'N.
  - The rear has twice the front's cornering stiffness and more μ, so the rear saturates at a
    smaller angle but carries more: that is the understeer.
  - Slides start from load transfer (braking) or from wheelspin and lock-up, not from the curve
    falling away.
- **Weight transfer:** pitch on the springs, with the tire forces acting 1.567 ft below the CG.
  Grip is proportional to load, and the brakes act on the front only. That is the brake-in-corner
  rotation.
  - The throttle drives the rear only, which uses up rear grip through the friction circle. It
    also moves load from the front to the rear, and C measured understeer.
- **Low-speed blend:** no switch. The tire's lateral spring and its relaxation length give the
  kinematic turn at low speed by themselves.
- **Engine and gears:** above. Comparing them with the Amiga's is the plan's separate "later"
  item.
- **The brake tipping point** (step E, checked with RAM dumps): half pedal sits right at the front
  tire's μN·r, and the arcade's axle loads jitter by about ±50 lb from frame to frame (1,820 and
  1,752 lb standing still, against 1,762.5 static). Whether the front starts to slide, and so
  whether the car turns in, depends on that jitter at the moment the brake goes on. The step E
  model reproduces the spike (+140% / +87% against +133% / +83%) with 3% more brake torque, and
  goes the other way (understeer) without it.

## Race clocks (2026-10-21)

The 68010 keeps both clocks in units of 1/250 s, counted by the IRQ5 tick, and every time it
shows goes through `$19136` (minutes = t / 15000, seconds = rest / 250, hundredths = rest × 0.4).

- **Tick:** IRQ5 (`$3D604`) adds 1 to `$FFFF8014`, then calls `$1D82A`. MAME's driver runs it
  at 32 MHz / 2^17 = 244.140625 Hz.
- **Time left** `$FF9822`: `$1D82A` subtracts 1 on every tick while the race clock runs
  (`$FF9816`), but only on 5 of every 16 ticks while `$FF9818` is set: from the crash
  (`$21752`, race state 4) to the end of its instant replay. The race-tick counter `$FF986A`
  runs at the full rate throughout.
  - **Start:** in state 1 (the start post) the clock is stopped and the HUD counts 10 to 0.
    State 2 begins, and the clock starts, when the engine runs or after 2500 ticks.
  - **Cap:** every frame time left is cut to the starting time (`$20F12`, disabled by ROM
    word `$3BA48`, 0 in rev 7), so an award never takes it higher.
  - **Below zero:** the engine is cut (`$9860`). The race ends when |V| < 5 ft/s (`$FF8F0E`,
    the squared speed, < $A3) or at −2500, 10 s past zero (`$20FDC`). Checkpoint and finish
    awards still count meanwhile and are added to the negative time.
  - **HUD:** m:ss (`$21F6C`), clamped at 0:00, colour 3 below 20 s, colour 7 in the crash.
    Below 20 s a dash lamp also blinks (`$18D68`). No sound is keyed on time left.
- **Lap time** `$FF9772` = tick − `$FF976E`, shown live on the dash as "LAP TIME m:ss:hh". The
  start-line marker (#0, segment 200, just past the start post) sets `$FF976E` and turns the
  lap clock on (`$FF976C`); the finish (#27 speed, #29 stunt) records it and keeps the best lap
  in `$FF4556`. The crash and its replay are left out: `$FF976E` += tick − `$FF97BE`.
- **Off road:** 2750 race ticks (`$FF982A` + 0xABE), shown as "OFF ROAD 10".."0"; then the car
  is reset to the road.
- **Times** (seconds × 250, `$229BA`, `$229E8`, `$22B24`). GAME DIFFICULTY (option word bits
  15–13) picks a preset (`$3A3D8`): starting time and extended play for the first, second and
  later finishes. Each lap has one checkpoint: 32 s on the speed route (marker #22) and 29 s on
  the stunt route (#9), whatever the lap (`$3A3C8`).

  | Preset | Start | Extended play 1st / 2nd / later |
  | --- | ---: | ---: |
  | EASY (MAME's pristine EEPROM) | 96 s | 48 / 47 / 46 s |
  | MEDIUM (the code's factory default) | 90 s | 44 / 44 / 45 s |
  | HARD | 84 s | 43 / 43 / 44 s |
  | VERY HARD | 78 s | 41 / 42 / 42 s |

- **Qualifying:** lap − `$FF9760` ≤ the champion's lap `$FF455A` (PHANTOM PHOTON, 1:33.00 at
  every boot). `$FF9760` comes from CHAMP LAP QUALIFICATION (`$1ED12`: +5, +2.5, −0.5 or −4 s;
  MAME's EEPROM gives EASY, +5 s), grows by 0.5 s after each game that did not qualify, up
  to +10 s, and is reset for every championship lap. The dash shows "BEAT" champion + term.
- **Championship lap:** timed from the green light; lost when the champion's time passes
  first. Time left plays no part.

Both clocks run at 244.14 / 250 = **0.9766** of real time: the tick is 4.096 ms, and the code
counts it as 4 ms. Measured with `tools/mame/plans/clock.lua` (`session.sh runs/clock1`): 244.141
ticks per emulated second. Time left fell 244.141 units/s and lap time rose 244.203 units/s,
which are both 0.977 displayed seconds per real second. The Amiga's countdown runs at 0.500 and
its lap clock at 0.76–0.80 (GAME_TIME.md). The crash-replay rates come from the code and were not
measured. The race state machine is `$20F12` (jump table `$21028`); the marker records start at
`$39F76`, 0x1A bytes each. MAME's operator defaults (time nibbles `$FF9766` = CB A9, `$FF9760` =
+5 s, champion 1:33.00, best lap 2:00.00) were read with `tools/mame/plans/settings.lua`.
The Amiga's arcade race timing (CUSTOM5=1) follows these rules: ARCADE_TIMING.md.

## Traffic at the start (2026-10-23)

The user: "when the game starts the other cars speed away while the player is left behind".
`plans/t_start_idle.lua` (snapshots every 0.5 s) and `plans/t_dump.lua` (the 68010's RAM
$FF0000..$FFFFFF every 0.25 s, `runs/t_dump`) with the car idling on the start line.
- **Table:** 7 cars at `$FF87E6`, 0x7C bytes each, position X, Y, Z as longs at +0, +4, +8
  (40 per foot, as the player's). Copies follow at `$FF9944` (0x72 apart) and `$FF9F26`
  (12 apart), lagging by a frame or so.
- **The grid:** four cars start with the player (5240, 4995 ft): two 75 ft ahead (both
  lanes), one alongside in the other lane, one 75 ft behind in the player's. They stand
  through the red light and pull away from 22.5–23.0 s (script time) whether or not the
  player moves. The other three are far away and run at about 130 MPH at once.
- **The launch** (1 s windows): the left car ahead 6.7, 16.5, 26.3, 35.9, 46.0 MPH at 1–5 s,
  9.8 MPH/s or 0.45 g, settling near 50; the right car ahead and the one alongside about
  0.42–0.45 g to 27–30 MPH; the one behind crawls at 4–7 MPH (held up by the idling player).

## The loop in the attract demo (2026-10-23)

The attract mode's second demo (from power-on without a coin, about 106–112 s) drives the stunt
route through the loop. It is a recorded playback: the MSP produces only 46 results in 240 s of
attract mode and the result block stays still. The playback's pose is at `$FF8404`: X, Y, Z longs
at 40 per foot (Y up), then a 2.14 matrix whose column 2 is the car's forward axis in (X, Y, Z)
(it fits the direction of motion to 0.0006 in squared error); a copy of the matrix is at
`$FF8F62`. Plans `a_attract.lua` (snapshots every 2 s), `a_snap.lua`, `a_dump.lua` and
`a_dump2.lua` (RAM every 0.1 s, 103–114 s); `tools/demo_pose.py runs/attract4 103 0.1` decodes
the pose.

- **Size:** the eye rises from 3.5 ft to 120.6 ft at the top, so the loop is about 117 ft high
  (the Amiga's: 630 units, 113 ft at 0.1791 ft per unit).
- **Speed:** about 90 ft/s (61 MPH) at the entry, 70–75 ft/s over the top, 100+ ft/s at the exit.
  At the top v²/r is about 1.7 g against 1 g of gravity.
- **It drifts sideways like the Amiga's:** from the entry (108.0 s) to the exit (112.0 s) the
  car moves 41 ft along the horizontal axis square to its entry heading, the road's width, at a
  steady 10 ft/s.
- **The car yaws with it:** its forward axis and its velocity have the same component along that
  axis throughout (slip under 1°): −0.03 at 14° of pitch, −0.17 (10°) at 140°, −0.10 on the way
  down. It is still turning (−0.07) on the road after the exit.
- **Not known:** the demo's wheel input, so whether the driver steered or the arcade's road
  surface turns the car. The Amiga's loop is a cylinder (every section's edge points the same way,
  (78, 0, 217)/230), and a car driving straight on a cylinder, square to its axis, goes round a
  circle: it would not follow the drift.

## The jump in the attract demo (2026-10-23)

The same demo drives over the stunt road's first jump right after the loop (114–118.5 s from
power-on). Plan `a_pose.lua` logs the playback pose every 1/60 s from `HD_FROM` to `HD_TO`
(`runs/pose1`, 113–175 s); the playback moves the pose every 3–5 frames, so speeds come from
distinct poses over 0.3 s or more. The pose's Y is 3.5 ft above the road.

- **The ramp:** 77 MPH at its foot, 10.7° of climb; 71 MPH (104.5 ft/s horizontal) at the lip,
  pose 33.6 ft (the road about 30 ft up).
- **Take-off:** along the ramp's slope. The velocity's pitch is 9.4–10.2° as the car leaves, the
  body's 7–8°: the body already turns nose down, the motion does not.
- **Flight:** ballistic. A quadratic over 115.75–117.5 s fits to 0.18 ft with 31.3 ft/s² and
  17.2 ft/s up at the lip; 6 ft above the lip at 116.33 s, 1.83 s and 183 ft from the lip to
  the landing. The body turns from 7° to −21° at a steady 16–17°/s.
- **Landing:** on the landing ramp's 10° downslope at pose 15.4 ft (the road about 12 ft up),
  about 39 ft/s down and 98 ft/s along, 8–11° steeper than the slope: about 19 ft/s into it. The
  car runs down the slope at −10° and is level on the flat at 118.4 s, 76 MPH.

## The crash checks (`$708BD0`, 2026-10-24)

`$7515C0` = 1 starts the crash. It is set by:
- the sum of the body velocity's components (`$74E240 + $74E280 + $74E2C0`) beyond ±300 ft/s;
- S = int(S/2 + (Fx + Fy + Fz)/2) (`$751640`, the body's total force from `$703420`: both
  wheels, gravity and drag) beyond ±`$7515E0`, which is 10 × input word 19 (`$794130`): 5200 in
  every logged run, so 52,000 lb. Each axle bears at most the car's weight (3,525 lb) and its
  tire at most μ times that, so the sum stays under about 25,000 lb: no landing reaches it;
- the yaw rate `$74E200` beyond ±10 rad/s;
- both wheels on surface 7;
- the scenery collision `$7099C0` (an impact beyond ±2400 at `$70CD40`) and the 68010's
  collision request at `$7251B0` (against `$751080`).

`$751600` (S off its own running average `$751CB0` by more than `$751620` = 20,000, or a
collision under the crash limits) is another flag, not identified (perhaps the thump), not a crash. There is no landing test: the arcade
crashes no landing on the road, however fast it comes down.
