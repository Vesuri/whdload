# Arcade-like handling for the Amiga version: plan (2026-10-20)

Goal: make the Amiga car feel closer to the arcade car. Bit-exact emulation is not a goal.
The plan has two parts. First, find out what the arcade model does, with as little reverse
engineering as possible. Second, use that to replace the Amiga steering and skid behaviour.

## What is already known

From public sources:
- Max Behensky wrote the arcade car model together with Doug Milliken, co-author of
  *Race Car Vehicle Dynamics*. Milliken was credited as a "test driver".
- Jed Margolin's page says: "The TMS34010 does not have floating point, so Max could only
  model the car as having two wheels." That is a bicycle model. Race Drivin' moved the same
  C code to a DSP32C and used four wheels.
- Margolin also says the model "smoothly and dynamically changes depending on the mode",
  that is, it behaves differently at low and high speed.
- The model covers the engine, transmission, springs, shock absorbers and tires, and it
  drives the force-feedback wheel.

From the ROMs (see ARCADE_ROMS.md):
- The MSP code is TI C with software doubles and a variable, clamped time step.
- Its constants are recognisable as plain decimals. Examples: 0.0118125, 0.1125, 1.95,
  3.25 and 7.5, plus integers such as 104, 59 and 62.
- The init data has a table that looks like gear ratios: -6.4, 0, 6.4, 3.7, 3.25, 1.95 at
  `$779FC0`. It also has a 9-entry curve at `$77E900` running from 2.5e-6 to 2.03.
- Neither the table nor the curve has been confirmed. The scan is in
  `tmp/arcade/msp/consts*.txt`.
- Correction from step D: these were IEEE readings of doubles that have no hidden bit. The
  real values are 0.004, 0.05, 0.95, 1.25, 3.5, 40, 27 and 30; the gear ratios are −2.4, 0,
  2.4, 1.7, 1.25 and 0.95; the "curve" is part of a sine table.

So the concept is the textbook two-wheel model. We do not need to rediscover the equations.
We need the parameters, the tire curve shape, the low-speed mode switch, and above all
numbers for how the car feels.

From the Amiga version (PHYSICS_ACCURACY.md):
- The model is kinematic. Steering turns the heading at a rate that is halved above 20 MPH
  when the steering force is high.
- A skid is a yes/no event above 70 MPH. It sets a spin of 3.5 × half-steer and freezes the
  movement vector.
- The spin decays by 9/10 every 8-field step. Countersteer does nothing.
- The Phantom records 12-byte poses, and the replay ring stores snapshots. Neither replays
  inputs through the physics, so changing the model does not desync them.

## Part 1: find out what the arcade model does

Stop as soon as there is enough to tune the Amiga model. Steps 1 and 2 probably suffice.

### Step 1: label the result block (about half a day)

Work out which of the 0x86 result words are position, heading, speed, yaw rate and the
skid indicators. There are two ways to do it:
- **Static:** follow the result words in the 68010 code to the speedometer, the tachometer,
  the camera pose sent to the ADSP and GSP, and the tire screech sound. Ghidra already has
  `$18704` copying the block into game state.
- **Dynamic:** in MAME, drive straight and then turn, and see which words change and how.

### Step 2: measure the feel in MAME, headless (about a day)

The user does not need to drive. MAME runs without a window and owns its PID.

Setup:
- A Lua autoboot script inserts a coin, starts a game, picks automatic or manual, and saves
  a state on the start line.
- Each manoeuvre starts by loading that state. This keeps runs short, so the car does not
  reach scenery or trigger the off-road reset.
- Inputs come from a read tap on the ADC data port, which returns scripted wheel, gas and
  brake values.
- Every MSP frame logs the input block, the result block and the 68010 tick counter.

Manoeuvres:

| Manoeuvre | Measures |
|---|---|
| Full throttle in each gear, then coast-down | acceleration, top speed per gear, drag |
| Braking from 60 and 100 MPH | deceleration, lock-up |
| Steady steering at 30/60/90 MPH, several angles | lateral grip limit, understeer as speed rises |
| Step steer | yaw response time and overshoot |
| Lift off or brake mid-corner; power on mid-corner | whether the rear steps out (weight transfer) |
| Start a slide, then countersteer or hold | whether and how fast a slide recovers |
| Full lock at walking pace | the low-speed mode and its turning circle |

Output: a feel table and plots. The same manoeuvres go through the Amiga harness, using the
existing input fixtures and motion captures, so the two cars can be compared side by side.
This step also settles the open question about the time-step units.

### Step 3: read the code only where step 2 leaves questions (1–2 days, optional)

Do not write a decompiler. Instead, produce a trace that shows each float operation with its
real values:
- Put MAME breakpoints on the eight float library entries. For one frame, log the caller PC
  and the raw operands from the A14 stack, then decode them in Python.
- Each call site then reads like `72F5A0: 0.42 * 3120 = 1310`. Combined with
  `msp_code.dis`, the formulas become legible.

Read only what step 2 could not answer:
- **Tire force curve:** past the peak, does the force drop off or stay flat? This decides
  how slides start and end.
- **Weight transfer:** how front and rear grip shift under braking and throttle.
- **Low-speed mode:** where it switches and how it blends.
- **Engine:** the torque curve and the gear ratios.

Leave these out: suspension and vertical motion, force feedback, track contact, the exact
integrator.

## Part 2: use it on the Amiga

### The idea

Replace only the steering and skid logic (native `$b35e` steering and the `$b62a` spin decay)
with a small fixed-point two-wheel model. The native engine, position integration, track
contact and collisions stay as they are.

The Amiga already keeps the heading separate from the movement vector, which it holds during
a skid. A bicycle model only needs to keep them separate all the time:

- **State:** heading (existing), movement direction (existing), plus yaw rate r and sideslip
  β. Forward speed u comes from the native engine.
- **Each tick:**
  - Slip angles: α_f = β + a·r/u − δ and α_r = β − b·r/u.
  - Each slip angle goes through a saturating tire curve. Its peak is μ·N, with N shifted
    front to rear by the native engine's acceleration or braking. This is where lift-off and
    brake oversteer come from.
  - Integrate r and β. The heading advances by r·dt, and the movement direction is
    heading + β.
- **Low speed:** below a few MPH, blend into the kinematic turn ψ̇ = u·δ/L, as the arcade
  does. This also avoids dividing by u near zero.
  Step D/E: the arcade has no blend. Its tire's lateral spring and relaxation length give the
  kinematic turn by themselves, and the step E model keeps them (see step E).
- **Surfaces:** off-road classification lowers μ. With no wheel contact there are no tire
  forces. Code that forces the angles on the loop and the jumps must also reset r and β.

What this gives that the Amiga lacks:
- Progressive grip.
- Slides that grow and shrink continuously.
- Countersteer and throttle that actually affect a slide.
- Weight-transfer oversteer.

The skid flag the rest of the game reads (screech sound, other checks) would become a
threshold on |β| or on the rear slip.

### How to build it

- **Fixed tick:** a two-wheel model is not stable at the native 8-field step, so run it once
  per field. Use the enhanced motion path's elapsed-field loop, following AmigaXDev's
  fixed-time-simulation playbook. That makes it independent of frame rate on every CPU.
- **Cost:** each tick needs a few dozen 16.16 multiplies and two divides. The cost should be
  small, but it must be measured on the A500 before anyone claims so.
- **Tuning:** fit the parameters to step 2's feel table, scaled to Amiga units and the mouse
  steering range of ±16. Mouse input is analogue enough for this.
  Step E: the arcade's own parameters already fit. Steering must use raw mouse X (±320
  counts), since ±16 cannot express small steering at speed.
- **Option:** keep it behind its own option setting, so the original handling and the current
  enhanced build remain available. G2: a third CUSTOM1 value. Ship it as a separate PR, not inside PR 29.
- **Validation:** step 2's manoeuvres in the Amiga harness should land near the arcade
  numbers. Also check the jump, the loop, crash and recovery, the replay and the Phantom.
  The user's own driving is the final judge.

### Later, if wanted

- Compare the engine and gear performance with the arcade and adjust the native tables.
- That is a separate change from the handling model.

## Steps (option C, approved 2026-10-20)

Every step names its output and when it counts as done. The arcade work lives in ignored
`tmp/arcade/`. MAME always runs headless, with its own config, nvram and state
directories, an owned PID and a time limit.

### A. Arcade harness (MAME, headless): done 2026-10-20

Details are in ARCADE_ROMS.md under "MAME harness". MAME's save states cannot be used (the driver
saves none of its own state), so every run boots from power-on with a calibrated pristine EEPROM.
That takes about 3 s of wall time and is deterministic. The start point is the car idling on the
start line at script time 24.5 s.

- **A1 Sandbox run.** Boot `harddriv` with `-video none -sound none -nothrottle`, private
  directories and `-seconds_to_run`.
  Done when it reaches attract mode, a snapshot shows the expected screen, and MAME exits
  cleanly.
- **A2 Get into a race.** A Lua script presses Coin1, turns the Key (START1) and selects the
  automatic transmission, then saves state `start`.
  Done when loading `start` puts the car on the start line at speed 0.
- **A3 Control the inputs.** Drive the inputs from a per-frame schedule: wheel `12BADC.0`
  (0x010..0xff0), gas `8BADC.0`, brake `12BADC.1`, clutch `8BADC.1` and shifter
  `8BADC.3/4`. Use Lua `set_value`, or a read tap on the ADC if that fails.
  Done when the input block at `$FF8ECC` shows the commanded values.
- **A4 Logger.** At every MSP result, record the emulated time, the 244 Hz tick, the input
  block and the 0x86-word result block, written as JSON.
  Done when two runs from `start` with the same schedule give identical logs.

### B. Label the arcade state: done 2026-10-20

Details are in ARCADE_ROMS.md under "Result block".
- **Labelled fields:** the rotation matrix, position, world velocity, angular rates, speed, RPM,
  per-gear values, force-feedback torque, tire squeal, off-road flags and gauges.
- **Time step:** dt is model time computed from the real 244 Hz tick, so measuring against
  emulated time is valid.
- **Speed:** MPH = `$8DEA` / 4.07 (needle, ±3%), which makes one foot about 39.7 world units.
  Step D found the exact factors: `$8DEA` is 4 per model MPH and one foot is 40 units.
- **Conversions:** `tools/hdstate.py` converts log rows to heading, sideslip, yaw rate,
  lateral and longitudinal g, MPH and gear.

### C. Arcade feel measurements: done 2026-10-20

Details, the feel table and what it means for step E are in ARCADE_ROMS.md under "Feel
measurements".
- **Test ground:** the manoeuvres run on the flat grass behind and to the left of the start line,
  with the grass made into road. A write tap on the MSP's per-wheel surface types does that, and
  it also stops the off-road countdown.
- **Manoeuvres:** C1a–C1g are 25 plans in `plans/c1*.lua`. `tools/mame/c_runs.sh` runs them all
  in about 80 s, using closed-loop speed and heading control.
- **C2:** `tools/feel.py report` produces 231 metrics and SVG plots.
  - 221 metrics repeat within 5% (or a small absolute floor) when every manoeuvre is shifted by
    0.37 s.
  - The rest were run at seven phase shifts and are given as medians and ranges. Seven are
    timing details of small steering steps, limited by the ±20 jitter of the steering word.
    Three are braking in a corner at the grip limit, which is a genuine tipping point.
- **Main findings:**
  - textbook understeer, with a characteristic speed of about 70 MPH
  - about 1.08 g of grip at every speed, flat past the limit
  - a fast yaw response, with overshoot growing from about 10% at 30 MPH to 40–55% at 90 MPH
  - weight transfer: braking in a corner rotates the car, throttle gives understeer
  - full braking locks the wheels
  - steering alone never starts a lasting slide
- **Step D:** at the time, C seemed to answer what D was planned for. D was done anyway and
  explains every finding above.

### D. Code reading: done 2026-10-20

Details are in ARCADE_ROMS.md under "MSP vehicle model".
- **D1 Value trace.** Read taps on the float library's entries and exits log every operation
  with its caller, operands and result (`tools/mame/ftrace.lua`, `plans/d1_trace.lua`).
  - `tools/ftrace.py` prints a frame next to the lifted code (`tools/msp_lift.py`).
  - The trace showed that the MSP's doubles have no hidden bit: 0.M × 2^(e−1023).
    4,679 of 4,690 logged operations match exactly; the rest are add/subtract cancellations.
    Every constant read before was off, and the "unresolved internal units" are feet and
    seconds.
- **D2 The model.** A two-wheel car on pitch suspension. Each wheel has spring and damper
  suspension, a Fiala brush tire with a relaxation-length lag, a friction circle, and its own
  spin, so it can spin up or lock.
  - Rear cornering stiffness and μ are higher than the front's, so the car understeers.
  - Brakes act on the front only; drive goes to the rear only.
  - There is no low-speed switch: the tire's lateral spring gives the kinematic turn.
  - Every parameter has been read: mass, inertia, geometry, springs, tires, steering, drag,
    brakes, engine table, clutch, gears.
  - Together they reproduce C's measurements: characteristic speed, low-speed curvature,
    turning circle, coast-down, shift points.
- **Exact units:**
  - model time is 0.004 s per 4.096 ms tick, so it runs 2.3% slow;
  - `$8DEA` is 4 per model MPH;
  - positions are 40 per foot.
  `hdstate.py` now uses these, and C's tables moved by at most 1%.
- Each open question from C has an answer.

### E. Reference model in Python: done 2026-10-21

**The user's tolerance (E2):** "anything resembling more of a car than the original Amiga
code is an improvement, so it's close enough when it feels like driving a car and isn't too
taxing on the 68k." The 10% counts below are a guide, not a gate.

**Files** in `tools/arcade/`:
- `amiga_units.py`: E1, the conversions.
- `handling.py`: E2, the float model.
- `handling_fx.py`: E3, the 68000 twin. `handling_fx.py sweep` runs the overflow sweep.
- `handling_check.py ROOT [--dt S|arcade] [--model lag|static|pitch|fixed] [--steer mouse|native] [--vs M]`:
  - replays each C run in ROOT (`tmp/arcade/mame/c/base`) through a model, using the arcade's
    steering word, brake pedal and ground speed;
  - measures the result with feel.py's own code;
  - compares it with the arcade, or with model M within 5%.
- `feel.py`: `load()` accepts a list of states, and `analyse(root, get)` takes a run loader.

**E1 units** (`amiga_units.py`, from the native code):

| Quantity | Amiga | Mapping |
|---|---|---|
| Time | PAL field 0.02 s; native step 8 fields (f0 = 6.25/s) | model step = 1 field = 0.02 × 0.9765625 = 5/256 arcade model s |
| Heading | G($994A), quarter degrees, 1440 per turn, wrapped ±720 (`$b44e`); `$b1d0` adds the steer value per step | 229.18 units per rad; 1 rad/s = 4.584 units per field |
| Speed | G($9928) word; each step moves the long position by 1.5·v (`$b512..$b592`), 8 long units per world unit | speedometer ≈ 0.28·v MPH; taking it as real MPH: v = 1 is 0.4107 ft/s, a world unit is 0.3504 ft |
| Steering | mouse X G($95FA), accumulated per frame, clamped 0..639, centre 320 (`$024c`); native steer (X−320)/20, ±16 | δ = 35° × (X−320)/320: 0.109° per count = 12.8 arcade steer words |

- **Scale check:** at the native full-steer rate (8 units/step above about 23 MPH), 100 MPH
  gives 1.0 g against the arcade's 1.08 g. The native low-speed turn (16 units/step) gives
  16.8 ft at 5 MPH against the arcade's 15.1 ft. So the Amiga roads suit the MPH-consistent
  scale.
- **Native steering resolution is too coarse:** with (X−320)/20, C1d's small 90 MPH step
  (126 words, about 10 counts) truncates to zero. The model reads raw mouse X.
- **Native longitudinal forces exceed the arcade tires** (for G). In game time, 0–60 MPH
  averages 0.85 g and full braking is 1.44 g (velocity −18 per step from the brake term,
  GAME_TIME.md). The arcade's front tire locks above about 0.75 g, and the rear spins above
  about 0.8 g.
  - G must map the native drive and brake terms into tire forces, for example with a brake
    ramp. The native engine already computes drive, brake, drag and slope separately.
  - The model clamps its force input at ±8,000 lb.

**E2 float model** (`handling.py`): D's parameters, unchanged.
- **State:** lateral velocity v, yaw rate r, tire deflections y_f and y_r, wheel speed while
  sliding, and the load-transfer lag. Forward speed u is an input.
- **Tire, as `$710D30`:**
  - z = |α|/α_sl, with α = v/|u| (α = v when u = 0) and α_sl = 3μ'/C';
  - z ≥ 1: the patch sticks, Fy = k·y + c·ẏ with ẏ = −v, clamped to μ'N;
  - else secant = N·C'·(1 − z + z²/3). If |u|·k·dt < 0.5·secant, the lag runs:
    ẏ = −y·|u|·k/secant − v and Fy = k·y + c·ẏ. Otherwise the steady curve:
    Fy = μ'N·(1 − (1−z)³) and y = Fy/k;
  - friction circle μ' = √(μ² − (Fx/N)²).
- **Wheels:**
  - A torque whose 0.916 share reaches μN starts a slide.
  - While sliding, the force is μN against (u − ωr, v), and ω̇ = (T ∓ μN·r)/I_w.
  - A wheel that has only just started to lock pushes μN sideways. That is the arcade's
    brake-in-corner yaw spike (see ARCADE_ROMS.md, "Wheel spin").
- **Brake:** front only. The brake fade s(ω) is applied inside the model.
- **Load transfer:** ΔN = Fx·1.567/10, where Fx is the tires' total in body axes.
  - The arcade is quasi-static too: its pitch moment is about 0 in a slide.
  - **Chosen form, `lag`:** a 0.1 s first-order lag (dt/τ = 25/128). It smooths the Amiga's
    on/off brake and fits slightly better.
  - **`static`** is the plain formula; **`pitch`** is the arcade's springs and dampers.
- **Body:** v̇ = ΣFy/m − u·r, ṙ = (a·Fy_f − b·Fy_r)/I, explicit Euler. The front force is
  rotated by δ.
- **Range guards:** |r| ≤ 12 rad/s, |v| ≤ 256 ft/s, |y| ≤ 4 ft, wheel slip ≤ 128 ft/s, force
  input ±8,000 lb. They act only in runaway cases, for example a torque held while standing
  still.
- **Replay lesson:** the tire Fx must be in body axes, m·(V̇ − a_y·sin β)/cos β + drag. Using
  m·V̇ was off by about 200 lb in slides and made the slide peaks 40% too big.

**E2 results**, within 10% or C's repeat floor:

| Run | C1c | C1d | C1e | C1f | C1g |
|---|---|---|---|---|---|
| Arcade step, static | 21/21 | 52/54 | 32/36 | 45/46 | 35/35 |
| 1 field (20 ms), lag, mouse resolution | 21/21 | 51/54 | 34/36 | 44/46 | 34/35 |
| 2 fields (40 ms), lag | 21/21 | 40/54 | 32/36 | 27/46 | 35/35 |

- **One field is good; two fields are not:** response times grow by about 45 ms and slides
  overshoot. The model runs every field.
- **The remaining misses at one field:**
  - timing details of the small 90 MPH step, which spread between arcade runs too;
  - the brake tipping point, where the arcade's ±50 lb load jitter decides;
  - the 90 MPH countersteer overshoot (6.0° against 5.2°);
  - the 90 MPH full-brake yaw peak (8.9 against 10.5 °/s);
  - the 25% lock sideslip at 5 MPH (−4.3° against −3.8°).
- **The car-like behaviour is all there:**
  - understeer;
  - a flat 1.08 g limit;
  - yaw overshoot growing with speed;
  - lift-off tightening the line and power-on widening it;
  - braking in a corner turning the car in;
  - slides that recover by themselves, and countersteer that works;
  - full braking ploughing on;
  - the kinematic turn at low speed.

**E3 twin** (`handling_fx.py`): the same algorithm in 68000 integer arithmetic.
- **Semantics:**
  - MULS and MULU take word operands;
  - DIVS and DIVU divide a long by a word, and the quotient must fit a word;
  - ASR rounds down;
  - longs are checked at every site.
- **Formats** are Q formats per quantity:
  - speeds Q6 words, with states as Q22 longs;
  - r and y Q11 words, with states as Q27 longs;
  - loads Q2; forces in lb; μ, z, sin and cos Q14;
  - heading a Q16 long in G($994A) units.
- **Constant step:** dt = 5/256 is folded into the constants.
- **Inputs:** native velocity eighths, mouse X − 320, the tires' longitudinal force, and the
  brake torque.
- **Per axle:** one DIVU for z, one for the lag rate (only on the lag branch), and one for
  Fx/(μN), which indexes a 257-entry √(1 − x²) table with interpolation. A sliding wheel adds
  an integer square root and two DIVS. sin and cos δ come from a series.
- **Tracks E2:** `handling_check.py ROOT --model fixed --vs lag --steer mouse` puts all 192
  handling metrics within 5%. On the 21 handling runs:
  - the largest yaw-rate difference is 0.63 °/s against peaks of 47–76 °/s, RMS about
    0.1 °/s;
  - the largest sideslip difference above 5 ft/s is 0.28°.

  Against the arcade it scores the same as the float model: 21/21, 51/54, 34/36, 43/46, 35/35.
- **No overflow** across the input range: `handling_fx.py sweep 200` runs 550 sequences of
  30 s:
  - every corner of the input box held, covering 7 speeds (reversing included), 5 steering
    positions, 5 force levels (±20,000 lb included, beyond the clamp) and brake on and off;
  - 200 random jumping sequences.

  The sweep prints the peak of every value with its bit count; the tightest are the slip
  divisor (14.5 of 15 bits) and the r and v states at their guards.
- **Cost, an estimate from instruction timings, not a measurement:** normal driving (40,549
  replayed fields) needs 38 MULS, 15 MULU and 4.6 DIVU per field.
  - At the 68000's worst-case 70 cycles per multiply and 140 per DIVU, that is about 4,400
    cycles of arithmetic per field, 3% of an A500's 142,000.
  - With the moves, shifts and branches around them it is perhaps twice that.
  - H2 measures it.
  - **Ways to cut it:** multiply by constants with shifts and adds; take sin and cos δ from a
    table, or only when the mouse moves; skip the model while the car stands still.

### F. Amiga baseline: done 2026-10-21

C's manoeuvres ran on the A500 profile in both builds, and the tables below put them next to
the arcade's (ARCADE_ROMS.md, "Feel table"). `amiga_feel.py report` prints all of C's metrics
with one column per Amiga matrix; the last report is in ignored `tmp/prof/feel-report.md`.

**Files:**
- `tools/feel_fixture.s`: the in-game driver, built only into private VERIFY_DRIVE slaves. Its
  header has the details.
  - At race entry it places the car on the test ground.
  - It runs a plan of timed entries: cruise, heading hold, mouse steps and ramps, buttons, and
    waits.
  - It feeds the native input like a player.
  - It logs an 80-byte record every field, and the complete pose at the end of every physics
    pass.
- `tools/build_feel.py [--slow] [NAME...]`: 23 of C's 25 plans translated through E1 (all but
  the stick and half-brake runs), plus six Amiga-only plans (below). It builds one slave per plan in `tmp/build/`.
- `tools/capture_feel.py OUT --plan NAME [--custom1 0|1] [--slow N]`: one run in the FS-UAE
  harness.
  - gdb stops only at the fixture's flush routines, once per 32 entries.
  - It writes nothing to the guest.
- `tools/run_feel.py ROOT --custom1 0|1 [--slow N] [--jobs N]`: a whole matrix, four emulators at
  a time, each under its own INSTANCE.
  - The enhanced matrix takes about 9 minutes of wall time.
  - The original takes about 4.
- `tools/arcade/amiga_feel.py`: converts the records into `hdstate.py` states and measures
  them with feel.py's own code (`report`, `trace`).

**Test ground:** the open grass north of the start straight. The car starts at
(x, z) = (23,500, 29,500), facing heading 360 (+x).
- **Grass as road**, like C's road-everywhere tap. The fixture builds patch two places:
  - `$b762` (nop): the engine never takes its grass branch, so there is road drag and no
    off-road throttle loss;
  - `$b146` (bra): the off-road deadline never starts.

  Contact stays the native flat-ground contact.
- **Near the course:** far from the road sections it searches, the road cursor takes garbage
  and the game crashes (G1). So a run ends if the car leaves x 22,800–47,000, z 26,800–35,500.
  None of the 58 runs did.

**Controls:** only the native ones are used.
- **Steering:** mouse X. C's wheel offsets become counts × 320/2032 (E1), and the arcade steer
  word is counts × 12.8.
- **Gas:** button word 4 raises the throttle G($991c) by 2 per native step, and 1 lowers it by
  2. Opening it fully takes about 8 s of game time.
- **Brake:** button word 5. It brakes and lowers the throttle. The brake is on or off, so C1b's
  half pedal and C1a's stick runs have no Amiga equivalent.
- **Mouse pedals** (H3 round 8, CUSTOM1 = 2): the right button is the gas and the left the
  brake, each moving 0.1 of its travel per field; the fixtures publish them in
  `_handling_pad`.
- **Closed loop:** a cruise and a heading hold replace C's controllers.
  - The cruise moves the throttle with buttons 4 and 1, and brakes when more than 3 MPH too
    fast.
  - The heading hold steers by at most 3 native units.

**Builds:**
- **Enhanced** (CUSTOM1=1, the release). On the test ground it makes a physics pass every 2.5–3.2
  fields, scaled by T, so game time runs at the native rate.
- **Original** (CUSTOM1=0) takes one native step per drawn frame.
  - The test ground draws so little that the A500 draws a frame every 2.8 fields, 2.9 times the
    native rate.
  - So the original matrix runs with VERIFY_SLOW and CUSTOM4=5, which adds five fields to every
    frame. That gives 6.5–7.1 passes/s, 4–14% faster than the native 6.25.
  - Its real-time values are inflated by that much. Speeds and rates scale with the pass rate,
    and lateral g with its square.
  - Its C1g runs at 8 MPH: in first gear its velocity jumps between about 9 and 28 (2.5 and
    7.8 MPH).
- **Same physics:** per native step the enhanced build reproduces the original.
  - About 30 steps into C1a the velocity is 306 against 308, with the same gear changes.
  - Both top out at velocity 446.

  The differences between the two Amiga columns come from the original's pass rate.

**Timing:** position and heading change only at the passes.
- `amiga_feel.py` interpolates between the poses captured at the end of each pass.
  - Enhanced poses are timed by the fields the physics has consumed.
  - The original's poses are timed by the field in which the pass ended.
- Speed is the ground speed over ±0.1 s. The original uses ±0.3 s, because its one step per
  frame stutters over 0.1 s.

**Amiga-only runs:** E1's mapping never reaches the native limits, so six runs go to them:
- `c1ex-lim-*`: C1e at native steer 6 (wheel 762, 120 counts). That is the largest steer that
  does not halve the turn at 60 MPH.
- `c1fx-90-*`: C1f at 90 MPH with native steer 8 (wheel 1016, 160 counts), which starts the
  native skid.

The tables use the arcade's conventions: real time at E1's scale, left turns, and nose-in angle
as defined in ARCADE_ROMS.md.

**Straight line (C1a, C1b)**

| Metric | Arcade | Amiga enhanced | Amiga original |
|---|---|---|---|
| 0–30 / 0–60 / 0–100 MPH, automatic | 3.2 / 6.3 / 13.3 s | 1.1 / 2.5 / 6.9 s | 1.0 / 2.2 / 4.5 s |
| Launch, first second | 0.32 g | 1.21 g | 1.08 g |
| Automatic upshifts | 48, 67, 92 MPH at 5,750 rpm | 50, 64, 89 MPH at 5,220 rpm | 52, 69, 100 MPH at 4,950–5,100 rpm |
| Top speed | 140 MPH after about 40 s | 125 MPH within 15 s | 142 MPH within 15 s (147 at the measurement window's peak) |
| Off the throttle in 4th, at 110 / 90 / 70 MPH (Amiga: button 1 held) | 0.18 / 0.15 / 0.11 g | 0.34 / 0.47 / 0.60 g | 0.56 / 0.72 / 0.77 g |
| Full braking from 60 MPH (original: from 70) | 0.87 g; 143 ft, 4.5 s | 0.45 g; 217 ft, 5.3 s | 0.56 g; 221 ft, 4.9 s |
| Full braking from 100 MPH (original: from 110) | 0.85 g; 390 ft, 6.6 s | 0.48 g; 593 ft, 8.8 s | 0.63 g; 580 ft, 7.8 s |

The cruise holds the native velocity for 60 and 100 MPH, so the original's pass rate starts its
stops at about 70 and 110 real MPH.

**Steady cornering (C1c: constant speed, steering ramped over 16 s)**

| Metric, at 30 / 60 / 90 MPH | Arcade | Amiga enhanced | Amiga original |
|---|---|---|---|
| Yaw gain below 0.4 g (°/s per 1000 steer words) | 31.7 / 43.1 / 45.4 | 5.6 / 5.2 / 4.9 | 6.3 / 5.9 / 5.3 |
| Path curvature gain (1/1000 ft per 1000 words) | 12.6 / 8.6 / 6.0 | 2.2 / 1.0 / 0.6 | 2.5 / 1.2 / 0.7 |
| Lateral at the end of C's ramp | 1.08 / 1.08 / 1.06 g | 0.26 / 0.30 / 0.33 g | 0.34 / 0.39 / 0.43 g |
| Nose-in angle at the end of the ramp | −1.9° / 1.8° / 2.4° | 0.2° / 0.2° / 0.1° | 0.7° / 0.5° / 0.4° |

C's ramps end at 50, 30 and 20% lock, which is native steer 8, 4 and 3. The arcade is past its
limit there; the Amiga is not.

**Step steer (C1d)**

| Run | Arcade: steer word, steady yaw, lateral | Amiga: steer word, native steer | Enhanced: yaw, lateral | Original: yaw, lateral |
|---|---|---|---|---|
| 30 MPH small | 470; 14.5 °/s; 0.34 g | 499; 1 | 1.4 °/s; 0.03 g | 1.6 °/s; 0.04 g |
| 30 MPH large | 1,290; 35.8 °/s; 0.84 g | 1,306; 5 | 7.5 °/s; 0.18 g | 7.2 °/s; 0.18 g |
| 60 MPH small | 180; 7.5 °/s; 0.35 g | 218; 0 | 0 | 0 |
| 60 MPH large | 490; 16.9 °/s; 0.79 g | 525; 2 | 2.9 °/s; 0.14 g | 3.0 °/s; 0.16 g |
| 90 MPH small | 130; 5.1 °/s; 0.36 g | 166; 0 | 0 | 0 |
| 90 MPH large | 450; 11.9 °/s; 0.84 g | 474; 1 | 1.4 °/s; 0.10 g | 1.7 °/s; 0.14 g |

- **Arcade response:** the yaw reaches 63% in 34–108 ms and overshoots by 7–55%.
- **Amiga response:** the native turn has no dynamics. Each pass adds the steer value to the
  heading, so the yaw rate steps at the next pass: within 2–4 fields in the enhanced build here,
  and about 7 fields in the original.
- **Not comparable:** the report also prints Amiga response times (−40 to 122 ms) and overshoots
  (up to 119%). They measure the 0.25° heading steps and the pass spacing, not a response.

**In a corner at 60 MPH (C1e: an action held for 3 s)**

E1 maps both of C's corners (wheel 180 and 240, so 28 and 38 counts) to native steer 1. That is
1.5–1.7 °/s and 0.07 g, against the arcade's 13 and 16 °/s. The Amiga rows below use the limit
corner instead: native steer 6, 9.4 °/s and 0.45 g.

| Action, after 2 s | Arcade, 0.7 g | Amiga enhanced, steer 6 | Amiga original, steer 6 |
|---|---|---|---|
| Lift off | 52.6 MPH; yaw +7% | 41.3 MPH; yaw −0.5% | 43.5 MPH; +3% |
| Brake (arcade: amount 1500) | 27.1 MPH; yaw spike +133%, then −19% | 28.2 MPH; yaw −1.7% | 28.5 MPH; +3% |
| Full throttle | 73.4 MPH; yaw −17% | 62.8 MPH; yaw −49% | 74.6 MPH; −48% |

- **Speed alone:** the Amiga's yaw rate ignores lift and brake. Braking to 28 MPH more than
  halves the radius at the same yaw rate.
- **Throttle:** as the speed rises, |steer|·(v+1) passes 1,300 and the native turn halves. It is
  a step, not understeer.
- **Nose-in angle:** it stays within 1.4°.

**Slides (C1f)**

| Metric | Arcade | Amiga enhanced | Amiga original |
|---|---|---|---|
| C's slide steering at 60 MPH (Amiga: 1,306 words, steer 5): peak nose-in angle and yaw | 4.7°; 34 °/s | 0.8°; 9.2 °/s | 1.3°; 8.9 °/s |
| The same at 90 MPH (1,203 words, steer 4) | 7.7°; 30 °/s | 0.5°; 7.8 °/s | 1.1°; 8.3 °/s |
| Steering held: heading change in 5 s, 60 / 90 MPH | 117° / 77° | 39° / 31° | 43° / 35° |
| Limit angle plus full brake, 60 MPH: peak yaw, speed lost in 5 s | 6.1 °/s; 32 MPH | 4.2 °/s; 41 MPH | 3.6 °/s; 49 MPH |
| The same at 90 MPH | 10.5 °/s; 33 MPH | 3.1 °/s; 45 MPH | 1.8 °/s; 56 MPH |

C's slide steering stays below the native skid threshold, so the Amiga simply turns.

**Native skid (Amiga only):** `c1fx-90`, steer 8 at 90 MPH.

| Metric | Amiga enhanced | Amiga original |
|---|---|---|
| Skid starts after | 0.16 s | 0.14 s |
| Steering held: peak nose-in angle and yaw | 32°; 25 °/s | 33°; 29 °/s |
| Speed | 90 → 45 MPH in 1.1 s | 90 → 46 MPH in 1.0 s |
| Released, or countersteered, after 1 s: settled after the action | 1.1 s, no overshoot | 0.9–1.0 s, overshoot ≤ 0.9° |

- **A scripted spin, not a slide:**
  - the movement vector freezes;
  - a spin of 14 heading units per step decays to zero;
  - the speed halves;
  - after 1.6–1.9 s the movement direction snaps to the heading.
- **Driver input:** release and countersteer do not shorten the skid. They only change how far
  the heading turns before the snap.
- **Repeats:** with the steering held, a new skid starts as the car speeds up again, 2.7–3.0 s
  in.

**Low speed (C1g)**

| Metric | Arcade | Amiga enhanced | Amiga original (8–10 MPH) |
|---|---|---|---|
| Path radius at 5 MPH: 25 / 50 / 75 / 100% lock | 64 / 32 / 21 / 14.9 ft | 69 / 36 / 24 / 18.1 ft | 113 / 58 / 38 / 29 ft |
| Yaw rate at those locks | 6.5 / 13.3 / 20.8 / 29.6 °/s | 6.3 / 12.6 / 18.8 / 25.0 °/s | 7.1 / 11.6 / 20.5 / 26.1 °/s |
| Nose-in angle at those locks | −3.8° / −9.2° / −13.5° / −18.7° | 0.1° / −0.9° / 1.9° / 1.7° | 0.4° / 0.2° / 2.1° / 2.5° |
| Full lock at 10 / 15 MPH | 15.7 ft at 0.46 g / 17.4 ft at 0.92 g | 35 ft at 0.21 g / 53 ft at 0.31 g | 35 ft / 53 ft |
| Full right lock at 5 MPH | 15.1 ft | 18.9 ft | 30.7 ft at 8.8 MPH |

**What F means for G:**
- **The native turn is kinematic.** The yaw rate is the steer value times a constant at every
  speed: 1.56 °/s per native unit, 25 °/s at full lock.
  - At speed the Amiga turns 6–9 times less per steer word than the arcade.
  - At low speed the radius grows with the speed instead of staying near 15–17 ft.
  - There is no sideslip outside the skid (at most 2.5°), no overshoot and no weight transfer.
- **The native limit is a rule.** Above 20 MPH, |steer|·(v+1) > 1,300 halves the turn. Since
  the lateral g is proportional to v times the steer value, that caps it at about 0.45 g of game
  time at every speed. The C1e limit runs measured 0.45 g at 60 MPH.
  - Full lock past the halving gives 8 units: 0.6 g at 60 MPH.
  - Above 70 MPH a force over 2,000 starts the scripted skid.
- **Resolution:** (X−320)/20 truncates C's small 60 and 90 MPH steps (14 and 10 counts) to
  nothing, and C1e's corners to steer 1. The model's raw mouse X (E1) removes that.
- **Longitudinal**, enhanced against arcade:
  - acceleration is 2–4 times harder (launch 1.21 g against 0.32);
  - lifting off slows the car about 2–5 times harder;
  - full braking is about half as strong (0.45–0.48 g against 0.85–0.87);
  - top speed is 125 MPH against 140.
- **Correction to E1:** E1's 1.44 g brake came from a brake term of 18 measured at low speed.
  From 60 MPH the velocity falls by 6–8 per native step, net of the closing throttle: about
  0.5–0.65 g.
- **Force mapping for G2:** G2 maps the native brake from these measured rates, not from E1's
  estimate. The native launch still exceeds what the arcade's rear tire takes (about 0.8 g).

**Caveats:**
- **Quantization:** headings are 0.25° steps, and the passes come every 2.5–3.2 fields
  (enhanced) or about 7 fields (original). Response times and overshoots below about 0.1 s are
  not measurable on the Amiga.
- **C1a** holds full throttle for 30 s, not C's 50; both builds reach top speed within 15 s.
- **The original's real-time values** are 4–14% fast (lateral g up to 29%) because of its pass
  rate. On a real A500 they depend on the scene.
- **Settle give-up:** the cruise waits at most 15 s to settle. The original's low speeds never
  settle, so they start on the give-up.
- **Speeds** are ground speeds at E1's scale (0.28 MPH per velocity unit). The speedometer comes
  from the RPM and lags while accelerating.

### G. Amiga implementation: done 2026-10-21

The model runs in the game when CUSTOM1 = 2. The source is on the local branch
`harddrivin-handling` (from `harddrivin`, not pushed):
- `HardDrivinHandling.s` (new) holds the model, the hooks and the boot fixture.
- `HardDrivinTime.s` includes the module and calls its installer.
- `HardDrivinPhase.s` gains three site labels (`equ *`, no code).
- `HardDrivinRelease.i` adds `VERIFY_HANDLING` to the release features.
- `HardDrivinHD.s` makes C1 the list `C1:L:Simulation:Original,Enhanced framerate,Enhanced
  framerate with arcade handling`. The ReadMe text waits for I1.

**G1 integration points.** Offsets are game code; G(x) is a4 + x − $10000.

| What | Where | At CUSTOM1 = 2 |
|---|---|---|
| Native steering `$b35e` | b362 skips it all during a crash (G($9606)); b36a–b38e integrate roll, pitch and the skid spin; b390 clears G($f790) and needs front contact (G($9910) & 3); b3a0–b44c steer value, halving, skid start, yaw; b44e–b4fe wrap the angles to ±720 and refresh sin/cos G($9448..$9452) | The enhanced build already defers b390 onward to `_phase_steering_continue`. The model's steps replace b394–b44c; the native tail b44e still runs |
| Yaw helper `$b1d0` | yaw += rate (×−3/2 when cos pitch < 0, upside down in the loop); pitch and roll get rate × sin terms | The model's whole heading units go through it, so slopes and the loop keep their native coupling. With 8 fields the enhanced Q16 path adds them exactly |
| Skid flag G($af31) | set b428; read b3fc, b50c (hold the movement vector), b61a (sound 4, spin decay, skid end, throttle × 7/8), b72e/b74a (drive halved), b7ac (drag doubled), $8a1a (replay record bit 15); cleared at crashes bcdc/bdba and resets 8850, 10900, 10b00, 10e80 | Never set. The replay bit ($8a1a) and the screech ($b61a, through `_audio_skid`'s pacing) follow the model's tyres |
| Turn halving G($f790) | set b3ec; b79a doubles the road drag; cleared b390, 10e84 | Stays clear, so there is no native turn drag (H) |
| Skid spin G($991a) | set b440, decayed b62a; cleared 59ae, 108d0, 117f4 | Stays 0 |
| Heading G($994a) | b1d0, the wrap at b456/b466; absolute writers 9106 (recovery), d92e (replay restore), 10a64 (recovered pose), 10d12 (race start), 1120a, 11394, 11596 | A heading the model did not leave resets it |
| Movement vector G($991e/$9920/$9922) | b512–b574: 1.5·v along heading and pitch, held in a skid; read by crash drift (bc62, bd40), the barrier bounce (bf88, reversed), landing (cc6c), recovery (10a98) | The published vector gets the model's sideways velocity, so drift and bounces follow the real motion |
| Position G($98fc/$9900/$9904) | longs, 8 per world unit; the words G($98f6..) are long >> 3 (b5fc) | Each steering call adds the sideways displacement to x and z, keeping a Q8 remainder |
| Wheel contact G($9910) | bit n = wheel height G($947e + 2n) < 4 (cabe–cb06); native steering tests bits 0–1 | Bits 0–1 load the front axle, bits 2–3 the rear. An axle in the air has no tyre forces |
| Mouse X G($95fa) | accumulated every VBL at $24c, clamped 0..639; the enhanced build latches it once per frame (`_dispatch_latch`) | A ring of 64 samples, one per field, written by the VBL hook |
| Speed and brake | G($9928) word with the phase solver's fraction PH_CURRENT_V; brake byte G($9911) | u from the eighths; the force from the speed change; the brake byte routes it to the front brake |
| Resets | `_motion_reset` callers: race start, recovery, collisions (bcc8, bda6), Phantom, replay end; the crash countdown skips steering | The model resets itself: on a heading it did not write; after a pass without steering (crash, start, replay); on a speed change over 40 eighths per field (collision) |
| Catch-up today | 68000: one pass of every elapsed field (`_dispatch_cpu_single`), no cap; 020+: substeps of up to 8 fields, nothing discarded; pause, options and replay stop the field count (TS_ACTIVE) | At most 50 model steps a frame; older fields are left out |
| Loop and jumps | no code forces the heading; b1d0's inverted factor handles the loop | In the air the yaw rate and the sideways velocity carry on |
| Attract demo, replay, Phantom | route playback and recorded poses; no player physics | Unaffected |

**G2 module** (`HardDrivinHandling.s`):
- **Option** (the user's choice of 2026-10-21):
  - C1 is a list with values 0, 1 and 2.
  - Any nonzero value still selects the enhanced simulation, so the existing tests of
    `_ct_ct1` and CUSTOM1=1 icons keep their meaning.
  - The handling installs only at 2.
- **Fixed step with catch-up** (the user's request of 2026-10-21):
  - One step is one PAL field (dt = 5/256 model s).
  - A frame that took n fields runs n steps inside the phase solver's chunks (the steering
    call of each chunk runs PH_DT steps), or all of the pass's fields on the fallback path.
  - Drawing never waits for the model.
- **`_handling_step`** is `handling_fx.FxCar.step` in 68000 code. Two additions are now in the
  twin as well, with defaults that leave E3 unchanged:
  - a contact mask (bit 0 front, bit 1 rear);
  - a peak flag per axle (past the curve's peak, or sliding).
- **Forward speed:** u = (eighths × 27559) >> 13. The eighths are PH_CURRENT_V >> 13 while the
  phase solver is current, otherwise G($9928) × 8, clamped to ±4160 (145 MPH, the twin's
  range).
- **Longitudinal force:** 295 lb per eighth gained per field, measured from the speed change
  since the previous steering call over that call's fields. This is the previous chunk's net
  force, held for this one.
  - **Initial limits** (H3 tunes them):
    - drive 2,115 lb (0.6 g);
    - braking with the brake on 2,470 lb (0.7 g); the front brake torque equals that force;
    - engine braking 705 lb (0.2 g), on the rear.
  - These keep a wheel from locking or spinning at the native engine's 0.5–1.2 g (F).
- **Mouse:** the VBL hook replaces `_time_vbl` at $50 and stores X in ring[TS_FIELDS].
  - A frame's first step reads index TS_PREVIOUS − TS_ELAPSED + 1, and each step reads the
    next index.
  - A sample the VBL has not stored yet is read live.
  - So step k uses the mouse at the end of its own field.
- **Heading:** the model's turn accumulates in Q16. Whole units go through b1d0 once per
  steering call, then the native tail wraps the angle and refreshes sin/cos.
- **Sideways motion:** each field adds v × 457 >> 8 (Q8 long units) along (cos ψ, −sin ψ),
  using the chunk's native sin/cos. That is the right of the heading, since a positive
  steer raises ψ.
- **Screech:** set by any step past a peak, or with a sliding wheel, above 18 MPH.
- **Far references:** the module lies beyond PC-relative reach of Time.s and the slave
  globals. The installer reaches them as `lea here(pc)` plus an assembler-constant
  difference, and keeps pointers for run time.
- **Cost:** not measured; H2 measures it.

**G3 hooks.** `_handling_install` installs all of them, and only when CUSTOM1 = 2:
- **game code:**
  - $50: the VBL ring, then `_time_vbl`;
  - $8a1a: the replay skid bit;
  - $b61a: the screech;
- **slave code** (JMP/JSR abs.l plus a NOP over two 4-byte instructions, then a cache flush):
  - `_phase_steering_site`: JMP `_handling_steer`;
  - `_phase_neutral_site`: always take the steering call, since the model turns with the
    mouse centred;
  - `_phase_vector_site`: the published movement vector.

With CUSTOM1 = 0 or 1, the code that runs after boot is exactly the release's.

**G4 tests:**
- **`tools/check_handling_step.py SLAVE LISTING`** loads the built slave's code hunk into
  Unicorn (68000 model) and calls `_handling_step` with a private state.
  - Inputs: E3's sweep (every corner of the input box held for 1,500 fields, 200 random
    sequences) plus contact changes.
  - Result: 562 sequences, 843,000 steps; the complete state equals the twin after every
    step.
  - Coverage: 652,347 of the steps had a sliding wheel and 708,861 were past a peak.
  - Time: about 21 s.
- **The boot fixture `VERIFY_HANDLING_MATH`**, in the HDSPIN02 style, runs 64 xorshift
  sequences of 250 steps at boot.
  - It publishes per sequence a checksum of the whole state after every step and the final
    v, r and ψ, after `HDHANDM1`.
  - `tools/check_handling_math.py NEW-RUN` boots it in FS-UAE (A500, CUSTOM1 = 2) and
    compares with the twin: all 64 match (`tmp/prof/g-handling-math-a500`).
  - `--unicorn SLAVE LISTING` checks the script's mirror quickly.
- **`tools/check_installed_code.py`** dumps the live game code at the title screen for the
  release (`harddrivin` at 1d36ff0, built from `git archive`) and the new slave, at
  CUSTOM1 = 0 and 1.
  - Every byte of the 77,116 is identical, except:
    - patch calls into the slave, each resolving to the same label (34 at CUSTOM1 = 0, 182
      at 1);
    - two addresses into the game itself (its entry JMP and the A4 setup). The larger slave
      loads the game $2000 lower, and these move with it.
  - Runs: `tmp/prof/g-installed-c0`, `g-installed-c1`.
- **F1's records:** byte-identity with step F's own records cannot hold for a slave that
  changes the option string. `tools/compare_feel_records.py OLD NEW` compares two matrices run by
  run (rec.bin and steps.bin).
  - **The new slave against F:** its CUSTOM1 = 1 and 0 matrices (`g-feel-a500-enhanced`,
    `g-feel-a500-original`) differ in every run, from about field 92 on.
    - A per-field sample catches a pass at another point (velocity 92 against F's mid-pass
      96).
    - Some frame boundaries move, and a few runs end a few fields apart.
    - The gear-table pointer G($9940) moves with the game.
  - **Bisection:** `build_feel.py --source DIR --pad N --prefix P` builds the fixture slaves from
    another source tree, padded to the new slaves' size. Each control was compared on c1c-60.
    - The release source padded: the same load address and F's sample at field 92. It still
      differs from F later (record 116), so layout alone moves records.
    - The same plus a ~100-cycle delay at install: identical to the padded control. A
      boot-time difference inside the slave does not matter.
    - The new source with `VERIFY_HANDLING` removed: identical to the new slave.
    - The release plus only the new C1 string: identical to the new slave. WHDLoad parses that
      string before the game starts.
  - **Result:** the release plus the new C1 string, padded to the same size (`g-opt-a500-*`),
    gives byte-identical records to the new slave in all 58 runs: 29 at CUSTOM1 = 1 and 29 at
    CUSTOM1 = 0 with CUSTOM4 = 5.
  - **So the handling module changes nothing at CUSTOM1 = 0 or 1.** The records move only with
    the option string and the slave's size, which any release with this option would share.
- **Smoke test, CUSTOM1 = 2** (`run_feel.py g-feel-a500-arcade --custom1 2`): all 29 plans ran to
  the end. The report (`tmp/prof/g-feel-report.md`) puts the arcade, the current build and the
  model side by side:

| Metric | Arcade | Enhanced | CUSTOM1 = 2 |
|---|---|---|---|
| Yaw gain at 30 / 60 / 90 MPH (°/s per 1000 words) | 31.7 / 43.1 / 45.4 | 5.6 / 5.2 / 4.9 | 30.9 / 42.5 / 43.8 |
| Lateral limit | 1.06–1.08 g | 0.26–0.33 g | 1.09–1.14 g |
| Step steer 60 MPH large: yaw, lateral, overshoot | 16.9 °/s, 0.79 g, 23% | 2.9 °/s, 0.14 g, 71% | 18.0 °/s, 0.86 g, 33% |
| Step steer: yaw at 63% | 43–97 ms | 13–117 ms | 50–136 ms |
| Slide at 60 MPH: sideslip, yaw, heading change in 5 s | 4.7°, 34 °/s, 117° | 0.8°, 9.2 °/s, 39° | 5.6°, 34 °/s, 117° |
| Countersteer at 60 MPH: settled after | 1.37 s | - | 1.34 s |
| Full lock at 5 / 10 / 15 MPH: radius | 14.9 / 15.7 / 17.4 ft | 18.1 / 35 / 53 ft | 15.4 / 16.2 / 18.3 ft |
| Sideslip at 5 MPH, full lock | −18.7° | 1.7° | −19.8° |
| C1e brake in the 0.7 g corner: largest yaw change in 1 s | +133% | +107% | +12% |
| C1e lift: largest yaw change, speed after 2 s | +13%, 52.6 MPH | +107%, 41.3 MPH | +25%, 41.2 MPH |
| C1f brake at 60 MPH: largest yaw | 6.1 °/s | 4.2 °/s | 20 °/s |

- **Agreement:** the in-game model reproduces E2's agreement with the arcade: the steady
  gains, the limit, the slides, the countersteer and the low-speed kinematic turn. The
  sideslip shows that the sideways motion reaches both the position and the movement vector.
- **Slower step responses:** partly measurement. The heading moves in 0.25° steps, and only
  at passes (every 2.5–3 fields here).
- **Open for H** (H1 analyses them):
  - The brake-in-corner spike is missing. The arcade's comes from a just-locking front
    wheel, and the 0.7 g brake limit never locks it.
  - Braking in a slide yaws three times as much as the arcade (20 against 6 °/s).
  - The native engine braking makes lift-off slow the car twice as hard.
  - There is no cornering drag, because the native turn drag (G($f790)) is gone and the
    model's induced drag is not fed back to the speed.

### H. Validation and tuning

- **H1** Re-run F1 with the new model and compare against the arcade targets.
- **H2** Laps that include:
  - the jump, the loop and the bridge
  - crash and recovery, replay and the Phantom
  - off-road driving
  - an A500 cost measurement
- **H3** The user drives it. Tune parameters, and repeat H1 and H2 after each change.

**Status (2026-10-22):** H1 and H2 done as far as automation goes. H3 round 1: the user's
first drive found runaway spins; fixed (below), and H1 and H2 repeated. H3 round 2: the second
drive found spins that never stop and roll-overs on slopes; fixed (below), H1 and H2
repeated. H3 round 3: braking took far too long; the brake now brakes at its limit, on the
front only (below), H1 and H2 repeated. H3 round 4: the stunt road's jump felt floaty and
crashed; the enhanced landing test now follows the native odds (below). H3 round 5: the
user's decisions: a native renderer crash fixed in every mode, and the arcade's take-off at
CUSTOM1 = 2 (below). H3 round 6: the arcade's flight, ballistic under 1 g, at CUSTOM1 = 2
(below). H3 round 7: the arcade's engine and gearbox replace the native engine at CUSTOM1 = 2
(below). H3 round 8: with mouse control the buttons are pedals at CUSTOM1 = 2 (below). H3
round 9: the course's real scale, 0.1791 ft per world unit, at CUSTOM1 = 2, and the arcade's
undoubled time limits (below). The rest of the arcade physics follows. The next drive waits
for the user. The H1 and H2 notes below describe G's module, whose release build was
byte-identical to G's: G's CUSTOM1 = 2 matrix (`g-feel-a500-arcade`, report
`tmp/prof/g-feel-report.md`) was H1's re-run.

**H1 open items, analysed:**
- **Braking: the arcade's brake-in-corner spike and its plough under full braking.** Both
  come from the front wheels locking, and the Amiga's on/off brake cannot do both:
  - The arcade's C1e brakes at half pedal (1500, 0.68 g in a straight line), right at the
    front wheels' lock point. The spike is a wheel that only just locks; E2 found it
    decided by ±50 lb of load jitter.
  - Its C1f brakes at full pedal, which locks the front wheels: the car ploughs on.
  - G passes the native braking force (0.45–0.57 g) as the brake torque, so the front
    wheels never lock.
  - `tools/arcade/brake_sim.py ROOT [--torque T] [--old]` replays G's brake runs
    through the twin with other mappings. Full pedal (4,653 lb ft, with the total force
    at most what locked wheels give, 2,604 lb, so the rear gets no torque) gives the C1f
    plough; torques near the lock point (2,500) give spikes from +197% to −101% and a
    44 °/s slide, depending on the run.
  - Full pedal in the game (`h1-brake-a500`, built from a trial of that mapping, since
    reverted; report `tmp/prof/h1-brake-report.md`):

| Metric | Arcade | G | Full pedal |
|---|---|---|---|
| C1e 0.7 g brake: largest yaw change in 1 s / after 2 s | +133% / −19% | +12% / −18% | −122% / −96% |
| C1e 0.9 g brake: the same | +83% / −14% | −29% / −12% | −124% / −95% |
| C1f brake at 60 / 90 MPH: largest yaw | 6.1 / 10.5 °/s | 20 / 12.5 °/s | 8.7 / 8.3 °/s |

  - **Kept G's mapping.** Full pedal matches C1f, but braking in a corner then stops the car
    turning altogether (−96% against the arcade's −19% two seconds in). G matches the
    arcade's half-pedal corner braking, which is close to the native car's own braking
    force. The C1f difference is the arcade's full pedal against the Amiga's weaker brake.
- **Engine braking** (lift at 60 MPH: 41 MPH after 2 s against the arcade's 52.6; coasting
  0.34–0.64 g against 0.11–0.20 g) is the native drivetrain, the same at CUSTOM1 = 0 and 1.
  The model already limits the engine braking it sees to 0.2 g, so the handling matches
  the arcade's lift-off behaviour (+25% against +13% yaw change). Only the speed loss
  differs. Changing it means changing the native engine at CUSTOM1 = 2: a question for H3.
- **Cornering drag:** the model's forces are not fed back to the speed. The front tyre's
  force along the car is about 0.06 g at 1 g of cornering at 60 MPH, and up to about
  0.3 g in a full-lock slide. The cruise control in C hides it, so no feel metric shows it.
  Feeding it back means changing the native velocity from the module: a question for H3.
  **H3 round 1 does this** (below): it turned out to be the cause of the runaway spins.

**H2 cost on the A500** (profiler traces of 500 fields; `capture_solver_profile.py` now takes
`--custom1 2`, `frame_budget.py` counts `_handling` as a module):

| Run (CUSTOM1 = 2) | Fields per frame | Frame | Model per frame | Model per field |
|---|---|---|---|---|
| `h2-cost-c1c60-c2`: C1c ramp at 60 MPH | 3.25 | 64.9 ms | 4.01 ms | 1.23 ms (8,760 cycles) |
| `h2-cost-brake-c2`: braking in a turn from 100 MPH (`h2-brake-turn`) | 3.09 | 62.0 ms | 3.90 ms | 1.26 ms (8,960 cycles) |
| `h2-cost-slide-c2`: C1f slide held at 60 MPH | 3.33 | 67.0 ms | 3.90 ms | 1.17 ms (8,300 cycles) |

- Per field: `_handling_axle` 0.51–0.58 ms (both axles), `_handling_step` 0.45–0.46 ms,
  `_handling_steer` 0.14 ms, `_handling_sync` 0.06 ms, `_handling_vector` 0.01 ms. The VBL
  ring hook adds 205 cycles (0.03 ms, from the trace).
- **About 6% of the A500**, as E3's estimate said (4,400 cycles of arithmetic, about twice
  that in all). A frame costs 1.2 ms more for every field it took, so at about 3 fields
  a frame the A500 draws about 6% fewer frames.
- The same C1c plan at CUSTOM1 = 1 (`h2-cost-c1c60-c1`) took 60.1 ms a frame at 2.99 fields.
  The two runs are not the same scene: the arcade car turns round, and the "wrong way"
  overlay costs about 2 ms a frame (`1058e`).
- **Ways to cut it** are E3's: shifts and adds for the constant multiplies, a table for sin
  and cos δ, and skipping the model when the car stands still. Each keeps the twin exact.

**H2 laps** (`build_feel.py lap-ROUTE`, `tools/lap_report.py`; runs in `tmp/prof/h2-laps-a500`,
report `report.txt`). `feel_fixture.s` gained a road follower (FE_FOLLOW):
- **The route:** pure pursuit along a route through the road sections' centres
  (`tmp/track-geometry.json`), every 50 units. The steering gain comes from the curvature to
  the aim point, scaled by the understeer step C measured.
- **The speed profile:** the route's cruise speed, 0.9 g on its corners and 0.35 g of
  braking ahead of them. The jump run-up and the loop get full throttle (the native
  throttle rises only 2% per native step).
- **Native rules:** the plans keep the native start and the native grass rules. Crashes,
  replays and recoveries run their course with the buttons released.
- **Seeded starts:** `lap-jump` and `lap-loop` start on the stunt road at 112 MPH, as the step
  4 probes seeded it. `lap-jump` keeps 70 units left of the centre line, where the probes'
  clear seed ran (a vehicle stands on the ramp's centre line). `lap-offroad` drives 350 units
  right of the main road.
- **The loop:** the driver holds the wheel straight through it. The loop's section centres
  move sideways as it spirals, and chasing them made the arcade car enter 17° off its axis
  and roll; it then lost contact and the native code threw it 1,500 units forward and
  1,200 up in one pass.
- The driver is for testing: it sees no traffic and does not race. Runs of its earlier
  versions are kept in `h2-laps-a500/old` and `v3`.

| Run (A500, final driver) | Result |
|---|---|
| `lap-main`, CUSTOM1 = 2 | **The whole main road**: 12,650 fields (253 s with one replay), 78 MPH on average, top 90. Flights of 30–44 fields over the bridge crest and four humps at 82–88 MPH, all landing. Two checkpoint bonuses. One crash on the first bridge approach (field 652, straight at 83 MPH on the centre line, velocity to 0 at once: something in the lane), then the countdown, the full replay and recovery |
| `lap-offroad`, CUSTOM1 = 2 and 1 | 350 units right of the road at 40 MPH on the grass, native rules: off-road recoveries every 18–20 s in both modes, and nothing else |
| `lap-stunt`, CUSTOM1 = 2 | The fork on the bridge, the drop (flights of 33–41 fields, landing at 86–93 MPH), the jump six times at 89–104 MPH: every landing short (stunt 22–24) and a crash. Never reached the loop |
| `lap-jump`, CUSTOM1 = 2 | Seven jumps at 94–99 MPH, every landing short (stunt 22–23) and a crash. An earlier version of the driver landed once at 98 MPH and drove on to the loop |
| `lap-jump`, CUSTOM1 = 1 | Never reaches the lip: crashes on the ramp at stunt 18 in its lane |
| `lap-loop`, CUSTOM1 = 2 | Four entries at 116–118 MPH, 1–6° off the loop's axis (the approach still steers): the car fell off every time |
| `lap-loop`, CUSTOM1 = 1 | One entry on the axis at 116 MPH: down the far side |

- **No hang and no game crash** across the final runs: 35 crashes, 33 full replays (about
  740 fields each), 55 recoveries (crashes and off-road), flights and falls from the loop.
  Every run went on to its field limit or the end of its route.
- **The loop and the jump fail with native handling too.**
  - In the enhanced build the loop's outcome depends on frame timing. The native car on
    the same straight entry (heading on the loop's axis, 116 MPH, wheel centred) passes
    the loop, fails it with frames one field longer (`lap-loop-c1-slow1`, CUSTOM4 = 1), and
    passes with two (`-slow2`). CUSTOM1 = 2 makes frames about 6% longer, which is within
    that.
  - In an earlier version of the driver the arcade car entered exactly on the axis too.
    It stayed on the loop to the top and fell from there; the native car lost contact at
    69° and came back. Step 4 already recorded the loop's pitch domain and contact failures
    (open-work.md's history (git, up to b9b59016), C4).
  - The jump: step 4's seeded jump landed at 112 MPH; this driver reaches 89–104 MPH at the
    lip and lands short. The tape route (VERIFY_DRIVE) also crashes on landing at 103 MPH.
- **One thing the arcade handling changes:** at loop speed the native car turns at most
  about 5 °/s (its 0.45 g cap), the model about 12 °/s (1.08 g). So a player can enter the
  loop further off its axis than before, and the native loop code handles that badly (the
  throw above). A question for H3.
- **Not covered:** the Phantom race needs a qualifying lap, which this driver does not make.
  The Phantom is a recorded-pose playback and the player's car runs the model as in any
  race, but nothing here has run one.
- **Replay:** the driver keeps its hands off from a crash to its recovery, since a held
  button skips the replay; 33 of the 35 crashes played it to the end. Whether the replay's
  screech follows the model's (the `$8a1a` hook) was not listened to.

**H3 round 1 (2026-10-21): runaway spins.** The user's first drive: "if the car goes into a
slide, there's no way to recover. In fact, the car starts spinning faster and faster."
- **Reproduced:** `build_feel.py h3-spin-V-AFTER` (V 60 or 90 MPH): full throttle and full
  left lock for 1.5 s, then full (`counter`) or half (`half`) right lock, or the wheel centred
  (`centre`), for 3 s, the throttle held all along. `tools/spin_report.py ROOT` prints the yaw
  rate, heading and speed. G's module (`h3-spin-old`, built from 126798b with `--source`):

| Run | G: largest yaw after the change, turned in all, speed at the end | Fixed (`h3-spin-new`) |
|---|---|---|
| 60 MPH, counter | 196 °/s, 46° back and forth, 117 MPH | 29 °/s, 13°, 117 MPH |
| 60 MPH, half | 188 °/s, 288° (most of a spin) | 38 °/s, 20° |
| 60 MPH, centre | 94 °/s, 101° | 17 °/s, 28° |
| 90 MPH, counter | 256 °/s, 646° (nearly two spins) | 29 °/s, 14° |
| 90 MPH, half | 81 °/s, 164° | 33 °/s, 19° |
| 90 MPH, centre | 17 °/s, 22° | 12 °/s, 20° |

  G's car also gained speed while it spun (89 to 122 MPH at 90 MPH, counter).
- **Cause 1, no forward dynamics.** The native engine alone set the forward speed u. The
  model's v̇ = ΣFy/m − u·r had no partner u̇ = Fx/m + v·r, so as the car yawed the speed
  was never turned into the car's sideways direction or scrubbed off: a spin kept full
  speed along the heading and pumped energy into v and r. In the twin, 60 MPH, 1000 lb of
  drive, full lock then full countersteer: G's rule winds up to 360 °/s with v at its
  256 ft/s guard (`tools/arcade/spin_sim.py 60 1000 1.5 counter --old`).
- **Cause 2, the rear made up the front tyre's drag.** The step gave the rear wheels the
  force less the front tyre's force in body axes. That is right for the arcade replays,
  whose force is the arcade's total tyre force, but the game passes the native engine's
  net force, which knows nothing of the steered front tyre's drag. With the Amiga's on/off
  throttle (drive at its 2,115 lb limit) and full lock, the rear had to push 2,115 lb plus
  over 1,000 lb of front drag: the rear wheels spun, the rear lost the side grip that
  stops a spin, and the countersteered front then drove it.
- **The fix** (`HardDrivinHandling.s`, 1ae501e on the local branch; `handling_fx.FxCar.step(..., fx_total=False)`):
  - The rear wheels get the force less the front wheel's own longitudinal force (its
    brake), so the steered front tyre's drag is the model's.
  - The step outputs du, the forward speed it adds beyond the force: (front force along
    the car + rear force − the force) dt/m + v·r dt (Q22, `HS_DUF`).
  - Each field's step uses u = the native speed + the du of the call so far, stopping at
    zero rather than changing sign. The call then adds the sum to the native speed: to the
    phase solver's anchor and current velocity when it is current (so the native engine
    goes on from the new speed), otherwise to G($9928). The next force measurement starts
    from the speed the model left.
  - **Whole units only.** Each engine chunk runs the native engine from the anchor's
    speed word, and a phase ends on the whole endpoint, dropping the fraction. A first
    version that added fractions lost a whole unit (0.28 MPH) per native step whenever
    du was below zero at all (about 0.08 g): the straight-line top speed fell from 125 to
    117 MPH. The fix carries the fraction (`HS_CARRY`) until it makes a whole unit.
  - The twin keeps `fx_total=True` as its default, so E2/E3's replays and their results
    stand. `check_handling_step.py` and `check_handling_math.py` use the game's rule and
    compare du too: 562 sequences (843,000 steps) and the 64 boot sequences in FS-UAE
    (`i-handling-math-a500`) equal the twin. `handling_fx.py sweep 200 --drive`: no
    overflow; du peaks at 28 of 31 bits.
- **H1 again** (`i-feel-a500-arcade`, report `tmp/prof/i-feel-report.md`, columns arcade /
  G / fixed). The handling moved closer to the arcade almost everywhere, and nothing broke:

| Metric | Arcade | G | Fixed |
|---|---|---|---|
| Lateral limit at 30 / 60 / 90 MPH | 1.08 / 1.08 / 1.06 g | 1.09 / 1.14 / 1.13 g | 1.06 / 1.11 / 1.08 g |
| C1f slide at 60 / 90 MPH: largest sideslip | 4.7 / 7.7° | 5.6 / 8.3° | 5.0 / 7.2° |
| C1f 90 MPH countersteer: settled after, overshoot | 1.38 s, 5.2° | 2.24 s, 11.6° | 1.62 s, 5.7° |
| C1f 60 MPH countersteer: settled after, overshoot | 1.37 s, 2.1° | 1.34 s, 3.6° | 1.64 s, 2.9° |
| C1fx 90 MPH, larger lock, countersteer: overshoot | - | 36.6°, never settled (a spin) | 5.8°, settled in 1.32 s |
| C1e 0.7 g corner, full throttle: largest yaw change in 1 s | −17.7% | +11.7% | −31.8% |
| C1e 0.7 g corner, lift: yaw change after 2 s | +7.4% | +0.6% | +4.8% |
| C1e 0.9 g corner, brake: largest yaw change in 1 s | +82.8% | −29.1% | −21.4% |
| Top speed, 0-60 MPH | 140 MPH, 6.26 s | 125 MPH, 2.53 s | 125 MPH, 2.54 s |

  - Power-on in a corner now widens the line, as in the arcade (G tightened it).
  - The step responses (C1d) and the steady state (C1c) are within run-to-run spread of G.
  - The brake-in-corner spike is still missing (H1's analysis stands).
  - C1f 60 MPH brake reports no settling time: single passes show 2.6 °/s, one 0.25°
    heading step, just over the 2 °/s criterion. The trace equals G's.
- **H2 again** (`i-laps-a500`): `lap-main` the whole road as before (12,646 fields, 78 MPH
  on average, the same crash on the bridge approach with its replay and recovery, all
  flights landing, both checkpoint bonuses). `lap-offroad` as H2's CUSTOM1 = 2 run, the
  same recoveries and the same crash at field 9756. `lap-stunt` ran to its field limit:
  four crashes with replays and recoveries, a jump landed at 90 MPH and a loop entry
  (pitch to 175°), then the race clock ran out (the car then stands still, as H2 noted).
- **A latent crash in the enhanced build, found by `lap-stunt`:** a first run stopped at
  field 8384 with an address error in `_checkpoint_post` (`HardDrivinCheckpoint.s`,
  `move.w 18(a0)` with A0 = 1; `tools/fault_probe.py` replays a run to a field and stops at
  the first fault vector).
  - The native section search (`$dc00..$deba`) only takes sections with a corner below the
    car. When none qualifies, it stores its uninitialised local `-$e(a5)` in the cursor
    G($98e4) at `$de92`. Here the car had fallen below the stunt road. The native search
    wraps such a cursor into the list on the next pass, but `_checkpoint_post` runs first
    and checked only the upper bound.
  - **Fixed** (7dfd2ba, a commit of its own): it also requires the cursor to be even and at
    least G($98e0), the first section. This code is the enhanced build's (CUSTOM1 = 1 too), so the fix belongs in the
    release as well, and CUSTOM1 = 0/1 now differ from 1d36ff0 by this check.
- **The car rolled over first (open).** Before that fault the driver was circling at full
  lock (about 60 °/s) at 25–35 MPH on the embankment with one wheel down, and pitch and roll
  grew until the car was upside down. The native yaw helper (`$b1d0` and the enhanced
  `_motion_yaw_add`) adds −r·sin(roll) to pitch and −r·sin(pitch) to roll. That coupling is
  hyperbolic, not a rotation: pitch + roll (or pitch − roll) grows at the rate |r|, about
  1 rad/s here. The records show pitch + roll going from 30 to −600 units while pitch − roll
  stayed small. On the ground the contact code levels the car, and at the native turn rates
  (at most 25 °/s) it wins; on a slope with one wheel down at the model's low-speed rates
  it loses. Correct kinematics would rotate the tilt instead (one sign flipped), but that
  also changes the loop, where the coupling acts on purpose. A question for the user.
- **Cost on the A500** (`i-cost-c1c60-c2`, the same plan and settings as
  `h2-cost-c1c60-c2`): the model takes 4.28 ms a frame at 3.27 fields (G 4.03 ms at 3.25),
  1.31 ms a field (G 1.24 ms): about 0.08 ms (560 cycles) a field more. `_handling_step`
  1.62 ms a frame (G 1.49), `_handling_steer` 0.53 (G 0.44), `_handling_feedback` 0.06.
  About 6.6% of the A500.

**H3 round 2 (2026-10-22): spins that never stop, and roll-overs on slopes.** The user's
second drive (screen recording from 0:47): "When the car starts sliding it still goes into a
wild rotation which never quite stops. Combined with hills this makes the physics break
rather massively." In the video the car runs wide at about 100 MPH in the long right curve
after the bridge (main sections 21–49), leaves the road past the barn and spins on the grass.
It then tilts more and more, ends up looking straight at the sky, and the off-road counter
keeps restarting.
- **Reproduced:** `h3-curve-hold` (`build_feel.py`) seeds the car on main section 20 at
  100 MPH and follows the curve for 1 s. It then steers full right with full throttle for
  0.5 s and half right for 3 s, and centres. With 16b1981 the car leaves the road, and with
  the wheel centred the yaw rate grows from 35 to 60–100 °/s and stays there (19 MPH, to the
  end of the run). `tools/tilt_report.py` prints yaw, pitch, roll and contact. The fixture
  now also logs the model's state after each pass (`model.bin`, `amiga_feel.models()`).
  - That shows a steady state: v −86 ft/s, r 69 °/s, u 28 ft/s, both axles past their peak
    with equal side forces (1,717 / 1,713 lb), so no yaw moment. The drive force (fx) sits at
    its 2,115 lb limit.
- **Cause 1, the native engine refills the speed.** The native engine is power limited
  (`$b832..$b8a6`: Δv = √(v² + P) − v, then up to +40 per native step), so it pushes hardest
  when the speed is low. In a spin the model's v r takes u away every field (the car turns,
  so its forward speed becomes sideways speed). The native engine put it back, much faster
  than 2,115 lb would; `tools/replay_run.py` and `donut_sim.py` in `tools/arcade` (twin replays) showed the twin alone damps
  such a spin. The model only ever saw 2,115 lb of it. The rest acted like an outside force
  pushing the car along its heading, and −u r turned it into sideways speed: a spin that
  never ends.
- **Fix 1** (`_handling_sync`, 962221d on the local branch): while a tyre is past its peak (either axle's peak flag from
  the last step), the native speed gained beyond the drive limit comes off again, through
  HS_DU. While the tyres have grip to spare it stays, so straight-line acceleration is the
  native one.
  - Two simpler versions were tried. Taking the surplus off always made 0–60 MPH 4.68 s
    instead of 2.68 s. Taking off the share v²/(u² + v²) brought the spin back: when v fell
    while r was still high, the surplus returned and restarted the slide.
  - `h3-curve-hold` with the fix: u falls to 0 and v decays at about 1 g. The yaw rate stays
    until v drops below a r, about 6 ft/s, then stops within 0.3 s, and the car drives off.
    The spin lasts as long as the slide, 4.6 s from leaving the road at 100 MPH with the
    throttle held. The rear's friction circle with 2,115 lb of drive keeps it going that
    long; that is the model's power oversteer, as the arcade has it.
- **Cause 2, the yaw helper's coupling** (the open question from round 1). `$b1d0` adds
  −r sin(roll) to pitch and −r sin(pitch) to roll. `$b268` builds the car's up vector as
  R(heading)·(sin roll, cos roll cos pitch, −cos roll sin pitch). So positive roll is the
  right side down, positive pitch is the nose up, and a positive heading change turns right.
  Turning about the car's own vertical axis keeps that axis where it is, so for small angles
  pitch' = −r roll and roll' = +r pitch: the tilt turns with the car and keeps its size. The
  native roll term has the opposite sign for an upright car (it is right when upside down,
  where tan pitch changes sign), which makes any tilt grow at the turn rate.
- **Fix 2** (`_handling_turn`, 00a2f93): with pitch and roll both below 60°, the model's whole heading
  units go straight to the heading. (pitch, roll) are rotated by the same angle with the
  game's sine and cosine, rounded, and the enhanced build's last-angle words get the same
  changes. Above 60° (the loop) the native helper runs as before.
  - The game's cosine (`$2ac4`) adds 360 to its stacked argument and falls into the sine
    (`$2aca`, D0/D1/A0 only), so the sine is called first.
- **Verification:**
  - `tools/check_handling_turn.py SLAVE LISTING RUN` (Unicorn, with the game's own sine code and
    table from RUN): 200,000 cases, 85,187 rotated and 114,813 native, all equal the model.
    D6/D7/A2–A6 and the stack are preserved, and the fields word is restored. It fails on a
    model with the rotation's sign flipped.
  - `check_handling_step.py`: 562 sequences, 843,000 steps, unchanged.
  - The H1 matrix (`h3r2-feel-a500`, report `tmp/prof/h3r2-feel-report.md`): all 231 metrics
    identical to round 1's. On the flat test ground pitch and roll are 0, and no plan has a
    tyre past its peak with drive beyond the limit.
  - H2 laps (`h3r2-laps-a500`): as round 1, with no hang and no game crash.
    - `lap-main`: the whole road (12,645 fields), the same crash on the bridge approach, every
      flight landing, both checkpoint bonuses.
    - `lap-stunt`: a jump landed at 90 MPH and a loop entry (pitch 160°).
    - `lap-jump` and `lap-loop`: fail as before.
    - `lap-offroad`: recoveries every 18–20 s.
  - `check_installed_code.py` against 16b1981 (`clock.slave`): CUSTOM1=0 and 1 install the same
    game code (`h3r2-installed-c0`, `-c1`).
  - In game, against 16b1981 built with `--source` (`feel-old-`) and with fix 1 alone
    (`feel-aonly-`, a copy whose `_handling_turn` always takes the native path):

| Run | 16b1981 | Fix 1 only | Both fixes |
|---|---|---|---|
| `h3-curve-hold` (spin onto the grass) | 60–100 °/s to the end of the run | stops after 4.6 s | stops after 4.6 s, drives off |
| `h3-rollover` (round 1's roll-over, seeded at its field 8150) | pitch to ±170°, yaw 280–340 °/s, falls 800 units through the ground | pitch ≤ 42°, roll ≤ 33°; the roll fights the slope for 30 fields, then drives on | pitch ≤ 28°, roll ≤ 27°; follows the slope from the start, flies off the edge and crashes on landing |
| `h3-bank-right` (off the top of the 46° bank, yawing 20 °/s in the air) | pitch 24 → 117°, roll −35 → −158°: lands upside down | (not run) | the tilt keeps its size (42°) and turns: (24°, −35°) → (41°, 4°) → (1°, 41°) |
| `c1a-auto` 0–60 / 0–100 MPH, top speed | 2.68 / 7.06 s, 125 MPH | | 2.70 / 7.08 s, 125 MPH |
| `h3-spin-*` (flat ground) | largest yaw after the change 12–38 °/s | | 12–42 °/s |

  - The other new plans: `h3-curve-centre` and `-counter` (no spin), `h3-bank-left` and
    `h3-bank-slow-*` (the seeded car slides down the bank to 45–73 MPH and mostly flies), and
    `h3-hill-spin` and `h3-dip-spin` (full lock at 60–90 MPH only reaches 10–20 °/s; the car
    flies off the crest or crashes in the dip). None of them told the builds apart on the
    ground.
- **Not covered:** the cost. `_handling_turn` replaces the native helper call, which has three
  trig calls, two multiply helpers and three angle updates, with two trig calls and four
  MULS; the sync adds a flag test. Neither is measured.
- **The fixture:** `build_feel.py` plans can name a route (`ROUTE_OF`), and seeds can be on the
  main road (`MAIN`, the road cursor only), at a section's centre height (`Y`), or at a
  given place (`at`).

**H3 round 3 (2026-10-22): braking.** The user: "With both mouse buttons held down it takes
forever to get the speed down." Measured with `h3-brake-floor-60` and `-100` (full throttle
from rest, then both buttons until the car stands still; roots `h3brake-c1`, `h3brake-c2`):
- **Before:** from 100 MPH (throttle 87) 10.8 s at 0.42 g; from 57 MPH (throttle 31) 6.7 s,
  and the car first gained 3 MPH. CUSTOM1 = 1 and 2 brake alike. The arcade: 6.6 s and 4.5 s.
- **Why, the native engine (`$0B662`):**
  - The brake takes the speed / 35 per native step (2/3 of it below 35, which is why the car
    finally snaps to a stop), the drag the speed / 32 + 1: both fade with the speed, 0.35 g
    from 20 to 5 MPH.
  - Both buttons close the throttle at 2 per step, 12.5 per second, so the engine pushes
    against the brake for up to 8 s.
  - G's module passed that weak native force as the brake torque, and ignored the brake
    while the native speed still rose.
- **Fix 1, the brake at its limit** (`_handling_sync`): with the brake on, the front axle on
  the ground and the car going forwards, the model gets fx = brake torque = −2,470 lb. What the
  native engine did beyond that in the last call (its brake, drag and engine together) comes
  off again through HS_DU, as for the drive surplus. In the air or reversing the native
  brake stays. The throttle is left to its native ramp, so it is not shut after a short
  brake. 0.7 g, not the arcade's 0.85: H1 found that a brake torque past the front wheels'
  lock point (about 2,500 lb ft) stops the car turning in a corner altogether.
- **Fix 2, the brake on the front only** (`_handling_step` and `handling_fx.py`): the rear
  wheels got fx less the front wheel's own force, so whatever a front tyre past its limit
  could not take went to the rear tyres. With fix 1 alone a brake tap at 85 MPH in a 1 g
  corner then braked the rear, which let go: the stunt and loop laps fell to a mean 41 and
  39 MPH. While braking the rear now gets fx less the brake torque (zero; the faded torque
  at walking pace).
- **Results:**

| Metric | Arcade | Round 2 | Round 3 |
|---|---|---|---|
| C1b from 60 MPH: time to stop, deceleration | 4.47 s, 0.87 g | 5.28 s, 0.45 g | 4.34 s, 0.59 g |
| C1b from 100 MPH: time to stop, deceleration | 6.57 s, 0.85 g | 8.76 s, 0.49 g | 7.24 s, 0.60 g |
| Full throttle, then brake from 100 MPH | - | 10.8 s | 7.5 s, 0.58–0.73 g in every 20 MPH band |
| C1e 0.7 g brake: largest yaw change in 1 s / after 2 s | +133% / −18.6% | +26.7% / −12.9% | +135% / −19.8% |
| C1e 0.9 g brake: the same | +82.8% / −14.0% | −20.8% / −12.3% | −90.9% / −15.9% |
| C1f brake at 60 / 90 MPH: largest yaw | 6.1 / 10.5 °/s | 20.1 / 15.6 °/s | 32.6 / 32.3 °/s |

  - The brake-in-corner spike H1 missed is there now (C1e 0.7 g). At 0.9 g it swings the other
    way first; two seconds in both match.
  - Braking in a slide (C1f) yaws more than before, three times the arcade.
  - The matrix (`h3brake-feel-a500`, report `tmp/prof/h3brake-feel-report.md`): 155 of 279
    metrics differ from round 2. Outside braking the changes are small: the cruise brakes
    when more than 3 MPH too fast, and its approaches differ.
- **H2 laps** (`h3brake2-laps`): no hang or game crash. `lap-main` the same (mean 78 MPH),
  `lap-jump` the same, `lap-offroad` one crash more. `lap-stunt` (mean 70 MPH against 77) and
  `lap-loop` (56 against 83): the driver brakes at about 85 MPH in a 1 g corner of the stunt
  road, the car turns in and the rear lets go (`tools/brake_events.py`: 4 and 11 brake taps
  followed by more than 50 ft/s of sideways speed, against 1 and 3). In round 2 the same taps
  braked at the native 0.1–0.4 g. The spins end with the car stopped within 3 s.
- **Verified:** `check_handling_step.py` (843,000 steps, its random sequences brake with
  any fx) passes with the twin changed alike; installed code at CUSTOM1 = 0/1 identical.
- **Not measured:** the cost (a flag test, a contact test and one MULU/DIVU per call while
  braking; two moves per step).

**H3 round 4 (2026-10-22): the jump.** The user: "it's very hard to get past the bridge on
the stunt track because the car seems very floaty - it spends a lot of time in the air and
then comes crashing down." Not handling: the landing is `HardDrivinMotion.s`, so CUSTOM1 = 1
and 2 alike. Measured with C4 probes from the `jump_clear` seed at seven lip speeds
(`build_c4_geometry_probe.py` with `C4_VELOCITY` and `C4_THROTTLE`, 450 fields, A500):
- **The long flights are native.** The pitch rate at take-off is whatever the rear-only
  contact passes (`$cab6`, mask 12) last measured on the lip: −8 in the original (two
  samples), −3 or −8 enhanced. A rate of −3 or −4 keeps the nose up, the car flies long and
  lands steep. The original also crashed 3 of 4 jumps at 88–101 MPH at the lip and landed
  all 3 at 53–66 MPH.
- **The enhanced landing was stricter.** The native crash at `$cc2e` needs a fall speed over
  50 and the average wheel height below −5 after the step. Contact counts from below 4
  units, so a native step closing on the ground at u units per step lands 4−u to 4 deep: a
  crash with chance (u−9)/u, half at u = 18. Short passes reach full contact long before −5,
  and `_motion_fall_ground` crashed every full contact with a fall over 50: 4 of 14 probes
  landed.
- **Fix:** for variable intervals `_motion_landing_depth` (`$cc2e`) answers "not deeper",
  and `_motion_fall_ground` crashes only where the wheels closed on the ground faster than
  `LANDING_U` = 18 units per native step since the last pass in the air or on two wheels
  (`_motion_fall_airborne` records its average height). The native median; the ground's
  own slope counts, as in the native depth. Zero and eight fields stay native.
- **Results** (crash = the throttle dropped to 0 within 40 fields of landing):

| Lip speed | Original | Before | After |
|---|---|---|---|
| 88–101 MPH | 1 of 4 land | 0 of 8 land | 2 of 8 land |
| 53–66 MPH | 3 of 3 land | 4 of 6 land | 6 of 6 land |

  - The first build had the landing flag test inverted (CLR sets Z before the BEQ), so no
    variable-interval landing crashed at all; the laps then hung. The numbers above are
    the corrected build's.
  - The take-off lottery stays native. Forcing the rear-only pitch rate (`FEEL_FORCE_RATE`,
    `C4_FORCE_RATE`) to −12 or −16 lands more jumps than −8, which crashes every jump of
    a lap at a fall of 51–59: an option for the user, not done.
- **H2 laps** (`landing3-laps`, CUSTOM1 = 2, against `h3brake2-laps`): `lap-main` the same
  (one crash, finished 54.07 against 54.04), `lap-stunt` and `lap-loop` the same crash
  counts (7, 8), `lap-offroad` one crash fewer. `lap-jump`: round 3 crashed all 8 jumps; now
  the first jump lands at 90 MPH and the car reaches stunt section 66 instead of 27.
- **`lap-jump` then crashes the game** at field 13,850: during the replay of a crash that
  followed a 720-field flight off the world from the loop (road pointer 0; the loop's
  known open problem), the native span filler (`$33e0`) gets a span of about −11,800 words
  and its jump into the unrolled fill (`jmp $345e(pc,d2.w)` at `$340c`) lands in `$7c00`.
  WHDLoad (NOREQ) ends on the address error that follows. Native renderer code, reached
  here because the car now gets past the jump; not fixed (`tools/hang_probe.py` finds it).
- **Verified:** jump probes; laps above; installed code at CUSTOM1 = 0 identical, at
  CUSTOM1 = 1 only the 6 bytes of the `$cc2e` patch differ.
- **Not measured:** the cost (one test per pass in the air, a multiply per landing).

**H3 round 5 (2026-10-22): the user's decisions.** "1. Yes, you should fix encountered
renderer crashes that are present in the original, regardless of the enhancement options are
enabled. 2. Follow the arcade version in this regard if possible" (the take-off pitch rate).
- **The renderer crash (b2c686a, every CUSTOM1, release v1):** the 2D polygon routine
  (`$3736`) clips polygons that cross the window (x −160..159, y −67..67, G($960C..$9612))
  with 16-bit MULS/DIVS. Vertices far outside, as in a replay of a car off the world,
  overflow and stay outside; the edge rasterizer (`$2da2`) and the span tables (two
  320-entry tables at `$30500`) hold only the window, so the span fill's computed jump at
  `$340c` (21-word table) lands in other code. `_fixclip_v1` (`$39c8`) does not draw a
  clipped polygon with a vertex outside the window; unclipped polygons lie inside by the
  routine's own bounding-box test, so they are not checked.
  - **Verified:** `lap-jump` now runs its 20,000 fields through four replays of flights off
    the world; `lap-main` and `lap-stunt` dropped 0 of 3,000 clipped polygons each
    (`hang_probe.py` with breakpoints; `lap-loop`'s count ran out of time); installed code
    at CUSTOM1 = 0 and 1 differs only at `$39c8`. Not measured: the cost, about 100 cycles
    per vertex of a clipped polygon.
- **The arcade take-off (CUSTOM1 = 2):** the arcade car on its rear wheels alone pitches
  nose down under the rear spring's load (1,741 lb at 5 ft, less an 850 lb drive force at
  1.567 ft, over 2,000 slug·ft²: 3.7 rad/s²) for its 10 ft wheelbase, so it leaves a lip
  at 3.7 × 10 ft / speed: −9.7 quarter-degrees per native step at 95 MPH, −17 at 54. From
  the model's equations, not measured in MAME (that needs a driver on the arcade's stunt
  road). The Amiga car stays on its rear wheels for 28–32 ft (10 fields at 95 MPH, 20 at
  54; contact counts below 4 units and the lip is convex), so `_contact_pitch_rate_only`
  adds a third of the arcade's acceleration per field (`CONTACT_TIP`, capped at −45)
  instead of the native −asin(gap)/4 sample. `_handling_install` sets `_contact_arcade`.
  - **Probes** (`jt-*-c2`): all 7 land (round 4: 4 of 7 at CUSTOM1 = 2); take-off rates −9
    to −11 at 87–101 MPH, −20 at 55–67.
  - **The Amiga's flight follows the body's pitch** (`$b500`: the movement vector is
    1.5 v along the current pitch and heading, plus the native fall speed), the arcade's is
    ballistic. So the arcade's rate makes flights shorter and steadier: 62–71 fields at
    87–101 MPH (round 4: 62–165); at 55–67 MPH the car tips over the crest (19 fields).
  - **Laps** (`tip-laps` against `landing3-laps`; the slave sizes differ, so the runs are
    not field for field): `lap-main` and `lap-offroad` the same, `lap-stunt` 5 crashes
    against 7, `lap-loop` 6 against 8, `lap-jump` and `lap-stunt` 3 of 4 jumps landed; the
    fourth (88 MPH) came down short and nose down and hit the landing ramp's front edge.
  - **Verified:** installed code at CUSTOM1 = 0 and 1 identical to the clip build.
  - **Open, for the user:** a ballistic flight (the flight keeps the take-off direction
    while the body turns). It needs the two native reads at `$b520/$b536` and eight slave
    reads (`_phase_project_core`, `HardDrivinProjection.s`) of the pitch trig to use a pair
    held at take-off, at CUSTOM1 = 2 only; the contact, landing and engine code keep the
    real pitch. CUSTOM1 = 1 must then be shown identical record for record.

**H3 round 6 (2026-10-22): the arcade flight.** The user: "Implement the arcade flight."
CUSTOM1 = 2 only.
- **Ballistic flight:** the first pass with no wheel on the ground holds the pitch's sine and
  cosine (`_flight_fall`, `HardDrivinProjection.s`). The movement projections use them while
  held: native `$b512..$b577` (replaced by `_handling_flight_vector`), and the slave's
  `_projection_integer_components`, `_projection_components` and `_phase_project_core`.
  Contact, landing and engine code keep the body's pitch, and the body turns on at its
  take-off rate. The hold ends at the native ground pass (`$cc8a`: three wheels or a
  diagonal pair), a crash or a reset.
- **1 g:** the native fall acceleration of 5 long units per native step² is 8.6 ft/s²
  (0.27 g) at E1's 0.3504 ft per unit; flying along the body's pitch, which tips the
  motion down, is what brings the native car back to the landing ramp. Ballistic at 0.27 g,
  the probes flew 255–271 fields and 1,890–2,250 units at 87–101 MPH, past the ramp, and
  came down at −77° (`jfl-*-c2`). `FLIGHT_G` = 19 is the arcade's 32.2 ft/s² (18.8).
- **Two wheels keep the flight:** when the hold ended at the first contact, the native
  passes on two wheels moved the car along its body (−24° on the ramp) and kept the fall,
  so the wheels closed on the ground at 31 units per native step and all four fast probes
  crashed (`jfg-*-c2`).
- **Eight-field landings:** at 1 g the fall always exceeds the native test's 50, so the
  native depth test (wheels below −5) crashed the passes that happened to last exactly 8
  fields (`jfh-*-c2`). At CUSTOM1 = 2 they use the closing-speed rule (`LANDING_U`) too.
- **Probes** (`jfi-*-c2`, round 5's seeds and throttles): all 7 land and drive on.

| Lip speed | Round 5 | Round 6 |
|---|---|---|
| 87–101 MPH | 62–71 fields, 470–650 units, all land | 88–101 fields, 650–910 units, all land |
| 67 MPH | 19 fields | 60 fields, 350 units |
| 55–56 MPH | 19 and 47 fields | the same |

  The fast flights peak 5–16 units above the lip (round 5: 2–10) and touch down on the
  front wheels at about 47 ft/s vertical, 21–24° nose down, on the 9° ramp.
- **Laps** (`flight-laps` against `tip-laps`; not field for field): `lap-main` and
  `lap-offroad` the same. The bridge jump (stunt 20): 2 of 3 landed (round 5: 3 of 4); the
  third left the lip at the road's edge and hit the structure in the air, as round 5's
  crash there did. Stunt 6: 2 of 2 (round 5: 2 of 2). Crashes: `lap-jump` 5 (7),
  `lap-stunt` 6 (5), `lap-loop` 8 (6). The loop still fails as before (its known open
  problem); the flights out of it now last 225–477 fields instead of 517–1,350.
- **CUSTOM1 = 0 and 1:** the installed game code is identical to round 5's
  (`check_installed_code.py`). The slave's new tests never branch there (`_contact_arcade`
  is 0), but they cost cycles, and the lap fixtures are not robust to that: `lap-jump` and
  `lap-stunt` at CUSTOM1 = 1 diverge from round 5 at field 36 and 60 (a VBL sample on the
  other side of a physics pass). Control: round 5 run twice is identical; round 5 with ten
  NOPs in the ground pass diverges alike. So record-for-record identity cannot show this.
- **Not measured:** the cost (CUSTOM1 = 1: a test per projection, a call per pass on the
  ground or in the air; CUSTOM1 = 2: as much again while held).
- **Found, not caused:** the `VERIFY_PROJECTION_MATH`, `VERIFY_MOTION_MATH` and
  `VERIFY_POSITION_WIDE_MATH` builds do not assemble (branches out of range); round 5's do
  not either.
- **The loop (the user's drive: "I'm having a really hard time with the loop"):** the
  Amiga has no centripetal force to hold the car on the loop; its contact drops out on the
  way up (69–80°) and upside down at the top (172–180°), and only the native fall along
  the body (0.27 g) lets it touch again. Round 6 turned those dropouts into flights at 1 g.
  Now only a car upright and within 45° of level takes off (`_flight_fall`: |sine| ≤
  cosine); elsewhere the native fall and motion run.
  - **Loop probes** (C4 `loop` seed, wheel centred; `lp*`, `lpt*`): from 95–129 MPH entries
    and throttles 60–100 the car reaches the top at 95–122 MPH and loses contact there in
    every build: CUSTOM1 = 0, 1, round 5, round 6 and the fix. So this seed does not show a
    pass (step 4's passes, `c4-final-loop-*`, came from older CUSTOM1 = 1 sources). Round 6
    then fell away faster; the fix matches round 5 (same outcome at 4 of 5 speeds, the
    fifth differs as timing does).
  - **Jump probes** (`jfj-*-c2`): identical to `jfi-*-c2`.

**H3 round 7 (2026-10-23): the arcade engine and gearbox.** The user: "Implement arcade engine
and gearbox." At CUSTOM1 = 2 (e8b2ea0) the handling module now runs the arcade's drivetrain
(`$730490`, ARCADE_ROMS.md) every field, and the native engine's speed, RPM and automatic
shifts are left out.
- **The native engine** (`$B662`) still runs its crash test, the phase solver's gear site
  (`$B904`, which takes a manual gearbox's shifts at `$B9BA`) and its tail (`$BAC6`: the
  brake byte, the engine sound from the RPM). Three patches, CUSTOM1 = 2 only: `$B678` goes
  straight to `$B904`, `$B90C` (its automatic shifts) to `$BA8A`, and `$BA8A` (the
  speedometer from the RPM through the native gear table) writes the module's speedometer
  and target speed instead.
- **Per field** (`_handling_engine`, before the model's step):
  - automatic shifts at 602·(gas + 3)/4 and 366.5·(gas + 3)/4 rad/s, at most one per model
    second (`g_7538F0`, one second of `g_751200`); after a model reset the lowest gear that
    would not shift up at the speed. A manual gearbox keeps the game's gear (0 neutral);
  - the engine torque table (`$7529F0`, bilinear: 1000 rpm a column, 14/128 of throttle a
    row), times a factor by gear. Step D's "times 1.3" holds in 4th only: C1a's recorded
    run (`tmp/arcade/mame/c/base/c1a-auto`, word 0x17 is the clutch torque) shows 1.11,
    1.156, 1.2025 and 1.3 in gears 1–4, that is 1.2, 1.25 and 1.3 (the constants of
    `$735BC0`'s branches) times 0.925 (`$736EF0`) in 1st–3rd. Locked in 1st at 4,800 rpm
    this reproduces C1a's 0.55 g to 1%. On grass (G($E94A) = 0) the grass table
    (`$753170`) times 1.1 (times 0.925 in 1st–3rd);
  - the automatic clutch: full capacity (600 lb ft) while the driveline overruns the engine
    by 100 rpm, otherwise taking up as ω_e − ω_d/4 goes from 1,500 to 3,000 rpm; it slips
    at its capacity and locks when the engine reaches the driveline (`$730830`'s cases,
    engine inertia 0.4);
  - the rear wheel's torque is the clutch's through the overall ratio (gear × 3.5); locked,
    the engine's inertia × ratio² joins the wheel's, as a share of the torque
    ((m + I_w)/(m + I_w + I_e ratio²): 0.81 in 1st to 0.96 in 4th). The driveline speed is
    the rear wheel's (its sliding speed while it slides);
  - drag 0.0087 u² + 105 lb, 10 u more on grass, and after the time ran out (G($979C)) the
    arcade's forced stop, 1,500 lb; none of it takes the car past standstill;
  - gravity along the car, 1 g, on the ground (the native slope term was 50 sin θ per
    native step, about 4.2 g), not with G($F791) set (where the native one is off) nor in a
    held flight.
- **The step** (`HS_ENGINE`): the rear wheels get the drivetrain's torque (`HS_TREAR`), and
  the forward speed changes by the tyres' force less drag and gravity (`HS_FEXT`), plus
  v r. The load transfer follows the tyres' force of the last step, and the brake's
  −2,470 lb while braking: from the lagged tyre force alone the front was light enough at
  the brake's onset to lock (C1f brake: a 44° slide). The math test keeps `HS_ENGINE` clear,
  so `VERIFY_HANDLING_MATH` still checks the old path against the twin; the new path has no
  twin.
- **No throttle while braking:** the brake is both buttons, and the throttle they close at
  2 per native step drove against it for seconds (from 90 MPH 0.57 g).
- **Publication:** the speed as before (whole units into the phase solver's current
  velocity, or G($9928)); the phase solver's anchor moves with it, since an anchor with a
  fraction would step the speed down to its whole word with nothing from the engine.
  The speed may now change sign (gravity rolls the car back). The RPM (at most 6,500, the
  native limit) into G($992A) and, whole, the solver's anchor and current RPM; the
  speedometer G($992C) and target G($9926) from the ground speed; the gear and its pointer
  G($9940) when the automatic shifts.
- **Fixture:** the feel ground is grass made road; `build_feel.py` now also clears the
  module's grass flag (`HS_GRASS`) there. Without it the grass table held C1a at 38 MPH in
  1st, which is what the arcade does on grass. `amiga_feel.py`'s `model.bin` layout follows
  the state (bytes 72–79: trear, fext, fxt, engine).
- **Prototype:** `tmp/engine/drive_sim.py` (float).
- **H1** (`eng2-a500`, `eng5-a500`; arcade / round 3 (`i-feel`) / round 7):

| Metric | Arcade | Round 3 | Round 7 |
|---|---|---|---|
| Upshifts, full throttle | 47.9, 67.4, 91.6 MPH at 5,750 rpm | 50.0, 64.1, 88.9 MPH at 5,000–5,280 | 48.8, 68.5, 92.7 MPH at 5,705–5,754 |
| Coast in gear at 110 / 90 / 70 MPH | 0.18 / 0.15 / 0.11 g | 0.34 / 0.47 / 0.60 g | 0.18 / 0.15 / 0.11 g |
| 0–30 / 0–60 / 0–100 MPH | 3.2 / 6.3 / 13.3 s | 1.1 / 2.5 / 6.9 s | 6.9 / 10.0 / 16.9 s |
| Top speed | 140 MPH after ~40 s | 125 MPH | 133 MPH at 32 s, rising |
| Full braking from 60 MPH | 0.87 g, 143 ft | 0.45 g, 217 ft | 0.73 g, 173 ft |
| C1e 0.9 g lift: speed after 2 s | 51.7 MPH | 40.0 | 54.0 |
| C1e 0.7 g / 0.9 g brake: largest yaw change in 1 s | +133% / +83% | +14% / −21% | +102% / +82% |
| C1e 0.7 g / 0.9 g brake: yaw change after 2 s | −19% / −14% | −16% / −13% | −35% / −32% |
| C1f 60 MPH brake: largest sideslip, yaw | 0.4°, 6.1 °/s | 1.8°, 19.5 °/s | 3.1°, 31 °/s (settled 0.26 s after) |
| C1c 60 MPH: yaw gain, lateral limit | 43.1, 1.08 g | 42.1, 1.11 g | 41.6, 1.10 g |

  - The acceleration is the arcade's engine behind the Amiga's throttle, which opens at 2
    per native step: 8 s from closed to full. The arcade's launch with the pedal down is
    0.32 g; the drivetrain at full throttle from rest gives about 0.4 g in the prototype.
  - The brake now locks nothing and has no engine against it; the brake-in-corner spike
    appears (the front tyre only just within its limit), and the car slows more in the
    corner than the arcade's (−35% against −19% yaw after 2 s).
- **H2** (`eng5l-a500`): `lap-main` the whole road, no crash (round 6: one, on the bridge
  approach), mean 82 MPH (78), the crest flights landing. The bridge jump: lip 103–106 MPH
  (round 6: 88–90; 1 g on the ramp instead of 4.2 g), 102–106 fields, landed in all three
  laps that reached it. `lap-offroad`: recoveries every 23 s as before, top 48 MPH (the
  grass table; round 6 66). The loop as before: contact lost near the top, long falls.
- **Jump probes** (`je3-*`): all seven land; their seeded throttles were the native
  engine's, so the lip speeds differ (108–36 MPH against 101–55).
- **Loop probes** (`le3-*`): the top at 106–117 MPH (round 6: 95–122), contact lost there as
  in every build.
- **Installed code** (`check_installed_code.py`, `eng6-ic-c*`, against round 6's
  `flight7`): CUSTOM1 = 0 and 1 identical; CUSTOM1 = 2 differs only at the three patches.
- **Not measured:** the cost (a table lookup, two divisions and the clutch per field).
- **Left out:** the stick's clutch pedal (the Amiga's manual gearbox uses the automatic
  clutch), stalling and the start-up below 500 rpm, the 0.925 factor's real condition (taken
  as 1st–3rd), the arcade's re-engagement gear choice beyond the reset pick.

**H3 round 8 (2026-10-23): mouse pedals.** The user: "I don't think the mouse controls in
this game make any sense at all." With mouse control (G($95F8) = 3) at CUSTOM1 = 2 the right
button is the gas and the left the brake, independent pedals that move 0.1 of their travel per
field (`HANDLING_PEDAL`, 10 of 100) towards fully down while held and back while released.
The user's design; the rate is a first guess to tune after a drive.
- **Native controls** (`$7C32`): the left button (CIAA fire, either port) sets bit 2 of the
  latch G($95F6), the right (POTGOR bit 10) bit 0; the VBL ORs them in each field and the
  controls pass clears the latch. Natively word 4 raises the throttle by 2 per pass (with
  the engine started), bit 0 lowers it by 2, and word 5 brakes in mouse mode. Two patches,
  CUSTOM1 = 2 only: `$7D28` goes on to `$7D5E` in mouse mode (the joystick modes keep the
  native buttons), and `$7DCA`'s both-buttons brake is skipped. The latch still starts the
  engine, skips the replay and drives the menus.
- **Per field:** the latch holds every press since the last controls pass, so the module
  reads the buttons itself (`_handling_buttons`), as the native VBL does, less its mask
  G($8FC7) of buttons held since a click. The VBL stores them with the field's mouse X
  (`_handling_held`); the field loop's `_handling_pedals` moves the pedals, writes the
  throttle G($991C) and brake byte G($9911), and sets the brake torque to the pedal's share
  of 2,470 lb ft. The gas is the native throttle until the engine starts (G($ADDC)), as the
  buttons cannot move it then either, and closes after the time ran out.
- **Gas and brake together:** both work. Round 7's "no throttle while braking" now applies
  only to the joystick modes, where the brake is still a button combination.
- **Test drivers:** they publish the native words as before, and the held buttons in
  `_handling_pad`. `feel_fixture.s`: 4 holds the gas, 1 releases it, 5 holds the brake
  alone, 0 keeps the gas as it was, so the cruise's gas pedal hunts within 10 of its aim.
  `_verify_throttle_hold_buttons` (C4 probes) holds the gas while the throttle is below
  its target.
- **Results** (A500, `ped3-a500`, against round 7 and the arcade):

  | | Arcade | Round 7 | Round 8 |
  |---|---|---|---|
  | 0–30 / 0–60 / 0–100 MPH | 3.2 / 6.3 / 13.3 s | 0–60 10 s | 2.8 / 5.8 / 12.7 s |
  | Shifts | 47.9 / 67.4 / 91.6 MPH | 48.8 / 68.5 / 92.7 | 48.9 / 68.8 / 92.5 |
  | Top speed in 50 s | 140 MPH | 133 at 32 s | 136 MPH |
  | Coast in gear, 110 / 90 / 70 MPH | 0.18 / 0.15 / 0.11 g | the same | the same |
  | Braking from 60 / 100 MPH | 0.87 / 0.85 g | 0.73 / – g | 0.73 / 0.72 g |
  | C1e brake, 0.7 / 0.9 g: largest yaw change | +133 / +83% | +102 / +82% | −31 / −52% |
  | C1f brake at 60 MPH: largest yaw rate | 6.1 °/s | 31.0 | 19.8 |
  | C1e lift at 0.9 g: speed after 2 s | 51.7 MPH | 54.0 | 57.2 |

  - The brake's 0.2 s travel takes away the turn-in spike: the arcade runs stepped the
    pedal to full at once, and the front tyres' load now grows with it.
  - `lap-main` runs to the end without a crash in 222 s (round 7: 226 s), mean 83 MPH. The
    other laps as before: `lap-jump`'s landings crash, the loop fails, `lap-offroad`
    recovers.
  - Jump probes (`pe3-*`): all 7 land, lips 107–37 MPH as round 7's. Loop probes (`pl3-*`):
    the top at 105–117 MPH, contact lost there, as in every build.
  - An earlier build (`pe1`, `pl1`) closed the gas before the engine started, so the
    probes' seeded throttle went to 0; the native throttle before the start fixed it.
  - `c1a-auto` now leaves the test ground (done 4) at about 136 MPH after its metrics.
- **Installed code** (`check_installed_code.py`, `ped3-ic-c*`, against round 7's `eng6`):
  CUSTOM1 = 0 and 1 identical; CUSTOM1 = 2 differs only at the two patches.
- **Not measured:** the cost (a few dozen instructions per field).

**H3 round 9 (2026-10-23): the real scale.** The user: "driving at 140 definitely does not feel
like 140, more like 70 at max." E1 took the native speedometer's MPH as real (0.3504 ft per
world unit). The course says otherwise:
- **Road width:** every Amiga road section is 230 units from edge to edge (main and stunt). The
  arcade's road at the start line is 41.2 ft wide: MAME runs `w1L` and `w1R`
  (`tools/mame/plans/w_edge_L.lua`, `_R`) leave it at 15 MPH to each side, and the front wheel
  reaches the grass at z = 5,021.0 and 4,979.8 ft. So a world unit is 0.1791 ft (±0.005) and
  v = 1 is 0.2099 ft/s: 1.956 times the speedometer's scale.
- **The course:** start to checkpoint is 52,791 units, about 9,500 ft, which the arcade's 96 s
  allow at 67 MPH; the lap is about 14,000 ft, the champion's 1:33 an average of 104 MPH. At
  E1's scale it was 18,500 ft, hence the doubled limits; Domark's own countdown runs at half
  speed for the same reason.
- **Re-analysed at this scale**, round 8's car reached 0.54–0.58 g at its grip limit and 29 MPH
  after C1e's 60 MPH corners: it drove at half the arcade's speed past the scenery.

Changes, CUSTOM1 = 2 only (the other settings keep the speedometer's scale, as the original):
- `amiga_units.py`: `FT_PER_WORLD` from the road (`FT_PER_WORLD_SPEEDO` keeps E1's first).
- `HardDrivinHandling.s`: `HM_K_U` 14087 (from `handling_fx.py`), `HANDLING_K_PH` 4764,
  `HANDLING_K_LAT` 893, `HANDLING_K_STEP` 7146, `HANDLING_V8_MAX` 8138 (145 MPH),
  `HANDLING_JUMP` 78 (the same 3.2 g). The model itself works in feet and is unchanged.
- `HardDrivinProjection.s`: `FLIGHT_G` 37 (1 g). `HardDrivinContact.s`: the take-off rate
  doubled (`CONTACT_TIP` is now half of it and doubled in the code: the car stays on its rear
  wheels about 86 units, 15.3 ft). `HardDrivinMotion.s`: `LANDING_U_ARCADE` 35, the native
  median's closing speed at this scale.
- `HardDrivinTraffic.s`: traffic speeds were set at the speedometer's scale too; with arcade
  handling the traffic integrates twice each frame's fields (2, not 1.956).
- `HardDrivinClock.s`: the arcade's limits in `_clock_limits`, doubled by the installer unless
  CUSTOM1 = 2 (ARCADE_TIMING.md).
- Tools: `feel_fixture.s` rescales G($9928) by 1/1.956 with arcade handling (`_feel_velocity`)
  and the seed by 1.956, so plan and route speeds are real MPH there; `build_feel.py` route
  radii, braking distances and pursuit gains at the new scale, routes on the centre line
  again; `lap_report.py` and `arcade_report.py` report real MPH for CUSTOM1 = 2;
  `check_clock.py` checks the stored arcade limits; `capture_clocks.py` reads HDFEEL03 and
  takes `--prefix`.

Results (A500, `sc1-a500` feel, `sc5-a500` laps, `sc5-clk` clocks):
- **Feel at real speed** (arcade / round 8 re-analysed / round 9): grip limit at 30, 60 and 90
  MPH 1.08 / 0.54 / 1.08, 1.08 / 0.58 / 1.11, 1.06 / 0.56 / 1.06 g; speed 2 s into C1e's 0.7 g
  lift, power and brake 52.6 / 28.9 / 53.7, 73.4 / 37.3 / 74.2, 27.1 / 12.5 / 25.4 MPH; braking
  from 60 MPH 0.87 / – / 0.73 g. C1a (from its records; it now leaves the test ground after
  30 s): 0–60 in 5.9 s, 0–100 in 12.7 s, shifts at 48 / 68 / 92 MPH, 136 MPH at 30 s.
  `c1c-90` also leaves the ground.
- `check_handling_step.py`: the 68000 state equals the twin after all 843,000 steps.
- **Laps:** `lap-main` in 117 s without a crash, mean 81 MPH (round 8: 222 s). With the right
  lane (lane 57) the driver ran into the same-direction traffic, which it does not avoid; on
  the centre line before the traffic fix it met the oncoming car on the start straight.
  `lap-slow` crashes once near the end. The stunt routes' 125 MPH, set at E1's scale, now
  crash over the crests.
- **Arcade timing** (CUSTOM5 = 1): `lap-main` starts with 1:36, reaches the checkpoint after
  80 s with 0:15.96 left (+32 s) and finishes with 0:14.58 left (+48 s); `lap-slow` (55 MPH)
  runs out, the race ends 5.3 s later; CUSTOM1 = 1 still starts with 3:12.
- **Jump probes** (`se1-*`, round 8's real lip speeds): 81, 73, 66 and 53 MPH land; 107 and 96
  MPH now fly about 600 ft and crash, and 39 MPH crashes: the gap is half as long in feet as
  before.
- **Loop probes** (`sl1-*`): entries at 97–111 MPH, contact lost near the top, as in every
  build.
- **Installed code** (`check_installed_code.py` against round 8's `pedal3`): identical for
  CUSTOM1 = 0, 1 and 2.
- **Not measured:** the cost.

**H3 round 10 (2026-10-23): the loop, investigation.** The user: "Continue implementing the arcade
physics." The loop is the part that fails in every build. What fails, and why (CUSTOM1 = 2,
`build_c4_geometry_probe.py` loop seeds at 112 MPH, `tools/loop_track.py` and
`tools/loop_pass.py`):
- **The geometry:** stunt sections 37–48 are a 12-sided polygon, 30° a facet (section pitch
  word 60, 180, … 660, then −660 … −60), radius about 315 units (56 ft), 630 units high. Each
  section's edge points the same way, so the surface is a cylinder; along it the road moves
  sideways by its whole width (230 units) over the loop.
- **Step length (A500):** a 68000 frame is one physics step of about 10 fields, which at the
  real scale is about 180 units of straight travel, a facet and more. The wheel-height pitch
  feedback cannot follow: on the way up the car's pitch lags the road by about 55°, the front
  wheels sit 130–230 units under the surface, and the car runs straight past the top (y 899
  against the road's 630) and loses contact at 93–132° of pitch (`sl1-*`). The native scale
  moved half as far per step, which is why it was marginal before round 9.
- **Short steps:** the 68060 (1–2 field steps, `lf-*-060`) follows the pitch to 172–176° and
  loses contact at the top, at the road's edge (lateral −113 of ±115): the car keeps its heading
  and the road has drifted half its width.
- **With the wheel held slightly left** on the loop (mouse 300, `lm4-300-060`, fixture
  `c4_fixed_input.s`) the car stays on past the top, then the pitch sticks near −165° while the
  road goes to −105°, contact goes, and it falls back. The heading also swings by tens of degrees
  over the top (the native yaw helper's ×−3/2 when inverted). Holding 260–280 or 340–360, or the
  native follow driver, fails earlier.
- **Shorter steps on the A500 are not affordable:** a test build capped steps at 2 fields on
  sections steeper than 11° (`lm6-*`). The pitch then follows as on the 68060, but each native
  pass costs 5–6 fields on a 68000 (it prepares the scene), so one 2-field step ran per frame and
  the pending fields grew to 31 (`lm6u`, the new `--timing` columns pending, frame_steps,
  frame_fields, discarded). Reverted.
- **The arcade** (ARCADE_ROMS.md, "The loop in the attract demo"): about 117 ft high, entered at
  61 MPH, over the top at 70–75 ft/s (1.7 g of v²/r); it drifts the road's width sideways at a
  steady rate, and the car yaws with it (up to 10°, slip under 1°). Whether the demo's driver
  steered is not known.

**Design:** with arcade handling, while a wheel is on a loop facet, move
the car along the loop's surface by its speed and the step's fields instead of in a straight line,
whatever the step length:
- the arc position from the distance travelled (v × fields), the sideways position from the
  heading relative to the road (so steering moves the car across, and the drift needs the wheel
  as the arcade's yaw suggests, unless the arcade road proves otherwise);
- the position on the polygon (between section centres) and the pitch interpolated between the
  facets' pitches, so it turns smoothly as the arcade's suspension makes it;
- the heading and roll from the relative yaw and the pitch, composed properly instead of the
  native inverted ×−3/2;
- the handling module's 1 g along the slope from that pitch; the car leaves the surface when
  v²/r falls below the inward component of gravity (about 29 MPH at the top), into the
  ballistic flight;
- off the loop's sections, and on CUSTOM1 = 0 and 1, nothing changes.

**Implemented** (the user: "Steer a little."): `HardDrivinLoop.s`, CUSTOM1 = 2 only.
- **Where:** `_loop_step` at the start of `_dispatch_after_physics`, after each step's physics
  and before drawing. It recognises the loop by its section pitches (0, 60, 180) and holds the car
  from halfway along the flat section before it (section 36) to halfway along the one after
  (section 49), so the pitch blends in and out.
- **Motion:** the facets are walked by the step's distance (3v/128 units a field, the native
  1.5 v per 8-field step, times `_time_scalar_fields`) round the cylinder, and sideways by
  sin(relative heading); a car going straight keeps its place on the cylinder while the road
  drifts past it, so the drift needs about 6.5° of heading, i.e. a little right steering on this
  loop. The position is put on the facet plane, the pitch interpolated between facet midpoints,
  and the heading, pitch and roll composed exactly from that pitch and the relative heading (the
  native `$2B0E` arcsine, sine, cosine and the `$9564` root), so the inverted heading stays right.
- **The model:** `_handling_turn` adds the model's turn to the relative heading while the loop
  holds the car; its gravity uses the sine of the loop's pitch (the native sine lags a pass, and
  `G($F791)` would leave the slope to the native fall, which the loop discards).
- **Letting go:** at the end; off the road's edge or when v² < 253·G·(−cos θ) (v²/r below the
  inward pull of gravity, about 29 MPH at the top), the car is lifted 24 units off the surface,
  its contact cleared, and `_flight_release` lets that one flight start at any pitch (ballistic at
  1 g); on a crash or a recovery's road pointer it just lets go.
- **Probes** (A500 unless named, `tmp/loopprobe.sh`, the player-like `c4_loop_steer.s` driver that
  aims the relative heading at the drift less a share of the offset): through the loop with all
  four wheels down at 63, 80, 90 and 112 MPH entries (`ls3-*`), on the 68020 (`ls3-*-0020`) and the
  68060 (`ls3-*-6050`). Coasting in at 506: over the top at 235 (49 ft/s, v²/r 1.3 g), the loss
  that of a 110 ft climb plus about 25% drag and engine braking (`lc5-559`); at 88 ft/s under full
  throttle the top is passed at 79 ft/s (the arcade's demo: 90 in, 70–75 over the top). It leaves
  5.5° off the road's heading (the demo about 4°). The wheel held straight: off the side near the
  bottom, a flight and a crash (`lw4-559`). Too slow (coasting in at 470 or 430): let go at
  110–124° of pitch, falls at 1 g and crashes landing on its roof (`lc7-*`).
- **Laps** (`lp13-a500`): `lap-main` 117.2 s without a crash, as round 9. `lap-loop` passes the loop
  on its second entry and reaches stunt 89, further than any earlier build (stunt 57); its first
  entry falls from the top (its pursuit steering works in car space, which fails upside down).
  `lap-stunt` and `lap-jump` crash where they did.
- **Bugs fixed on the way:** distance lost across facet crossings (the facet routine overwrote the
  distance left), a sign-extension that made every step cross to the end, the gravity sine.
- **Fixed in round 12:** a car falling off upside down lands roof first, the body passes through
  the road before the wheel points touch, and the crash keeps its fall velocity, so it sank below
  the road until the replay. Not measured: the cost (only while on the loop: about a dozen trigonometric
  calls and a root per step).

Found, not caused: a probe slave 196 bytes shorter than a working one did not boot ("live game not
found"); padding its helper to a longword (`cnop 0,4`) fixed it, so something after the verify
code needs longword alignment.

**H3 round 11 (2026-10-23): suspension and vertical motion.** The user: "Implement suspension and
vertical motion." The arcade car pitches on a front and a rear spring and damper 5 ft either side
of the centre of gravity (`$70D590`, ARCADE_ROMS.md); its loads are the tyres' loads, and the tyre
forces act 1.567 ft below the centre of gravity, so braking dives and driving squats. The native
contact pass (`$CAB6`) instead pushes the car out by the wheels' average depth and snaps its pitch
to their height difference.
- **The native heights are too coarse for heave:** the wheel heights `G($947E..$9484)` come from
  `$C36C`, interpolating a ground triangle whose corners `$C022` has already rounded to words: whole
  units, 0.18 ft, about 540 lb on a spring. A heave spring on them chatters, and a tracked ground
  height (`su5`) was biased at constant pitch. Asked the user; chosen: **pitch springs, native
  height**.
- **Implemented:** `HardDrivinSuspension.s`, CUSTOM1 = 2 only, hooked at `$CB52` and `$CB94` of the
  contact pass. On its ground branch (three wheels down, or a diagonal pair) the springs own the
  pitch: the ground's pitch from the wheel heights, interpolated to the axles and smoothed; the
  springs and dampers stepped per field (at most 50), with the model's longitudinal force; the
  pitch snap skipped, the native push and landing test kept. The axle loads feed the model's tyres
  (`.lagged`), and the model's slope force subtracts the springs' pitch against the ground
  (otherwise a braked car crept forward from its own dive).
- **Vertical motion:** the native motion moves the car along its body pitch, so the springs'
  pitch against the ground climbs it off (or into) the road: that rise is taken back each pass,
  and what is left of the rounding falls under gravity (the native push only lifts).
- **The jump's lip:** with springs on every contact (`su10`) the take-off rotation was lost, and
  flights ran 72–91 fields nose up against HEAD's 38–50. With fewer than three wheels down the
  native pair contact turns the car again, and the pitch velocity hands over to the native pitch
  rate: the seven `jump_clear` probes (`tmp/jumps.sh`, `tools/jump_pass.py`) crash 3 of 7 as HEAD,
  flights 39–65 fields, nose down at landing.
- **Feel (A500, `su11-a500` against `b13-a500`):** C1c at 60 MPH yaw gain 41.8 (b13 41.0, arcade
  43.1), max lateral 1.12 g (1.11; 1.08); 0–60 5.85 s, top speed 135 MPH; C1e braking in a corner
  −28.6% yaw change after 2 s (−25.5%; arcade −14.0%); C1f slide brake at 90 MPH largest sideslip
  3.0° (2.0°; arcade 1.1°), at 60 MPH 2.2° (1.7°; 0.4°): the faster load transfer moves these away
  from the arcade. Braking dive about 1.25–1.5°.
- **The arcade's axle loads** (MAME, `plans/n_trace.lua` around `c1f_slide`: the z components of
  the wheel force vectors at `$74E3C0`/`$74E480` +80 every MSP frame; `c/loads/c1f-90-brake`, its
  log identical to the base run's): the front rises from 1,660 to 2,228 lb about 0.1 s after the
  brake, the rear falls to 1,030–1,140 (full pedal, about 0.87 g), front plus rear varies from 3,160
  to 3,630 lb, and on release the front falls to 1,600 and the rear rises to 1,800 within 0.2 s.
  `su11` peaks at 2,232 and 1,317–1,360 at its 0.7 g, its sum 3,460–3,690 lb; `b13`'s lag rose to
  2,150 without overshoot and held the sum at 3,525. So the springs transfer the load as the arcade
  does, and the larger C1f sideslip is the brake input that H1 found: the arcade's full pedal locks
  the front wheel and takes its lateral force away (largest yaw rate 10.5 °/s against our 19.7).
  No change.
- **Laps:** `lap-main` 117.0 s without a crash. `lap-stunt`, `lap-jump` and `lap-loop` crash 6, 6
  and 9 times in 240 s (round 10: 6, 7, 7), reaching stunt 52, 53, 84 (59, 51, 89): within the
  runs' spread.
- **Loop probes** (`sl-*`, as `ls3-*`): through the loop with contact kept at 240, 300 and 419
  entries, faster over the top (92, 99, 115 MPH against 89, 94, 106); 559 and 782 crash as before.
  419 now crashes at field 419 after leaving the road past the loop's exit; round 10's build,
  run longer (`bl-419`, 520 fields), crashes there at 446.
- **Cost on the A500** (`su11-cost-c1c60` against `su11-cost-b13-c1c60`, the C1c 60 MPH plan, 500
  fields from 600): the springs take 1.15 ms a frame at 3.16 fields (0.36 ms, about 2,600 cycles, a
  field; `_suspension_spring` 0.37 ms a frame), the model 0.26 ms more; frames 63.4 ms against
  61.5 (3.2%). `frame_budget.py` now counts `_suspension` and `_loop`.
- **Bug fixed on the way** (2b0fff8b): `_loop_enter` read through the road cursor `G($98E4)`,
  which the native search at `$DE92` leaves as an uninitialised local (an odd address) when no
  section qualifies: an address error on the stunt track.
- **Release build:** `r14.slave` boots to the title screen on the A500 at CUSTOM1 = 2 and keeps
  running, as `r13` (`tools/boot_check.py`, samples where it runs and takes screenshots).
- **Open:** the C1f and C1e brake differences above (the brake input, not the springs); roll stays
  native (as the arcade's).

**H3 round 11, the drive (2026-10-23).** The user: "It feels much more like a car but the rear end
gets loose really easily - for example when trying to jump the first ramp of the stunt track."
- **Reproduced:** `h3-ramp-50` … `h3-ramp-110` (`build_feel.py`) seed the car on stunt section 13,
  40 units left of the centre line, and follow the road up the first ramp (sections 17–19, 9°)
  under full throttle, over the lip and down. `tools/ramp_stat.py` counts passes with the rear
  load at zero on the ground and the largest slip and yaw rate. `lap-jump` cannot show it: its
  route leaves the ramp's left edge (130 units off the centre line) in every build.
- **Cause:** the springs took their pitch from the ground through the native whole-unit wheel
  heights, while the height stays native. At the ramp's foot, the crest and a nose-down landing
  that put an axle past its free length while the native contact had its wheels down, and a pass
  (7–10 fields on the A500) with no rear load spun the car (su11's ground estimate also lagged
  0.7 s, a quarter a pass). Following the ground at once, a travel stop, the pass's average load
  and starting at rest each moved the spin elsewhere (su12–su16).
- **Fix (su17):** the body's pitch is the ground's pitch that the native pass measures, plus the
  springs' own displacement, which only their forces move (braking, driving, the tyres), within a
  travel stop of 0.3 ft at the axles (3.4°; 0.7 g of braking takes 0.12 ft). The springs start at
  rest on the ground branch, and the tyres get the pass's average load.
- **Results (A500):** the seven ramp runs: no spin, largest slip 0.9–2.3° (b13 0.7–2.2°; su16 spun
  at 110, su15 at 100, su12 at 80). Feel matrix as su11 and b13 (C1c gain 41.3, C1f 90 brake 2.6°
  of sideslip, su11 3.0), braking dive to 1.5°. `lap-main` 117.1 s clean; `lap-stunt` and `lap-jump`
  6 and 7 crashes; `lap-loop` stunt 54 (it fails its first entries in every build). Loop probes as
  before (240 and 300 pass, 300 losing contact briefly at −136°; 419, 559, 782 crash). Jump probes 3
  of 7 crash as before; nine full-throttle entries from 300 to 420 (`tools/fastjumps.sh`) on each
  build: no crash anywhere, the lip lottery in all (b13: one flat take-off, one without rotation;
  su11: one no flight, one without rotation; su17: one no flight, one flat, three without
  rotation). Cost not re-measured (the smoothing out, a division a pass in).
- **Release:** `r15.slave` boots to the title (`tools/boot_check.py`).
- **The faster machines** (`a1200-020`, `a4000-060-50`; passes of 1–2 fields): the seven ramp runs
  slip at most 0.3–1.5° in both builds, no spin. But the ramp's landing crashes in most runs in both
  builds (68020: b13 5 of 7, su17 6 of 7; 68060: 3 and 4; A500: 0 and 1, su17's at 110 MPH on the
  climb, as b13's on the faster machines). On the 68020 the car touches down, then rises 26 units
  with no wheel down and crashes coming back (`b13-0020/h3-ramp-70`, fields 330–360): a bounce off
  the landing that predates the springs, in the per-native-step landing and flight code (rounds 4
  and 6). Round 12 found the A500 was the odd one out.

**H3 round 12 (2026-10-24): the ramp's take-off and landing.** The user chose to measure the
arcade's landing rule before setting the take-off and the limit. CUSTOM1 = 2 only.
- **The faster machines were right.** The arcade's attract demo jumps the stunt road's first
  ramp after the loop (ARCADE_ROMS.md, "The jump in the attract demo"): it leaves along the ramp's
  slope (velocity 9.4–10.2°, body 7–8°) and flies ballistically, 17.2 ft/s up, 31.3 ft/s², 1.83 s,
  6 ft over the lip. The 68020 flew the same (`b13-0020/h3-ramp-50`: 16.8 ft/s, 32.6 ft/s²,
  1.92 s; Amiga fields are 50 Hz). The A500 left nearly flat (0–1.5 ft/s up, 1 ft over the lip):
  - the rear-only tip (`CONTACT_TIP`) adds per field, and a 68000 pass counts all its 10 fields on
    the rear wheels: −17 quarter-degrees per native step against the arcade's 3.7 × 10 ft / v
    (−11.6 at the lip; the 68020's two passes reached −8);
  - the flight held the pitch after its first pass in the air, which had turned with the pass's
    length (9° to 3° on the 68000, 9° to 8.25° on the 68020).
- **The arcade crashes no landing** (ARCADE_ROMS.md, "The crash checks"): speed, yaw, scenery,
  surface 7 and a force sum over 52,000 lb, which a landing cannot reach with each axle bearing
  at most the car's weight. With the arcade's flight on Domark's course (a landing ramp lower than
  the arcade's: 8.7 ft up 170 ft past the lip against about 12 ft at 183) the car comes down on the
  flat at its foot at about 46 ft/s, over round 4's 39 ft/s (`LANDING_U_ARCADE`): with that rule the
  candidate (`tk1-*`) crashed 5, 7 and 6 of the 7 ramp runs on the A500, 68020 and 68060.
- **Changes:** `_contact_pitch` stops the tip at the arcade's take-off rate for the speed
  (`CONTACT_TIP_V` 6464 / v). `_flight_fall` holds the pitch trig of the last pass with a wheel
  down (`_flight_ground`, `_flight_lip`), so the take-off follows the lip's slope at any pass
  length; the loop's release keeps the current pitch. `_motion_fall_ground` judges no landing with
  arcade handling (`LANDING_U_ARCADE` removed); CUSTOM1 = 0 and 1 keep `LANDING_U`.
- **Results** (`tk2-*`, the ramp runs `h3-ramp-50..110`, `tools/ramp_flight.py`): every landing from 50–100 MPH survives on
  the A500, the 68020 and the 68060, all three flying alike (2.0–2.3 s, 200–265 ft, 4–7 ft over the
  lip; before, the A500 flew 1.1–1.3 s and 1 ft over). No spin: slip at most 0.9–2.1°. The 110 MPH
  runs crash on the climb on the A500 and 68020, as before. `lap-main` 117.1 s clean. Jump probes
  (`tk2j-*`): all 7 land (round 11: 3 of 7 crashed). Loop probes (`tk2l-*`, 450 fields) as round 11
  (240 and 300 pass, 419, 559, 782 crash). `lap-stunt` to 6,016 fields: the ramp at stunt 21 flew
  104 fields and landed at 78 MPH; the route's driver crashes elsewhere, as in every build.
  CUSTOM1 = 0 and 1 install the same game code as r15. `r16.slave` boots to the title.
- **The roof landing** (round 10's open item): falling off the loop's top upside down, the car
  reaches the road roof first, the crash turns its wheels away from the road, and with no pass on
  the ground again its fall carried it 41 ft through the road (`rf1-470`, coasting in at 470).
  `_loop_floor` (`HardDrivinLoop.s`, after each step with arcade handling) holds a crashed car
  upside down at the height of its last pass in the crash with a wheel down: it now slides down
  the loop's inside to the road (`rf5-470`; lowest −26 units for the one pass that crosses, from
  −232). Loop probes, `lap-main` (117.0 s, clean) and CUSTOM1 = 0 and 1 as before; `r17.slave`
  boots to the title.
- **The steep crash:** the crash keeps the speed (every crash starts at `_motion_crash_start`;
  this kind leaves the speed word), and the native motion carries the car along its body: coasting
  in at 430, the car let go at the top crashed at 65° and climbed 87 ft, staying up until the
  recovery (`rf5-430`). `_loop_floor` now levels the flight's hold for a crashed car beyond 45°
  (the horizontal direction of travel, falling at 1 g): it comes down on the road 175 fields after
  the crash (`rf6-430`; its first 30 samples still rise with the native crash drift). Loop and
  jump probes, `lap-main` (117.0 s) and CUSTOM1 = 0 and 1 as before; `r18.slave` boots.
- **Cost on the A500** (`r18-cost-c1c60-c2` and `-c1`, the C1c 60 MPH plan, 500 fields from 600):
  at CUSTOM1 = 2 frames take 63.5 ms at 3.18 fields (round 11's su17 64.2 ms at 3.23), the model
  6.32 ms a frame, the springs 1.22, the loop module 0.10: round 12 adds nothing measurable. The
  physics phase takes 10.1 ms a frame against 4.2 at CUSTOM1 = 1, whose frames take 60.2 ms at
  3.01 fields (not the same scene: the cars drive differently). So about 5.5% more frame time on
  the A500, the 6.6% question for the release.
- **Open, for the user's drive:** the brake at full mouse pedal is 2,470 lb ft (0.73 g, no lock);
  the arcade's full pedal is 4,653 (0.87 g, front lock and plough). H1 kept the softer one because
  the full one stopped corner braking from turning the car.

**H3, for the user:** the release build with the arcade's take-off and landings (round 12), the springs after the drive (round 11), the loop (round
10), the traffic's 0.45 g, round 9's real scale and the first drive's fixes is
`tmp/build/HardDrivin-arcade.slave`, also `r18.slave` (r17 without the steep crash's fix, r16 without the roof landing's fix, r15 before round 12's take-off and landing, r14 the first springs, r13 the loop without the springs, r12 without the loop, r10 the first drive's fixes; round 9's is `h3r9.slave`, round 8's is `h3r8.slave`, round 7's is `h3r7.slave`, round 6's is `h3r6.slave`, round 5's `h3r5.slave`, round 4's `h3r4.slave`, round 3's `h3brake.slave`, round 2's `h3r2.slave`, 16b1981's `clock.slave`, round 1's
`HardDrivin-arcade-h3r1.slave`, G's `HardDrivin-arcade-g.slave`). From the game directory:

```sh
make run SLAVE=tmp/build/HardDrivin-arcade.slave FSUAE="$FSUAE_ARM" WHD_ARGS="CUSTOM1=2 CUSTOM5=1 CUSTOM4=0" WAIT=1
```

Questions for the drive:
- slides and their recovery, and the cornering drag that now slows the car in corners;
- the steering response and the mouse range (full lock is ±320 counts from the centre);
- braking: straight-line stops, and braking in corners, which now turns the car in (round 3);
- the real scale (round 9): speed past the scenery, the arcade's time limits with CUSTOM5=1;
- the mouse pedals (round 8): right button gas, left brake, 0.1 of the travel per field;
- the arcade engine and gearbox (round 7): the automatic's shifts, engine braking when
  lifting, 1 g on slopes, the grass top speed;
- spins and slides off the road, and the car on slopes and over crests (round 2);
- the springs (round 11): dive under braking, squat under power, the car over crests and on
  landings;
- the loop (round 10): about 6.5° of heading to the right keeps the car on the drifting road,
  over the top at 29 MPH or more;
- loop entries and the jump: the arcade's take-off (round 5) and flight, ballistic under 1 g
  (round 6), at CUSTOM1 = 2, and the ramp's take-off along its slope (round 12); no landing
  crashes, as the arcade (round 12);
- whether the A500 cost is acceptable: about 5.5% longer frames (round 12's measurement).

Each tuning knob is a constant in `HardDrivinHandling.s` (the force limits) or in
`handling_fx.py` and the module together (the tyres, the steering ratio). Changing the twin
also means re-running `check_handling_step.py`, H1's matrix and H2's laps.

### H3, refined (agreed with the user 2026-11-01)

H3 was "the user drives, I fix what they find", with no end and no budget. From round 13 it
measures the gap to the arcade, closes it in order of importance within a cost budget, and
ends when every gap is within tolerance or accepted.

- **H3a Gap table.** One scored table: arcade against CUSTOM1 = 2 on the A500 and the 68020,
  with E2's tolerance (10%, or C's repeat floor). Rows, reusing C, F and H1 where they can:
  - steady cornering: steering gain, the 1.08 g limit, understeer (C1c), low speed (C1g);
  - transients: step-steer yaw overshoot (C1d), lift-off in a corner (C1e), slides and their
    recovery (C1f);
  - braking: straight 0.87 g, front lock, in a corner and in a slide (C1b, C1e, C1f);
  - acceleration, shifts, top speeds on road and grass (C1a, round 7's runs);
  - vertical: crests, the ramp jump, landings, the loop (the MAME attract demo, round 12);
  - the crash rules: the arcade's checks (`$708BD0`) against the Amiga's.
  Each row: measured value, within tolerance or not, the likely fix and its cost.
- **H3b Budget.** One A500 ceiling, set with the user: frame time against CUSTOM1 = 1 (now
  +5.5%, round 12's measurement). The model runs every field on the 68020 and faster. Every
  H3c change is priced against it (`capture_solver_profile.py`, `frame_budget.py`).
  **Set 2026-11-01:** the user: "allow up to about 10% over CUSTOM1=1 on the A500" (now +5.5%).
  The arcade handling cannot run without the enhanced simulation (the model needs elapsed
  time; the original steps once per drawn frame), and on the 68000 the enhanced simulation
  follows the frames anyway, so the budget prices the handling alone.
- **H3c Close the gaps,** worst felt gap first, one A/B change each, H1 and H2 re-run after
  each. Known candidates:
  1. the brake: the arcade's 4,653 lb ft with front lock and plough (the user decides: H1
     kept the softer brake because the full one stops corner braking turning the car, as
     the arcade's does);
  2. braking in a slide: 3.0° sideslip against the arcade's 1.1° (since round 11);
  3. ground sampling on the A500: contact once per 7–10-field pass and whole-unit (0.18 ft)
     wheel heights; per-field fractional ground would make the A500 behave like the 68020;
  4. the crash rules: which native causes (barriers, objects, surfaces) stay;
  5. the steering: the mouse range (±320 counts) and response against the arcade's wheel;
  6. traffic collisions: still the native response.
- **H3d The user's drives** after each group of changes, not each round. Feel findings become
  rows in H3a's table.
- **Exit:** every row within tolerance or accepted as a deviation (some are by design: the
  Amiga course differs, its landing ramp is lower), the cost within H3b's budget, the user's
  drive OK. Then I1.

**H3a, the gap table (2026-11-01, r18 = 18504326, CUSTOM1 = 2).** Matrices `tmp/prof/h3a-a500`
and `h3a-020` (`run_feel.py --custom1 2`, C's 25 plans and `h3-ramp-50`…`110`), report
`tmp/prof/h3a-feel-report.md` (`amiga_feel.py report tmp/arcade/mame/c/base`), ramps
`tools/ramp_flight.py`. Tolerance 10%. "A500 / 020" are the two machines.

| Row | Arcade | A500 / 020 | Verdict | Candidate |
|---|---|---|---|---|
| C1c yaw gain 30 / 60 / 90 MPH (°/s/k) | 31.7 / 43.1 / 45.4 | 30.9 / 41.7 / 41.6, 31.3 / 42.0 / 42.2 | pass (90: −8%) | — |
| C1c max lateral 30 / 60 / 90 (g) | 1.08 / 1.08 / 1.06 | 1.07 / 1.13 / 1.08, 1.08 / 1.11 / 1.07 | pass | — |
| C1c steer at 95% of the limit, 90 MPH | 588 | 487 / 513 | fail (−13 to −17%) | steering (5) |
| C1d steady yaw and lateral per steer word | — | within 10% (small steps quantised: 218 against 178) | pass | — |
| C1d yaw 63% rise (ms), large steps 30 / 60 / 90 | 97 / 56 / 43 | 141 / 93 / 83, 102 / 71 / 56 | A500 fail, 020 near | A500 sampling (3) |
| C1d "within 10% after" (s) | 0.15–1.09 | 0.12–1.48 | fail both, suspect | check the metric first: headings are ¼° a field |
| C1e lift and power, 0.7 / 0.9 g | yaw change 13 / 20%, speeds | within a few %, power's first 1 s −31% vs −18% | mostly pass | — |
| C1e brake in the corner: largest yaw change in 1 s | +133% / +83% | −32% / −44%, −31% / −28% | fail: no spike | brake (1) |
| C1e brake: yaw change after 2 s | −19% / −14% | −29% / −30%, −30% / −27% | fail | brake (1) |
| C1f slide 60 hold: largest sideslip, after 4 s (°) | 4.7, 1.7 | 8.8, 5.1 / 5.0, 1.7 | A500 fail, 020 pass | A500 sampling (3) |
| C1f slide 90 hold / release / counter | 7.7° slip, settles 0.62 / 1.38 s | 8.3 / 8.1°, 0.66–0.78 / 1.58–1.68 s | pass, counter overshoot 7.5 / 6.4° vs 5.2 | — |
| C1f speed lost in 5 s of a held slide (MPH) | −0.2 | 6.6 / 4.9 (60), 4.8 / 4.6 (90) | suspect: the throttle stays at 40–70% (`trace … c1f-60-hold`): the fixture's cruise moves it 2 a native step and lags the slide's drag | cruise control, not the car |
| C1f brake 60 / 90: largest yaw (°/s) | 6.1 / 10.5 | 18.5 / 16.7, 18.7 / 18.8 | fail (2–3×) | brake (1), slide braking (2) |
| C1f brake 60 / 90: largest sideslip (°) | 0.4 / 1.1 | 2.1 / 2.8, 1.5 / 2.7 | fail | brake (1), slide braking (2) |
| C1b full brake: deceleration (g), stop from 60 (ft) | 0.87, 143 | 0.73, 180 / 179 | fail (−16%, +26%) | brake (1) |
| C1g low speed: yaw, radius at 25–100% lock, 5–15 MPH | — | within 5%; 15 MPH lateral 0.79 vs 0.92 on the 020 | pass | — |
| C1a 0–30 / 0–60 / 0–100 from the gas (s) | 3.23 / 6.26 / 13.27 | 2.7 / 5.7 / 12.5, 2.7 / 5.8 / 12.6 | 0–30 fail (−16%), rest pass | launch (new) |
| C1a top speed | 140 | 136.5 still rising when the car leaves the test ground at 31.7 s | unmeasured | longer ground or a lap |
| C1a coast in gear, C1a stick, C1b half pedal | 0.11–0.20 g, … | not run (ground ends; no stick; no half-pedal plan) | unmeasured | plans |
| Stunt ramp (attract demo): lip pitch, flight | velocity 9.4–10.2°, body 7–8°; 1.83 s, 183 ft at ~100 ft/s | body 5.2–9.5° (4 of 6 runs 5–6°), 7.8–9.5°; 2.0–2.3 s, 200–264 ft at 103–129 ft/s | 020 pass, A500 take-off flat; longer flights by design (faster lips, lower landing) | A500 sampling (3) |
| Ramp landing pitch (°) | the 10° downslope | −20 to −26 (two runs 0 / −2), −10 to −15 | A500 nose-down | A500 sampling (3) |
| Ramp at 110 MPH | — | crashes on the climb, both | as before | crash rules (4) |
| Loop (round 10–12 probes) | 61 MPH entry, slip < 1° | over at 29+ MPH with ~6.5° right heading | accepted (the drifting road) | — |
| Crash rules | speed, yaw, force, surface 7, scenery | native barriers, objects, surfaces; no landing crash | to compare | crash rules (4) |
| Traffic collisions, steering range | — | native; ±320 counts | unmeasured | (5), (6) |
| A500 cost | — | +5.5% frame time against CUSTOM1 = 1 | H3b decides | — |

**Ranking for H3c** (largest felt gap first): (1) the brake, which also explains most of (2);
(3) A500 pass sampling: slides, step-steer lag, the ramp's take-off and landing differ from the
020, which matches the arcade; the launch (0–30 16% quick); then the crash rules, steering and
traffic. Test fixes first: the C1d settle metric, the fixture's slow cruise in slides (done,
below), a test ground long enough for top speed and coasting.

**H3c (1), the brake (2026-11-01, 11d95274, `r19.slave`).** The user: "take the arcade's full
brake with front lock and plough. If possible, make it such that if it turns out to be
unplayable with the mouse it's easy to turn off (or otherwise adjust)."
- Full pedal is the arcade's 4,653 lb ft (`HANDLING_FX_BRAKE`); the twin was already checked to
  −4,653 (`check_handling_step.py`).
- **The pedal rate matters:** at a tenth a field the front spends several fields braking near its
  lock point (~2,500 lb ft), the load leaves the rear and the car spins (C1f 90 brake on the 020:
  11.4° slip, 29.7 °/s, against the arcade's 1.1°, 10.5). The arcade's test steps the pedal.
  Brake pedal rates tried, A500 C1f 60 / 90 brake slip and yaw: 10 → 2.1° 18.5, 6.4° 24.1;
  25 → 1.1° 12.5, 3.3° 16.4; 34 → 0.9° 9.2, 2.8° 16.3; 100 → 0.6° 6.0, 2.0° 12.0. Kept 34
  (`HANDLING_PEDAL_BRAKE`, full in 3 fields): close to the step and a click still brakes partly.
- **`CUSTOM4=1` ("Arcade brake: Soft")** restores r18's brake, 2,470 lb ft and 10 a field
  (`_handling_brake`, `_handling_brake_rate`, set at install); its matrix equals r18's on the
  020. Not in VERIFY_SLOW builds, whose CUSTOM4 is the delay. `capture_feel.py` and
  `run_feel.py` take `--custom4`.
- **Results** (`r19b-*`, `r19s-*`, `r19-*`): C1b 60 MPH 0.90 g, 142 / 138 ft (arcade 0.87,
  143); 100 MPH 353 / 348 ft (390). C1f brake 60: 1.1° 11.3 °/s / 1.0° 12.5 (0.4°, 6.1);
  90: 2.7° 16.3 / 3.2° 18.7 (1.1°, 10.5). C1e brake now ploughs, −123% and −88% after 2 s,
  because the plan brakes at full pedal while the arcade's C1e is half pedal (1500): not
  comparable until a half-pedal plan exists. Everything else in the matrix as r18. `lap-main`
  117.2 / 116.8 s clean with either brake; `lap-stunt` crashes as often as r18's (r18c-*: 5).
  CUSTOM1 = 0 and 1 install the same code.
- Drive slave `r19.slave` = `HardDrivin-arcade.slave`. Not pushed.

**H3a re-run with a fixed test driver (2026-11-01, `h3a2-a500`, `h3a2-020`, r19).** The
A500's gaps (H3c 3) were the tests, not the car:
- **Slides:** the fixture's cruise aimed the gas from G($991C), which the model publishes once a
  pass, so on the A500 it held a button for 3–4 fields and pumped the gas through the slide
  (drive force −550..+590 lb pass to pass), moving the load to and from the rear. With the gas
  held instead (`c1f-60-keep`) the A500's model slip fell from 7.5° to 3.3°; slower passes on
  the 68020 (VERIFY_SLOW +1/+2/+4 fields: 4.4/4.2/5.9°) and entry speed (A500 59.8–62.3 MPH:
  5.5–7.5°) did not explain it. `feel_fixture.s` now follows the pedal field by field
  (`FEEL_PED`, resynced from G($991C) at a pass when 30 apart). C1f 60 hold: A500 5.2° / 020
  4.0° (arcade 4.7), after 4 s 2.4 / 1.9 (1.7), speed lost 2.6 / 0.2 MPH (−0.2, was 6.9 / 4.9);
  90 hold 7.5 / 8.6° (7.7). `amiga_feel.py` keeps the cruise's gas within 64..3968 so feel.py
  never takes a closed or open pedal for C1e's lift or power (it measured 58 MPH "after 2 s").
- **Step steer:** the model's own yaw rate (model.bin) reaches 63% in 3 fields and 90% in 5–6
  on both machines; the A500's longer measured times are its poses, once a frame. That is the
  frame rate: accepted.
- **Ramp:** body pitch in the air A500 5.2–10.2° (mean 7.9), 020 6.2–9.5° (8.0), arcade 7–8°;
  flights 230–278 / 208–256 ft. The first table's flat A500 take-offs were scatter: the lip is a
  lottery on both machines.
- So H3c (3) needs no game change and the A500 cost stays +5.5%. Left over 10%: C1e brake (needs
  a half-pedal plan), C1f brake yaw (12 / 12.5 °/s at 60 against 6.1; 15.2 / 17.2 at 90 against
  10.5), C1c 90 MPH gain (40.1 / 40.9 against 45.4, −11%), counter-steer overshoot at 90
  (7.2 / 8.2° against 5.2), C1d settle times (the metric), C1a 0–30.

**H3d, the drive of r19: the shake (2026-11-01, 7e1fd5d2, `r20.slave`).** The user: "when
accelerating the car is constantly shaking vertically (nose dropping?)".
- **Seen in `h3a2-a500/c1b-full`:** under full power in first gear the pitch G($994C) ran
  3, 5, 7, 4, 6, 3… quarter degrees, a saw-tooth of 1° about every 3 passes (5 Hz), the height
  with it; coasting stayed still.
- **Cause:** `_suspension_measure` took the ground's pitch every pass as the body's pitch less
  the native wheel heights' difference, whole units (0.64° for a pair). With the springs
  displaced (squat, dive) the rounding went back into the next pass's pitch: x' = D + x − Q(x)
  has no fixed point unless the displacement D is a whole step, so the pitch climbed by D's part
  of a step each pass and dropped by a step.
- **Fix:** the ground's pitch (`SU_GD`) is held until a new estimate is more than a pair's whole
  unit (`SUSP_GD_BAND`, 0.0555 ft at the axles) away; `SU_VALID` = 1 on touch-down takes the first.
- **Results (A500, `su20-a500` against `h3a2-a500`):** c1b-full squat a steady 4 quarter degrees,
  3 pitch reversals in 580 fields against 75. Ramps 50/70/90/110: rear unloaded 2/1/2/1 passes
  (0/2/1/1), slip 0.8/1.2/1.6/11.6° (1.1/1.3/1.8/9.9). `lap-main` clean, 1,665 fields a lap (1,662).
  `lap-stunt` 2 crashes, 5 recoveries (r18's 5 crashes). `r20.slave` boots to the title.

**H3c (4), the crash rules: measured (2026-11-01, r20).** `capture_feel.py --crash-sites` breaks
on the four native writers of the crash countdown G($9606) and logs which fires (`crash.txt`),
with the car's move and the wall segment (`$BFEE`) or the object (`$BCE0`/`$BDBE`).
- **The native rules** (`$BAxx..$C01E`, `$CC2E`):
  - `$BCE0` scenery object: crash above 45 MPH (G($992C)), any angle; below, bounce (the
    movement vector reversed, speed zeroed);
  - `$BDBE` traffic: the same 45 MPH rule;
  - `$BFEE` wall segments (list G($995C), G($9960) of them, while G($ADD8)): the pass's move
    crossing one crashes at any speed;
  - `$CC54` landing: with arcade handling the depth test is skipped (`_motion_landing_depth`),
    so it fires only on a touch-down with cos pitch or cos roll below 0 (upside down, vertical)
    falling faster than 50: every hit in the stunt laps is a failed loop or a roof landing.
- **The arcade's scenery rule** (`$70B2D0..$70CEA0`, lift.txt): the car's velocity in the
  object's frame (ft/s × 40, `$70D450`) on the axis of the face it meets (`$751E30` = 1..4):
  above ±2400, which is **60 ft/s (41 MPH) along the face's normal**, it crashes; below, that
  component is reversed and halved (`× −50/100`, at least ±1 ft/s). So the arcade scrapes a
  barrier at any speed at a shallow angle, and the Amiga crashes on any wall touch and on any
  object above 45 MPH.
- **Where the laps crash** (`cs-a500`, `cs-a1200-020`, lap-stunt / lap-jump / lap-loop, 240 s):
  A500 lap-stunt 2 roof landings; lap-jump 4 walls (one beside the first ramp's foot, three at
  stunt 53, segment (25275, 14650)–(25400, 15450)) and 2 roof landings; lap-loop 2 walls (stunt
  53), 5 roof landings, 1 traffic. 68020 lap-stunt 7 objects at 55–89 MPH (stunt 15, 39, 42,
  53–54, 95–216 units off the centre line but one), lap-jump 1 wall, 1 traffic, roof landings,
  lap-loop 3 objects, 1 wall (stunt 45), 2 roof landings.
- **Ramp at 110 MPH** (`h3-ramp-110`): `$BFEE`, the wall from the ramp's left corner (32325,
  18000) to (34125, 17100). The kink between stunt sections 13 and 14 needs about 1.6 g at
  110 MPH against the car's 1.08 g: it runs 175 units left, off the road, into that wall. By
  design (any car runs wide there), not a crash rule.
- **Candidate change:** walls and objects take the arcade's rule: crash when the speed along the
  hit face's normal exceeds 41 MPH, otherwise reflect that component at half and keep the car on
  its side. Traffic stays native until (6) measures the arcade's 68010 rule; roof landings stay.
  The user (2026-11-01): the arcade rule.

**H3c (4), the arcade's scenery rule (2026-11-01, f6967ce6, `r21.slave`).**
- **Walls** (`_handling_wall`, `$BF80`): the movement vector G($991E/$9922) (which carries the
  model's sideways speed) along the wall's unit normal; beyond `HANDLING_WALL_CRASH` (419 long
  units a native step, 60 ft/s) into the wall the native crash goes on; slower, 1.5 of that
  component comes off along the normal: the forward part (G($9448), G($944A)) into G($9928)
  (÷ 1.5), the sideways part (G($944A), −G($9448)) into HS_V, HS_V8 kept so the model does not
  take it for a collision reset; the car is put 1 unit clear along the normal (keeping its
  motion along the wall), no crash drift (G($9912)), the native thump (sound 7), and $C00A
  returns −1 so the caller rebuilds the scene as after a native bounce.
- **Objects:** the native objects are points found in a box ahead of the car (forward 2 to
  40 + MPH/3 units, ±30 + MPH/8 sideways), so a hit is head on and the normal speed is the
  speed: `_time_object_mph` (Scalar.s) is 41 with arcade handling, 45 otherwise. Traffic stays
  native (6).
- **Results** (`w3-a500`, `w3-a1200-020`, crash sites per 240 s, against `cs-*`): A500 lap-jump
  walls 4 → 1, lap-loop 2 → 1; 68020 lap-jump 1 → 1, lap-loop 1 → 0. `lap-main` clean on both.
  The rest are roof landings, objects at 55–89 MPH and traffic. At stunt 53 the car meets the
  wall at about 60° at 35 MPH: it stays out, its normal 30 MPH reversed at half, and since the
  body still points at the wall the rest is mostly sideways, which the tyres scrub: 5 MPH
  forward 0.1 s later, as the arithmetic gives. `h3-ramp-110` still crashes there (its 80 MPH
  run off the road meets the wall more steeply). CUSTOM1 = 0 and 1 install the same code
  (`check_installed_code.py` against r20); `r21.slave` boots to the title.

**H3c (5), the steering (2026-11-01): no game change; the C1c gain metric was biased.**
- **Range and ratio are the arcade's:** δ = 0.6109 rad × steer / 4096 (`$72DA20`, ±4092 at full
  lock, 35°); the mouse's ±320 counts give the same 0.611 rad (`HM_K_DELTA`). The arcade's
  steer-rate term (steer + rate × ticks / 2) predicts between its MSP results and has no
  counterpart to add with per-field mouse samples.
- **The model is the twin:** replaying the 68020 `c1c-90` run's own u, counts and fx through
  `handling_fx.FxCar` gives the game's yaw rate to 0.1–1 °/s. Held at 205 words and 90 MPH the
  twin settles at 8.1 °/s (39.4 °/s per 1000 words), the float model the same.
- **The arcade's 45.4 was the metric:** `feel.c1c` fitted |yaw| on |steer − centre| through the
  origin, the centre being the mean steer before the ramp. The MAME runs approach holding their
  heading with a steer offset and a yaw of their own (30 / 60 / 90 MPH: −8.5 / −9.4 / −19.7
  words, −0.24 / −0.55 / −0.85 °/s), so the offset counted as gain: at 90 MPH the raw arcade
  yaw is 7.34 °/s at −200 words, 36.7 per 1000. The gain is now the slope of yaw on steer with
  an intercept. Report `tmp/prof/h3c5-feel-report.md` (h3a2 runs): yaw gain 30 / 60 / 90 MPH
  arcade 31.2 / 37.6 / 35.3, A500 31.2 / 37.2 / 36.7, 68020 30.8 / 39.2 / 33.3; curvature
  12.4 / 7.4 / 4.7 against 12.4 / 7.4 / 4.9 and 12.2 / 7.8 / 4.4. All within 6%.
- **Steer word at 95% of the maximum** is the first sample past it, so the cruise's gas
  pumping moves it (90 MPH: 588 against 603 / 462): not a steering gap.
- Gap table rows "C1c yaw gain 90" and "C1c steer at 95%, 90 MPH" become passes.

**H3c (6), traffic: first reading (2026-11-01), not measured.** The Amiga crashes on a car above
45 MPH (`$BDBE`) and otherwise stops and drifts back, as for an object. The arcade's MSP takes
the 68010's collision words (`$794140..$794180`: an impulse direction, the other car's mass
and the closing speed, by their use) into `$727760`, a one-dimensional elastic collision of the
two masses ((m₁ − m₂) / (m₁ + m₂) and 2m₁ / (m₁ + m₂) applied to the velocity along the
normal, the approach clamped at −30), and sets the crash (`$7251B0`) when the result exceeds
`$751080` = 50 (ft/s, 34 MPH, if the MSP's usual units). The lift garbles that comparison, so
the threshold's quantity needs a MAME run into traffic (a plan steering into the car alongside
at the start, at a few closing speeds) before any change.

**H3d, the drive of r21: the nose drop on hills (2026-11-02, 3f89b13b, `r22.slave`).** The user
(A1200/040, 50 fps): "The car's nose still tends to drop for a frame in many situations; while
accelerating but also when coasting. Hills are also a problem."
- **Measured** at one pass a field (`a4000-040-25`, `lap-main`, `c1a-auto`), with a diagnostic
  build whose model log holds `_suspension_state` (and the wheel heights) instead of the model's:
  on hills and crests the ground's pitch `SU_GD` alternated pass by pass (4.45, 5.52, 4.20, 5.78,
  3.94°) and the pitch with it, 45 one-pass spikes of 0.5–1.5° on the lap; the height ran a
  saw-tooth (sinking 1/8 unit every few fields, lifted a whole unit by the native push).
- **Causes:** (1) where the slope changes the estimate moved by about twice the body's pitch
  (on flat ground once, as the 90-unit wheel spacing says; why twice there is not known), so an
  estimate taken whole swung back past the band each pass; (2) the height's take-back of the
  native motion's rise used the springs' displacement only, so the held ground pitch's error (up
  to the band, 0.64°) climbed the car off the road or into it.
- **Fix:** within the band the ground's pitch is held; up to twice the band it moves to the
  band's edge (moved half the way, a quarter degree of pitch moved the wheel heights' rounding by
  a unit and the estimate back: a quarter-degree flip each field); further it is taken whole (a
  ramp's foot, a lip) unless that reverses the last pass's move. The pitch word is rounded to the
  nearest quarter degree and kept within ¾ of one. The take-back uses the pitch word less this
  pass's estimate (the pitch before the measure lifted the whole car at a ramp's foot and spun it).
- **Tried and dropped:** halving the wheel scale (the dive doubled and lifted the rear wheels
  under the brake); half the distance or ¾ of the excess beyond the band (the lip followed late:
  the rear-pair contact turned the car nose down, −21° landings on the 040).
- **Results** (`tmp/prof/nd-040/dJ-*`, `suJ-a500`, `suJ-020`, `qfJ-040`; tools `/tmp`-only):
  - 040 `lap-main`: one-pass spikes 45 → 0 on the ground (the rest are flights); pitch reversals
    28 → 9 per 1,000 fields (native handling 7); height slope changes per 1,000 units over the
    first 21,000 (≥ 0.02 / 0.04 / 0.08): 8.9 / 5.5 / 1.0 → 5.8 / 3.0 / 0.6 (native 2.3 / 1.8 / 0.5).
    `c1a-auto` height steps ≥ 0.5 unit 73 → 0.
  - 68020 `lap-main` pitch reversals 27 → 7, height changes ≥ 0.3 unit a field 101 → 38 per
    1,000 fields; `lap-stunt` reversals 28 → 17.
  - A500: `c1b-full` steady under power and brake (1 reversal per 1,000 fields, as r20).
  - Ramps 50/70/90/110, slip (°) and rear-unloaded passes: A500 0.9/1.0/2.8/7.2, 0/1/1/0 (r20
    0.8/1.2/1.6/11.6, 2/1/2/1); 040 0.5/1.2/1.1/6.3, 3/3/2/0 (r21 1.0/0.9/1.3/1.1, 3/3/2/0); 020
    0.6/1.1/1.6/1.2. The 040 leaves the lip at 7.25° and lands rear first at −1° (r21 5.25°, +3.5°).
  - `r22.slave` boots to the title as r21. Cost: a few multiplies a pass, not measured.

**H3c (1), a half and a full brake on the mouse (2026-11-02, `r23.slave`).** The user: "holding
the left mouse button down without having held it down in the last half a second only presses
the pedal down half-way (at maximum) - releasing the button and pressing it again within half a
second presses the pedal down all the way down".
- `_handling_pedals`: a press of the left button aims the brake pedal at 50 (`HANDLING_PEDAL_HALF`),
  a press after at most 25 released fields (`HANDLING_DOUBLE`, 0.5 s) at 100, at the same rate
  (34 a field, 10 with CUSTOM4=1, whose soft brake halves too). State `HS_BPREV`, `HS_BWIN`,
  `HS_BFULL` (`HS_SIZE` 144). The buttons are the VBL's per field (`_handling_held`), so the
  window counts fields on every machine.
- Test drivers: `_handling_pad` bit 3 with the left button brakes at full pedal;
  `feel_fixture.s`'s brake (5) sets it, so the matrix's full-pedal plans are unchanged. A plan
  without it would be C1e's and C1b's half pedal.
- **Checked:** `_handling_pedals` from the slave in Unicorn (a scratch script, not kept): a
  hold 34, 50, 50…; presses after 1–25 released fields full, 26 and 40 half; a quick double
  click 34, 50, 16, 0, 0, 34, 68, 100; pad bit 3 full; the gas unchanged. A500 (`r23-a500`):
  C1b full 0.90 g, 135 ft from 60 MPH (r19 0.89, 135); C1f 60 / 90 brake as r19 (1.1° 12.5 °/s,
  2.4° 15.2). Half pedal (`r23h-a500`, the fixture without bit 3): 0.70 g, 177 ft from 60 MPH,
  0.69 g, 452 ft from 100, against the arcade's pedal 1500: 0.68 g, 182 ft and 488 ft.
  CUSTOM1 = 0 and 1 install the same code as r22 (`check_installed_code.py`); boots to the
  title as r22.
- **The red marker** between the RPM and MPH dials (`$ED72`) is the native throttle G($991C):
  bright segment at the bottom closed, at the top full (screenshots, 040). The user read it as a
  brake pedal (a brake press with the gas released drops it); asked, they kept it as the gas
  (2026-11-02). `_dispatch_held_ramps` still applies the native throttle ramps to the button
  word with mouse pedals; no effect on the throttle byte was measurable (A500, 040), so left.

**H3d, the drive of r23 (2026-11-02, `r24.slave`, `r25.slave`).** The user: the double click
"definitely" locks the fronts, but "single hold easily locks the fronts in corners"; the rear
steps out with gas and brake together; the timing is right; the hill climb is fine, but braking
hard the nose "does jump up again on some frames though and then falls back down".
- **Single press 35%** (8b661ca2, user's choice): 50% (2,326 lb ft) was above the front's lock
  point (about 2,070). 040 (`hb-h35-040`, `hb-h50-040`, half-pedal fixture): front sliding
  passes 0 at 35% (1-2% at 50%, 54% at full); 0.9 g corner yaw after 1 s +18% against -54%
  at 50%; C1b 0.50 g, 248 ft from 60 MPH. Gas and brake stay independent (user's choice).
- **The nose jump** (`r25`): hard braking on slopes put the rear corner points 2-3 units up
  (dive about -10 quarter degrees); at 4 the native contact counted only the front pair (mask
  3), `_suspension_release`, then `_suspension_touch` restarted the springs at rest: +2.75 to
  +3.5 degrees for a frame, rebuilt over about 6 passes, about every 14 passes.
  `_suspension_pair`: with SU_D < 0 and mask 3, the rear's height over the front (both
  wheels) within 4 |D| + 2 units (Q22 at the axles) stays on the ground branch (`SU_PAIR`
  returns GE flags at $CB52). Not the rear pair under a squat: its lip delay changed A500
  take-offs. Hill braking plans (`/tmp` build_hill.py: follow `main`, brake at plan t 420 /
  570 / 790): nose-up jumps >= 1 degree 2/5/3 -> 0/1/2, the rest a landing (braking began
  in the air) and the valley's genuine pair contact. Ramps identical to the r24 control on
  the 040 and A500; 040 `lap-main` reversals 7.4 -> 8.1 / 1,000 fields, `lap-stunt` 15.9 ->
  10.2 (crashes 5 / 6, the lottery); A500 C1b 0.90 g, 136 ft. CUSTOM1 = 0 and 1 install the
  same code as r24; boots to the title.

**H3b, the A500 cost of r25 (2026-11-02, 4c0de344, `r26.slave`).** The C1c 60 MPH plan, 500
fields from 600 (`capture_solver_profile.py`; the profiler now needs `PROFILE_FSUAE=tmp/profile-emulator/fs-uae`
and `HD_PROFILE_DIRECT=1`: the shared FS-UAE was rebuilt and round 12's binary is gone; paths absolute).
- r25: CUSTOM1 = 2 67.86 ms a frame at 3.39 fields, CUSTOM1 = 1 60.22: **+12.7%**, over the budget.
  Round 12's slave rebuilt (18504326 with the local harness's c2dbb14 fixture, byte-identical) gives 63.54
  on this emulator as then, so the emulator is not the cause; with today's fixture 64.39.
- Bisection: 64.4 ms through f6967ce6, 67.7 from 3f89b13b (the hill pitch). The model's cost per
  field is unchanged; `_render_rotate_x` went 0.14 -> 1.85 ms a frame: its zero-sine path runs only
  at pitch 0, and the nearest-quarter-degree rounding made the cruise's pitch 1 on flat ground (the
  squat about 0.4 and the held ground error `SU_GD` 0.4 quarter degrees; the hold band then kept 1).
- Fix: a recomputed pitch within one quarter degree of level is 0, a word of +-1 drops to 0 within
  one, and a level word is kept up to 1.5 (`SUSP_LEVEL_HOLD`). A snap without the level hold left the
  word at 1 (67.45 ms). Result: **64.36 ms, +6.9%** (scene prep 6.42 ms); the C1c cruise level for 439
  of fields 600-1100.
- Regressions against r25 (`r26-a500`, `r26-040`): C1b 0.90 g, 142 ft; C1f 60 brake as r25; pitch
  reversals the same or fewer (040 ramp-90 17.2 -> 1.6 per 1,000 fields); crashes as r25; landings
  in the usual scatter (A500 ramp-90 -30.25 -> -11.75 degrees, 040 -2.75 -> -10.25). CUSTOM1 = 0 and
  1 install the same code as r25; boots to the title.

**H3c, the user's drive of r26 (2026-11-02; c77a042f, 39641b16, 4bc3db54, `r27.slave`).** Flat
road and gentle slopes fine; three reports: a crash "with the bridge" while driving under it
on the stunt road, the nose rising into the sky for 12 s after jumping the first ramp (the
recording at 2:28), and the rear getting loose on a lift.
- **The dip under the main road** (stunt 61–68, 92 units down; `h3-dip-80..130` from section
  61, `h3-under-60..120` from 57): the native contact measures the wheels against the road
  polygons near the camera, a plane from an object's ground polygon within 25 units of it
  (`$9E02`, copied at `$A150`, `$CA14`/`$C6EC`) or the flat ground (`$C94E`). Leaving the crest
  at speed, the car came down on a plane under the floor: no wheel down, the flight fell
  through it (A500 to 23 units under at 115 MPH, the 040 7–16 at 130) and the inside test
  (`$BDBE`) crashed it under the bridge. The road cursor G($98E4) is right in flight
  (`capture_feel.py --break-tag`).
- **The ramp's nose-up** (`h3-rampl-60..110`: 65 MPH, lanes 60–110 left of the centre line;
  `h3-rampr-*` 15 left, between the parked car and the oncoming truck): over the gap
  (stunt 20–21, the only section flagged $400) there is no road polygon, and near the left
  edge a sloped face of the tower became the plane: on the 68020 the rear pair touched it
  25–50 units above the deck and the car tipped to 55°, flying on so (lane 60 and 70).
- **Fix (39641b16):** before the native contact (`$CDF2`, `_road_contact`, HardDrivinLoop.s), the
  road table's quad under the car's centre (the cursor's segment or one either side, edges
  an eighth of the width out, the plane of the half it is in, at most 45°) gives the
  surface. Wheels measured on something more than 6 units under it come down by the
  difference (not over the gap), so the native ground pass lands the car; an object's plane
  more than 6 units above it, or steeper than 45°, is no ground. Off the road (over 1,700
  units from the cursor's section) nothing runs.
- **The object box (c77a042f):** the right-lane runs crashed into the oncoming truck, and
  `h3-ramp-110` into the parked car 40 units off its line: the box is 30 + MPH/8 units each
  side. It stays 30 with arcade handling (the forward reach still grows with the speed).
- **The gas pedal (4bc3db54, the user's suggestion):** it comes back 5 of 100 a field instead
  of 10 (0.4 s from full). C1e on the A500 against r26: at the Amiga limit (`c1ex-lim-lift`)
  the yaw change in 1 s 72.8 → 62.8%, sideslip 9.7 → 7.1°; at 0.7 and 0.9 g within a few
  percent. The test drivers hold their speed with the pedals, so the slower lift changes
  their throttle too: `c1f-60-release` 7.5 → 15.4° of slip, and the A500 `h3-under-80`
  brakes on the crest and spins on landing (with the old rate and the floor it passes).
- **Results:** dips: A500 80/100 pass (r26 crashed from 100), 115/130 leave the crest at the
  bend and land 45 units past the right edge; 040 and 68020 all pass (80–130). Underpass:
  A500 60 passes, 80–120 crash (r26: 80 passed); 68020 60/80 pass, 100 crests on the right
  edge and flies 66 units off the road, 120 off the road as r26. Ramps: every flight at 6–9°
  on all three machines; lanes 70–80 hit the tower on the climb on the 040 and 68020.
  `lap-main` clean (A500, 040); 040 `lap-stunt` 3 crashes in 12,000 fields (r26 8). C1b
  0.89 g, 146 ft (r26 0.90, 142). CUSTOM1 = 0 and 1 install the same code as r26; `r27.slave`
  boots to the title.
- **A500 cost** (C1c 60 MPH plan): with the old gas rate 64.36 ms a frame, r26's (+6.9%);
  with the new one 66.44 (+10.3%): the plan's cruise control works the pedal, and the
  slower lift leaves the pitch off zero in 53 of 150 passes (r26 18 of 156), which costs the
  renderer (H3b). The floor itself is 0.1 ms.
- **The dip's banks (d76593fb, `r28.slave`):** the user's recording 16.44.29 (1:05-1:14:
  checkpoint, extra time, under the bridge) shows the car riding the right bank at the dip's
  exit at about 95 MPH, where the failing runs landed 45-65 units past the edge. The quad
  now tests the real edges first (`_road_inside`); past them it takes half the width more,
  and there the floor applies only in a cutting (the surface at or below the ground, car
  Y + h <= 0). An object's plane above the road is refused only between the edges, so the
  banks stay ground. Results: dips 80-130 pass on all three machines (A500 115/130 fixed);
  underpass A500 60/80 pass, 100 flies straight off the crest as the road bends left and
  meets the right bank 86 units out (`$BDBE`), 120 drives 150-230 units off the road as
  r26; 68020 60-100 pass, 120 as r26 (`$BFEE` wall). Ramps pass but 040 lane 70 (the tower,
  as before). `lap-main` clean (A500, 040); `lap-stunt` 040 3 crashes (r27 3), A500 5, none
  in or past the dip (r27 5, three at the dip). A500 C1c 60 MPH 66.44 ms, as r27. CUSTOM1 =
  0 and 1 install the same code as r27; boots to the title.
- **Falling from the loop (bf9ad0eb, `r29.slave`):** the user's recording 22.35.18 (0:52, 1:21,
  3:22): entering slowly, the car let go and the view showed only sky (once stray polygons)
  until OFF ROAD reset it. Loop probes on the 040 (`loopprobe.sh`, `C4_STEER=1`, entries 200-470,
  `C4_THROTTLE=1` to coast): two jumps. (1) Let go under the top, the floor took stunt 42-45
  (normals ny > 0, every other section's ny < 0) for ground and pushed the car 2,000 units
  under (y -1667, -2682, -4193): `_road_quad` now refuses a quad facing down. (2) Falling back
  from the climb on its tail (pitch 106), the front pair measured -3,309 on a near-vertical
  facet (r26 too, with the floor off), the contact threw the car 1,700 up and the pitch went
  to 695 degrees: off the loop a wheel more than 256 under (`ROAD_DEEP`) is no ground. After:
  no jumps (deepest -51). Open: let go at 95 degrees on the climb (`c400`) the car lands on the
  57-degree face and stays there stopped, all four wheels down; refusing the road polygons
  where the cursor's section is pitched past 45 degrees made it fall through the ground for
  good (the cursor stays on the face) and lost the loop at full throttle, so it was dropped.
  Loop probes at 300/400/559 match r28 exactly; dips, ramps clean; `lap-main` clean (A500,
  040); `lap-stunt` A500 3 crashes, 040 5 (two traffic hits near the dip, wheels down).
  CUSTOM1 = 0 and 1 install the same code as r28; boots.
- **After the loop fall (r30):** the user's recording 23.10.11. At 6:01 the car fell back off
  the loop, hit the blue traffic car and flew over the loop into the sky; at 6:33 it fell back
  and the view showed only sky through OFF ROAD 10 to 0. Loop probes on the 040 at 60 MPH
  entries (`C4_THROTTLE=40-48`): let go too slow at 95 degrees, the car rolled back onto the
  lower facets and the native contact, which has no centripetal test, drove it up past the
  vertical again at walking pace (pitch 141-171, 110 ft up); it dropped held stiff at that
  pitch and stood on its tail at 33-67 degrees, the tail 50-90 under, until the recovery (the
  sky view). (1) `_loop_enter` also takes the car back on a facet within 90 degrees of level
  (`LOOP_REENTER`), its pitch within 45 of the facet's and facing along the loop, at any
  speed: now it rolls back down and off the loop and drives on (five entries, no crash; the
  old `c400` stall on the 57-degree face rolls back too). A throttle-50 entry that flew the
  flat section before the loop (no contact there) went round on the native contact at constant
  speed in r29; it is now held from facet 1, under gravity, and lets go at 105 degrees. (2) The
  crash drift (`_motion_drift`, the last pass's move over 30 samples) is level with arcade
  handling: it carried the bounce up (6:01) and the fall into the ground. (3) `_loop_floor`
  eases a crashed car's pitch to level or upside down, whichever is nearer, 6 degrees a field
  (`LOOP_SETTLE`; at 1.5 the native contact's front pair, which the crash reaches past the
  `$CDF2` hook, held it nose down at -105), and holds a crashed car steeper than 45 degrees at
  least at the ground (the road's surface over a section), contact or not: coasting in at
  470 the car lands on its roof, tips flat in 20 fields and rests upside down at y 0 until the
  recovery (r29: nose down at -100, 42 under). Loop probes at 300/400/559 as r29 (one field);
  `lap-main` clean (A500, 040); `lap-stunt` A500 3 crashes, 040 3 (finished). CUSTOM1 = 0 and
  1 install the same code as r29; `r30.slave` boots.

**H3c (6), traffic in the arcade and the draw order (2026-11-03, 6ef73b6c, `r31.slave`).** The
user: "other cars drive through each other. Also, the other cars getting rendered on top of
scenery even though they should be obscured is highly annoying."
- **The arcade's traffic** (`plans/tr_long.lua`, `runs/tr_long`: the 7 records at `$FF87E6` every
  0.25 s for a whole race, the car idling on the start line; two scratch scripts, not kept): a car
  that comes up behind a slower one in its lane brakes to its speed and holds 35-40 ft back (car 2
  behind car 1 at 39-42 s, 8 against 9 MPH), then moves across a lane (10 ft over 3-5 s) and
  passes; no two cars came within 10 ft but on passing in opposite lanes. Traffic also waits for
  the player: the three cars that left the grid crawl at 3-12 MPH ahead of the idling car, the one
  behind it stays stopped, the three far ones alternate about 120 and 58 MPH.
- **The Amiga's traffic** (`$CE70`): each record only slews its speed (+23) to its target (+22)
  along a fixed lane's route; nothing looks at the other cars or the player. Open: a following
  rule (a lane change needs a lateral offset the routes do not have).
- **The draw order** (`$FDD4`): the background list, type-57 objects and low class-8 objects,
  then the whole plain road (`$FC1E`), then the objects far to near by their depth (`$8924`
  inserts by the rotated centre depth, the far side for classes 4/16 and type 111). The road needs
  no order of its own: a section hidden by a crest faces away and is culled. Structures (class 16:
  types 8, 9, 48, 61) draw their own road sections after themselves (`$FA58`, flags `$F8`).
- **Fix** (`HardDrivinDepth.s`, CUSTOM1 nonzero): `$FE72` records the plain sections of both
  roads (their farthest corner from the strip, colour, surface and marking polygons) and sorts
  them far to near; before each object (`$FE9E`, `$FECC`) the sections farther than its near side
  (depth less radius) are drawn; `$FF36` draws the rest. A section is moved after an object only
  when all its corners are nearer than the object's bounding sphere, so it cannot be hidden by it.
- **Checked:** frames of `lap-stunt` (040) before and after the last flush in the same frame
  (a scratch script, not kept): the late road covers grass, the climb to the loop covers a car on the
  ground beside it, the loop's base loses a pixel line to the nearer road. A500 C1c 60 MPH
  (`dc0/dc1-cost-c1c60`): scene draw 0.56 → 0.66 ms a frame, frames 67.5 / 67.1 ms. CUSTOM1 = 0
  installs the same code as r30; CUSTOM1 = 1 differs at the four sites; `r31` boots (A500).

**H3c (6), traffic following (2026-11-03, cc688059, `r32.slave`).** The user: "Car traffic: follow
only. They shouldn't care about the player car."
- **Rule** (`_traffic_follow`, Traffic.s, CUSTOM1 nonzero, every other frame before `$D43A`'s
  loop): a car with a car ahead in its lane (same direction +20 and lane byte +18, ahead along
  its segment +28..32) within 223 units (40 ft, centres) is held to that car's speed scaled by the
  two segments' lengths (speed is route phase a field, 200 to a segment of any length), a unit
  below it within 195 (35 ft), two within 160. The cap stays in the companion (byte 22) and the
  speed step's acceleration stops at it until the next pass; the player is ignored.
- **Cost:** comparing every pair from the records was 3.5 ms a frame on the A500 (the slave
  runs from contended memory, about 1.3 µs an instruction); a list by lane (rebuilt when a key
  changes), each pair once and every other frame: 0.49 ms (C1c 60 MPH, frames 67.13 → 66.85-67.69
  ms against r31 across runs).
- **Checked** (a scratch script, not kept: every record and its object every 5 traffic frames, the
  `lap-main`/`lap-stunt` fixtures): r31 cars 9/10 and 6/7 pass through each other (down to 0
  units); r32 they follow at 204-258 units (5-95 %, median 220, 39 ft) on the 040 and 186-259 on
  the A500 (dips to 144 at segment changes). Without scaling by the segments' lengths the gap
  fell to 78 when the leader entered a short segment. `lap-main` clean (A500, 040), `lap-stunt`
  2 crashes each at the field limit (the driver does not avoid traffic). CUSTOM1 = 0 installs the
  same code as r31 (the game loads 0x1000 lower); `r32` boots (A500).
- **Not done:** the arcade's lane change to pass a slower car (the routes have no lateral
  offset) and its traffic waiting for the player (not wanted).

**H3d drive of r32 (2026-11-03, recording 09.09.10; 57d79342, ce39a1fc, fc69e241, `r34.slave`).**
- **Bridge crash (1:17, 1:31):** `$BDBE` fired on the main road's bridge deck (type 81 at
  20266/0/16233, radius 408) while the car drove through the dip 73-90 units below it: the
  inside-the-faces flag (32, set at `$A386` from `$9B22`) ignores height. `_handling_inside` at
  `$BD3C` passes over an object whose base is more than 40 units above the car. Plans
  `h3-dipl-{105,110}-LANE` (dip with a lane offset); the remaining dip/under crashes are the
  driver flying off the crest at stunt 62 into the cutting's walls at ground level.
- **Draw order (0:25, 1:22, 1:37):** cars below the road (y < -5) were drawn by a pre-pass
  (`$FE40..$FE72`) before the road, so scenery in front hid them; it is skipped and they go
  through the sorted pass. A car farther than both roads' last strip points (`_depth_extent`)
  is not drawn (3,000 fields of `lap-main`: 158 skips, a car in the dip seen from the main road
  and one 4,700 units out; no wrong hides seen).
- **Bank (1:56):** gravity acted only along the car, so on the 46 degree bank the tyres alone
  held the turn. The lateral update adds W sin(roll) (G($9450)) on the wheels, off the loop,
  above 4 degrees of roll. `h3-bankf-V` (stunt 68-94 from a seeded start at stunt 69; the seeded
  car does not steer for 60-80 fields, so earlier seeds were invalid), largest distance from
  the route r32 → r34: 30 MPH 348 → 27, 40 57 → 45, 60 104 → 70, 75 399 (flew off) → 81; 90 MPH
  still crashes at stunt 74 before the bank. Short hops (5-18 fields) remain on the bank.
- **Cost (A500, C1c 60):** without the dead band the main road's stray 0.8 degrees of roll moved
  the car off the level pose (+1.6 ms in scene xform, physics +0.2). r32 → r34: 67.17 → 67.86
  (field 450), 66.85 → 67.47 (600), +1 %, within the ±1 ms layout noise; depth alone was 65.93.
  Fields past ~900 are past the C1c plan (the fixture's `$0C09A` crash), not usable windows.
  The profiler needs `PROFILE_FSUAE=tmp/profile-emulator/fs-uae HD_PROFILE_DIRECT=1`.
- **Checked:** `lap-main` clean (A500, 040); `lap-stunt` crashes early (stunt 13-14) on the 040
  in r32-r34 alike, as the driver is chaotic there. CUSTOM1 = 0 installs the same code as r32;
  `r34` boots (A500).
- **Open (0:22):** cars over the stunt road's raised fork (class 16, type 8, radius 2172): its
  faces are drawn at its far key, cars after. A fix needs a plane test of each car against the
  structure's faces and a repaint, which costs A500 time.

### I. Release

- **I1** Document the option, decide its default with the user, and commit it as a
  separate change and PR, outside PR 29.

### Order and effort (rough)

| Steps | Effort |
|---|---|
| A1–A4 | ½–1 day |
| B1–B3 | ½ day |
| C1–C2 | 1 day |
| D1–D2 | 0–2 days |
| E1–E3 | 1–2 days |
| F1 | ½ day |
| G1–G4 | 3–5 days |
| H1–H3 | open-ended |
| I1 | ½ day |

The user's input is needed at H3 (driving) and I1 (the default). E2's tolerance and G2's option
(CUSTOM1 = 2) were given on 2026-10-21. A–G are done; H1 and H2 are done as far as automation
goes; H3 rounds 1–7 are done (round 7: the arcade engine and gearbox), and the next drive
waits for the user.

**H3c (2), slides, the brake in a slide and coasting (2026-11-04, `r39.slave`).** The user drove
r38: "the steering curve feels fine. The slides are still too easy"; then "test the rear end
getting loose while coasting and steering".
- **Test fixes first.** `feel_fixture.s`: the lift followed 10 a field while the gas lifts 5
  (`HANDLING_GAS_LIFT`, since 4bc3db54), so the cruise pumped the gas; with arcade handling the
  cruise now sets the pedal itself through `_handling_gas` (2782bfed), a PI with `hd.lua`'s gains,
  so speed holds through slides as in MAME (−0.2 to +0.5 MPH lost in 5 s). `build_feel.counts`
  maps a wheel offset to the steer word the arcade read, 2 × offset − 10 (E1's mapping steered
  2–7% more; at the limit that decides a spin).
- **Brake in a slide** (62b2a762): the pedal goes straight to its target (was a third a field) and
  the load transfer follows the tyres' force while braking (the brake torque had loaded the front
  to 2,690 lb against the arcade's 2,300; MAME `plans/n_trace3.lua`, wheel force vectors x/y/z,
  `mame/c/forces/`). C1f brake largest yaw 60 / 90 MPH: A500 6.0 / 9.2, 020 7.8 / 9.4 (arcade
  6.1 / 10.5; were 9.2–12.5 / 15.2–18.7); C1b from 60 MPH 0.82 g, 149 ft (0.87, 143; was 136).
- **Coasting** (C1h, `plans/c1h_coast.lua`, `c1h-V-WHEEL`: cruise, then gas off and the wheel at
  once): the automatic box shifts into 1st at ~30 MPH as the arcade's does, but with the rear
  wheel sliding the clutch chattered ±5,000 lb ft a field (a field at capacity overshoots the
  light wheel) and the car spun. 5d9aa709 passes the torque that matches engine and wheel in
  the field. Largest sideslip, arcade / A500 / 020: 40-350 0.1 / 1.7 / 0.2 (was a spin), 40-650
  27.6 / 48 / 31, 60-200 0.9 / 1.8 / 1.0, 60-380 32 / 49 / 40.
- **Left:** C1f 90 hold 7.7° against 10.3 / 9.5 and its counter-steer overshoot 5.2 against
  7.1 / 6.1. With the arcade's own loads, rear force, speed and steering (MAME traces), the twin
  still gives 8.6°: about 1° is the 50 Hz model step (handling_check at other steps is not
  monotonic), the rest small input differences near the limit. The A500 slides 1–1.5° more than
  the 020 everywhere (inputs once a pass). 020 `c1a-auto` reports StopIteration (also before
  these changes); `check_handling_step.py` fails with UC_ERR_READ_UNMAPPED on r38 and r39 alike.
