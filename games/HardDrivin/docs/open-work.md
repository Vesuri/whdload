# The tyre and off-road sounds, the landing's pitch (2026-11-06)

The user's drive (recording 13.46.48): the tyre screech is nearly always a slow howl and now
and then much higher, the off-road sound is weak, and on a landing (0:32) the car's pitch
turns to the ground's in one frame where the replay (0:46) turns it over several.

**Sounds.** The effects are native events through `$8AE` (table at `$A0C`), each a channel,
a sample (G entries of 10 bytes: length in words at +2, pointer at +6), a volume and a
Paula period, which the channel service (`$2F8`-`$3D4`) writes to AUDxLC/LEN/PER/VOL:
- event 4, the screech (`$950`): channel 3, period 1100 (3.2 kHz), volume 30, a 5,598-byte
  sample (1.7 s). Live (`$B624`, arcade handling `_audio_skid`) and replay (`$10C24`) both
  use it, so every screech is at 1100.
- event 7 (`$9A4`): channel 3, period 500 (7.1 kHz), volume 25, a 4,158-byte sample: the
  pitch-correction and landing contacts (`$CD52`, `$CC84`, `$BD02`, `$BDE2`). Likely the
  higher sound the user hears.
- event 8, off the road (`$9BE`, from `$B166`): channel 2, period 700 (5.1 kHz), volume 64,
  a 10,706-byte sample (2.1 s).
The samples at their own and faster periods are in ignored `tmp/sfx/` (dumped from chip RAM
in a race) for the user to choose. A period is one word in each event's code (`$952`, `$9C0`).

**Landing pitch, postponed.** The native contact pass (`$CAB6`) and the springs' first
ground pass (`_suspension_touch`, CUSTOM1=2) put the car on the ground's pitch at once; the
replay interpolates its records. Two attempts were reverted:
- keeping the body's pitch against the ground at the touchdown, eased out an eighth a field
  (or the springs displaced within their travel): the pitch is level in about 0.7 s, but on
  the A500 `lap-stunt` the first jump landed at 43 MPH from 58 (the native snap kept 61)
  and the run then crashed short of the big jump;
- easing only the camera's pitch (`$D9D8` G($994C) to G($9946), `$B376` taking it back at
  the pass's start): the camera's pose is the physics' frame too (the road's camera-space
  strip is searched for the car's section, `$DD84`, and the contact's geometry follows), so
  a one-word offset at a lip gave the car a nose-up rate of 5 words a pass in the air and
  it turned over (`lap-stunt` on the A4000/040).
A smooth landing needs the renderer's matrices apart from the physics', or the springs'
landing tuned so the speed is kept.

# The car in replays on grass, the draw distance postponed (2026-11-06)

**Replays.** The user's drive of 480502d2 (recording 12.37.56, 0:55-0:57 and 1:43-1:54): in
replays the player's car vanished on the grass. A car farther than both roads' last strip
points was not drawn (`_depth_extent`, from the depth reorder), and the replay camera stands
off the road with only the sections near it drawn. The skip is gone (10f38b59): cars are
drawn as the native order draws them, and the crash replay is still pixel identical to it.
The grass case was not reproduced by a scripted drive.

**Draw distance (reverted, postponed).** The user asked for 1.5 times the distance on faster
machines, the A500 as it is, and the road extended only ahead. Native limits:
- Each road takes 13 sections from 6 behind its cursor (`$DC00` the course road, `$DF52`
  the stunt road; 7 at `$DF76` for the stunt road seen from another road), up to 40 when
  sections are flagged (the strip buffers' size), and keeps the strip points between -700
  and 4,000 units ahead (`$DF0A`, `$E298`, `$E2B0`). About 7 sections ahead: 3,500 units on
  the course road (sections ~500 units), 2,900 on the stunt road (~420).
- Objects are drawn within 4,000 units of the camera in X and Z (`$E364`-`$E38A` the
  background list, `$E4E0`-`$E506` the sorted list of 100 entries; the course has 99
  objects). The box is compared unsigned: a wider one wraps near the world's edges.
- The road's and objects' points share a pool from G(-$1688), 3,600 bytes up to the road's
  stream pointers G(-$878), with no check of its end; a larger square overran it.

ed9ab03a/518710b6 took 4 more sections, 6,000 units and an allocated pool on a 68020 or
later; the user's drive of it (recording 13.46.48) had a lap finished off the road (2:06),
cars and the player's car inside the bridge (0:37, 0:53) and a car pitched on level ground
(0:28). The section count is not only drawing: the same routines search the selected
sections for the nearest one to the car (`$DD84`-`$DE5A`, `$E106`-`$E1E2`, limited to 10
past the previous best) and set the cursor G(-$671C), the road G(-$66B0) and the section
triggers (`$DB80`, `$92C0`, `$936A`); with 4 more sections ahead the cursor can jump 10
sections ahead instead of 6. The user: revert and postpone. A later attempt has to keep that
search on the native count (only the transform loop longer), clamp the object box, and keep
the allocated pool.

# The car in replays covered by scenery (2026-11-06)

The user's drives of 4.0b: on the stunt road past the barn (recording 09.28.11, 2:42-2:45)
cars and a sign beyond the hill showed through its slope, and in replays (recording
10.10.09, 1:17-1:30, 1:49-2:03) the player's car was often covered by blocks of the
scenery's colour or vanished. Both are `_occ_car`/`_occ_solid` (4440c9fe), the repaint of a
solid's faces after a car.

- **Replays:** a face was filled when the car's centre was behind its plane at all, and for
  a solid clipped at the camera whether or not the face was towards it, so a car on the road
  across a coarse terrain face (1 to 58 units under it, radius 109) was covered by the face
  clipped to its box. A face is now filled only when it is towards the camera and the whole
  object is behind it (farther than its radius). The crash replay (`tmp/depth2/replay2.sh`:
  A1200/040 NoMMU, the brown car hit at the top of the first hill, 36 frames) is now pixel
  identical to the native draw order; the previous build differed in 13 frames.
- **Slopes (reverted):** 480502d2 also tested every object, not only class 8, filled the
  faces seen from above (ground), and filled the solid's own road sections ($FA58, recorded
  by `_depth_collect`) again when the object was wholly behind the plane through three of
  their strip points. On the scripted barn drive (`tmp/depth2/drive.sh`, `plan-t6.txt`) it
  hid a grey and a green car that 4.0b drew on the hill's slope. The user's drive of it
  (recording 13.46.48) had a green polygon reaching into the sky near the barn (0:24) and in
  a replay (0:53), and cars vanishing under the bridge (0:37, the replay at 0:53), none
  reproduced by script. The user: keep the replay fix, drop the rest for the release. Only
  cars are tested again and ground faces are skipped as in 4.0b, so cars past the barn's
  hill can show through its slope again (recording 09.28.11, 2:42-2:45). Checked: the crash
  replay is pixel identical to the native draw order (36 frames), the barn drive runs
  without a fault.
- **Seen, not changed:** in replays the orange centre markings appear only once the player
  has passed them; the native draw order shows the same.

# An access fault off the road (2026-11-06)

Driving off the road up the slope after the barn (A1200/040, CUSTOM1=2, from the start with
the gas held and the mouse 40 counts left at field 450) ended in a WHDLoad access fault in
4.0b's slave as well: `_loop_enter` read the section pitch through the road cursor G($98E4),
which a native search that finds nothing leaves uninitialised ($252A009E here), checking only
its lower bound before the read (since 3925c24c). It now bounds the cursor by the road's
first and last sections and to a section's start before reading through it. The same drive
no longer faults; `lap-loop` reports as before (flights, the 180 degree pitch, crash, replay
and recovery within a field).

# Quitting a race at speed (2026-11-06)

The user's drive of 4.0b (A1200/040, CUSTOM1=2 CUSTOM5=1): after Q at speed, the next race's
start screen showed high RPM and MPH and the car crept forward before the engine started.
The native engine's speedometer site `$BA8A` (`_handling_speedo`) runs before the model's
first pass and published the aborted race's `HS_MPH` and `HS_TARGET` into G($992C) and the
target speed G($9926). The new-race and Phantom sites (`$59ba`, `$117f8`,
`_time_initial_scalars`) now return the handling state to its boot values
(`_handling_new_race`). Repro `tmp/qbug/repro.sh` (A1200/040, gas held for 750 fields,
Q, name entry, AUTO): 4.0b's slave starts the next race with speed 20 and target 19, and
the car moves 85 units before the start; the fixed build has 0, 0 and no movement. The
release slave no longer matches `release/slaves.sha256` (4.0b).

# Release 4.0b (2026-11-04)

The user chose to release r39 (H3c 2, ARCADE_HANDLING_PLAN.md) as 4.0b, dated 04.11.2026
(fork ddaf8365). New installs set CUSTOM1=2 (arcade handling; was 1). The splash offers Race
timing Amiga or Arcade only; CUSTOM5=2 stays as a tooltype for testing (ARCADE_TIMING.md).
The fork's archive had 65 members: the earlier 64 plus `source/HardDrivinDepth.s`.

**The A500 cost.** For CUSTOM1=1, the step 5 renderer saves 12.5 ms per swap in window A and
5.8 ms in B; the step 4 simulation costs 7.1 and 5.8 ms. So CUSTOM1=1 runs at about the
original's speed. That is arithmetic across two builds, never measured directly. The user:
"If the net is about 0 on the A500, that's perfectly fine."

**Open:**
- CUSTOM1=2 costs 12% over CUSTOM1=1 on the flat C1c test ground (r34: 67.7 against
  60.2 ms a frame), estimated 4–5% in scenery windows (not measured). The user has not
  accepted it against the 10% budget.
- The user's verdict on the 90 MPH slide gap (C1f 90 hold, 7.7° arcade against 10.3 A500 /
  9.5 020) after driving r39. They drive with `make aja` (68040), so the A500's extra
  1–1.5° of slide is not what they feel.
- Two ReadMe "Arcade controls" claims come from the code and were never checked in play:
  joystick and keyboard keep the game's own throttle under arcade handling, and manual gears
  work with arcade handling.
- The H3c (2) scratch analyses are in ignored `tmp/hdgrab/` (copied from the session's
  scratch; their paths are the old repository's): `replay.py` replays a 020 run's per-field
  `model.bin` inputs through `handling_fx` in the game's drivetrain mode (it reproduced the
  game's 9.4° exactly; variants for loads, rear torque, constant u); `allarc.py` feeds the
  twin the arcade's loads, rear force, speed and steering from the MAME `n_trace3` traces
  (8.6° against the arcade's 7.7°); `coast.py` runs `feel.c1f(S, …, 'hold')` over the C1h
  runs, arcade against Amiga; `mdump.py` dumps `model.bin` per pass. The MAME traces are
  `tmp/arcade/mame/c/forces/` (c1f-60/90-hold and -brake) and `tmp/arcade/mame/c/coast/`
  (C1h).

# The arcade brake (2026-11-01, H3c 1)

ARCADE_HANDLING_PLAN.md "H3, refined" and its gap table (H3a). At CUSTOM1 = 2 full pedal is the
arcade's 4,653 lb ft, locking the front wheels (C1b 143 ft from 60 MPH, as the arcade); the mouse
brake pedal is full in 3 fields, as a slower one spins the car near the lock point. CUSTOM4=1
("Arcade brake: Soft") restores r18's brake. 11d95274, drive build `r19.slave`, not pushed.
Open: the A500 budget (H3b), then H3c (2)-(6); a half-pedal C1e plan.

# The ramp's take-off and landing (2026-10-24, H3 round 12)

ARCADE_HANDLING_PLAN.md H3 round 12, CUSTOM1 = 2. The arcade's attract demo jumps the stunt road's
first ramp (MAME, ARCADE_ROMS.md): it leaves along the slope and flies ballistically, as the 68020
already did; the A500 left nearly flat (the rear-only tip counted a whole pass, and the flight held
the pitch after its first pass in the air). Now the tip stops at the arcade's take-off rate and the
flight holds the last ground pass's pitch, so every machine flies alike. The arcade has no landing
test (its crash checks: speed, yaw, scenery, surface 7, a 52,000 lb force sum no landing reaches), and
with its flight Domark's ramp comes down on the flat at 46 ft/s, so arcade handling crashes no
landing. Ramp runs 50–100 MPH land on all three machines; laps, loop and jump probes as before or
better. A crashed car upside down (a roof landing after falling off the loop) no longer sinks
through the road, and one crashed steep no longer climbs along its body. Drive build `r18.slave`. Waiting on the user's drive.

# Suspension (2026-10-23, H3 round 11)

ARCADE_HANDLING_PLAN.md H3 round 11. The arcade's pitch springs and dampers (`HardDrivinSuspension.s`,
CUSTOM1 = 2) own the pitch on the native ground branch; the height stays native, because the native
wheel heights are whole units (0.18 ft), too coarse for heave (the user's choice). Jumps and the
loop as round 10, `lap-main` without a crash; C1f slide-brake sideslip 3.0° at 90 MPH against 2.0°
(arcade 1.1°): the arcade's axle loads (MAME) move as the springs' do, so this is the arcade's
full-pedal lock-up, the brake difference H1 found. The user's drive: the rear came loose at the stunt track's first ramp;
the springs no longer take the ground's pitch as their displacement (su17, `r15.slave`), ramp runs at
50–110 MPH as without them. Costs 0.36 ms a field on the A500 (frames 3.2% longer).

# The loop (2026-10-23, H3 round 10)

ARCADE_HANDLING_PLAN.md H3 round 10. On the A500 a step is a whole frame (about 180 units at the
real scale, more than one of the loop's 30° facets), so the pitch cannot follow and the car runs
past the top. Short steps (68060) follow it, but the road drifts its width sideways and the car,
holding its heading, leaves it at the top; held slightly left it goes over and then loses the road
on the way down (pitch stuck near −165°, heading swinging). 2-field steps on the A500 cost 5–6
fields each and were reverted. The arcade's attract demo (MAME) goes round at 61 MPH and yaws up
to 10° with the drift. Proposed: move the car along the loop's surface by the distance travelled
(step-length independent), pitch interpolated between facets, heading from the relative yaw,
detaching below v²/r = g. Implemented (the user: "Steer a little."): `HardDrivinLoop.s`; probes pass
the loop on the A500, 68020 and 68060 from 63 to 112 MPH with a little right steering, `lap-loop`
reaches stunt 89 (before: 57), `lap-main` unchanged.

# The user's first drive at the real scale (2026-10-23)

- **GAME OVER jerky:** the slide moved a column per 8 fields; now per 2 (GAME_TIME.md
  "Faster slide"). 68030: all 20 columns, one per frame.
- **OFF ROAD 43, then 1:** CUSTOM5's carried deadline met the native seconds-only BCD
  subtraction across a minute. `$105dc` now subtracts in hundredths (ARCADE_TIMING.md);
  `check_clock.py` checks it, and `r10-offroad` counts 5, 4, 3 across 1:00.
- **Lazy at low RPM:** the user drives with the mouse pedals and cares only about arcade
  handling. New `rollon-15`/`rollon-25` plans floor the gas cruising in 1st (`ro1-a500`):
  25.7 to 47.7 MPH in 2.1 s at 0.4–0.57 g; the arcade's c1e-mid-power run, 25.1 at
  3,040 rpm in 1st, to 47.6 MPH in 2.5 s at 0.43–0.64 g. From rest ours pulls 0.5–0.6 g,
  the arcade's 0.24–0.37 (the clutch slipping at 2,200–2,800 rpm). Part throttle is weak
  in the arcade's table too (cruising at half gas, 0.1 g). No change; asked the user where
  it feels lazy.
- **Slides:** grip limit 1.06–1.11 g against the arcade's 1.06–1.08 (round 9). No change.
- **Pulling away, the traffic leaving the player behind** (the user: "Getting up to speed is
  an ordeal"). The harness from standstill on the start line (`r11-start`, CUSTOM5=1):
  68 MPH after 8 s, 0–60 about 5.5 s; the arcade 6.3 s. The traffic: round 9 ran its whole
  step twice per field, so it reached its speed in half the time. Now only the distance is
  doubled (`_traffic_accel_fields`). `capture_clocks.py --traffic N` saves the records:
  the speed byte is about 3.7 MPH a unit (cruising 27–58 MPH for the cars measured), each
  field adds accel/8 (accel 1–3), so 1–3 g, 45 MPH in about 2 s (`r11-traffic-new2`;
  before 2–6 g, `r11-traffic-base2`). Still far above the player's 0.3–0.6 g. The user
  chose to follow the arcade: MAME (ARCADE_ROMS.md "Traffic at the start") shows its grid
  cars launching at the green light at about 0.45 g. With arcade handling every car now
  accelerates at 0.45 g (`TRAFFIC_ARCADE_ACCEL`, a speed unit 3.91 MPH): 9.8 MPH/s in
  `r12-traffic`, 47 MPH 4.5 s after the start as the arcade's left car. `r12-a500`
  lap-main: 117.3 s, no crash, as round 9.

# Arcade handling step H3 round 9 (2026-10-23)

The user: "driving at 140 definitely does not feel like 140, more like 70 at max."
(ARCADE_HANDLING_PLAN.md H3 round 9), CUSTOM1 = 2:
- **Finding:** the Amiga road is 230 world units wide, the arcade's 41.2 ft (MAME): a world
  unit is 0.1791 ft, not E1's speedometer-based 0.3504. Arcade handling drove at half speed
  past the scenery, and the arcade's time limits had to be doubled.
- **Changes:** the handling module's unit conversions, flight gravity, take-off rate, landing
  threshold and traffic speed at the real scale; the arcade's undoubled time limits with
  CUSTOM1 = 2 (still doubled for 0 and 1).
- **Results:** feel matches the arcade at real speeds; `lap-main` in 117 s without a crash,
  mean 81 MPH, inside the arcade's 1:36 limit with 15 s to spare; the fastest jump probes now
  overshoot the landing; the loop as before.
- **Verified:** installed game code identical; handling step and clock checks pass.
- **Next:** the rest of the arcade physics (the user, 2026-10-23: "the speed first").

# Arcade handling step H3 round 8 (2026-10-23)

The user: "I don't think the mouse controls in this game make any sense at all."
(ARCADE_HANDLING_PLAN.md H3 round 8), CUSTOM1 = 2 with mouse control:
- **Pedals:** the right button is the gas, the left the brake, independent, each moving 0.1
  of its travel per field while held and back while released (`HANDLING_PEDAL`, to tune
  after a drive). The brake torque is the pedal's share of the full brake. The joystick
  modes keep the native buttons.
- **Test drivers:** `feel_fixture.s` and the C4 throttle hold publish the held buttons in
  `_handling_pad`.
- **Results:** 0–60 in 5.8 s (arcade 6.3, round 7 10); shifts, coast-down and braking as
  round 7; the brake-in-corner spike is gone with the brake's 0.2 s travel; `lap-main`
  without a crash; jumps land; the loop as before.
- **Verified:** installed game code at CUSTOM1 = 0 and 1 identical to round 7.
- **Not measured:** the cost.
- **Next:** the user's drive.

# Arcade handling step H3 round 7 (2026-10-23)

The user: "Implement arcade engine and gearbox." (ARCADE_HANDLING_PLAN.md H3 round 7),
CUSTOM1 = 2:
- **Drivetrain:** every field, the arcade's torque table (by gear: 1.11, 1.156, 1.2025, 1.3,
  read from C1a's recorded run), automatic clutch, shifts at most once a second, gear
  ratios and the locked engine's inertia drive the rear tyre; drag 0.0087 u² + 105 lb,
  grass drag and table, 1 g along slopes, the forced stop after the time ran out. The
  native engine's speed, RPM and automatic shifts are skipped; speed, RPM, gear and
  speedometer come from the module.
- **Braking:** no throttle while the brake is on; the brake's force sets the load transfer.
- **Results:** shifts within 1 MPH and 50 rpm of the arcade; coast-down equal; braking
  0.73 g from 60 (arcade 0.87, round 3 0.45); the brake-in-corner spike appears; 0–60 in
  10 s behind the 8 s throttle; `lap-main` without a crash; jumps land; the loop as before.
- **Verified:** installed game code at CUSTOM1 = 0 and 1 identical to round 6.
- **Not measured:** the cost.
- **Next:** the user's next drive.

# Arcade handling step H3 round 6 (2026-10-22)

The user: "Implement the arcade flight." (ARCADE_HANDLING_PLAN.md H3 round 6), CUSTOM1 = 2:
- **Ballistic flight:** from the first pass with no wheel on the ground until the native
  ground pass, the car moves along the pitch it took off with; the body turns on.
- **1 g:** the native fall is 0.27 g. Ballistic at that, the fast jumps flew 3.8 times too
  far, past the landing ramp. The flight now falls at the arcade's 32.2 ft/s².
- **Landings:** the flight's direction is kept on two wheels, and eight-field passes use
  the closing-speed landing rule too.
- **Results:** all 7 jump probes land (87–101 MPH: 88–101 fields, 650–910 units); laps as
  in round 5 within the runs' spread; the loop fails as before.
- **Verified:** installed game code at CUSTOM1 = 0 and 1 identical to round 5. The lap
  fixtures cannot show CUSTOM1 = 1 identical record for record: a timing-only control
  diverges alike.
- **Not measured:** the cost.
- **The loop** (the user's drive): round 6 also made loop dropouts fly at 1 g. Only take-offs
  upright and within 45° of level fly now; the loop runs natively, as in round 5. The
  loop itself stays hard: seeded entries lose contact at the top in every mode, the
  original's included.
- **Next:** the user's next drive.

# Arcade handling step H3 round 5 (2026-10-22)

The user's decisions (ARCADE_HANDLING_PLAN.md H3 round 5): fix renderer crashes present in
the original in every mode; follow the arcade's take-off.
- **Renderer crash fixed** (b2c686a): clipped polygons with a vertex outside the screen
  window are not drawn (`_fixclip_v1`, `$39c8`). `lap-jump` runs through; 0 of 3,000
  clipped polygons dropped in `lap-main` and `lap-stunt`.
- **Arcade take-off** (CUSTOM1 = 2): a car on its rear wheels pitches nose down at the
  arcade's rate, 3.7 rad/s² over its 10 ft wheelbase. All jump probes land; laps as good
  or better; one lap jump in four comes down short.
- **Open, for the user:** ballistic flight. The Amiga moves the car along its pitch, so the
  arcade's rate shortens flights; the fix touches ten movement reads (plan).
- **Not measured:** the cost of either.
- **Next:** the user's next drive, and the ballistic-flight decision.

# Arcade handling step H3 round 4 (2026-10-22)

The user: the stunt road's jump feels floaty and the car comes crashing down
(ARCADE_HANDLING_PLAN.md H3 round 4). CUSTOM1 = 1 and 2, in HardDrivinMotion.s:
- **Why:** the long flights are the original's: the take-off pitch rate is a sampling lottery
  in both. The enhanced landing crashed every full contact with a fall over 50; the native
  one also needs the wheels below −5 after its coarse step, which spares about half.
- **Fix:** variable intervals skip the native depth test (`$cc2e`) and crash where the
  wheels closed on the ground faster than 18 units per native step, the native median.
  At 88–101 MPH at the lip 2 of 8 probes land (original 1 of 4, before 0 of 8); at 53–66
  MPH 6 of 6 (original 3 of 3, before 4 of 6).
- **Verified:** jump probes; H2 laps as before, `lap-jump` gets past the jump; installed
  code at CUSTOM1 = 0 identical, at 1 only the `$cc2e` patch.
- **Open, a game crash:** `lap-jump` (CUSTOM1 = 2) ends at field 13,850 in the replay of a
  flight off the world from the loop. The native span filler's computed jump (`$340c`,
  `jmp $345e(pc,d2.w)`) takes a span of about −11,800 words and lands in `$7c00`; WHDLoad
  ends on the address error. Reproduce with `tools/hang_probe.py OUT --plan lap-jump
  --custom1 2 --records 13800`. A clamp there would touch CUSTOM1 = 0 code; the user decides.
- **Option, not done:** a fixed take-off pitch rate (−12 to −16 lands more jumps).
- **Next:** the user's next drive.

# Arcade handling step H3 round 3 (2026-10-22)

The user: braking with both mouse buttons takes forever (ARCADE_HANDLING_PLAN.md H3 round 3).
The native brake fades with the speed and the engine pushes against it while the throttle
closes at 2 per step: 10.8 s from 100 MPH. CUSTOM1 = 2 only, in HardDrivinHandling.s:
- **The brake at its limit:** 2,470 lb (0.7 g) on the front tyres; what the native engine did
  beyond that comes off again. 7.2–7.5 s from 100 MPH (arcade 6.6), 4.3 s from 60 (4.5).
- **The brake on the front only:** a front tyre past its limit no longer passes the rest of the
  brake to the rear. The arcade's brake-in-corner spike now appears (C1e +135% against +133%).
- **Verified:** check_handling_step.py; H1 matrix (braking as above, the rest close); H2 laps
  without hangs; installed code at CUSTOM1 = 0/1 identical.
- **Open:** in the stunt and loop laps the driver's brake taps at 85 MPH in a 1 g corner now
  spin the car (it stops within 3 s). Braking in a slide (C1f) yaws 3× the arcade. The cost
  is not measured.
- **Next:** the user's next drive.

# Arcade handling step H3 round 2 (2026-10-22)

The user's second drive (ARCADE_HANDLING_PLAN.md H3 round 2): a spin that never stops, and on
slopes the car tilts until the physics break. Two causes, both fixed in HardDrivinHandling.s
(962221d and 00a2f93 on the local branch harddrivin-handling, not pushed).
- **The engine refills the speed.** The native engine is power limited and refilled the
  forward speed the model's v r took away in a spin, far beyond the 2,115 lb the model saw.
  That surplus pushed the car along its heading, and the spin never ended. Fix: while a
  tyre is past its peak, the surplus comes off again. With grip to spare it stays, so
  0–60 MPH is unchanged (2.70 s).
- **The tilt grew.** The native yaw helper's roll term had the wrong sign for an upright car,
  which made the tilt grow at the turn rate. Fix: below 60° the tilt is rotated with the
  heading instead, keeping its size; the loop keeps the native helper.
- **Verified:**
  - `check_handling_turn.py` (Unicorn): 200,000 cases.
  - The H1 matrix: identical to round 1.
  - H2 laps: as before.
  - Installed code at CUSTOM1=0/1: identical.
  - The drive's spin: now stops when the slide does.
  - Round 1's roll-over: gone.
- **Not measured:** the cost.
- **Next:** the user's next drive.

# Arcade race timing, CUSTOM5 (2026-10-22)

The user reported that neither race clock keeps real time and that they differ. Both are the
original game's VBL clocks (GAME_TIME.md table): time left 0.500, lap 0.76-0.80. The arcade's
both run at 0.977 (ARCADE_ROMS.md "Race clocks"). The user asked for a mode choosing Amiga
or arcade timing: real time, the arcade's limits and rules, MAME's operator defaults.
- **Limits:** the arcade's own limits can't be met on the Amiga course (at least 99 s flat out
  to the first checkpoint against 96 s), so the user chose the arcade's limits doubled, with
  the options menu's difficulty picking the arcade preset.
- **Code:** HardDrivinClock.s, `C5:L:Race timing:Amiga,Arcade` (ARCADE_TIMING.md), local
  commit 16b1981 on harddrivin-handling, not pushed. The ReadMe text is still to do, with I1's.
- **Verified:** check_clock.py in Unicorn; installed code identical with CUSTOM5 off; A500
  captures of exact real time, awards, the time out with its 10 s grace and stop speed, crash
  5/16 with the lap clock stopped, and an 11 s off-road limit.
- **Not exercised in-game:** the countdown start, an award after zero, the cap, the Phantom
  race and the handicap's easing.

# Arcade handling step H3 round 1 (2026-10-21)

The user's first drive (ARCADE_HANDLING_PLAN.md H3): slides could not be recovered and the
car spun faster and faster. Two causes, both fixed in HardDrivinHandling.s (1ae501e, local
branch harddrivin-handling, not pushed): the native engine alone set the forward speed (no
u' = Fx/m + v r, so spins pumped energy into the yaw), and the rear wheels made up the
steered front tyre's drag (at full throttle and lock they spun). The model now feeds its
forward speed change back to the native speed, in whole units (fractions in the phase
anchor cost a unit per native step), and the rear gets only the native drive. H1 and H2
repeated: closer to the arcade, laps fine, A500 cost 1.31 ms per field (+0.08).
`lap-stunt` found a latent enhanced-build crash: `_checkpoint_post` trusted a section cursor
that a failed native search leaves uninitialised; fixed with a lower bound and evenness
check (7dfd2ba; CUSTOM1=1 too, so it belongs in the release as well). Open: the native yaw helper's
pitch/roll coupling is hyperbolic and rolled the car over on a slope at the model's yaw
rates. Next drive: tmp/build/HardDrivin-arcade.slave, CUSTOM1=2.

# Arcade handling step H1/H2 (2026-10-21)

ARCADE_HANDLING_PLAN.md step H: H1 and H2 done as far as automation goes; H3 waits for
the user's drive (slave tmp/build/HardDrivin-arcade.slave, CUSTOM1=2, command in the
plan). The module is unchanged since G (126798b, local branch harddrivin-handling).
A full-pedal brake mapping was tried and reverted (it kills turning while braking in a
corner). A500 cost measured: 1.17-1.26 ms per field, about 6%. The road follower
(feel_fixture.s FE_FOLLOW, build_feel.py lap-*, tools/lap_report.py) completes the main
road. The stunt route fails in both handling modes: jump landings, and a loop whose
outcome flips with frame timing. The open questions for H3 are in the plan.

# Skid entry fixes A+B — 1d36ff0 (2026-10-20, pushed)

User reported slides start too easily, spin up suddenly and cannot be
countersteered. Review: these are native Amiga mechanics (see
PHYSICS_ACCURACY.md, last section); two enhanced amplifiers fixed in
HardDrivinMotion.s/HardDrivinPhase.s: entry-step spin hold and once-per-step
skid-entry gate. User has a separate plan for improved handling (option C);
do not start it without their design.

# Documentation location (2026-10-14)

All eight former src/*.md documents now live beside this
file in ignored docs/, with their original filenames and contents.
They are intentionally excluded from the upstream PR. Source and release
artifacts are unchanged.

# Dead-code cleanup (2026-10-13)

Removed Fast edge-array experiment, unused events-begin-step, phase-scalar-step
and preserving phase-project wrapper. Root cache now omitted with phase solver;
reference-only build retains it. Reference integrator is still a live fallback.
Release cleanup-release.slave text47906 bytes (-344). Build/reference/symbol/
branch audits and A500/020 short gameplay/13 render sites pass; disabled171 ranges
pass. Capture names cleanup-*; their banks gzip verified, owned runtimes removed.
No new performance claim. See STEP6_RELEASE.md post-integration cleanup section.

# Disk cleanup (2026-10-13)

Completed raw trace files and duplicated assembly listings were removed.
Inactive disposable emulator runtimes were removed after PID checks, retaining
screenshots, configurations and score files. Play runtimes were preserved.
Memory fixtures are retained as verified gzip files; tools expecting raw .bin
files need to decompress the specific fixture before reuse. Summary reports,
input tapes, harness tools, source, game inputs and release builds remain.
Cleanup inventory: tmp/cleanup-completed-work.json.

# Release integration complete — 148d807 (2026-10-13)

Normal build includes HardDrivinRelease.i features, WHDLoad17 C1/C2 config.
Installer enables CUSTOM1 in new icons. CUSTOM3 ignored in release; automatic
000/020-Fast=6, 030=0, 040/060=2. Physical chip/nonfast address guard required
because KickEmu reports virtual expansion as MEMF_FAST on Chip-only020.
HD_DEVELOPMENT=1 opts out for old isolated builds (local wrappers updated).
Final source/report: STEP6_RELEASE.md. Release s6-final.slave 48250text bytes.
21 final s6f-* matrix captures complete; 13 render sites each pass. 172 disabled
ranges onA500/020/040; final A500 repeated. WHD17 final020159swaps; 040MMU functional
388swaps/nonblank/codeunchanged. Chip-only020 native despiteCUSTOM3=7; delay1
preservesoriginalwait despiteCUSTOM3=1. 32 gameplay module instruction sources
unchanged (comments only); no input fixtures in normal release.
Highscore test s6-flow-direct-020: naturalrace4216returns/66crash, replay,
GAMEOVER, input-onlynameentry, SaveFile380 and normalAbort. Saved cipherexact,
s6-score-reload freshboot380byteexact. UsesNoWriteCache/WriteDelay0. Buffered
writes hang during exit inWHDLoad20 emulator, SAMEloop with500byte standalone
save-probe.slave(no gamecode): s6-save-api-20. No productionworkaroundforced.
WHD17 cached full game s6-flow-cached-17 also passes: 4216 returns/66crash,
all events including normal exit, saved380bytes exact cipher.
Earlier failedflowcaptures areNOTsavingpasses. Early s6-*matrix superseded by
s6f-* afterphysicalmemoryguard. AttempttoaddQshortcuttoflowfixture overflowed
PCrelativephaseinstall, rolledback; s6-flow-write-020 runinterrupted/notvalid.
All accepted exceptions/deferredP3/full-lap/intro remain. Userplayinstances
untouched. About1GB reclaimed fromverifiedgzip/deadownedruntimecleanup.
PR29 updated, pushed and ready for review. .DS_Store untouched.

# Handling corrections committed — 52bec54 (2026-10-13)

Current goal: ensure enhanced physics accuracy after user reports easy sideways
slides in ordinary turns and off-road, perhaps around60MPH. Two fixes in
HardDrivinMotion.s / HardDrivinPhase.s; authoritative PHYSICS_ACCURACY.md.
Steering now uses CURRENT velocity/RPM-derived MPH, restoring engine anchor V
before native endpoint evaluation. Native spin recurrence held for8fields,
then trunc(signed_word(spin*9)/10); spin-rate integration splits at boundaries.
Motion offset24 is now elapsed spin PHASE0..7, not Q16 carry. HDSPIN02 fixture.

Validated: current-speed matrix5544 (old1120 extra/480 missed onset cases),
matched-input onset4752, native full-step297 incl135reverse, spin180sequences/
5886checks, embedded math595spin+all prior angle/fall/position/drift/crash cases.
Actual700field input-only captures physics-handling-v2-{020,040,a500} pass268
spin returns and6exits. First road skid128consumedfields on020/040. Beforecode
physics-skid-before-020 had roughly240fields between observedentry/exit.
Normal physics-normal.slave byteidentical s5-final-normal.slave.
No new FPS claim or full-lap claim; existing clock/deferred checks remain.

Private tools check_spin_recovery.py, check_spin_native_frame.py,
check_skid_onset.py, check_skid_current_speed.py, check_skid_anchor.py,
check_live_spin.py, check_physics_motion_math.py. Probe code is relocated to
unused0x80000/0x81000 in isolated Unicorn; initial d73800/d74000 placement
OVERLAPPED older snapshot power table, so superseded test failures invalid.
Final private code uses absolute references to preserve snapshot storage.
Current source is fully built and tested in emulator too.

All capture jobs for this work completed. Seven stopped owned runtimes removed;
snapshots gzip-verified with SHA256, saving168MB (physics-cleanup.json).
Corrected no-input playable slave physics-play-final.slave is launched in
play-physics-040: A1200/04025MHz,2MBChip+8MBFast,CUSTOM1=1 CUSTOM3=2.
User handling feedback is still welcome; no full-lap pass is claimed. User play instances are separate;
do not kill old play-a1200, play-a500-s5, play-a1200-s5, play-a1200-040-s5.
Pre-existing .DS_Store remains untracked. Step6 release integration still pending.

# Step 5 COMPLETE — 932d743 (2026-10-13)

Step-5 goal achieved. All captures/analysis jobs completed. Tracked authoritative
report STEP5_RENDERING.md; local roll-up tmp/s5-final-report.json.
Commits: 2c564f5 rotations, b468149 lean wait, dcb1d3d cache diagnostic fixes and
candidate pricing, 932d743 final selection/matrix/plan closure.
Normal build unchanged. Step 6 release integration is next, NOT started.
Preserve accepted C2/C5 exceptions, original clock defects and deferred P3,
C3 full-lap timing, C6 human laps and intro work.

Final measured CUSTOM3 policy for developer VERIFY_RENDER build:
000 (both memory profiles) and 020+Fast =6; 030/50 =0 original renderer;
040/25,040/40,060/50 =2 rotation only. Automatic CPU/memory patch selection and
release UI still belong to step6; developer mask can request rejected variants.
Do not promote Fast edge arrays or private background prototype.
Final source gameplay s5-audit-a byte-identical s5-wait-v3-a; cache fixes only
change VERIFY_CONTACT_MATH/VERIFY_TRAFFIC_ROUTE_MATH diagnostic builds.

Final off/selected swaps per500fields A/B/attract:
A50039/41,58/60,67/72; A500Fast39/43,58/62,69/73;
020150/159,222/223,231/238;030252/252,333/333,348/348 (selected=off, notduplicate);
04025 240/245,272/274,290/299;04040 244/247,274/273,297/306;
060246/248,270/274,300/309. 04040 B losesone swap0.36%, explicitlydocumented.
Wholewindow comparisons, not equal-scene/net-original simulation claim.
Original clocks differ in030/04040 B start despite matched sampled pose values.
030 finalrotationB333->326; +wait326->314, so originalrendererselected.
04025 wait274->270; retainoriginalwait for040/060 conservativepolicy.
Earlier rotationbinary matrix superseded by finalsamebuild results.

42wait experiment runs +21samebuild off runs audited all13render sites (63).
All27native trace executable snapshots unchanged;161branchrangespass;
172disablednative rangespass with freshnormalbyteequals2-final-normal.
Finalselected040MMU s5-final-mmu500fields242swaps FUNCTIONALONLY, viewedcockpit
(crackedwindshield isgamecrash, not emulatorerror),13sites/codeunchanged pass.
ContactMMU216wide/162response/189projection/45roll/135pitch andtrafficMMU126pass.
All63matrixruntimes plusMMU anddiagnosticownedruntimesremovedafterPIDchecks;
traces/calibrationbankscompressedwithdecompressedSHAverification. Userplay-a1200
andpreexistinguntracked.DS_Storeuntouched. No pending repositorychanges.

Additional contract evidence: independentPythonwaitmodel16384casesmatchesold/new
with guestmaterializedCCR. Actualtracehelperregister/stackchecks2535+2690A500,
9815+10360A1200calls pass. IMPORTANT profiler copies raw regs.sr without MakeSR;
initial trace-X checker failed because SRisnotmaterialized, so do NOT use its
SRcolumn as CCRproof. IsolatedUnicornmodelmaterializesSRandisvalid. Nativevertex
models readD/Adata, notrawSR. No emulator binary/timing changes made.
Rotationcompleted-call grouping rotation-calls.json confirmsquarterturncosts
A500Y26 7467->2355cycles;0203376->920;generalpathsmalloverhead documented.

Privatebackground prototype s5-bg-proto-attract, source s5-bg-source,1200guarded
modelcasespass but nohardwarepixel-twin claim. Sync72->73swaps; evenalllastplane
waits removed normalized146calls savesonly2.93% beforebarriers. Notpromoted.
CockpitallrestoreA500<3%;020excludingdynamiclargegaugecostleaves2.06/2.84%
optimisticstaticceiling. Edgeentiredivisionranges<3%. Spanrewritepriced<3%.
Do not restart these rejected designs without new evidence.

# Latest step-5 handoff: b468149, all jobs complete

HEAD b468149 commits lean wait candidate +initialvalidation after2c564f5rotation.
Goalfinishstep5ACTIVE. No current runtime jobs. Ignore stale active-job entries
below: sessions46518/23726/31472/54270/59046/34903 allcompleted.
Currenttrackedcode HardDrivinRender bit2 uses BLITWAIT macro originalCIAbackoff.
V3samebuild rotationonly2 / +wait6 swaps: A500A41/41,B59/60;
020A159/159,B219/223. Waitms/swapA500A4.2117/3.6143 B3.0949/2.8045;
020A4.3908/4.3538 B3.2802/3.3412 (differentworkload, notisolatedgain).
16384contractcases pass, check_render_patches13sitesall8capturesPASS.
Normal s5-wait-normal byteequal s2-final-normal. V3attractslavebuilt with
HD_FIXTURE_FLAGS=-DVERIFY_ATTRACT=1 build_s5_reference.sh.
V3MMU s5-wait-v3-mmu500fields348swapsFUNCTIONALONLY; nonblankplanaroutput,
codeunchanged and13sitechecks pass. Screenshotcockpit.png generated.

Remaining wait validation: all7profiles +attract with2vs6 (A500/020 A/Bdone),
finalcombinedselection andeventuallyfull0vsselectedcombinedrenderer matrix.
Do notclaimStep5done. Backgroundasync, cockpit/overlays, remainingcandidate
pricing andcacheaudit documentation stillrequired. Pixel-looprewrites require
pixel twin; currentrotationguardedvertexcontract is not called pixel twin.

Additionalprice_solid_rewrite.py on actualeligibleuniformsolid work gives
optimistic CPUwork saving A500A1.622/B1.345%;020A2.389/B2.402%, with ZEROdispatch,
maskinversion,alignment,loopoverhead and25%eligibleinteriorstore saving, preserving
finalplaneD2/flags. Below3%threshold: skip thisparticularsolidspanrewrite, not
blanketclaimallrasterizersimpossible. Reports solid-rewrite-price.json inside
s5-rot-v2-{a500,a1200-020}-{a,b}-0. Larger native span shares overstate opportunity.
Native2da2wholeedge setup2.864%A500A and1.34%020A: replacing twoDIVU cannot
save3% there. Projection2b74/facedot2bde alreadyregisterresident16x16 operations,
notpaired32x32. ZeroSin/cosunitextra specialcases only358/35163A500Avertices,
402/23763B,1356/130733020A,1416/88249B; don'timplementmarginalextra shortcuts.

Separate000Fastmemorydiag built s5-memory-000-a withVERIFY_RENDER_000_MEMORY=1.
Prefix s5-memory-000-a500-fast-a-{0,1}:39/40swaps, edge3.140/3.042ms/swap,
originaledge1.223%window. No equalworkbenefitclaim, memoryoptionnotselected.
AllnewtracesautoSHAcompressed+ownedruntimecleaned. DocsSTEP5_RENDERING pending
lastfactscommit; no productioncodechanges sinceb468149. Preexisting.DS_Storeuntouched.

# Step 5 active: rotation committed; lean blitter wait being measured

HEAD 2c564f5 commits gated renderer + exact rotation shortcuts and STEP5_RENDERING.
Goal finish step5 remains ACTIVE, not complete. No new agents authorized.
Step4 exceptions C2/C5 accepted; C3 automated full-lap + C6 human laps + P3 deferred.

Rotation full 42-run matrix complete. Swaps per500fields A/B/attract off/on:
A500 39/41,58/59,67/72; A500fast40/42,60/60,69/73;
020150/159,222/222,231/237;030251/251,323/325,349/349;
04025 240/245,272/274,290/298;04040 244/247,276/278,297/306;
060246/248,273/274,300/309. No rawwindowregression, notequal-scene/netoriginalclaim.
Prefixes s5-rot-v2 (000/020 A/B plus000attract), s5-rot-v2r (fastCPUs + Fast000/020attract).
All sourcebuild s5-rotation-v2-{a,b,attract}. Rebuilt source-a byteidentical v2-a.
6000 original/model/Unicorn cases fullregs/stack/CCR/guardedbuffers/overlap pass.
Model native trace matched35134A500+132209020 vertices. Branch150pass.
Normal s5-normal byteequal s2-final-normal; fresh s5-normal-disabled172rangespass.
MMU s5-rot-mmu-040500fields344swapsFUNCTIONALONLY outputcockpit.png viewed,
codeunchanged. All18traceprofiles gamecodeunchangedbeforeafter.

HardDrivinRender.s currently UNCOMMITTED wait experiment. CUSTOM3bit0 Fastedges
experimental/notselected (initial020wholewindowregressed despiteedgerowcostdown),
bit1rotation,bit2wait onlyCUSTOM2zero. Earlier selfpatch attempt didnotreturnfrom
resload_Patch, then OSidle; failed s5-wait-A6 no benchmark. Do not use.
V2redirect11originalgameJSRsites instead; PERF_EXISTING_RANGE baselineoriginal
slaveJSR_blitwait+2NOPs, notpristine; check_render_patches.py checks target/listing.
V2tightpoll bootworks,16384contractcasespass. A500A41/41wait4.199/3.420ms;
020A159/158wait4.422/4.769ms. TightpollNOTselected due020regression.
Private s5-tight-wait-render.s + s5-tight-wait-contract.json preserve oldsource.
CurrentV3 _render_wait usesBLITWAIT macro0args, retainsCIAbackoff, onlyskips
MOVEM+delaychecks.16384contractpasses. s5-wait-v3-{a,b}.slave/.lst built.
Active matrix sessions46518(a500),23726(020) using run_render_matrix.py;
outputs tmp/s5-wait-v3-<profile>-matrix.{log,json}. States2(rotation)/6(+wait),
windowsA/B. Eachcapture autoanalyses thenSHAverifiedzstdcompressionanddead-runtime
cleanup. Check these jobs before starting more. Sourcecomment/docs pending commit.
V2matrixsessions9789/35086 likelydone; initialfailedsessions12992/45280done.
Allrotationmatrixsessions41628/33703/35069done; no remainingrotationjobs.
Smoke36955done;CUSTOM2gate36804done:13sitespass. Waittest20141done.
Newauditor checks existingwaitpatches +rotationnativepatchranges.

Tools: capture_render_window.py supports --slave,--profile,--window A/B/attract,
--render N,--custom2 N,--fields500,--trace,--mmu. CUSTOM1always1.
run_render_matrix.py env S5_MATRIX_PREFIX (freshprefix),S5_BUILD_PREFIX,
S5_RENDER_STATES='2 6',S5_WINDOWS='A B'. Profilestrace000/020otherscounters.
Always envPROFILE_FSUAE=$PWD/tmp/profile-emulator/fs-uae HD_PROFILE_DIRECT=1.
Runner derives shortINSTANCE s5m+sha256(name)[:8] (longnamesexceededUnixsocket).
Lock.pid files guard sameprofile and skip6-completedrows; partial4row reruns should
usefreshprefix, do not overwrite/loop on deadPID. Local build_s5_reference.sh uses
HD_FIXTURE_FLAGS=-DVERIFY_ATTRACT=1 forattract (normaldefaultDRIVE), sameStep4flags.
Contracttestscheck_render_rotation.py,check_render_memory.py,check_render_wait.py.
Currentwaittest reportdescription stillsays tight thoughV3backoff: fix label only.
Traceanalyse_render_trace includes replacementY/X andwait symbols costs. Direct
rangesnotinclusive. Rotationtrace model uses actualoriginalinputs/outputs.
price_span_paths.py recorded solidboundary/interior costs andpatterns; nofillercodeyet.

Remaining step5: select/validatewait variant acrossallprofiles+attract+MMU;
cache/codewriteaudit documentation (alreadycacheson, nativeSMC usesdatapointers,
lowmemstubcreatedbeforefinalcacheflush), remainingcandidatepricing andworthwhile
pixelkernels withguardedpixel twins, finalcombinedmatrix/netoriginalqualifiedreport.
Planexistingrotation2b74isprojection/2bdeisfacedotproduct, notpaired16x16longmath.
Nativeclippingalreadyhasearlyacceptreject; backgroundalready10longstores/row.
No claims of finishedstep5. Keep P3 deferred.

Cleanup: allcompletedmatrixtracescompressedSHAchecked andownedruntimesremoved.
s5-inactive-cleanup.jsonremovedfailedsocket/selfpatch,normal,MMU/debugruntimes
withdeadPIDs (154867678bytes). Captures remain. Disklast~92GBfree. Failedlogs
are nottiming evidence. Preserveuser play-a1200. Newrawtraces can be3.6GB each;
compact immediately. Git only.DS_Store preexistinguntracked besidescurrentchanges.

# Step 4 closed within accepted scope (2026-10-13)

User explicitly deferred C3 automated full-lap timing. C1/C2/C4/C5 complete;
C3 closed for current scope with full-lap timing unverified/deferred. C6 human
laps and P3 remain deferred. C2 native clock dependency and C5 0.029365 ms/frame
excess exceptions accepted. Original defective clocks preserved. No production
changes or captures for closure. Step 5 next, not started by this request.

# C2 clock exception accepted (2026-10-13)

User explicitly accepted demonstrated clock-dependent differences while preserving
original clocks, including defects. C2 complete with exception; untouched-clock
comparison remains failed, conditional gameplay equivalence evidence unchanged.
C1/C2/C4/C5 complete; C3 full-lap deferral scope remains outstanding.
P3 and C6 deferred. No source changes or new captures.

# C5 excess accepted (2026-10-13)

User explicitly accepted C5 remaining 0.029 ms/frame excess. Selected source
62e9913: A 7.050927562, B 5.769365478; B excess 0.029365478 over 5.740.
C5 complete with build-specific exception; raw measured gate failure retained.
C2 clock exception and C3 full-lap deferral scope remain undecided.
User asks what C2 exception means; explain conditional gameplay equivalence
under matched native clock observations, not untouched-clock equivalence.
No production changes or new captures.

# Closure audit: pending decisions, no active runtime jobs

CurrentHEAD62e9913 sourcehashes matchc5-fused-summary; G1ApassesBfails.029365.
C2causalreportconditionaltrue/unchangedfalse/c2acceptedfalse. C3full_lap_verified
false; userhumanlapdeferralconfirmed, broaderautomatedscopequestionpending.
ThreequestionsnowcollectedunderSection6 Outstandingclosuredecisions, docscommit
pending. NoanswerreceivedtoC2clockexception,C3scope,C5.029excess. Do notassume.
Thisturnauditedandconsolidateddecisions. Previousgoalturnprogress(realcodecommit).
Do notmarkcomplete. Futurecontinuationsshouldrevalidateuserreplies beforemore
changes; allremainingclosurepathsdependonthesependingdecisions. Blockedthreshold
notyetmet; no automaticpause. P3/humanlapsremain deferred.

# Current: fused scan selected; B excess0.029365ms, user decisions pending

AuthoritativeSweep worlditerator usesD6=8 aftercachedbounds, preincrementsA3,
CMP.B+DBEQfusesclassreject+loopdecrement. AllcandidatespreserveD6; boundsradius
unusedafterpreparation. Active/E931gatesmovedbeforeMOVEM. Stateoffsetsunchanged.
check_c5_fused_world.py1536oldHEAD/newcases allclassbyteswithactive/inactive,
pools0/1/2/7/98/129,types,overflow/counterwrap;all106statebytes,records,regs,
stack/CCRexact. Native32/reused32/world96/scan-count20 also pass.
HeaderstaleopenC4commentcorrected; D6nearcommentnowcallervalue. C4logicunchanged.

Selectedc5-fused-{a,b}-{off,on}500fields:7.050927562/5.769365478;
Apasses8.070,Bfails5.740by.029365478. Sweep2.466872/.749450.
Boff/on73/60swaps7.288380/5.990449FPS,137.719196/165.687453ms,
poly26.708333/27.389831(2.55%). A38/39swaps260.955957/253.561191ms.
Finalsourcerebuildc5-fused-source-a/b byteequalcaptures; normalidentity147branches,
disabled169rangefixtureexclusions,4traceaudits pass. Reportc5-fused-summary
sourcehashesupdatedaftercommentchangesandbyteidentityverified.

Rejectedinactivefinishhelpertestedandcapturedc5-finish:earlyBTSTactive+pushBEST+
LEAstackpopbranchesnativeonlyinactive+BEST0. 1024fullreg/CCR/statecasespass,
collisiontests pass, butB6.681702worse; REVERTED. Productionfinishunchanged.
Privatec5-finish capture/listing retainsrejectedcode; no promotion. c5-finish
summarysourcehash belongsrejectedcode;don'tuseascurrent. Cleanupbothsets~9.78GB
each reports c5-fused/c5-finish-cleanup; runtimesPIDdeadremoved. Allsessions
58223/14653/99903/16004/52399/57398/40660/89145/71288terminal. Noactivejobs.
Initialc5-scannamecollision abortedbeforerun; historicalcapturesuntouched;
buildc5-scan-a/b slave/lst restoredfromverifiedhistoricalretainedcopies.

NEWpendingquestions: DoeshumanlapdeferralcoverC3automatedfull-laptimingtoo?
AndacceptC5.029msremainingexcess? Noanswersyet. EarlierC2clockexceptionquestion
alsoawaitsanswer. Do notassumeanyaccepted. C1/C4complete; C2/C3/C5open;
C6/P3deferred. Goalactive. DocsupdatedcommitpendingcheckHEAD.

# Current: word-only traffic cleanup; selected B deficit0.214435ms

Production Traffic first5zero interpolationpaths skipCLR.L andBRA; lowwordonly
consumers permitthis, finalD0/CCRunchanged. Final check_c5_pose_zero.py20000 and
check_p1_pose.py20000 rerunpass; sourcehashedc5-word-pose-check.json. Finalsource
rebuildc5-word-source-a/b byteequal capturedc5-word-a/b. Normalbyteequal,
147branches,disabled169rangesfixtureexclusions and500fieldcoveragepass.

Selected current c5-word-{a,b}-{off,on}: G1A7.147527991 B5.954435442 -> Bfails
5.740by.214435442. Aoff/on38/39swaps,mean260.955957/253.561206ms.
Boff/on73/60swaps,7.288380/5.990449FPS,137.719196/166.027101ms,
poly26.708333/27.152542(1.66%scene mismatch). Sweep2.603144/.773706.
Trafficdeltas-.465895/-.152466. Physicsdelta6.822962/5.401367. Do notcalltotal
savingisolatedarithmetic: nativeclock/render/physicsmixchanges.

REJECTEDprivatec5-eightexperiment: _traffic_frame hot8..255 andphase_apply8
skipswalker so nativetail ownsroutewrap.44kold/newrecord+first14statecasespass;
livec5-eight-native-traffic1440updates92crossingspass; prepared34flagshows
1260hotupdates90hotcrossings. BUTfreshgate7.191480/6.300888,trafficB-.667352
butphysics6.227506 ->worseoverall. REVERTEDhotextension. Production9..255asbefore.
Privatecandidate tmp/c5-eight-traffic.s andcheck_c5_eight_micro.py retained.
Do notclaimexperimentpromotedoruseitsnative8proofasproofchangedprodgate.

C3refreshed8awardcapturesat98f333c(beforewordcleanup): c3-zero-{checkpoint,finish}-
{a500,slow}, c3-zero-v2-{checkpoint,finish}-{020,040};actualprofilesa1200-020,
a4000-040-25. Failedoriginalfastnames setup-onlybadprofile not evidence.
Checkpointvideo30/40/28/26,consumed27/37/28/26;finishvideo40/36/30/28,
consumed34/31/28/28. Onceeach,correctlatch,noawardcrash. Notfull-lapacceptance.
Reportc3-zero-awards-summary sourcehashesandcapturedslaveidentity.

Allsessions39330/40165/62658/96056/25938/4605/90319/9701/5829/21098/3527/
7161/93473/14769/82960terminal. Cleanupc5-word/c5-eight each~9.78GB reclaimed,
c3-zero156MB, native-runtime additionalcleanup report. AllPIDdeadbefore removal.
Noactivejobs; userplay preserved. Docsupdated,commitpendingcheckHEAD.
C1/C4complete,C2exceptionpendinguser,C3/C5open,C6humanlaps/P3deferred.Goalactive.

# Current: exact zero traffic interpolation lowers cost; B remains 0.483 ms over

Authoritative HardDrivinTraffic.s _traffic_pose_values skips each zero-input
MULS/DIVS pair, leaves nonzero arithmetic/overflow unchanged. Final roll still
executes200-phaseSUB to preserve X. Firstdraft test expanded to materializedCCR;
whole nativeblock flags differ alreadyfromexistingwrapper, so compareoldHEADhelper
vsnewhelperCCR; separatepristineblock outputtestunchanged. check_c5_pose_zero.py
20000passes withall128zeromasks plus randomfullsigned/phase/overflowcases;
check_p1_pose.py20000nativeblockpasses. NoP3 cadencechanges. Nativephysicsmix
analysis c5_native_physics_mix.py exposed106enginecalls59physicsreturns vs73/73off;
P3unchanged. Zeromultiply nativehelperoptimization rejectedaspoorzerohitrate.

Fresh c5-zero-{a,b}-{off,on}500fields sourcehashpaired traces auditpass.
G1 A7.182020725 <8.070; B6.223302738 >5.740 by.483302738.
Trafficphase deltas-.398786880/-.215553245. Oldc5-rotate8.023/6.881.
Boff73swaps identicalbaseline,on60swaps5.990449FPS169.422136meanms,
29.915254vs26.708333polys12.01%mismatch. Do notclaimtotalsavepurearithmetic.
A38/39swaps;on253.033843ms. Sweep2.598774/.946906.
All147branches,disabled169rangesfixtureexclusions,normalidentity,comment-only
finalsourcerebuild c5-zero-source-a/b byteidenticalcaptured. Reportc5-zero-summary.
C4previousmatrixnotrerun(playercollisioncourseunchanged); arithmeticexacthelper
comparison iscompatibilityevidence. Documentsupdated. CommitpendingcheckHEAD.
Allsessions25793/88027/87733/58294/80967/66477/42435/66607/62090terminal.
Cleanupc5-zero-cleanup verifieddecompressedSHAandremoved2ownedruntimecopiesPIDdead,
reclaimed9777013515bytes. Noownedlivejobs;userplayruntimepreserved.

C1/C4complete,C2exceptionawaitinguser(noresponse),C3timing/full-lapopen,C5Bopen.
Humanlaps/P3deferred; keepgoalactive. Nextsave~.484msBwithoutenginecadencechanges,
orfinishindependentC3timingwork. Pendingclockexceptionnotautomaticallyaccepted.

# Current: C4 complete, twenty live extreme-profile cases pass

C4 is now complete in the tracked plans. Production assembly unchanged from14c53b3.
check_c4_live_matrix.py passes20cases; report c4-live-matrix-summary.json.
Stationary c4-live-follow/headon, turning c4-turn-follow/headon, moving
c4-moving-v3-follow/headon, loop/jump/checkpoint/finish c4-final-*; each slow/060.
Slow stationary/turning sweep1 each, crash25; moving follow sweep1 at18fields,
headon native contact; allfast nativecontact. Exact targetmain96/actor10 proven.
All overflow0. Loops no crash exit50/51; jump nativecrash324/349. Awards onceeach.
Aux650*11 records allclass64 non-solid. Notfull-lap or arbitraryT proof.
Private moving v2 was invalid (seedbefore race then reset); v3 requiresdrive_state2,
flagtransition0->1, targetmoved>=20, actualpositive speed. No clock/trafficwrites.
Alljobs terminal (8588,60865,27048,92599 plus previous sessions); cleanupreport
c4-live-matrix-cleanup.json compressedcalibrationSHAverified and8ownedruntimecopies
removedPIDdead. Keepuserplay runtime. Source-hashed manifests underbuild/.

C1/C4complete,C2clockexceptionpendinguserreply,C3equal-time/full-laptimingopen,
C5latestA8.023passes/B6.881failsaccepted5.740. C6humanlaps/P3deferred. Goalactive.
Do notaskhumanlapsorassumeclockexceptionaccepted. Priorhandoffbelowhasdetails.
Docscommitpendingthishandoff; checkHEAD. No codechanges thisturn.

# Current: C2 causal clock replay matches all650 gameplay states; exception pending

Source unchanged from14c53b3. Builtc2-clock-native PHASE+SWEEP+DISPATCH_NATIVE+
STEPINPUT_TAPE. Productionx86 capturesc2-clock-record-v2 CUSTOM1off and
c2-clock-natural-on:650returns,660controls,all97taperecords19mousepositions;
6251/6341fields. Untouchedclockfails: car33badfirst99,replay376,pointer185,
mainobjects551; RNG/traffic exact. Inputs match. Reportnative-world-comparison.

NEW causal diagnostic underignoredtmp. capture_clock_counterfactual.py records
16armed nativeclockreadsites (9executed). Records G9790.l,G9798.l,G979c.b;
on replayinjectsonlythose9bytesatidenticalPC/physics-indexsequence; no deadline/
recovery/car/input/RNG writes. All4062observations exact, immediateGDBreadback
assertionspass. c2-clock-debug-record/replay650states ALLcar/RNG/replay/pointer/
traffic/all12actors/main98+aux11objects match. SceneBooleanmatch,660inputs match.
6251/6323fields. StrictdataBSSstilldiff; allremainingbytesclassifiedno masks:
VBLclocks/music/channel, retainedinstructiontextstate90aa..90b6+9ca2..9cf0
(provenunchangedfromanchor); polygonfill9050..9058 andclippingscratch979e..98de
onlyreturn0. CodeownersGAME_TIME updated. C2stillOPENunchangedclockgatefails;
thisiscausalconditionalvalidationnotwaiver. Asyncquestionnowaskedwithfullproof:
acceptdocumentedclockexceptionorKeepC2open. Awaitreply; don'taskD4preserveagain.

GDBoriginalstub silentlyignoreswrites (alreadyknown). Initialc2-clock-record
exceeded20breakpointlimitbeforegameplay; c2-clock-replay-onwritesignored, invalid.
Hostreplayc2-clock-host-replayusedverifiedLLDBwritesbut~.25/sec; intentionally
stoppedownedcaptureSIGINT, noacceptance. Preservedhost-write-log. host_poke.pynow
supportscomma-separatedaddress/data groups, validatesreadbackallwrites.
Finalefficientbackend: privatecopytmp/clock-debug-build of sharedAPROF
source/build, addcheckedRAM-only Mpacketwritehandler via localclock-debug-writes.patch.
BuildnativeARM (existingobjectslibsARM; initialx86linkfailed; removedonlylocalbarto.o,
rebuiltclang++/clang). Neveruseforperformanceclaims. Originalprofileemulatorunchanged.
Withoutwrites diagnosticARM reproducesbothx86controls EXACT physics/controls/world
bytes,eventfields,clockobservations. c2-clock-emulator-equivalence.json2pairspass.
ToolforcesGDBbinary-download-packetoff to selectM, verifiesvaluesimmediately.
Finalc2-clock-causal-summary.json source/emulator/slave/tape hashes, invalidattempts,
conditional_simulation_equivalence:true,unchanged_clock_equivalence:false,c2_accepted:false.

Allsessions56379/15374/44032/94818/29849/21461/61398/72894/74959/81117terminal.
7ownedruntimesremovedrecordedPIDsdead;calibrationbanksandfailedrawstreamsSHAverified
compressed; cleanupc2-clock-cleanup.json. Noactivejobs. Privateemulatorbuildretained
forreproduction. Productassemblyunchanged, docsupdated; commitpendingthishandoff.
C1complete,C2decisionpending,C3/C4/C5open,C6/P3deferred. LastC5A8.023passes,
B6.881failsaccepted5.740 (scenemismatch). NoautomaticC2passorStep4completion.

# Current: exact sweep shortcuts bring A within budget; B still fails

Authoritative Sweep now caches 6 LONG limits (SW_LIMITS82, state106bytes),
uses SUB.W/BVS for endpoint range, exact yaw(sin16384/cos0) EXG+NEG and flat
pitch(sin0/cos16384) skip. Other rotations unchanged. P3 remains deferred.
Bounds algebra: x and x-d against [-r,r] => x in [-r+min(d,0),r+max(d,0)].
Limits computed once per pool from ASR3 current/start long positions; candidate
retains signed-word movement validation. Existing counters/state offsets preserved.

Tests sweep-bounds-equivalence20123 (old gitb8a625c vs new assembled predicates,
fullsignedword raw/delta/extents and fractional start/end), endpoints20049
(including overflow eachaxis), native rotation15000 explicit fastpaths/extrema,
native32/reused32/world96/scancount20/interpolation10000/filter10000 pass.
Source final comment-only rebuild c5-rotate-source-a/b byte-identical to captures.
147branches, normalbyteequal, disabled169ranges with fixture exclusions.

Final c5-rotate-{a,b}-{off,on}: 500fields each10.015943522s, mincoverage
.9999998029584383. G1 A8.023431838346012 <8.070 by.046568161653988;
B6.880910041446374 >5.740 by1.140910041446374. Sweep2.605970930/.983988375.
Aold8.526803,new8.023432 delta.503371 but sweep-only.415339, othersampling/
phasechanges also contribute. Bofftrajectory changes again (now73swaps vsold84).
DO NOTcherrypickbaseline: B remainsFAIL underacceptedlimit, scene10.32%mismatch.
G2 Aoff/on3.793951/3.893792 FPS,38/39swaps,260.956018/254.088836meanms,
poly57.756757/54.947368; B7.288380/5.890608,73/59,137.719196/169.580275,
poly26.708333/29.465517. Nativecheckpointcalleeextra0 inbothwindows.
Intermediatec5-bounds-only gate8.504439/6.979916 retained, notcurrent.
Finalreportc5-rotate-summary includeslatestsourcehashes/rebuildequivalence.
Cleanupfirst c5-bounds reclaimed9779389720bytes; finalcleanup report
c5-rotate-cleanup.json. Noemulatorslive; ownedruntimes removedafterPIDdead.

C1complete, C2/C3/C4/C5open, C6/P3deferred. A-costdeficit resolved; next B gate
and native-clock/full650 mismatch, plus remainingtrajectory/laptimingacceptance.
Do not askforhumanlaps. Do not markStep4complete. See prior detailed handoff below.

# Current: checkpoint/finish post-physics evaluation integrated and measured

New authoritativeHardDrivinCheckpoint.s (_checkpoint_post), includedwithTerrain
inTimeIFDVERIFY_DRIVETRAIN_PHASE. Dispatch_after_physics conditionalBSR. Exactly
revisedprivatehelperbody: 0/8/forcedbypass;racegate;current/nextroadflags3000;
nativeC022 withtemporarycursor+20;save116workspacebytes+selectedword;freshdirection
G9464vsG9470;restorescratch/cursorbeforeaward;native92C0/936A withE930temporarily0,
restoredafter. Native scenechecksretainedfallback. Noenginecadence/P3change.

Builtc3-cross-source-a/b AND checkpoint/finish fixtures: byte-identical to measured
c3-cross-cost-a/b AND capturedc3-cross-v2-checkpoint/finish. Exactcmpverified. Normal
byte-identicalbaseline;branch147;disabledA/B169rangesinclfixtureexclusions. Source
helperpasses512unitcases; testreadsauthoritativeCheckpointwithsymbolaliasforold
capturedlayout. privatebuild_c3_crossing_cost retiredguard; builderC3_CHECKPOINT_POST
nowrejects(sourcealreadyintegrated). Omitprivateflagforfuturefixtures.

8v2captures130fields: checkpoint A500/slow/020/040 video30/40/28/26, consumed27/37/28/26;
finishvideo40/36/30/28 consumed34/31/29/28. Eachawardonce/latchcorrect/noawardcrash.
Reports c3-cross-source-timing-summary.json carriesbinaryequivalence+sourcehashes.
Notfulllap/C3complete. Final4x450fieldsource loops/jumps sameprioroutcomes, NO
checkpoint/finishawards: slowloopnocrashpeak615exit50;fastloopair309/310peak627.25exit51;
slowjumppeak224.5air148..315crash324;fastjumppeak221.125air137..345crash349.
Reportc3-cross-source-geometry-summary.json. Fastjumpnextwaypoint127712->127720 at348,
slowstays127712; targetwaypointtuple(110,24,25,0). NativeE4A2..E4D0 ORscrash into94BA,
DB84 suppresseswaypointwhile94BA nonzero: slowcrashed324 beforesection25, fast348
progressbeforecrash349. Don'tmisclassifypointerdifferencealoneastunnelling.

C5currentc3-cross-cost-*500fieldpaired: G1A8.526803211167987>B8.07 by.456803211;
B4.136775093864274<5.740 (margin1.603225). Newhelper self.066399911/.056562342ms.
Nativecalleeextra0bothwindows (noactualquery/awardcalleeinthosewindows). Sweep
3.021310264/.971933149. Aoff/onFPS3.794/3.794 poly57.756757/54.891892 (4.96%);
B8.386629/5.890608 poly14.493976/28.120690 (94.02%sceneMISMATCH). Bdisabledtrajectory
changedvspriorbuild; NOTisolatedoptimizationorbaselinecherrypick. G1overallstillfailA.
Frame_budget now dynamicallyWATCHes _private_checkpoint_post or _checkpoint_post,
adds native_timing_extra onlynon-slavecalleeinstructions insidehelper callstack;
reportC5adds nativeextra toavoidomittinggame work outsidephysicsphase. Source
reportc3-cross-cost-summary hasprivateoriginalmanifests+authoritativehash/equivalence.
All4tracesvalid500fields mincoverage99.999969%. AllsourceASMsmeasured via exactbyteeq.

Allsessions6510/19518/89674/19548/50189/93808/95314/29220terminal0. 6ownedruntimes
removedPIDdead; 16capturescalibration+4costtraces zstddecompressionSHAverified;
cleanupc3-cross-source-cleanup.json reclaimed10096193065bytes. Noactivejobs.
C1complete,C2/C3/C4/C5open,C6/P3deferred. NextremainingcostA.457ms, fullnative650
clockdependency,full-lap timing/remainingextremeT acceptance; don'tclaimstep4complete.

# Current: road-workspace restoration fixed; finish matrix and stronger private event query

Authoritative source HardDrivinTerrain.s now saves/restores116bytesG9446..94B9
aroundoptionalC022/footprintquery, beforebothnativecontinuations. Trigger: stronger
check_c4_terrain_boundaries usedvalididentitytrig+realroadboundarycenters vsoldzero
initialtrig. Oldcodechanged58scratchbytes; carstateonlystillmatched. Oldclaimall
nativeglobalsunchangedwasweak. Repro check_c4_terrain_boundaries_before.py gitf6d9a50
reportc4-terrain-boundary-before-check.json. Updatedteststrictall32KBdata nowpasses
16boundarycases. Native24cases pass withvalidtrigs andallregsagree. Scratchselector
relocated-0x1000 (first+0x1800placementfailedPCrange; noactualbuildissue).

Built c4-workspace-a phase+sweepSTEPINPUT, normalbyteequal, branch147. CUSTOM1off
80fields c4-workspace-off checks169ranges incl6fixtureexclusions. Live450fieldloops
c4-workspace-loop-060/slow exactpreviousmetrics: fastair309/310peak627.25exit51;
slownoairpeak615exit50;bothnocrash,next127736. c4-workspace-summary.json sourcehashes.
C5lastmeasuredc4-guards PRECEDESworkspacechange; freshcostpending (don'tclaimcurrent
8.471/7.281measured). NoP3changes.

Finishfixturebuilder scenario finish seeds25000/0/25000heading360V400gear4, main
cursor0/maincourse and checkpointlatch255 explicitly. NOTfulllap. Builds c3-finish,
c3-finish-post madeBEFOREworkspacefix/privatehelperrevision. All8x100fields finish
awardonce,latch0after,nocrash. OrderA500,slow,020,040: baselinefield45/46/31/30,
post40/36/30/28, postconsumed34/31/28/28. Reports c3-finish-timing-summary.json.

Private c3_checkpoint_post.s revisedAFTERthosecaptures: preserve_terrain_selected
word bypushbeforecursor/workspace,popafter. RemoveearlystaleE930wrongwayguard.
AfterC022 compareG9464vsG9470(currentselectedleftZ vsnextleftZ), rejectphysical
reverse. ForforwardnativeawardtemporarilyclearE930,restoreafter. check_c3_checkpoint_post
512casesactualC022+hook withawardbodiesstubbed passallgame32KB/regs/stack/selection,
24awardcalls, bothcandidates/flags/race/physicaldirections/stalewrongway0/ff,
zero8forcedbypassX. Firstunitfailedbecausecapturedtrigsall0; fixedvalidyaw-343/+377
trig(sin-/+16339cos+/-1214),flatpitchroll. NeedsLIVEmatrix rerun beforeclaiming
sameeventtiming. Alsocost,wholecourse/gaps/air/crossingeligibility,collision etcopen.

Alljobs52081/32106/19474/76911/80533terminal0. Ownedruntimecopiesc3-fin-s/f,
c3-fin-rest-s/f,c4-w-offremovedPIDdead; calibration11captureszstdSHAverified,
c3-finish-workspace-cleanup.json reclaimed300732611bytes. Noactivejobs.
C2/C3/C4/C5open,C6/P3deferred. Nextrevisedpostquerylivematrix+scoping+cost,wholelap
andclockdependencyremain. Don'ttreatseededfinishaslaptiming.

# Current: checkpoint scene delay measured; private post-physics query helps

Authoritativephysics HEADf6d9a50 unchanged thisturn. C3newfailure: nativecheckpoint
award tiednearestroadflags inrender/scene pass oldpose (DE70/E1F6 flags3000,
bit12->92C0checkpoint,bit13->936Afinish). Marker92E2 actualcheckpointaward,
93BC actualfinishevent. WaypointsDB80 distinct. Mainflagcheckpointrecord106,
finishrecord1; stuntcheckpoint61. Newprivatebuilder scenario checkpoint seeds
22689/0/16453,yaw-343,V400RPM5000gear4,cursor60,stuntwaypoint6. Nogeometryedits.

capture_checkpoint.py forkofcapture_straight addsCHECKPOINT/FINISH breakpoints,
regexrowtags. Needs--timing --terrain --phase-inputs --sweep-world forcheckpoint
columns. Firstc3-checkpoint-{a500,slow,020,040}250fields omitflag => NOTeventevidence.
Reruns c3-checkpoint-event-*130fields: oneaward each,noawardcrash,latch255after.
Video/consumed36/50/30/28, intervals10/13/3/2. Maxwholeinterval10/13/3/2.
Priorposeconsumed26/37/27/26 so scene latencydoublesampling. Baselinespread22 fails.

PrivateC3_CHECKPOINT_POST=1 appends c3_checkpoint_post.s to copiedTerrain andbsr
_private_checkpoint_post at_dispatch_after_physics. Zero/8/forcedbypass, checks
race/wrongway, current+nextflags3000, listend; saves116bytesG9446..94B9 andcursor,
advancescursor20, callsnativeC022 usingphasepointer; selected1/2mapsoriginal/current+
next recordflags; restoreworkspace/cursorbeforecallingnative92C0/936A. Allregs
saved; stillUNVERIFIEDX/state sideeffects, finish,reverse,air,gaps/transitions,
wholecourseeligibility/cost. Notpromoted. Current/next-only scopepossiblemisses.

c3-checkpoint-post-*130fields video30/40/28/26, consumed27/37/28/26 ->14/11spread,
oneawardeach. StartupseedSTEPfield3consumed0 onA500/slow vs0/0fast. Keepbothmetrics,
noC3passclaim. c3-checkpoint-timing-summary.json includesfullmeasurements+scope.
Need developvalidatepostphysicscheckpointpolicy (includingfinish) andcost before
promotion. Wholelapsstillunverified,C6humanlapsdeferred.P3deferred.

Allsessions70780/6870/63757/81280/62327/90906terminal0. Sixownedruntimecopiesremoved
PIDdead, all12capturescalibrationzstddecompressionSHAverified; cleanupmanifest
c3-checkpoint-cleanup.json reclaimed391702366bytes. Noactivejobs.

# Current: terrain/pitch guards integrated, final-source geometry and cost checked

Source changes: HardDrivinContact.s invalid raw rear feedback +/-180 retains rate
except native8/forced; new HardDrivinTerrain.s included onlyVERIFY_DRIVETRAIN_PHASE,
MotionpatchesCDBE/C1B6 plusresetcontinuingword. Finite footprint/gap/priorcontact
candidate now authoritative. Ordinary binary identical,147branchranges,169disabled
ranges (inclinputexclusions). Pitch312+312forcedpass, reset256, complete native
terrain/collision/contact24cases matchallglobals/registers; realqueryboundary16
cases matchnativeglobals. check_c4_terrain_native/boundaries use authoritative
selector with old captured helper addresses; helper body renamed only. Initial
64KBglobalcomparison includedpatchedcode; fixedto32KBdata. Boundaryquery sentinel
provesqueryexecuted. No automatic C4 acceptance.

c4-source-loop/jump rebuilt WITHOUT privateKEEP_RATE/TERRAIN/CONT. Four450field
captures exactprototype metrics: jumpfastair137..345peak221.125crash349;slowair148..315
peak224.5crash324. Loopfastair309/310peak627.25exit51next127736;slownoairpeak615exit50
next127736. Bothloopsnocrash. Reports c4-source-geometry-summary.json.

Freshcost c4-guards-{a,b}-{off,on} finalsourcephase+sweep 500fields each.
G1 A8.470873058632208 B7.280574808945059, limits8.070/5.740 -> fail. Terrainself
.035226852/.030609580; sweep3.023329541/1.056450977. RawFPS3.794/3.794 and7.288/5.891;
polys57.756757/54.918919 and26.708333/29.224138 -> Bscenemismatch9.42%. Notisolated
helperregression. c4-guards-summary.json currenthashes. Sourcehash verification
alreadyinpairedreport; all4tracesvalidminimum99.99998%. NoP3cadencechange.

Allsessions92873/98985/95769/76969/7618/11420/78365/75053/27937terminal0. Cost+geometry
runtimesremovedownedPIDdead,trace/calibrationzstddecompressionSHAverified; reclaimed
9,812,667,825+158,391,681bytes manifests c4-guards-cleanup/c4-source-geometry-cleanup.
Noactivejobs. C2/C3/C4/C5open,C6/P3deferred. Next whole checkpoint/lap timing and
remainingextremeT collision coverage; coststillneeds .401/1.541ms. Don'tcherrypick
baseline orclaimfullstep4. Newterrainfamilyaddedprivateframe_budget attribution.

# Current: combined jump, pitch/native, and reset checks complete

User C6 human laps remain deferred; do not ask for lap confirmation despite the
stale goal objective. Goal active, C2–C5 still open. No production change this turn.
Combined KEEP_RATE+CONT+TERRAIN jump captures completed: fast air137..345 peak221.125
crash349/25; slow air148..315 peak224.5 crash324/25. Same metrics as noCONT jump.
check_c4_pitch_rate.py passes312 cases (204 unchanged/108 retained) and312 forced
native comparisons. Explicit IFND VERIFY_DISPATCH_NATIVE added to private builder
and copiedContact guard. check_c4_road_reset.py passes256 cases with nested resets
stubbed; materialized CCR compared. First scratch reset assembly failed PC range,
fixed scratch addresses before test (no game change). No full lifecycle proof.
Reports c4-combined-jump-summary.json, c4-pitch-rate-check.json, c4-road-reset-check.json.
Sessions8570/98970 terminal0. Owned c4-comb-f/s runtime copies removed PIDdead;
calibration banks zstd+SHA verified, c4-combined-cleanup.json. No active jobs.
Next: whole lifecycle/geometry native compatibility and final cost; guards remain
private, do not claim C4 completion or promote without remaining checks.

# Current: prefer guarded pitch rate + road continuation, not world object rewrite

AuthoritativeHEADphysicsc1115b4 landinggate unchanged. Correctednativejumpcrash
referencejustifiesreconsideringC4_KEEP_RATE (previousrejectionassumednocrash/
exactnativepeak). PrivateKEEP_RATE guardin_contact_pitch_rate_only readsraw-4(A5),
ifn!=8 andoutside[-180,180]returnswithoutoverwritingpriorrate. Existinghelper
alreadydoesnothingn0; ifpromotingaddexplicitforcednativecompatibilityguard/test.
Noobjectquery enabled innewcandidates; C4_SUPPORT_OBJECT leftoff.

c4-rate-landing-jump (KEEP_RATE+TERRAIN_ROAD, noCONT)450fields:
fastair137..345,peak221.125,crash349;slowair148..315,peak224.5,crash324.
Fastpeak/landingmatchesfiniteobjectprototype withoutnewquery. Thesepriorbuilds
retainnativeobjectplanes, justavoidinvalidfeedbackerasingrate.

Newbuilderflag C4_ROAD_CONTINUATION=1 (requiresTERRAIN_ROAD): addedqueryrequires
_private_road_continuing andpriorG9910nonzero; renderroadsets1, .nativeclears0,
_motion_resetclears0. Stateword appendedprivateMotioncopy(PCreach); selectoruses
MOVE.W toD0 notunsupported68000TSTPC. Footprint/gaptests unchanged. No newroad
fromoffroad/air state; originalroad/objectpriority,n0/8/forced branches retained.
check_c4_continuation.py usescurrentcopiedTimeprefixactualassembled,mockgeometry
functions;384flags/statecasespass (notgeometryproof).
Buildc4-continued-loop usesKEEP_RATE+CONT+TERRAIN plusFOLLOW/RACING/THROTTLE80.
fastair309/310,crash0,exit51,next127736;slownoair,crash0,exit50,next127736.
NeedcombinedCONTjump test(no suchjumpyet), reset/overhead/history scrutiny,
actualpitchguardnativevaliddomaincomparisons, normal/disabled/branch andcost
beforepromotion. Retainoriginalnativeobjectsurfacesratherthannewunvalidated
worldhighestfacepolicyifsmallercandidatepassesfullrequirements; notC4done.

Reports c4-continuation-progress.json,c4-continuation-check.json.
Allfourjobs34260/1605/78180/53306terminal. FirstcontinuationbuildfailedTSTPC;
emptycapturefoldersremoved(noemulatorsstarted), fixedthenbuilt/reran. Fourowned
runtimecopiescleanedafterPIDchecks,calibrationarchivesverifiedSHA; manifest
c4-continuation-cleanup.json. Noactivejobs. C2/C3/C4/C5open,C6/P3deferred.

# Current: authoritative landing-impact gate implemented and verified

HardDrivinMotion.s _motion_fall_ground now firstcmpfall50; <=50oldpath. If>50 and
crash0,saveD0/A0, n0/8oldpath, othernreturnCC4A nativehardimpactaction byadjusting
CC90return-0x46 withLEA(noXchange). Reentrycrash25oldpathfractionreset. IFND
VERIFY_DISPATCH_NATIVE excludesaddedlogicforcednative. ExistingpatchCC8A reused,
no newrange. Enginecadenceunchanged. Onlyterrain/object prototypes remainprivate.
check_c4_landing_source.py comparesCURRENTassembledsource against6ffbcae original
_ground and_ground_end/reset helpers over1568cases;1008native0/8/forced cases.
DirectUnicornSRreadlazyflagsunreliable; executeMOVE SR,$22000atreturntrampolines
thencompare actualSRword. Allregs/stack/target/X pass. Normalbuildbyteequals
s2-final-normal, branch145pass, finalsourceoffdisabled161pristinesitespassplus6enabled/overlaps(DRIVEenabled).
Builds c4-landing-source/reference andc4-landing-normal. Source+fixturebuild
c4-landing-final-jump usesC4_SUPPORT_OBJECT+TERRAIN only; noexperimentalimpactflag.

Private c4_landing_depth.s/flag wasfirstnegative-depth-onlyexperiment: fastcrash349
butpositivefullcontacthole. c4_landing_impact.s/flag fullgate helperfirstappended
PLPSCC8A butexistingpatchoverwroteit: c4-impact-complete-060/slow NOTactiveproof.
Correctedflag REPLACESexistingCC8Apatch andchains_motion_fall_ground. Nowthat
actualsourcehasgate, don'tuseC4_LANDING_IMPACTorDEPTH in newbuilds; useactualsource.
Privatewiredfast/slow c4-impact-wired-* firstcrash349/341counter25; finalsource
c4-landing-final-060 confirms349. Disabled c4-landing-source-off80fieldscomplete.
Reports c4-landing-source-summary.json andsource-check.json. Sevenjobsallterminal
39282/54343/77862/24015/50588/83687/49226;ownedrunscleaned afterPIDdead, verified
calibrationarchives c4-impact-cleanup.json. Noactivejobs, play-a1200untouched.

C5last8.405/6.866 predateslandinggate; needfreshfinalsourcecosteventually. C2clock,
C3checkpoint, C4terrain/fulltrajectories, C5coststillopen. C6/P3deferred. Do not
claimwholejumpacceptancejustcrashoutcomeparity; noobjectterrainpromoted.

# Current: native jump ALSO crashes; correct earlier interpretation

Newcapture c4-finite-jump-native-landing samec4-finite-object-jump slave CUSTOM1=0
nativepose+terrain via capture_c4_landing.py addslanding_crashG9606 toallrows.
Nativefirstcrashfield288counter25 wheels-17/-17/-9/-9; previous281mask3fall60.
OldnativeposecaptureDIDNOTcapturecrash; cannotinfer0 frommissingkey. Slowcrash
byitselfNOTregression. Fastnocrash ishandlingmismatch. Do not weakenimpactrule.
NativeCC2E..CC54 averagewheel<-5 (orupsidecosnegative) ANDfall>50 triggerscrash.
Slowprototype341wheels-25/-25/-11/-11fallprior126 jumpspastcontactthreshold;
fastsmallstepslandwithoutcrash. Need time-normalized contacttransition/native
impactpolicy proof. Native/timedwallfieldnumbers notsimtimecomparisons.
Report c4-native-landing-reference.json retainsfirstcrashandpriorrow.

capture_c4_first_landing.py savesexactCAB6 banks whenpriormask0 and>=3newwheels
below4. Capture c4-finite-jump-slow-landing usesexistingprototype,slowdelay4,350fields.
Snapshotnamedloss-* (samefirstlossinfrastructure), at341 for isolatedreplay.
Bothjobs90915/41050terminal. RuntimecopiescleanedafterPIDchecks andcalibration
archivedwithverifiedSHA. Noactivejobs. Allprototypeflags/sourcebelowunchanged.

# Current: private live finite-object wrapper improves fast jump; slow crash remains

Newprivatec4_object_contact.s: _private_object_ground savesallregisters, callsC94E
baseline, saves40bytes E936+E93A..E944(16),9944..9948(6),E94E..E95E(18). Copies
physics9448..9452toE93A..E944, pred994A..Eto9944..8; scansmainpoolG9962/G9966
active30/class28&0x12. BroadphaseworlddeltasXYZ(long) <=objectradiusword6+75.
Clone56bytes, countvertices+normals<=256; native97DCto1536bytebuffer; parsesfaces
count3..32 andindices<vertexcount; uses c4_support_face perwheel thennativeC6EC.
Takesminimumdistanceversusground. Restoresallglobals/regs. Savedfullscancheck
c4-object-runtime-check.json expected193/193/182/3 andrestorationpass.

build_c4_geometry_probe.py flagC4_SUPPORT_OBJECT=1requiresC4_TERRAIN_ROAD=1.
PrivateTimeappendswrapper+supportpredicate, selectorE94Btruebranches.objects to
querythenCDDA. Renderroadtrue STILLnativeC854; E94Bfalse noobjectscan. n0/8 and
forcednative unchanged. Noauthoritativeassemblyedits. NativeG9447ground2 flaghas
nowritesreadbygame soleft2; savedstateglobalscheckcoveredobjectbytesalso.

Buildc4-finite-object-jump, two450fieldcaptures terminal10197/40265:
fastc4-finite-object-jump-060 firstair137,lastair345,peak221.125,crash0,last449
mask15pitch0roll0Y8=7. slowc4-finite-object-jump-slow firstair147,lastair332,
peak229.125,crash25,last441mask15pitch1roll0Y8=-9. NotC4acceptance.
Reports c4-finite-object-progress.json. Removed2ownedruntimecopies afterPIDdead;
compressedcalibrationwithdecompressedSHA verification, cleanupmanifest
c4-finite-object-cleanup.json. Noactivejobs; play-a1200untouched.

Next removeE94Binvocationdependence with properroad/objectperwheelmergeand
vertical/overheadpolicy; currenthighestfacecouldsnapunderoverheadobjects.
Broadphaseuseslongsignedworldsubtractionanddoesnotcover16bitworldwrap; fixbefore
promotion. Additionalobjectpools, loopregression, slowlanding andcost remain.
Do NOTcallprototypecompletejustbecausefastjumpnowlands.

# Current: direct physics-pose object query proven in saved state

check_c4_object_mesh.py clones56byte object117524 from c4-jump-bad-plane lossbanks,
setsG_E936 scratch0x50000, calls native97DC throughsavedgame, outputclone44.
Originalobj unchanged. Nativeclone transformedgeometry matches all5observedraw
polygons uniquely atindices3,4,5,15,18. Formatrawverticesptr40,rendered44,faceptr52;
word20vertexcount36,byte22normals15,byte23faces23. Face stream count,normalindex,
countvertexindices,color (count+3bytes). Vertices+normals51 vectors.

check_c4_object_physics.py usescloneword0/2/4=objectworld8/10/12 minuspredicted
car98F6/F8/FA; copiesphysics9448..9452trigs toE93A..E944 andpredictedangles994A/C/E
to9944/6/8 fornativeconditionalrotations. Calls97DC thenfinitequeryfaces eachwheel.
OnlyRR supportedbyface15, nativeC6ECdistance3 vsrational3.7983. Physicsdirectplane
NOCA14eyeheight15subtraction. No renderereligibilityflagneeded forobjectquery.
Thisisofflineclone replay; needactualworldcandidateselection andruntimewrapper
that restoresmutatedrenderglobals/angles/pointer andallregisters. Staticnearby
objectsclassbits0x12, mainworldpool availableSweepG9962/count9966; broadphaseand
extraobjectpoolsneedproof. Count/indices/scratchbounds essential.

check_c4_finite_contact.py replaysactualoptimizedCAB6: recorded525/525/-735/-735
mask12rate0; finiteobject+ground193/193/182/3mask8 retainspriorpitchQ16 -129633;
road6/6/1/1mask12rate-218304. Nottrajectoryacceptance orfinalroad/objectpriority.
Reports c4-object-mesh-check.json,c4-object-physics-pose.json,
c4-finite-contact-response.json. Noemulatorjobs ornewlargefiles. Sourceunchanged.
Next runtimeperwheelworldquery/roadgapselection, tiltedoverheadsupportpolicy,
fulltrajectory andcost; C2/C3/C5 stillopen, P3/C6deferred.

# Current: finite supporting-face predicate validated; not integrated

Private c4_support_face.s: A1 convexXYZword vertices, D0count3..32,D1queryX,D2queryZ;
returnsD0bool;clobbersD3-D7/A2-A3. Requiresupwardcarspacewinding (allXZedgecross<=0,
somenonzero), everyvertex/queryXZwithin+-8191 so32bitproducts safe. No slope cutoff
or type39 exception. check_c4_support_68000.py actual68000 vs rationaloracle passes
10045 (saved5faces*9querypoints plus10000affinequads/windings/edges).
check_c4_support_faces.py75translationcheckspass; savedtopcontainscarcenterONLY
upwardcandidate. Exactlossmemorynativewheelcoordinates(-30,0,45),(30,0,45),
(-30,0,-45),(30,0,-45); onlyrightrearinside savedtopfootprint. InfiniteCA14top
6/6/9/9 isNOTphysicallyvalidreplacementforall4. Do not integrateasoneplane.
Next runtimeintegration finitePER-WHEEL road/objectcandidate selection, roadgap
masks, normal/worldup/overheadpolicy, originalcontrols/native8compatibility,cost.
No newemulatorjobs, no trackedassembly edits. Reports c4-support-faces-check.json
andc4-support-68000-check.json. Priorrootdiagnosis below remains current.

# Current: jump root is rendered end-face selection, not clipping alone

No tracked assembly edits. Exact replay check_c4_jump_plane.py uses c4-jump-bad-plane
loss-* banks captured atCAB6 firstfront/rear difference>360, field135. FlagsE94A0
E94B255. CA14 returnsrecorded525/525/-735/-735; native/optimizedC854=6/6/1/1;
C94E=193/193/182/182. PitchQ16 rate-129633(field134)->0(field135), air137.

capture_c4_surface.py observesA150 inputobject*(A5+12): type39,class2,world
31927,0,17304. Twofacesat135, lastwinsE94Eplane[-2,-35,9],[2,-35,9],[0,-21,8].
capture_c4_surface_raw.py also observes9B2E beforeclip; storesup to8XYZs/count.
The endface rawvertices[-8,-35,10],[154,-35,9],[153,-21,8],[-9,-21,9]. Its native
CA14still503/508/-741/-736. Topraw[-9,-21,9],[153,-21,8],[152,-45,-497],[-9,-45,-497]
normal[-24,81811,-3888], nativeCA14=6/6/9/9. Bottom=19/19/25/25. Clippingdistortsbut
wrongendface isprimarycause. Do not merelyreplaceclippedwithunclippedlastface.
Next: determinefinite upward/supportingfaces independentoflastclippedpolygon;
world/car orientation andlegitimateobjecttops/gapsneedproof. No type39blacklist.
Allproofhereisolatedsamephysicsstate; rawfacecaptureseparate deterministicrun.
Reports c4-jump-plane-replay.json. Builds unchangedc4-gap-road-jump.
Allcaptures terminal54637/43664/75483. No activeworkjobs.

# Current: gap-aware private terrain prototype tested; jump still fails

HEAD authoritative physics remains e7f65dd. No tracked assembly change this turn.
Private c4_terrain_road.s now hooks C1B6 with PL_PSS extra2, records D4 while
preserving original local writes/CCR/registers. IMPORTANT native candidate loop
is indices1,2 only (BLT3), not1..3. _private_road_mask rejects uncertain list wraps:
requires cursor-40>=base and cursor+60<=end, uses AF26/AF2A ends; quad startrecords
cursor+(selected-3)*20 and cursor+(selected-2)*20. Gap bit0x400 removes quad.
D2 mask bit1first,bit0second consumed by c4_road_bounds.s. Builder appends both
separate helperfiles (no duplicated bounds embedded in terrain selector).

Actual68000 checks: bounds5000(allfour masks),582inside; recordmask320; hook256
allnative registers/CCR/stack/localwrites identical. Reports c4-road-*-check.json.
Native geometry-to-record correspondence beyond safe simple indexing, vertical
support/under-road behavior and wheel edges still unproven; do not promote.
Probe duplicatesC022 acceptedpath; optimize only aftercorrectness.

Four450fieldcaptures allterminal:21325loopfast,63663loopslow,92358jumpfast,1989jumpslow.
c4-gap-loop-060: air309/310 only, crash0, exitssegment51, last449pitch0mask15.
c4-gap-loop-slow: noair,crash0,segment50,last449pitch-1mask15. Bothwaypointadvanced.
c4-gap-jump-060: firstair137,peak250.875,last449stillair,y53.25,pitch30,crash0.
c4-gap-jump-slow: firstair148,lastair315,peak224.5,landsbutcrashmax25,last445mask15.
Gap handlingdoesnotresolvejump launch/landing discrepancy. Investigatefirstloss
rate/domain andsame-pose branchqueries; do not claimC4passed. Reports
c4-gap-road-progress.json. Builds c4-gap-road-loop/jump are private fixtures.

Cleanup removed four .run copies after recordedPIDsdead; compressedcalibration
banks andverified decompressedSHA before rawremoval. Reclaimed282014473bytes.
Manifests c4-gap-runtime-cleanup.json,c4-gap-calibration-archives.json.
Userplay-a1200 untouched. No activeworkjobs.
C2clock/C3checkpoint/C4/C5stillopen; C6humanlaps andP3deferred.
Previousunboundedc4-road-final-* remainWITHDRAWN despite misleadingname.

# Current: C4 failures separated; no authoritative physics edit

HEAD physics e7f65dd unchanged. Private c4-first-loss-060 (same X360 loop fixture)
firstzero field259 pitch-314: center lateral-115.6 vs halfwidth115.3. Priorfields
250..259 monotonically approachside. This fast failure is input/side departure,
NOT evidence of current centerline contact instability. Exact preCAB6 loss-chip,
loss-fast,loss-motherboard banks retained18MiB with SHA in c4-loop-input-diagnosis.
Metadata/currentlisting c4-contact-base.lst; code helper addresses/calibrate anew.
Private fullgain fast failure152 was nearcenter14.2 and remains rejected.
Slow original firstair184 nearcenter-1.6 genuine arcsineoutdomain remains.

Private C4_ROAD_PITCH=1 added to build_c4_geometry_probe.py uses roadpitch14(cursor)
minus predicted994C when rawpitchdifference outside180, native8 unchanged. Alone
slowfirstair218 crashes331. Combined C4_FULL_PITCH=1 slowair275,fastair152; rejected.
Reports c4-road-pitch-experiment.json and c4-loop-centerline-diagnosis.json. Center
segments crossroadtriangles in successful native too: do NOT claim tunnelling
from that alone. New private builder uses PC-distance bridge to load_resload in
Phase install because fixture extras exceed16-bit reach; normal source unchanged.

Private C4_LOOP_MOUSE configurable(default360), X400 testcurrentphysics firstair312,
waypointnext changesat200pitch571 butexitunclean and loopsagain. Native divisor20
then speedturn threshold1300 halves steering, skid threshold2000 may follow.
X360=>2 butX400=>4 halved2 atV400; largerinputnotreliablystronger. Next investigate
speed-aware fixture steering (possibly X380=>3 untilV433), NOT tunephysics tobad
inputs. C3 lap/checkpoint,C2 clock,C5 cost stillopen; C6 humanlapsdeferred.

All captures terminal: roadpitch99406 failed socketpath-too-long beforedata,
retry22606 done; combined51862 done; firstloss5100 done; input40071092 done.
Use short INSTANCE names: c4-rp-s,c4-rg-s,c4-rg-f,c4-fl-f,c4-i400-f.
Six completed runtime copies removed after PID-dead checks; see
c4-road-input-runtime-cleanup.json. Captures retained, userplay-a1200 untouched.

# Current: guarded neutral steering optimization validated, C5 still fails

HardDrivinPhase.s skips repeated centered steering tails within one outer frame,
only after first tail has normalized all angles. Still publishes anchor MPH each
chunk. No engine-cadence reduction, P3 deferred. An unguarded private variant
failed due one-turn-per-call native normalization; guard fixes that. Tracked source
versus 85b70ba frame passes 3456 consecutive frame comparisons. Private harness
check_c5_neutral_steering.py retained; actual captured executable passes297 pristine
native comparisons incl135 reverse. All four c5-neutral captures terminal36323;
A analysis terminal61181, B56548. Branch145, disabled167 each, normalbyteexact.
Latest c5-neutral-summary.json overhead8.405121/6.865535 versus8.070/5.740;
excess0.335121/1.125535. Sweep3.018079/0.881874. Off/on swapsA38/38B73/59;
polygonchanges4.91%/4.71% below5%threshold; B FPSstillregresses7.288->5.891.
All500fieldtraces passduration/coverage. Archives97439/71409 complete, rawtraces
removed after SHA verified decompression. Four stopped runtimes removed after PID
checks; c5-neutral-runtime-cleanup.json. No remaining work jobs running.
Remaining C2 native-clock comparison,C3 lap/checkpoint,C4 loop/jump correctness,
C5 costs. C6 human laps deferred (goaltool required-lap wording stale).
No new test laps or P3 work authorized. Keep user play-a1200 untouched.

# Current: scan optimization tested; both latest C5 windows fail

HardDrivinSweep.s prepares world bounds/count once, DBF scans with exact final
counter on overflow, reuses native rotated scene point when byte34 nonzero.
c5-scan builds/captures all terminal. Native32 + reused32, world96,
interpolation10000, broadphase10000 and iterator20 cases pass. Ordinary build
byte equal, branch145 and off167 each pass. No Phase/Contact source changes.
Latest c5-scan-summary.json A8.923069/B7.334501 versus limits8.070/5.740;
excess0.853069/1.594501. Sweep3.012669/0.956033. Both scene mismatches >5%.
B baseline changed with build/clock; do not cherry-pick older baseline.
C1 complete; C2/C3/C4/C5 open; C6 human laps explicitly deferred by user.
P3 deferred. Goal tool's required human-lap confirmation text is stale.
No new phase-zero-steering optimization implemented; only a possible next
investigation, requiring native full-state proof before skipping any tails.
Four c5-scan traces archived with verified decompression SHA; raw copies removed.
Four completed runtime copies removed after PID checks; see
c5-scan-runtime-cleanup.json. User play-a1200 untouched. No work jobs running.

# Current: sweep eligibility optimization validated; C5 A still fails

Working trackedSweep.s changed: scene `_sweep_miss` guards SW_ACTIVE via68000PC
BTST, class8/type!=95 beforeMOVEM;worldfiltersclass/active/typebeforeBSR;shared
_sweep_candidate beginsafterguards. No changes collisionmath,counters,priority.
Actualnative32/world96/interpolation10000pass. Normalc5-filter-normal equals
s2-final-normal;branch145pass;bothfinaloffcaptures167rangespass.
Build c5-current-{a,b} originalsource50b6ffa includesPHASE+SWEEP, STEPINPUTonlyA.
500fields firstA1 B4000 pairedCUSTOM1 off/on. Currentoverhead10.9531508/5.0660734;
sweep4.9709028/1.9324135ms. Finalc5-filter pairs newsource9.5237087/3.9146885;
sweep3.4861020/1.3150667. A STILL1.4537087over8.07;Bbelowaccepted5.740.
Boffbaselinechanges120.680->160.578msandpolys13.84->36.55 withslavesize+12bytes;
clockdependency remains, donotclaimisolatedsavings. FinalG2A38/38swapsB63/58.
Reports tmp/c5-{current,filter}-summary.json, tools/report_c5_gate.py
retained. All8traces500fields10.015943522scoverage>99.99998%;checkedmatchingpaired
artifacts/config. Allrawtracesremovedafterverifiedzstd+sha,fingerprintsretained.
Allsessions terminal inclanalysis38347/70033/57580/68780/51150 archives63336/29787/
51998. Elevenownedruntimesremoved367382509bytesafterPIDsdead;cleanupmanifest
c5-runtime-cleanup.json. Userplay-a1200untouched. No running workjobs.

PrivateC4_FULL_PITCH experiment scalesnativecbb0halfcorrectionby1-2^(-n/8),
preservesfractionalcarryonfullcontact, retainsnative8exact andclampshelperinput
outside8 viaC4_CLAMP. Moduleonlyignoredc4_full_pitch.s appendedprivateTime.
Jumpfastgetsnonzeropitchfeedback butfastloopworsensfirstair259->152pitch291y363.
NOTpromoted. c4-fullpitch-experiment.json retainsfailure; no sourcecontactedits.
SourceSweepoptimizationonly. C2/C3/C4/C5stillopen; C6deferred. Do not extendaccepted
BexceptiontoA. NextC5sweepcost remaining3.486A;P3deferred. Furtherfastworldscan/
duplicatecandidaterejectionmustpreservecounters/priority/ties andnongraphobjects.

# Current: launch-rate diagnosis, no authoritative source change

Native c4-jump-clear-native terminal77819: takeoff185,land288,peak209.625. Native
wallfieldsnotcomparableconsumedtime. Slowenabledtakeoff151land264peak210.25;
fastoldtakeoff137peak250.875stillair299. New c4-jump-rate-slow/060 terminal74114/85421
captureterrain nowadds pitch_rate/roll_rate native and HDCRATE1 fullQ16.
Fastfield134mask12error6 ->rate-129633;135mask12wheels525,525,-735,-735 error2520
nativeasinzero ->rate0. Slowlastrearerror22 ->rate-408016, persistsflight.
Private C4_KEEP_RATE env inbuild_c4_geometry_probe.py skipsrateoverwritewhenraw
-4(a5)abs>180 andfields!=8. CopyContact.s only, manifestsfullcopiedsourcehashes.
Capturec4-jump-keep-rate-060 terminal13927,370fields:peak221.125land349;improved
butnotcorrectlanding, donotpromoteascompletefix. Noactualphysicsedit. Needderive
rearcontactfeedback cadence normalization/valid geometry treatment; simpleinvalid
rate retention insufficient. C4launch-rate-diagnosis.json retainsstates/hashes.
AllfourruntimecopiesremovedafterPIDdeadchecks; c4-launch-runtime-cleanup.json.
C2/C3/C4/C5open,C6deferred. Priorgoalturnprogress,currentnewdiagnosticprogress.

# Current C4 checkpoint: native-traversable loop, pitch domain failure, clear-lane jump

All current sessions terminal: 47624 native loop,9911 slow,38414 060,49092
terrain slow,11272 jump060,56370 privateclamp,10151 jumpslow. No work captures live.
C4 collision-id is traffic index11/12 referencing mainobject97/98, type62 class8;
not static! Full table pointer audit confirms. Jump-clear seed32425,0,18392 yaw-636
avoids vehicle without removing it. Both300field runs crashfree; slow lands by299
Y3.625 mask15,060stillair Y238.125. Not jump timing acceptance.
Loop-follow-v3 native traversesrotation nozero-contactthroughground323; afterwards
leavesroad. Sameenabledslowlosescontact184pitch241;060259pitch-314. Terrain read-only
columns wheel/cursor/predpitch expose native2b0e zero outsideabsnumerator180:
field162 wheels-113,-111,-22,-20 -> -182, next-185 =>pitchcorrectionzero.
Ignored build C4_CLAMP=1 optional wrapper atcba2 clamps numerator+-180 exceptT8.
HelperplacedendTime.s toavoidresloadPCreach. Wrapper sourcecopiedonly; noauthoritative
physicsedit. c4-loop-clamp-slow completesrotation buttransientair andbadexit/cursor;
doNOTpromoteasverifiedfix. Manifestflagsclamp, fixturemotionhashbuthelperinTime.s;
full copied source fingerprints added to clamp manifest. Allbinariesretained.
Explicit eightcompletedinstances cleaned afterallrecordedPIDsdead; see
c4-targeted-runtime-cleanup.json. Captureevidenceretained; userplayuntouched.
Report c4-targeted-diagnostics.json, trackedGAME_TIME/STEP4planupdated. C2/C3/C4/C5open;
C6deferredsupersedesgoaltext. Previousgoalturnwasstatus-only;thisturnnewdiagnostic
captureschangeaction. Nextsolve geometrycontact+flight, don'tsilentlyrelaxacceptance.

# Latest completed state: C3 controlled bounds committed9c1bc1c; C4 probes incomplete

Alljobs terminal: 80135/15704 loopv2,29418/57719jumpv2,72672native,37424/56827lane
exit0. Noactivecaptureprocesses. cleanupmanifestc3-c4-runtime-cleanup.json checks
recordedPIDsdeadandremoves703MBdisposable.run copies ONLYownedcompletedinstances;
allcaptures/buildsretained. Userplay-a1200untouched. Diskfree~141GB(beforecleanup),
largefreechangedoutsideour~700MBwork; don'tdeleteotherprojects.

Privatefixture scriptbuild_c4_geometry_probe.py correctedseed nowsets98EA/EC/EE
camerashortsaswellas98F6/F8/FA,longX8pose,road98E4=9952+20*segment,mode9950=1
(NOTFF),throttle100hold100. C4-loop-seed-v2 slowmaxpitch38leftcontactearly;060
getsaroundtopbutleavesroad. NativeCUSTOM1offc4-loop-native alsoleavesloopafter
pitch690 -> fixtureitselfnotvalidatedsuccessfulnative route, doNOTlabelwhole
failurearegressionorchangephysicstooverfit. Nativecapture --native-pose adds
pitch/roll/gear/rpm only; no crashbyte(nativecannotusephase-inputs).
C4jumpseedcenter17 coords32359,0,18418 yaw-635 collidesbeforeliponbothprofiles.
ValidatedoriginalwindowjumpLIP31873,189,17363 heading-636 MPH103gear4throttle100,
AIR31826,206,17240 MPH109 throttle89. ThisISstuntlipsegment20,priorcommentary
questionlocationresolved. c4-jump-lane usesstart32293,0,18443 yaw-636(the same
laneoffset-66,+25) stillcollidesbeforelip. Highspeedsolid/contactcrash zerosV;
probablytraffic/sceneobject, needactualcollisionhook/objectpointerreadnotguess.
19airframeslane060areAFTERcollision/recovery, notjumpcoverage. Bothfixturefailures
retained. c4-seeded-coverage.json passedfalse. NativeSCENEobjectcollisionBC62..
BCE0 zerosV, soidentifyA3objectandtypeatthosecalls beforealteringgeometrytest.

Roadloopgeometryspiralslaterally~230worldacrossfullturn whileyawrest1159constant.
Holdingcenterinputmaynottraversewholeloop evennative; successfulnative routeinput
required. Potentialsteeringwithinloop, noacceptedsequenceyet. Trackgeometryjson
hasallcrosssections/waypoints. Steeringboundcompletec421171 captures independent
curveexactglobal775returns;C3stilllap/checkpointunverified. C2clockquestionpending,
C5finalcostopen. No trackedcodeeditsafterc421171. LatestdocsC4explorationpending
commitafteridentitycheck. OriginalfullobjectiveunchangedexceptuserC6deferred.

# Latest: current-source controlled trajectory bounds pass; C4 seeds running

Source HEADc421171. check_c3_steering_curve.py usespristineengine+trig(g80DA/80D4)
andindependentQ6projection, globalXYZnoresets; all775activereturns passincluding
offroad. c3-steering-curve-comparison: consumed0..539spread V65.5/H7/P73.913327,
bounds75/7.5/80.130890 usingordinaryA50015fields. NeedJITtools escalation (sandbox
Unicorn exits132otherwise). Thisis simulationconsumedtime, notdisplayedposeproof.
Fresh c3-final-straight/brake all4profiles terminal25349/79496/45891/67986exit0.
check_c3_final_straight.py343flatnativeexactthrough420; report_c3_final_straight.py
absoluteconsumedspread65.5/74.8125vs75/80.15625 retainingstart43/54/40/40.
analyse_phase_fixed_heading.py uses INTEGRATEDtrig forzeroheldsteer, full550fields
499perframeforce/XYZpass(terrainentryinputnotglobalproof). Freshbrake217returns
pass viaanalyse_c3_brake_curve.py; report_c3_final_brake.py spreads11/3.083333vs
45/33.046875, stoprange158..163within15. TrackedGAME_TIME+STEP4planupdated.

C4newconcretegeometryfromnativecapturedroad data: inspect_track_geometry.py
writes track-geometry.json. Roadentries20bytes =leftXYZ,rightXYZ,yaw,pitch,roll,
flags. Stuntloop37..49(ymax630,pitch660/-660); straightapproachindex35 center
28161,0,14390 yaw1159(normalized-281). Jumpramp17..20 pitch37 lipY189, center
index17=32359,0,18418 yaw805(-635). WrappedXvertices needmodularaverage.
Private build_c4_geometry_probe.py copiestracked*.s intoignoredc4-fixture-source
andaddsone_time _private_c4_seed ONLYinprivateVerify. Metadata records allsource
hashes +fixturehash. No algorithm editsinthatcopy. Loopseed velocity400RPM5000gear4,
throttle22, mask15, heading-281,stuntflagFF,nextstuntwaypoint4(index51); coords
longX8andshortglobals. SWEEPenabled. SeedisNOTnormalstart/inputtape/benchmark.
Build c4-loop-seed.slave and.lst; capture c4-loop-seed-slow session66081 and
c4-loop-seed-060 session83519 RUNNING(lastconfirmedlive;mustpollthesehandles).
650fields, timing/phaseinputs/sweepworld. Noinitial-throttleassertforseed.
Ifsuccessfulmustverify actualfullpitchrotationloop/contact/recovery/checkpoint;
merelymaxheightnotproof. Jumpseedbuildparametersalsoavailablebutnotrunyet.
C2clockquestionpending; C3lap/checkpointopen;C5costnewbuildnotmeasured.

# Latest candidate: phase-aligned steering implemented and validated in part

Working source HardDrivinPhase.s + header HardDrivinDrivetrain.s changed; docs
GAME_TIME andSTEP4plan updated. Readyto commit coherentfixafteridentitychecks.
B390nativeorientationtail deferredwith pendingword; originalroll/pitch/spinonce
outer. _phase_frame preparesanchorV/R/MPH, steersPH_DT thenrestores8forengine;
updatesPH_SKID. Successclearspending,fallbackfinishesnative tail. Forcednative
hookcontinuesoriginalbody. Nochangeouterfullphysics/contact/gravitycadence.

Build c3-steering-phase.lst/slave; c3-steering-phase-v2-{a500,slow,020,040} all
550fieldcaptures terminal, sessions91351/4355/34215/46675 exit0. All779heading
returns exact360+floor(max(0,N-start-8)/2), allfinal164gear3. Start43/54/40/40.
Private check_c3_steering_native_frame.py297cases/135negative,T8withorientation,
variedangles/rates/fullpartialzero contactmanualneutralpass. IMPORTANT fixtures
mustflushUnicornTBafterrestoring images (uc_ctl0x4000000a) andinitializeDS_MOUSE28!
Beforefixingharness,cachednativeB35Ehidnewdefer andheldmouse0 madebadsteerrate;
those failuresresolvedharness,latestreportvalid. Runtime108c3-steering-native
passes s4-skid-native-reference;session13954terminal. Disabledsession99766exit0,
c3-steering-disabled.json167rangespasses activeDRIVE+STEPINPUT. Normalbinaryequal,
branch145passes. check_c3_steering_restart.py validatesnative136eightfieldendpoints
then1..31partitions2476points inclstopping/idle/restart, V/R/gear/headingexact;
notpositionoracle. Alljobsdone. Protectinteractiveplay-a1200.

C3 XYZfullboundstillopen. Preliminary linearinterpolationofactualreturns at
consumed1..539: maxpairworlddistance73.82445,heading7.5,V65.5;maxrecordedspeed
5.342059 world/field ->15fieldbound80.13. DO NOTdeclarepassfrominterpolationalone;
needbound interpolation/quantisation error or reconstructexactsegmentcurve.
Oldanalyse_phase_idle assumesframe-heldtrig, incompatiblewithnewsteeringchunks;
needoraclethat derivesnativeQ14trigpersegmentandprojectsactualphaseforecast,
notcapturedoldINPUTtrig. Geometryroad/contactonceoutercanstillcausedivergence.
C2 clockexceptionquestionstillpending; C4targetedloopjumpcheckpointcoverage and
C5newperformancebudgetopen. C6humanlapsdeferred; stalegoalwordingnotrequired.

# Latest: controlled steering-delay experiment complete

Capture session74931 exit0, no work jobs remain. c3-delay59-steer-040 same source
as e249093, STEPINPUT_STEER_AT59 only diagnostic input change. Onset moves42->58,
upshiftgear3 at217 beforeoffroad227; finalspeed164gear3 vsoriginal194gear2.
delay-diagnostic.json passeddiagnostic, acceptancefalse; allheadingcurvesexact.
This confirms startup timing changeslatergear outcome; originalfixture preserved.
No sourcefixyet. Braking and initialsteeringdiagnosis committed4941fd8; latest
experiment documentedinGAME_TIME. Requirednextwork: scale steering eligibility
on native8phase, supportingstop/restart; cannotjustspecialcasefixturestartup.
NativeB35EonlycallCDB2, orientationbeforephaseengineCDB6. B390startssteeringbody,
B3A0mousecalc,B3B2zeroVgate,B444yawcall,B44Enormalize/trig,B4FCepilogue.
Potentialsplit: onceouterroll/pitch/spin, steeringperexistingphasechunk; do not
repeatcontact/gravity ordiscardprojectedpitchbycallingfullB35Erepeatedly.
AnyimplementationmustretainT8native checks, phaseinvalid/fallbackbehavior,
newskidheldvectors, scalar8 restoration, currentphaseanchorMPH(992C), andcostgate.
Unimplemented idea only; needdesigncarefully. C2pendingclockquestion/C4/C5open.

# New reproducible steering diagnosis

report_c3_steering_start.py -> c3-steering-start.json: all786 integratedheadings
EXACT 360+floor(max(0,consumed-first_moving_frame_end)/2). Movingframeends
57/72/44/42; throttle starts43/54/40/40 =>steeringeligibility skips14/18/4/2fields.
Native B3B2 velocityzero test executesatCDB2beforeengineCDB6. Roadflagzero at
242/251/217/215; slowprofilesalreadygear3, fastgear2RPM5174/5197below5200.
Startupcadencedelayproved, full latertrajectory causality notproved. No source
change yet; correction must preserveT8native andstopping/restarting, notonlylaunch.

# Latest continuation: braking component documented; steering still open

Source remains e249093. New current-source captures c3-current-brake-{a500,slow,020,040}
(750 fields) and c3-current-steer-{a500,slow,020,040} (550 fields) are terminal.
Braking native curves pass 216 returns; c3-brake-comparison.json passes the C3
braking component: 15-field ordinary A500 bound, velocity spread15 vs45,
distance5.875 vs33.046875, conservative stopping-time spread6 vs15. Tools under
tools/analyse_c3_brake_curve.py and report_c3_brake.py. Tracked docs now
record this result; C3 overall remains open.

Steering current source: by consumed400 A500/slow speed166 gear3, 020/040
speed194 gear2. Native orientation B35E runs at CDB2, before phase engine CDB6.
Its B3B2 zero-velocity test skips steering on the first moving frame; possible
cadence dependency, not yet proved as the cause of later gear divergence.
Need inspect earliest differences before redesign. Do not repeat fullphysics
per segment or waive failing handling evidence. C2 clock exception question
still pending; C4 targeted loop/jump/checkpoint coverage and C5 final costs open.
C6 human laps explicitly deferred by user; stale active goal wording requiring
lap confirmation is superseded. No human approval needed for closure now.

# Latest checkpoint: e249093, C3 stationary-phase correction

Current HEAD e249093 follows C1 commit d4476d3. Both personalidentity/nohooks/
nosigning verified. Only preexisting .DS_Store untracked; no source changes left.
All sessions terminal, including99097 native and52754disabled. No emulatorjobs
remain from this work; protect userplay-a1200instance. Goal remainsactive, notdone.

UserC6humanlapsdeferred committedinbothplans. P3deferred,acceptedG1P6B5.740unchanged.
C2async questionstillpending (functions.request_user_input_async): mayclock-caused
650returndifferencesbeexplicitexception, orkeepC2openwhilepreservingD4clock? Do not
changeclock orassumeapproval. NativefreshC2diagnostics detailedbelow; no exception
accepted yet. No needrepeatD4preservevsfixquestion(useralreadychosepreserve).

NewC3bugfix: fullyzeroV/R (wordsANDQ16fractions) restartsPH_PHASEandanchorszero
at_phase_frame.ready. Previouslyidleframesselectedinitialphase, slowA500steady226
vsothers228. Currentc3-idle-throttle-{a500,slow,020,040} nowall228gear3. Complete
flattrajectorythroughconsumed420:29/22/110/182=343returns EXACTvsone-fieldnative
phasecurve, includingfractionalabsoluteX/V/R/gear; toolcheck_c3_straight_curve.py,
reportc3-straight-curve.json. Actualcontrolledinputstartsconsumed43/54/40/40,
realB662snapshotwallfields63/78/45/43; retainlatencies,notequalwalltimeproof.
Full550fieldperframecapturedinput/nativeXYZoracle499returnsallpass:
analyse_phase_idle.py writesphase-idle.json. Thisoracle resetsmodelphaseonlywhen
nativewords+fullmodelV/Rzero; basedanalyse_phase_manual.py otherwise.
Privatecheck_c3_idle.py88casesall8idlephasex11intervals identicalcar+phase outputs;
nonzerohiddenfractionsretainedexplicitcheck. check_c3_native_frame.py297cases/
135rollbackallnativeT8exact. c3-idle-native108matches s4-skid-native-reference.
Normal c3-idle-normalbyteequal s2-final-normal,branches144pass.
Disabledc3-idle-disabled initiallyfailedbecausecalleromittedcompiledSTEPINPUT;
preserveddisabled-missing-input-gate.json. RecheckedSAMEretainedbyteswithboth
VERIFY_DRIVE+VERIFY_STEPINPUTdeclaredactive,all166timingrangespassdisabled.json.
No timingpatchfailuremasked. TrackedGAME_TIMEandSTEP4plan documentallofthis,
C3explicitlystillopen. e249093commitsource+docs. FreshC5costnotdonefornewsource.

AdditionalcompletedPRE-idlefixmatrixcaptures:
- c3-brake200-{a500,slow,020,040}:750fields withBRAKE_SPEED200, availablefor
  descending100zero-throttleanalysis. Originalc3-brake-*100triggerhasresidual
  throttleatdescending100on slowA500andcannotisolatebraking. No datahidden.
- c3-steer300-{a500,slow,020,040}:850fields INITIAL22 X400 STEER_AT300. Early
  movingsteeragreestentatively;afterterrain~600fields020/040gearhistoriesdiverge
  (020gear2/040gear1at700whileA500gear3). Samplingbriefairbornecontacts/free-rev
  RPMmaycauseautomaticdownshifts; hypothesisnotyetproven. NeedC3bounds/fix,
  do notcallC3passedbytruncatingawaydifference. Startingsteeratfield0alsofailed
  widercomparison(040speed194gear2vsothers164gear3by500). Nativeengineperframe
  oraclesall1883oldinitialmatrixreturnsEXACTgivenactualinputs; problemis sampling/
  trajectorydependence, notthearithmeticoracle. Newidlefixmayremoveonecause;
  steering/brakingneedrecapturefinalonceappropriate. No fullhandlingclaim.

C4 PRE-idlefix probe c4-sweep.slave enablesexistingVERIFY_TIME_SWEEP flag missing
fromP6fullcandidate. c4-sweep-slow/0606000fieldfrozenroute capturescomplete.
reportc4-sweep-probe.json explicitlypassed=false(insufficientcoverage):
slow444returns,T10..22,3airborne,1crash,5197sweeptests/0hits/0overflow,
39984worldscan/4888rejected;0603862returns,T1..3,124airborne,1crash,sweepinactive
asexpected. Nocheckpointlatch,coursepositionsonly2/4,neitherprovesloop/jump or
crossedcheckpoint. Needtargetedcontrolledroute/fixture, notmoreofthesametape.
Capturetool --sweep-world nowrecords course_currentADCC,course_nextADD0,
checkpoint_latchAF30 andlap_clock9790. Existingprivatecheck_sweep_world.py and
check_sweep_native.py prove synthetic main-object crossings,notnaturalroute.
C4source unchanged; flagsnewcandidateonly. FinalC5mustaccountcostifSweepincluded.

No newrawinstructiontraces thisturn; capturesstate/events only,C2snapshotszstd.
FinalgoalshouldNOTbecomplete. C1done,C2pendingclockdecision,C3partlyfixedbut
bounds/steering/braking/lapcheckpointstillopen,C4targetedextremesopen,C5newbuild
cost/profileauditopen,C6explicitlydeferred. Currenttrackeddocsaccurate.

# Step-4 closure checkpoint: C1 complete, d4476d3

C6 human laps explicitly deferred; P3 deferred; accepted A500 B5.740ms overhead
remains. C1 committed d4476d3 with final A/B39/58 complete drivingframes,zero
fallbacks;flight/landing110/376/74returns A500/020/slowedA500; manual145/117
returns A500/020allgears0..4; signedprojection20k plusfullpristinenativeframe297
including135rollback. Native108 c1-final-native exact;disabled166;branches144;
normalbyteequal. Tools/fixtures ignored. Signedvelocitysupported,manualshift ends
partialphase andconsumesinputfirstsegmentonly;free-rev preservesVfraction.

C2 fresh c2-world-off/on650returns FAILED. Sameinputs660controls, RNG/traffic
recordsallmatch. Firstcar99;offrecovery99,on101. At98offBCD1601/deadline1603;
on1622/deadline1641. At99offreset,on1635stillbeforedeadline. car31badreturns,
replayring374,writepointer183,mainobjects551. NativeBCDpreservedperD4.
Async user question pending: accept documentedclockexception orkeepC2open.
Do notchangeclock ordeclareexceptionacceptedwithoutreply. LatestC2buildpre-signed
extensionbutforcednativebypassesphaseallthetime. Capturesvalidsamebuildoff/on.

C3 captured current-sourcesameflags allfourprofiles: c3-throttle-{a500,slow,020,040}
(550fields INITIAL_THROTTLE22 verified);c3-brake-*650fields trigger100;
c3-steer-*550fields INITIAL22X400. Allcapturescomplete, nojobsrunning.
Initialthrottleconsumedbefore A50043/slow54/02040/04040;maxinterval15/18/5/3.
FlatplateauA500/020/040speed228,slow226 (phase/startquantization). Atconsumed400
X8 A500226511.6/slow225964.6/020226548.7/040226549. NeedderiveoneA500frame
inputlatencyboundplusdocumentedquantizationphases, donotpicktoleranceafterfact.
Steer040remainsgear2offroad(speed194)whileothersgear3(speed164)around400fields;
smallterrainentry/startphase timingmaycrossautomatic5200 threshold differently.
This is observed unresolvedtrajectorydifference, notpassedC3. Needanalyse exact
sampling/phase envelopeorfixcause, donotjustlimitthetestwindowtohideit.
Brakecapturesstopsall;needcomparefromdescending100 withzerothrottle andelapsedfields.

C4 existingHardDrivinSweep.s gatedVERIFY_TIME_SWEEP currentlyNOTinbuild_step4_all.sh
(the fullP6candidateflags omittedit); currentmotioncaptureshavenosweep counters.
Need actualslowA500/060collisions,loop,jump pluscheckpoint/longcrossing evidence;
notdone. Existingcheck_native_contact_sweep/check_sweep_*tools andgeometryprivate
fixturesmayhelp. NoimplementationchangesafterC1commitexceptignoredharness/report.
C5 fullcostprofileonnewC1stillneeded;previousacceptedP6timingsarenotnewmeasurement.
C6deferreddocumentedbothplansandGAME_TIME. Protectplay-a1200instancealways.
Alltooljobsfinished through thischeckpoint. Disk198GBfree; no newrawinstruction
traces created,C2snapshotsautoarchivedzstd. NextrecordC2diagnosis in tracked docs,
finishC3/C4/C5, awaituserclockexceptionanswer. Keepgoalactive, notcomplete.

# Active goal: finish step 4 automated closure

User requests C1–C5 completion before rendering. User additionally defers C6 human
A500/68040 test laps. Do not wait for human laps or mark thempassed. P3deferred;
accepted A5005.740ms overhead remainssettled. Currentgoaltool wording mentions
C6 confirmation but latestuser explicitly overrides that condition. No newcommit
or captures yet in closure work. TrackedSTEP4_COST_PLAN updatedC6 andworkingorder.
Currentfocus C1: phase solver excludesair/partialcontact/fall/manual/neutral/reverse;
inspect nativeB500 andphasefraction transitions, implementwithindependentoracle.
Older currentdirection entries below are superseded.

# User direction: proceed to step 5

2026-10-13: user explicitly accepts current A500 B5.740ms/frame overhead for now.
G1 gap no longerblocks rendering work; do not resume P3 to chase it. Original
3.78target remainsreference, notmetnumerically. Step5next. C1–C6correctness remains
open; no fullsimulation-speed acceptance. Both trackedplans updated andcommitted.
Measure combined simulation+renderer againstoriginal to establish netwin.
Historical entries below claiming ResolveG1first are superseded by this direction.

# P7 complete and committed: 2c9c6ae

P7 a1200-020 (2MiBChip+4MiBFast) p7-a/b-on/off500field captures complete.
Same bytes as P6 fixtures; no game source edits. Reportp7-summary.json and
p7-final-audit.json source/build/config hashes allchecked. Tracecoverage minimum
99.9999817%, exact10.015943522s, allswapcounts checked. Fourarchives SHAverified,
no rawtraces. All sessions82948/60162/7600/46096/34792/33678 terminal.
Netphaseoverhead A0.283304034/B0.575775275ms =0.4657%/1.2294% of ownoriginal
60.833033/46.835119ms. No-negative-credit sensitivity0.813460554/0.709578413ms.
Swaps off/on A164/150 B214/222; enabledFPS14.976/22.165. Differenttrajectories;
no equal-scene FPS or fullsimulationacceptance claimed. P7reportonlynotgated.
CurrentP6A500G1stillB5.739547vs3.78fails. ResolveG1beforeC1–C6. P3deferred,
D3conditionalE2unchanged. User has playable non-VERIFY_DRIVE build
HardDrivin-play.slave and A1200 interactivecommand; never stop thatinstance.
Only preexisting.DS_Store untracked; personalidentity/nosigning/nohooks verified.

Everything below is historical context, not current instructions.

# P6 complete and committed: 368853a

P6 fresh baseline p6-base-a/b-on/off reproduced P5. Physics biggest overhead;
native unsigned divider122be largest individual arithmetic self cost B0.800366.
New exact158byte _phase_divide: one DIVU for word quotient, native two-word
fallback, wide restoring loop shortened to quotient bits with exact CCR.
172440 private68000 comparisons, native108, disabled166, branches144 passed.
Final p6-fast-a/b-on/off matches rebuilt p6-final binaries; normal/DRIVE/ATTRACT
match step2. Both installed divider bodies match private prototype. Audit
p6-final-audit.json includes source hashes and commit; no signing/hooks/personal
identities verified. Only preexisting.DS_Store untracked. All capture sessions done.

Identical-operand divider saving28.99% A /28.90% B; matched604/640 A calls,
82/512 B calls. Complete per-call traces in divider-calls.json; full report
p6-divider-matched-cost.json. Final conservative G1 total3.083583/5.739547 vs
8.07/3.78; B stillFAIL. The shared arithmetic moved native render division into
slave, so original accounting charges it in full outside simulation. Do not hide
or exclude it. Current otherhooks0.306802/.342149 are not fresh P5passes; prior
P4/P5 acceptance records remain specific to those builds. G1notrelaxed; no overall
step4completion. P6hasnoindependentnumericexit; it optimizes largest remaining
arithmetic symbol, not G1closure. PlanD3explicitly allows G1stillfailingafterP6.
P7next; P3deferred, D3conditionalE2authorization retained, no cadence/inputchange.
Final and baseline traces retained verifiedcompressed; removed500.9MB first
candidate p6-div traces. Full files under ignored tmp/ only.

Everything below is historical context, not current instructions.

# P5 complete and committed: 2062223

Final p5-empty pair: 0.247401892 / 0.292054668 ms, both below0.3; no exception.
Final audit passed and records commit; native108, disabled165, branch143,
private24000 boundary, final CPU40/151 physics=render calls, binary rebuild
and unchanged normal/DRIVE/ATTRACT verified. Personal identities, no signing/hooks.
Removed1.999GB superseded compressed probes; final four archives retained.
P3 deferred; P6/P7/G1/step4 open (currentB overhead5.690624 vs3.78).
Only preexisting.DS_Store untracked. Final policy session19269 terminal.
All entries below are historical.

# P5 final strict-target pass; audit/commit pending

Current source p5-empty-a/b: A0.247401892/B0.292054668 ms; both <=0.3.
No exception needed. Final policy session19269 still being checked. Source rebuilds
match captures; normal/DRIVE/ATTRACT match step2; native108, disabled165,
branches143 and private24000 boundary pass. Tracked plan updated. Complete
final audit and personal commit; G1/P6 remain open (B5.690624 vs3.78).
Earlier entries below are historical, not current instructions.

# P5 strict-target continuation: compact constants + inactive recovery

Previous goal turn made progress; no exception answer received. Continuing strict
0.3 target. Current source now p5-recovery-a/b, NOT the audited p5-fold snapshot.
All fold source files backed up in tmp/p5-fold-source for exact recovery.
Removed unused FC_PLUS/MINUS/T/RETAIN cache fields (no consumers); remaining four
coefficients passed all65536 intervals and306contact outputs. Inactive recovery
now resets presentation companion directly, skipping native108A2 prologue;
active recovery unchanged. New21600boundary cases pass including dispatcher
controls and recovery state/entry/flags. Current reports p5-compact-constants-check
and p5-recovery-boundaries-check.json. No new budget result yet.
Session36479 runs matched p5-recovery-b-on/off profiles and verified compression.
A profiles not yet started. A separate live-check chain was launched for current
native108, disabled, A500/020policy; check live tool session/status before restart.
No commit. Priorfoldcandidate remains documented0.291651/0.347961, not currentproof.

# P5 validated candidate; awaiting budget decision

Current source is p5-fold-a/b, uncommitted. Final paired 500-field A/B on/off
captures are p5-fold-{a,b}-{off,on}; all traces SHA/decompression-verified zstd.
P5 exact remaining-hook cost A0.291651121/B0.347961108 ms; A passes0.3, B+0.047961.
User asked via async whether to accept the P5 overrun or keep strict0.3. No answer
or exception yet; do not extend prior P4 exception. Goal stays active. Do not commit
as P5 complete without meeting the limit or explicit exception.
All correctness checks pass; p5-final-audit.json records current source hashes,
matching rebuilt binaries, native108, disabled164, branches142, unchanged normal/
DRIVE/ATTRACT, 19200boundary cases, full65536coefficients, 151072controls,
12000nativecontrols,16000audio, liveCPU40/151physics=renders, liveaudio30/105visits,
offroad31checks. Details in tracked STEP4_COST_PLAN P5 section.
Current full B overhead5.591686 vsplan3.78 failsG1. Bphysics helper1.806476,
nativeextra2.714691 do not reproduce historicalP4 figures; originalB72complete
frames vsold83 indicates changed late-window trajectory too. Do not describe
this as proven same-state regression; P6 needs to resolve measured physics cost.
Aoverall3.006518,helper1.412904,nativeextra0.706800.
P5 changes: fused000framebookkeeping, sharedboundedfallback, smallerdispatcher
saves, exact0..32constanttable, D0/D1-onlythrottleramps, emptycrashfastpath,
no-replayfastreturn, scratch-onlyoffroadaudiocadence. Native semantics preserved.
Discarded saturated-throttle experiment did not help; not present in finalsource.
Superseded P5 probe traces removed after finalcapture; reports/metadata retained.
Freed1.316GiB plus stoppedownedruntimecopies. Final evidence retained. Sessions
80671/97779/9667/62268 terminal, all earlier captures complete; no known emulator
running. Current binaryrebuildaudit complete. Preexisting.DS_Store leavealone.
Personal local gitidentitycorrect, hooks/dev/null, signingfalse; recheckbeforecommit.

# P4 complete under the user-approved helper exception

Final commit 1de9202 follows accepted-helper commit e67fa38. Native root at9564
uses the exact original Newton recurrence with guarded single DIVU and original
long-divider fallback. 96bytebody+8NOP replaces104bytes; no cadence/P3 changes.
Final matched p4-native-root-{a,b}-{off,on}: helper1.425256976/1.515211557,
within useraccepted1.494050/1.616246. NativeA10.403487825 vs9.703690967
(+0.699796857); B6.387203664 vs6.494453481(-0.107249816), both+1gatePASS.
687686root cases,6000engine,1200frame,300physics pass; live motion17/steer9/
offroad29/brake46/skidA50043/020190, prefixes stopairborne515/573. Native108,
disabled164,branch142pass; normal/DRIVE/ATTRACT byte-identical s2baseline.
Live root bytes and source fingerprints checked; p4-final-acceptance.json records
commit and complete audit. All profiles SHA/decompression verified compressed,
no raw traces retained. All sessions terminal34083/30946/53944/68544/93587/
44249/81056/69015/15524; no known active emulator. Only preexisting.DS_Store
untracked. Personal identities, no signing/hooks verified for both commits.
Removed412.5MiB disposable copies from24finished owned emulator instances,
kept captures/logs; finaloffruntime copies also cleaned after PID checks.
P3 remains deferred. Next planned phaseP5; G1/P7/closure not claimed complete.
Do not resume accepted helper-gap pursuit or discarded directRPM experiment.

# P4 helper result accepted and committed

User explicitly accepted the0.094/0.216ms excess. Commit e67fa38 contains the
validated p4-motion-a/b source and a consolidated STEP4_COST_PLAN acceptance
record. Rebuilt p4-accepted-a/b binaries are byte-identical to retained p4-motion
profile slaves. Personal author/committer verified, no signing/hooks.
Only preexisting .DS_Store untracked; no tracked edits remain.

The subsequent direct _time_rpm_engaged experiment was discarded in favor of
the accepted fully validated source. p4-rpm-b-on was completed and verified
compressed; session81637 terminal. Private exhaustive RPM experiment failed
harness setup and is not evidence; do not resume/reintegrate it. Fixtures in
ignored tools include an extra current rpm-engaged wrapper patch, now original
wrapper. Session72294 compared the discarded candidate; use earlier accepted
motion/native/frame evidence and matching binary rebuild for committed source.
Projection reuse analysis92794 terminal: optimistic velocity-only5/51callsA,
20/186B; no cache implemented. All captures/builds stopped (87437terminal).

Helper acceptance does not waive separate native physics gate: matched native
increase A1.820806998/B0.636921780ms, limit1.0. NativeA remainsopen; P3 deferred,
G1/step4closure alsoopen. Full original goal not markedcomplete because of this
remaining explicitly listed criterion. Do not chase the accepted helpergap.
All matched profile traces compressed; live correctness matrix documented in
committed plan. Any further work should address separate nativeA criterion,
without restarting P3 endpoint caching or changing cadence absent user direction.

# Current P4 matched profile audit complete

No performance source edits this turn. Session35085 terminal: captured and
analysed p4-motion-a-off and b-off, SHA/decompression verified compression,
raw traces deleted. report_p4_motion_pair.py verifies build/listing/game/emulator
hashes and all configuration except CUSTOM1, windows500fields at1/4000.
p4-motion-pair-summary.json stores source fingerprints and exact gates:
A helper1.4940495396974716; nativeon11.524497965269996,
off9.703690967162256; nativeextra1.8208069981077397.
B helper1.616245912397899; nativeon7.1596347586474165,
off6.5227129781909206; nativeextra0.636921780456496.
BothhelpergateFAIL, nativeAFAIL/BPASS. Earlier disabled baseline6.3800 forB
is superseded for this build by its matched6.522713. Do not mix baselines.
Current correctness matrix complete in bounded scopes as recorded below.
All captures stopped, no known running emulator. No budget exception accepted,
no commit/completion. Tracked plan current-status paragraph and paired audit
updated. User clarification remains pending (accept current helper timings vs
continue1.4); acceptinghelpergap alone does not waive nativeA gate or G1.

# P4 current live matrix complete

Session57137 now terminal. p4-prologue-skid-020 passed189checks,93skidframes,
1exit; first unsupported airborne inputfield572. All listed current live matrix
checks now pass their bounded scopes. Tracked cost plan updated. Source unchanged
since motion-prologue profiles. Helper still1.49404954/1.61624591; original1.4
criterion unmet, nativeA+1 unmet; no completion or commit claim. No accepted
budget exception. No known running emulator/capture. Next: cost reductions or
user-directed exception, then final matched profile/commit audit.

# Current P4 live validation continuation

No performance source edits this turn. Target remains1.4ms; asked user whether
accepting current1.494/1.616 after validation is intended. No answer yet.
Current p4-motion-native passed108 states against s4-skid-native-reference;
p4-motion-disabled passes163 ranges with VERIFY_DRIVE enabled only.
Fresh p4-current-steer9, p4-current-offroad29 (14offroad frames,15decay segments),
p4-current-motion17, p4-prologue-brake46 all pass. p4-prologue-skid-a50043
checks pass;17skid frames,1exit, first unsupported airborne inputfield514.
Latest chain session57137 continues with p4-prologue-skid-020; do not restart
while live. Session75426 ended after motion passed because p4-current-brake
name already existed; it never launched braking. Existing old capture preserved,
new names p4-prologue-brake/skid used. Sessions37808/1239/75193 terminal.
Final profiling and remaining helper/native cost gaps remain open.

# Current P4 motion-prologue follow-up

Current source also changes HardDrivinMotion.s: roll/pitch outer saves removed,
contact callees preserve D1-D3 and native callers discard D0/D1/A0/A1; yaw A0
saves removed. Native B35E consumers audited. check_p4_angular_entry.py 300
random rate/angle cases and check_p4_motion_entry.py 300 CDA4 cases pass.
The latter starts with existing captured angular state; arbitrary angles through
full contact exceeded baseline execution bound at case19, so use angular-only
fixture for that randomized domain. Branch141pass. Fresh normal/DRIVE/ATTRACT
byte-identical s2-final baselines: p4-current-build-identity.json.

Current on-only p4-motion-a-on helper1.4940495396974716,
native11.524497965269996, mean249.87153701002086;
p4-motion-b-on helper1.616245912397899, native7.1596347586474165,
mean180.286993656039. Both helper gates fail, native+1 fails A.
No matched-final profiles or completion claim. Both traces verified compressed
and raw deleted. Sessions65902/86931/50343 terminal. Builds p4-motion-a/b.
Six helper source modules plus cost plan modified, uncommitted. Existing live
p4-publish-offroad predates latest motion-prologue change; current live matrix
and native108/disabled163 still required. No emulator knowingly left running.

# Current P4 publish candidate and cleanup

Supersedes the root-cache/lookup proposal below: guarded power lookup is now
integrated, reciprocal anchor conversion was tested and removed (unused A,
once B), position integration unrolled, final scalar companions published once.
Current tracked source has five modified helper modules, not committed.
Latest p4-publish-a-on / b-on: helper 1.535293916450719 / 1.6215668275286617;
native 11.52360021934678 / 7.0717115059279125; frame mean
249.8714479773673 / 181.01547717344067 ms. Enabled-only diagnostics, not final
matched gates. Helper target fails both, native original+1 fails A. P3 deferred.
User suggested accepting the remaining .14/.22 ms; assistant recommended it,
but no numeric gate exception has been enacted and goal remains incomplete.

Revalidated current source: guarded power lookup4096, frame1200, physics100,
live p4-publish-offroad29 checks/14turning/15offroad all pass. Full frame compares
all final scalar companions, including randomized incoming state/skid. Only pure
memo bookkeeping excluded. Session54496 terminal. Earlier offroad capture is
complete, analysis passes; no need to restart it. Final native108, disabled163,
normal/DRIVE/ATTRACT identity and current live motion/brake/steer/skid matrix
remain to be completed, along with matched cost profiles if pursuing closure.

Archived p4-publish-a-on and p4-publish-b-on with SHA/decompression verification;
raw traces deleted, compressed sizes120/122MiB. Session16853 terminal.
Cleanup freed about4.5GiB further; filesystem258GiB available at last check.
Do not retain new raw traces after their analysis and verified compression.
No performance code changed during cleanup/verification continuation.

# P4 root-cache bypass and next exact lookup candidate

Current runtime additionally leaves native B856 JSR/argument cleanup unpatched
when VERIFY_DRIVETRAIN_PHASE is defined (nested IFND around root PL_PS). The
one-field reference integrator retains the root cache. The phase cache was mostly
misses: before/after counters A10hits/85misses, B4hits/102misses; full traceB108
calls/102misses. Avoiding wrapper overhead pays despite evaluating every root.
No engine endpoint cache or cadence change; P3 remains deferred.

Latest on-only p4-rootless-{a,b}-on matches current source:
A helper1.647356349708689/native11.511217261116672/frame249.34432273268516;
B helper1.8602568142615834/native7.628562972517308/frame168.40355545161594.
Bothhelper1.4 gates stillFAIL. Bothnative +1 gates also currently unmet. No final
matched-off or completion claim. Fresh A/B traces SHA/decompression verified and
compressed; no raw trace retained. Disk269GBavailable.
Private engine6000, fullphaseframe1200, nativephysics100 all pass cache bypass.
Fixture restores actual six bytes4eac81be584f at nativeB856 in candidate image.
Only removed pure root memo bookkeeping excluded from state comparisons; all
native globals,phase/scalars,position/motion,other caches,audio,SR/registeroutputs
remain exact. Root cache has no other game readers; reference path cache retained.
Branch141pass. Live p4-rootless-offroad29checks/14turns/15offroad passes.
Allcurrent sessions terminal28615,69144,81385,62658,43928,12551,66794.

New ignored prototype, NOT INTEGRATED: tmp/p4-power-table.s, generated by assembler
macro, and check_p4_power_table.py. All1024 signed throttle-byte/fourgear inputs
match pristine native2950 for fullD0 and intermediateD4 word, including223 DIVS
OVF cases! Correct stock ratios read from immutable native table(a4-733c):
gear0(0,800),1(7,800),2(9,750),3(10,600),4(10,450).
First call trunc(throttle*450/100). Second is first*DENOMINATOR/NUMERATOR,
not viceversa. On signedDIVS quotient overflow nativeD0 stays full product.
Table storesD0.l,D4.w,pad.w,4x256x8=8192bytes; macro avoids rawgamebytes.
Report tmp/p4-power-table-check.json. Currentpowercache countersA58hits/37misses,
B25hits/81misses. Exact table could remove miss divisions and cache bookkeeping.

Suggested next concrete candidate: phase-only _phase_power hook, preserving
existing _drivetrain_power as general fallback. Add alternate PL_PSS B696 target
under VERIFY_DRIVETRAIN_PHASE. New function/data inPhase.s can use PH_ACTIVE:
when inactive fallback; when active gear1..4 already guaranteed. Validate immutable
fourratio table once before using generated lookup, retain fallback on mismatch.
Index((gear-1)*256+unsigned throttlebyte)*8; load fullD0 and D4word; store native
-14(a5); return. Keep D2-D7/A2-A6 preserved except nativeD4 word contract.
This is a proposed path, not implemented or performance-proven. Need direct
exhaustive lookup+wholeengine/fullframe checks. Candidatepower memo bookkeeping
may be excluded only as unused implementation cache, never native game effects.
Beware fullphase private fixture code/table placement and PC-relative ranges
when adding8KB table; original loader source also needs rebuilt listing checks.
Instruction costs script p4_instruction_costs.py and reports in abiA/B identify
MULS and many small hook/position costs; VBL entries in its report are outside
physics and not P4 budget. Use frame_budget.py for actual exit numbers.

# P4 native-caller register audit continuation

Current source additionally narrows _phase_frame saves fromD0-D7/A0-A2/A6 to
D2-D7/A2/A6 and _phase_published toD2-D4/D7/A2/A6. Only D0/D1/A0/A1 caller
scratch dropped; D2/D3 remain preserved. CDB6 replaces engine+position calls,
and CDBE/contact callers overwrite scratch before use. _time_throttle_retention
now savesD2-D5 only; native B79A onward overwritesD1/A0, A1 caller scratch.
_contact_integrate_rate no longer savesD5 after its previous rotate rewrite.
_phase_frame compares adjacent V/R words as a single long against LAST V/R.

Verification latestsource: check_p4_first162003 pass; engine_entry6000 pass;
new check_p4_frame_entry1200 full phase frames pass (actual old/new phase, native
engine and native position; n1..32; arbitrary partial current/anchor; assertphasecalls).
Fixture patches current phase/scalar/power/root blocks in old captured image.
check_p4_physics_entry100 comparisons through nativeCDA4 also pass, requiring
actualphasecalls and matchingD2-D7/A2-A6 outputs. Original nativephysics itself
changesD2, so this compares its outputs rather than asserting entrypreservation.
Phaseframe fixture still asserts callee register preservation. Allnative globals,
phase/scalar/drivetrain/projection/motioncompanions,caches,audio,stack/SR match.
No claim these partial-image fixtures alone validate all current modules;
helpermicro covers contact/time, and full live/final native gates remain needed.
Branch141pass. Latest live p4-abi-offroad29checks/14turns/14offroad passes.

New diagnostic p4-abi-{a,b}-on cost (all current source):
A helper1.7383403022406327/native11.470232562936255/frame249.3441446673781;
B helper1.9175605606910497/native7.673605698564668/frame171.50115706589227.
Still above1.4 both. Bothnative +1 gates currently unmet vsoriginal9.7033/6.3800.
These on-only traces do not replace matched final profile requirements.
Both traces verified compressed; raw removed after analysis. No P3 or cadence
changes. All sessions terminal10633,13089,32982,40787,47685,1339,69362.
Current five modified helper modules remain uncommitted; no completionclaim.
Continue eliminating remaining phase/position/projection and hook overhead,
then all listed final checks and matched A/B before completioncommit.

# P4 projection continuation

Current source adds two verified changes after the prior continuation:
_phase_project_core holds the first rounded XYZ in D3/D4/D6 instead of a stack
array, then forms fractional neighbors directly. All callers audited: wrapper
saves all scratch, phase frame saves outer registers, movement position overwrites
scratch. Core now clobbersD0-D7/A0, preservesA1-A6. _contact_integrate_rate replaces
its high-product <<29 with ROR3 and maskE0000000, bit-exact for every long.
check_p4_first162003 cases passes latestsource; branch audit141 passes.
Live p4-stream-steer passes9 checks (3 turns), p4-stream-offroad29 checks,
14turns/13offroad, no skids in this fixture. Existing motion proof predates these
two changes. Full live/current native/off/build gates still needed for final.

Latest fresh diagnostic on-only p4-stream-a/b builds include all current changes:
A helper1.759552331946971/native11.47026965987523/frame249.34458983064576;
B helper2.0916490759164867/native6.986545657440979/frame170.09529189639872.
Target1.4 both still FAIL. Native reference A9.703325211396356/B6.380049551412865;
A native+1 limit still unmet, B fits in this diagnostic. No matched-off final claim.
Before projection/contact changes, scratch-b measured helper2.0684531701379805,
native7.802477650315908/frame170.61633946855218. Trajectory changes matter.

Exact projection cache study from scratch-b: only36/202 calls repeated a velocity
within a four-entry per-frame cache. Trig fixed perframe assumption. Not enough
benefit, no cache implemented. Report in scratch-b/projection-cache-study.json.
All new scratch/stream A/B traces compressed with hash/decompression verification;
raw removed. Disk273GBavailable at last check. Allsessions terminal11035,85015,
97749,41679,27174,77831,78484,95894,84017. Capture78484 succeeded but typo checker
analyse_phase_steer.py failed; correct analyse_phase_steering.py later passed.
No running emulator is intentionally retained. Git has five modified helper
modules (Contact,Drivetrain,Phase,Scalar,Time), plus unrelated .DS_Store.
P4 remains active, no completion commit. Need larger further helper reductions,
particularly phase/position/projection overhead, then finish listed verification.

# P4 continuation after disk cleanup

P4 remains active/incomplete. Uncommitted Phase/Scalar/Time changes after4ca7ed2
plus Drivetrain scratch-save reduction. Current paired phase interpolation and
hoisted position setup pass check_p4_first162003 and complete native engine6000.
Engine checker now places larger snippets in private trampolines and varies
partial-phase current V/R independently of anchors; DT8 still valid current=anchor.
It additionally patches current power/root wrappers. These drop D1/A0 saves:
native consumers overwrite these caller scratch registers; complete native globals,
companions, caches, pitch/audio count, callee registers, stack and SR match.
Power micro comparisons exclude only audited D1/A0 (and fixture A6 address).
Live p4-paired-motion passes17 returns with latest Drivetrain changes.

Measured paired candidate BEFORE Drivetrain save removal:
p4-paired-a-on slave1.81528677306415 native11.50727014680965 mean249.34417434492926;
p4-paired-b-on slave2.21514231263752 native7.619548039089193 mean173.2581521821792.
Both still FAIL1.4. These are diagnostic on-only captures, not final matched gates.
Both raw captures archived, hash/decompression verified; no raw trace retained.
Previous entry2 helper1.8813861/2.1823021; paired B has changed trajectory/workload.
Latest build p4-paired-motion includes register-save reductions; paired-a/b builds
predate those. Do not associate those performance numbers with latest source.
Next reduce remaining helper costs, validate full live fixture set/native108/off/
branches/unchanged builds, then matched final A/B before any completion claim.
P3 stays deferred; no cadence or gate changes.

User asked cleanup: removed10 redundant raw traces after SHA256-verified zstd
archives, saved22.62GiB. Explicit trace dirs: cprof-{on,off,b-on,b-off},
p4-entry2-{a,b}-on,s4-recordcost-{before,after},s4-profile-{fraction,current}.
Automatic review rejected broad *.bin cleanup including calibration; those files
were preserved. Compress only confirmed finished trace.bin after analysis.
All current sessions terminal:75015,25973,87793,87874,13246,28067,85829.
No emulator/checker process intentionally left running.

# P4 current checkpoint (2026-10-12)

Checkpoint committed as4ca7ed2. P4 is NOT complete. Current helper cost from matched p4-check-{a,b}-{off,on}:
A1.9952366046477572 / B2.415215911770523 ms per frame; target1.4 both.
Native physics11.547030646003869 /8.03231442207028 vsoriginal9.703325211396356 /
6.380049551412865; P3 remains deferred, conditional +1.0 gate unmet.
Constants outsidephysics0.04628956045395079 /0.038951018401670506 count towardG1.
Summary tmp/prof/p4-summary.json; tracked STEP4_COST_PLAN.md and GAME_TIME.md
record the verified implementation and boundaries. All source changes are CUSTOM1
helpers; no P3 endpoint cache or physics cadence change.
Actual68000 check_p4_first.py162003 cases; check_p4_constants.py65537blocks,
196611cached+196608fallbackcoefficients,306responses; allpass.
Live p4-check-motion17, brake46, steer9, offroad29, skid-a50043, skid-020189.
Skid scope ends firstairborne515/575. Native108, disabled163, branches141 pass;
normal/drive/attract byte-identical to s2-final baselines. Nativeoracle128/1440.
Old helper sources saved in tmp/p4-before. Diagnostic profiles first/current/fast/
lean2/next are superseded by check. archive_p4_probes.py hashes,decompress-verifies,
and removes raw traces only after verification. Do not overwrite the old sources.
Continue reducing the helper cost without relaxing budgets or resuming deferredP3.

# Current status and next work

**2026-10-12: P1 and P2 of `STEP4_COST_PLAN.md` are complete.**
P2 exact fixed-field recording overhead is 0.280504 ms/frame in A and 0.248648 in B
(limit 0.3), from matched p2-ready-{a,b}-{off,on}. Both pass.
B remains a scene mismatch. Summary: tmp/prof/p2-summary.json.
Recording now retains exact endpoint pairs and weights, resolving the unchanged
90x158 native ring before its first reader at 10b44. No R1 frame stamps. Allocation
29476 bytes:90x8 descriptors+91x316 pairs. Pairs shared per transaction, collision
replacement uses same origin; pool lifetime proven by >=90 later emissions.
Native/ineligible visits resolve and synchronize cursors. Allocation failure eager. Reset resolves pending tails before clearing descriptors
and preserves incomingX; actual68000 checks bothX values.
Pose buffers exchange pointers; check_recording uses previous/current pointer dump.
Current source/source comments and GAME_TIME.md describe the implementation.
Final builds p2-ready-a.slave (A), p2-ready-b.slave (B), p2-ready-playback.slave,
p2-ready-native.slave. Profiles all500fields, matchinglisting+slave anddistinctINSTANCE.
Private final check_p2_micro 10000records/790000words; check_p2_pending 10000records,
2000sharedtransactions/41393emissions,500replacements,95resolutions/4060047words;
check_p2_sampler4000pristine native comparisons. Live p2-ready-record A50050tx/78samples,
616fields/77fractional/29multi(max3), collision2replacement; -020191tx/79samples,
628fields/55fractional,duplicate0emits. Resolvednative ringexactboth.
Playback p2-ready-playback-a50056draws46fractional/78records/625age(target624),
-020223draws193fractional/79records/634age(target632). Both52RNG, audio passes. Threeframes
perprofile visuallyinspected (p2-ready-replay-inspection.png), no corruption.
108nativep2-ready-native exact; disabledp2-ready-disabled163, branch141, unchangedthree
baselinebuilds. All artifacts ignored. Nonfinalp2-probe/recip/defer/fast/final-a/shared/swap
captures are intermediate candidates, not final budget evidence.
P3 E1 evaluated: correctness passes, performance FAIL. Candidate NOT retained in
runtime; source remains P2. Final p3-final-{a,b}-{off,on} 500field traces show
2.324324 / 1.982759 engine entries per frame against1.75/1.25 limits. Cache3/90
and0/98; misses newphase60/57, throttle25/41,pitch2/0. Candidate physics15.454362 /
11.374694 ms; P2 15.487410/10.985855. B nohits and extraoverhead.
Source candidate tmp/phase-p3-e1-candidate.s; exactbuilds p3-check-a/b +listings.
check_p3_cache6000cases3567hits2433misses exact allnativeglobals,phase/scalars,
gearpointer,audio-count/pitch,regs/stack. Preserve nativeRPM LAST beforezero clamp;
firstprobe missedthis, finalcandidate corrected. Current checker loads actualpatched
image from p3-check-motion, matchingp3-check-a.lst. CacheHDENGC01state40bytes:
valid.w0,key22bytes2,endpoint.l24,nativeLASTs.l28,hits.l32,misses.l36.
Allanalyse_phase_* pass: motion17,brake46,steer9,offroad29,skid43/020188; latterstop
firstairfield519/574, noflightclaim. 128endpoints/1440partitionspass. Native108exact,
disabled163pass,branches141pass,normal/drive/attractbyteidentical. No E2; D3 defers
untilafterP1-P6. User deferred P3; P4 is next. P3 limits remain unmet, no E2 authorization change.
Do not resume P3 automatically or claim it complete.
CombinedG1 and step4closure remainopen.

Performance plan steps 1–3 are complete with the instrument limits below.
No gameplay or rendering optimization is enabled in normal builds.

## Accepted evidence

- Step 1: shipped/rebuilt stable attract output equivalence, native VERIFY_DRIVE
  tape and validated A500 checkpoint/jump/crash/replay windows, CUSTOM4 delay
  instrument, generalized per-machine calibration, per-field/per-physics snapshots
  and pristine relocated-byte PERF_RANGE checks. See internals.md and the retained
  step1 JSON reports; step-1 completion commit is 684665d.
- Step 2: seven profiles, each with two exactly matching 1000-field attract
  state/screen/swap captures and the full gameplay A/B windows. All current counts
  are in tmp/prof/step2-baselines.json and the tracked PERFORMANCE.md.
- Per the user's instruction, gameplay CPU/DMA samples are 500 fields (10.015944 s).
  A starts at race field 1; B at 4300 after the entire prior tape. Attract samples
  stay 1000 fields. There are 21 machine/window reports, including the accepted
  earlier A500 attract trace. step2-validation.json checks all required artifacts.
- 68000 and 020 instruction metrics include self/inclusive routine estimates,
  exact blitter/publication wait ranges and complete physics-call cycles. The
  030/040/060 backend lacks validated instruction timing. Their effective
  blitter_cycle_exact=false also omits blitter DMA slot records; report both
  unavailable, not zero. Display DMA and independent swap counts are available.
- 020 B and attract traces each repeat identically in every recorded instruction,
  DMA record, screenshot, cycle count and before/after memory byte. The independent
  breakpoint totals agree (202 and 484), but four B swaps and two attract swaps
  differ by one field between instruments. The cause remains unresolved; retain
  this timing uncertainty. 000 samples and 020 A agree field-for-field.
- All seven cache logs retain hardware CACR and API state. The 68020 has I cache;
  030/040/060 have I+D. Two separate MMU-on functional boots pass on 040 and 060;
  no timing claims use those boots.
- The fastest measured attract profile is 030/50, 38.489 FPS. Equal-layout ceiling
  control/instant-blitter/polygon-bypass runs give 38.539/44.180/49.870 FPS. Code
  differs only at the intended two-byte polygon entry, and range/config checks
  pass (step2-ceiling-validation.json). These are limits, not optimization gains.
- Normal, attract and drive binaries are unchanged byte-for-byte after the new
  VERIFY_CACHEAUDIT and VERIFY_CEILING/VERIFY_NOPOLY fixtures. The invalid bypass
  flag combination fails assembly. All six existing tool failure-path tests pass.

## Step 3 complete; step 4 in progress

See tracked GAME_TIME.md for accepted results and calibration limits. Constant
VERIFY_STEPINPUT matches 108 car states across A500, CUSTOM4=4, 020 and 040,
including 25 crash-state returns. Field-indexed input diverges by design. Native
lap-clock ABCD consumes incoming X; native countdown normally loses 0.01 per field.
The old field-1198 checkpoint label means recovery waypoint, not time bonus.

Recommended f0=6.25, engineering range 4–8, low confidence in historical intent.
This is a compatibility choice; unknown world scale and native clock defects
preclude a unique physical reference. T_max=1 initially, not a stability claim
based on long frame duration. Ordinary pair mean 71,673 cycles; vehicle collision
363,640 including scene rebuild. Step 4 must preserve the documented side effects,
modal epochs, remainders, replay time and finite-difference Doppler pitch.
Step 4 has a VERIFY_TIME elapsed-field observer and arithmetic helpers in
HardDrivinTime.s, plus VERIFY_TIME_SCALARS throttle/velocity/RPM hooks in
HardDrivinScalar.s. VERIFY_TIME_DISPATCH now feeds elapsed time into the development solver.
See tracked GAME_TIME.md for scope and remaining unscaled presentation behavior.
Normal/DRIVE/ATTRACT builds remain exactly unchanged. CUSTOM1 only installs
observer in VERIFY_TIME builds, plus scalar hooks when VERIFY_TIME_SCALARS is
compiled. VERIFY_SCALAR_FIELDS constant0..8 selects diagnostic T (default8).
Do not advertise it as completed decoupling.

Local capture_time.py PROFILE NAME --slave NAME.slave --passes N --fields N
sets CUSTOM1=1 (or --off), captures timing state at 10edc plus input VBL counts,
checks declared ranges. s4-time.slave is DRIVE+SLOW+TIME. s4-time-pause.slave is
DRIVE+TIME+TIME_PAUSE, and s4-time-replay.slave is DRIVE+TIME+TIME_REPLAY.
check_time_math.py uses s4-time-math.slave (TIME+TIME_MATH), compares 1215 signed
scale results and 11 large-backlog splits. Captures use independent INSTANCE.
All current jobs have exited; no emulator should be left running after checks.

Clock hooks: 50/6 VBL, 10ed4/8 loop, 7c52/8 pause,7c64/6 resume,
7770/8 options,77ac/6 resume,10f52/8 replay+submit. All CUSTOM1 PERF_RANGE.
HDTIME01 signature precedes32-byte state: fields,previous,elapsed,observed,
passes,T,return (7 longs), active,suspended,reserved[2]. Observer-only without VERIFY_TIME_DISPATCH; that gate now consumes time. Outer hook saves X using ROXL/LSR; interrupt preserves CCR.
Options boundary hooks unexercised; full replay iteration count not established.

Current scalar work: acceleration b8a2, throttle up7d36/down7d50, neutral RPM
b704..b72a and engaged RPMb8d2..b8ec; offroad retentionb78a..b79a.
PERF_RANGE/reset hooks include new race59ba, Phantom117f8, recovery108d8/10a88,
velocity collisionsbcc8/bda6, throttlecrashbce6/bdc4/bff4/cc5a, expiry7df0,
and discrete skidexitb654 (does NOT overwrite branch targetb65e!).
Scalar state HDSCAL01: velocity carry.w,last.w; throttle Q16 carry.l,last.b,pad.b;
RPM carry.w,last.w,gear.w (16bytes). Throttle carries Q16; velocity/RPM eighths.
Time_scale_q16 rate contract abs<=16383, fields0..8, signed carry±65535.
Retention loss table0,1085,2152,3201,4233,5247,6245,7227,8192 exactnearestQ16.
T1 decay follows native integer7/8 and clearsfraction, smallerT usesfullQ16state.

Local tools: capture_stepinputs.py now --slave NAME --custom1 1 --steps108;
compare_scalar_states.py NAME compares108G98f6..9952 bytes to s3-stepinput-a500
normalizingonlygearptr. check_scalar_hooks.py captures before/after actualhook
operands and modelsresults (--require-down for rampfixture). Latestformat expects
Q16THR state; old captures were beforeupgrade. check_retention_math.py reads315
privatefixturecases. check_time_math.py reads1215+11+441 cases.
VERIFY_TIME_SCALAR_MATH requiresTIME_SCALARS and testsretentionbeforegameinit.
VERIFY_STEPINPUT_RAMP requiresSTEPINPUT, countscontrolsfromraceentry, holds4 first
64passes then1 next64 then4. First s4-scalars-ramp-hooks INVALID downcoverage:
counteradvancedinmenus. s4-scalars-ramp-q16 final has64 downwardcalls andpasses.
Currentfinalnativeequivalence captures s4-scalars-final-{a500,slow,020,040};
allfour108-statecomparisonsPASS; s4-scalars-off pristineallnewrangesPASS.
Normal/DRIVE/ATTRACT baselinebytesstillidentical; six invalid flag/rangebuildsFAIL
asintended. Final q16rampfixture534actualhookupdatesPASS,retention315casesPASS,
math1215eighth+11debt+441Q16PASS. No active emulator jobs remain.
Motion module now adds angular rates, spin decay and fall acceleration (still
constant diagnosticT, NOT elapsed-frame simulation). VERIFY_TIME_MOTION requires
TIME_SCALARS. VERIFY_MOTION_MATH requiresMOTION, privatefakeglobals only.
Angle Q16 companions yaw0/pitch6/roll12 eachcarry.l,last.w; fallcarry.w18,last.w20;
ratecallerflag.b22; spincarry.l24,last.w28; total32bytes after HDMOTN01.
_time_split_q16 added as shared extraction entry for signed spinretention.
Native pitch/yaw call wrappers duplicate native stack argument and discard the
original displacedargument afterreturn; verify stack discipline whenediting.
Ratecallersb380,b38a,b448; lowlevelpitchb1c6/yawb254;rollbaseb36a.
Gravity invertedccc2; airborne dispatchccd4; ground dispatchcc8a/cca0.
HARD LESSON: cd86 AND ccd0 are sharedbranch targets. Initial patches atcd82 and
cccc overwrote them and stalledthefirst run. Thosepatchesaregone; neverreuse.
check_patch_branches.py audits externaldirectbranches intoeveryScalar/Motionrange
(current32), butinspectindirectentries separately. s4-motion-one-a500 invalid,
stoppedPythonPID48850 throughSIGINT andSession.close ownedhelper; no broad kills.
Steer-on earlyrunhappenedtopass108 butdoesnotvalidateunsafeoldcode; usefinal.
Hardcontact cb6c andbarrierbf80 clearpitch/rollfractions; rollsnapdispatchcd96
preserves sharedcda0return; scalarnewrace/recovery/collision/replay resetsMotion.
SpinlossQ16table0,857,1704,2539,3363,4177,4979,5772,6554; T1native9/10integer
truncation clearsfraction, smallTfullsignedQ16. Skidexitclearsfraction.

FinalT1captures s4-motion-final-{a500,slow,020,040}:108statesallmatchstep3baseline.
Nonzerosteering fixtureVERIFY_STEPINPUT_X=400 (default320,bounds0..639) added;
s4-motion-turn-final compareswith s4-motion-steer-off via compare_scalar_states.py
--reference NAME. These108-returncaptureshaveNOairborneorspinreturns: do NOT
claimlivegravity/spinacceptance. s4-motion-small field1 steeringsteps20..49show
0.5quarterdeg/updatewithin0.5quantization; steering-check.json provesratefromunits.
Private s4-motion-math-final135angle+315spin+81fallcasespass. s4-motion-off new
rangebytespristine. Finalnormalbuildsbyteidentical andfiveinvalidflag/rangebuildsreject. Allownedcapture
processesareterminal; no activejobsremain. Finalturn108statesmatchX400reference.

Ordinary position is now hooked at b500/8 (PL_P, original LINK, preserve TST)
and b578/30 (XYZ). HDPOSST1 state is old projected XYZ words at0/2/4,
padding6, signed 1/128-position carries.l at8/12/16; total20bytes. Motion reset
clears it. Helper computes [8*(v*(8+n)-u*(8-n))+carry]/128 with signed truncation;
n0 consumes nothing. Captures s4-position-one108states equal X400reference;
s4-position-small-hooks360liveaxisupdates/210fractionalresults all match model;
s4-position-math1323private68000cases +60 exact rational subdivision identities
pass. s4-position-off all ranges pristine; normalbuild byteequal. Branch audit34.
check_position_hooks.py owns its emulator and retains actual before/afteroperands.
Crash drift and crash countdown scaling are now implemented (see below). Native integer projection still
omits fractional longitudinal velocity; nonlinear steering correction acceptance
and full reset/writer audit remain. Do not claim equal-time trajectory proof.

Falling-position hook b5f2/10 now scales -v*T+a*T*(1-T)/2, including fall
velocity carry in eighths. Uses shared positionY carry at HDPOSST1+12. MS_FALL_ACCEL
word at HDMOTN01+30 stores the prior contact acceleration; fallposition consumes
and clears it, fall_delta writes it, ground/reset/mismatch clears it. T0 no motion.
First airborne step has no prior airborne accel; nonlinear transition acceptance
is still required. Private s4-fall-position-math405fallpositioncases +all earlier
mathcases pass. s4-fall-live400actualcalls (19nonzero fall) matches model atT1;
s4-fall-position-one108states matchX400reference; s4-fall-position-off pristine.
Direct branchaudit35ranges passes. All owned capture jobs completed.
check_fall_position_hooks.py is the current 400-call native-T live checker.
36 exact-rational explicit-Euler subdivision identities passed independently.

Crash drift b596/0x5c now uses the native30-sample envelope,8fields/sample.
HDDRIFT1: remainingfields.w0,lastvisiblecounter.w2, XYZcarry.w4/6/8,pad10.
At most2segments percall: native signed vector*floor((remaining-1)/8)/30,
then segmentfields/8 withcarry. Endpoint exactnative rounding; no reversingtail.
Four drift-start writers bc80/bd5e/bfa6/cc66 explicitly clear companions before
nativecounter30, including same-value resets. Existing Motion resets clearstate.
Crashcounter hooks10ef0/28 live and11680/36 Phantom consume200fields for25steps;
HDCRASH1 remaining.w,lastvisible.w. Initwritersbce0/bdbe/bfee/cc54 explicitreset.
Expiry one-shot setsADD7; liveclearAF32, PhantomsetsAF32=60andE92E=5.
FullPhantommode remains untested/unconverted elsewhere. TimerT0 doesnotexpire.

s4-crash-math includes56full driftsequences, rollingintermediateX/remainchecksums,
8crashtimersequences +zeroT/samevalue resetcases; priorarithmeticpasses.
s4-crash-one108states equaloriginal; crash-equivalence.json additionallymatches
9606/9912/ADD7/AF32/E92E,25crashstates andone observedreplayrequest.
s4-crash-off ranges pristine;normalbuildbyteequal;directbranchaudit46passes.
All capturejobs exited. Mathslave now~31KB, watch PC-relative range iffixturesgrow;
move largeprivatefixturearrays/module if needed rather than droppingcoverage.

Contact hooks are connected: ccfa/30 roll,cd2e/32 pitch,cd6e/18rear feedback,
cd86/6 full-rate zero constraint. HDCRATE1 is16bytes: rollfullQ16.l0,lastword4,
pad6; pitchfull.l8,lastword12,pad14. VERIFY_CONTACT_TRACE writes consumedrawerror
in pad6/14; no normalbuild logging. TRACE and CONTACT_MATH requireMOTION.
_contact_response Q16gain1-(.75)^T andgain/T; T8nativewordrounding,T0preserve.
_contact_project_q16 exactfloorsignedQ16*Q14 /16384 (boundsabs16383/16384).
_contact_add_angle preservescarry/wrap; _contact_scale_rate floorfullrate*fields/8.
Rollbase nowconsumeswide rate. Pitch-rate wrapper usesnativecos viaa4-7f2c andwide
projection, thenT andanglecarry; T8floorsprojectiontooriginalword. Originalstack
argument is explicitlyremoved. Other nativegeometryrotationcallers unchanged.
_contact_read_rate invalidates onnativewordchanges; allsamevalueresets covered
by_motion_reset and_motion_contact_rates. cd86 guard respectsnonzero fractional
rollrate evenwhenword0 (saved3regs=>returnslot12,redirectnativecda0).

s4-contact-math-full passes162response+189projection+45livefunctionroll+
135livefunctionpitch privatecases. Pitchstub suppliescos throughprivatejumpvector,
noactualgamewrites. s4-contact-one108corestatesmatchoriginal. s4-contact-off ranges
pristine. Branch-audit50rangespass. FullsmallTphysicalhandlingstillunverified.
s4-contact-tape-trace actualT8gamecalls1frontpitch+4rear allratesmatch recordedraw.
No actualrollcontact inthis400-returntape; privatefixturescoveritsfunction.
IMPORTANT s4-contact-tape GDBentryD0 readings differ inSIGNfromconsumedinputs for
3/5events (-10vs10,-15vs15,118vs-118). DoNOTuseoriginalfailedregisterbasedmodel
asproof. TRACE privateoperand recording confirmsroutine outputs. Needauditany
register-basedmodelchecks (e.g.scalar D4RPM) beforefinalacceptance; memory-based
snapshots/privatefixtures areindependent. check_contact_hooks.py currentlyuses
TRACEslave/recordedraw, ignoresunpairedboundarybreaks.
s4-contact-integrated-math invalidstartup: AF_UNIXpath toolong, terminalclosed
ownedPIDs. Successfulreplacement s4-contact-math-full usesINSTANCE=cfull.
Allcurrentjobs exited.

Fractional longitudinal projection is now connected through HardDrivinProjection.s
(includedbetweenContactandMotion). HDVPROJ1: currentXYZQ16 0/4/8, previous12/16/20,
extraQ16positioncarries24/28/32;36bytes. Positionentry snapshots; positionadd
updatesfraction (unlessAF31skidholds), integratesextraafterintegerXYZ. Motionreset
clearsall9longs. Nativeintegerprojectionunchanged: extensiononlySSvelocitycarry
[-7,7]*12288 Q16 (3/2 ofeighthvelocity), thenQ14 sin/cospitch+yaw. Mismatchwith
SS_VELOCITY_LAST clearslocalinputfraction, noforeignscalarstatewrites. Preserves
nativeoddinteger v+(v>>1)quantization; don'tclaimfinerintegerprojection.
_projection_delta fullfractionEuler [new*(8+n)-old*(8-n)]/16 thenQ16carry; exact
smallfactorlongproducts, ASR4loses<1Q16LSB/call. T0nomovement,preservescarry.
Separatefinecarrymeansnoformat change toHDPOSST1 1/128carry orfallhelper.
VERIFY_PROJECTION_MATH requiresMOTION; privatefixturecalledat_time_install.
s4-projection-math60projection+1323Euler casespass; resetstatezero.
s4-projection-small360liveaxisupdates allmatchmemoryoperands;200nonzerofraction
updates,11absoluteextra longpositionunits. check_projection_hooks.py usesmemory
only (avoidsGDBregisterdiscrepancy). s4-projection-one108states matchnative;
s4-projection-off disabledrangespass; normalbuildbyteequal. ExistingMotionMath
buildnow32274bytesstillassembles; keepnewlargefixturesseparate. Allcapturejobs
completed. Newbuildguardtested; toolscheck_projection_math.py and_hooks.py.

Traffic now gated by VERIFY_TIME_TRAFFIC (requiresSCALARS) plusCUSTOM1.
HardDrivinTraffic.s patches83c4/8 tableallocation,ce52/8 initrouteclear,d4d6/8
resetphase/speed,ce8a/42speed,d36e/18phase,bc4c/6collisionreverse. Branch audit56.
HDTRAFF1 signature followedpointer.l,size.l. ExecAllocMem PUBLIC|CLEAR count*16,
FreeMem priorblock onreload, existing_failmem abort onallocationfailure. No fixed
countlimit; liveSPS table12records. Repeatedreload/freepath notyetinteractive-tested.
Slot16bytes: speedcarry.w0,lastspeed.w2,oldfullspeed*8.w4,phasecarry/128.w6,
lastphase.w8,reservedbyte10,initbyte11,pad.l12. Index=(record-AF06)/46*16.
Nativeaccel1..3,target9..20; capceil(target/accel)*accel preserves nativeovershoot
fromzero-speedgrid (2toward9=>10,3toward20=>21). fullspeedin eighths, mincap.
Phase [v8*(8+n)-u8*(8-n)+carry]/128. Nativewrap±200afterhookpreservescarry;
geometryreadsoldphasebeforeadvance. T<=1,bytevelocity meansatmostoneboundary.
ResetD4D6 initflagforcesoneT8updateevenifdiagnosticT0; thennormalupdatesobeyT.
Collisionhelpernegatesfullspeed withsignedremainder; mode direction flips stay
nativeandcarryremainsconsistentwithsamephaseparameter. PlayerresetdoesNOTclear
traffic (independentworldactors). Table/raceresets clearaffectedslots.

check_traffic.py capturesbefore/afterallrecords andposewords for120worldupdates,
usesMEMORYoperands only. s4-traffic-native1440records/poses equalunpatched
s4-traffic-reference afterrouteptrnormalizationandseparateobjectposecomparison.
Native92crossings; s4-traffic-small1440updates atT1/8 allmatchmodel,1103fractional,
5routecrossings. Bothcapturecollision-observations.json havenoactualvelocity
reversal; don'tclaimlivefractionalcollisionproof. s4-traffic-math50private
reverse/mismatch/doublereverse casesplusinitT0 override+subsequentzeroT pass.
TRAFFIC_MATH requiresTRAFFIC; separate fixture avoids growingMOTIONmathsize.
s4-traffic-one108playerstatesmatchnative. s4-traffic-offdisabledrangespass,
normalbuildbyteequal. Allcapturejobsfinished.

Next: timedpresentation/input/dispatcher plusfulltrafficcollision/transition,
contact/replay andhumanacceptance. Phase-before-pose latencyneeds explicit
equal-elapsed comparison; do notlabelstoredphaseanddisplayedposeassameinstant. Read motion-next.md
for auditedpatchboundaries and algebraicposition/gravity/drift proposals. Those
formulas are designs, not validated implementation; preserve originalhandling
perplanandtestnonlinearcontact. Position carrymustsurvivepureintegerprojection
butresetatteleport/impulsewriters; don'tblindlyclearfractionaftereveryprojection.
Current _time_scalar_fields staysconstant; actualboundedvariableTdispatcher,input
latching,replay/Phantom/attracttimelines,performanceandhumanlapsstillopen.

Next: implement actual variable-T bounded dispatcher (NOT fixed tick+interpolation),
scale all inventoried quantities and explicit reset writers, latch input once,
convert traffic/replay/Phantom/menus/attract durations; prove native T1 equivalence,
compare machine trajectories and performance. Follow full plan, no silent skipping.
Human A500/040 lap acceptance remains at end. User was asked asynchronously whether
native-clock preservation or repairing CPU-dependent clock takes precedence; no
answer yet, preserve clocks unless user says otherwise. Do not mark goal complete.

Accepted artifacts: step3-{comparison,coupling,costs,course,validation}.json,
s3-coupling-*, s3-stepinput-*, s3-profile-a500-impact. The earlier s3-constant-*
sets are INVALID because guest GDB writes were ineffective; their metadata says so.

## State, writers, consumers and scaling rules

One outer pass takes `T = elapsed_fields * f0 / 50` native steps. Use 16.16
accumulators and signed fractional carries. With f0=6.25, nominal T=fields/8.
Measured PAL is 49.9204 Hz; use the specified nominal-50 convention consistently
and report its 0.159% difference from emulated seconds. T=1 must take the original
integer arithmetic and operation order, including clamps and truncation.

The table names writer/consumer routine families; the local direct-reference
index enumerates individual instruction sites. Initial data loading and native
new-race resets apply to every row. State resets/copies below must also reset or
copy any new fractional companion state. G($98ea..$98ee) is camera position,
G($98f0..$98f4) the previous/render pose, G($98f6..$98fa) current world pose,
and G($98fc..$9904) the higher-precision longword pose. Do not mix these domains.

| State and units | Writers / consumers | Chosen rule |
| --- | --- | --- |
| Throttle G($991c), integer 0..100 | `$07c32` ±2/clamps; `$0b662` off-road retention; `$0b500` skid-exit reduction; collision, `$059xx`, `$108a2`, `$117xx` reset; engine/physics read | ±2T with carry; off-road retention `(7/8)^T` while the native >30 condition holds; skid-exit 7/8 once as a transition; reset/clamp clears remainder. |
| Buttons G($95f6), X/Y G($95fa/$95fc), key/gear requests G($95ff/$991d), brake G($9911) | VBL/input readers/reset vectors; `$07c32`, patched gear selectors; `$0b662` consumes/clears requests; replay checks buttons | Latch input once per outer pass; consume discrete key/gear/start/replay-skip once. Held throttle/brake applies to elapsed time. Do not replay one-shot input on substeps. |
| Longitudinal velocity G($9928), native speed units | `$0b8a6` integration; `$0bcc8/$0bda6` collision reset; `$059c6/$108d8/$10a88/$11804` reset; steering, motion, engine, collision and race exit read | Evaluate native force law from unscaled velocity; multiply the resulting acceleration increment by T. Preserve drag, gradient and braking laws, ±40/−35 native rate limits, then scale their increments. Do not multiply the squared-speed force-law input by T². |
| RPM G($992a), target speed G($9926), MPH G($992c) | `$0b662..$0baea`; initial/recovery/race resets; cockpit, audio, collisions and score read | RPM slew ±450T; MPH and target-speed conversions keep units. Automatic/manual gear changes and gear-ratio RPM correction happen once per threshold/event, including native shift damping. |
| Gear G($9936), auto flag G($993e), table pointer G($9940) | Initial/selection `$059xx/$06faa/$087fa`, `$0b95x/$0b9ax/$0ba72/$0ba86`, `$118xx`; engine and cockpit read | Discrete state, no scale. Normalize known pointers only for comparison. Check crossing of shift thresholds on each bounded substep. |
| Projected motion G($991e/$9920/$9922), long XYZ G($98fc/$9900/$9904), word XYZ G($98f6/$98f8/$98fa) | `$0b500` integrates; `$0baee/$0cab6` correct; `$059xx/$090xx`, `$108a2`, `$10b08`, `$1100c`, `$113xx/$115xx` initialize or restore; geometry/camera/replay read | Keep displacement-source values in native velocity units; integrate XYZ with T and signed carries. Recompute word pose from longs. Teleports, replay restores and geometry corrections are not rates. |
| Angles G($994a/$994c/$994e), base/previous angles G($9944/$9946/$9948), quarter-degrees modulo 1440 | `$0b194/$0b1d0/$0b35e`, contact `$0cab6`; initial `$090xx`, camera `$0d54c/$0d960`, recovery and replay/end sequences; transforms, geometry and replay read | Scale angular-rate/steering increments by T before rotation helpers. Keep absolute angle copies, wrapping and terrain constraints unscaled. Carry fractions separately per axis; wrap the integer-plus-fraction consistently. |
| Roll/pitch rates G($9914/$9916), spin G($991a), native angle units/step | `$0cab6` contact feedback, `$0b440` spin creation, `$0b638` spin decay; collision/new-race/recovery resets; `$0b35e` integrates | Integrate rates with T; spin retention `(9/10)^T`. Contact quarter-angle corrections are relaxation toward geometry: use gain `1-(3/4)^T`, preserve native T=1 arithmetic. Where storing half the applied correction as next-pass rate, divide the time-scaled correction by T before the native half factor. Contact mask 12 assigns a rate without immediate rotation; keep that native rate then integrate with T. |
| Fall velocity G($990e), long-position units/step | `$0cd82` +5; `$0ccc6` inverted-contact acceleration; `$0cc90/$0cccc/$108c0` clear; `$0b5f8` integrates; landing threshold `$0cc42` reads | Acceleration ×T and position decrement ×T in native order. Hard contact zeroing is a constraint. A landing impulse or contact projection is not multiplied by T. No new Verlet/gravity term is added silently. |
| Contact mask G($9910), wheel gaps G($947e..$9484), normals/trig workspaces | `$0c854/$0c94e/$0ca14`, `$0cab6`, `$0b268/$0b35e`; steering, engine and collision read | Recalculate from current geometry each substep; keep distances, thresholds and Q14 trig units. Penetration projection at `$0cbdc..$0cc2a` remains unscaled. |
| Crash drift G($9908/$990a/$990c), countdown G($9912), crash G($9606) | Object/barrier collisions `$0bc62/$0bd40/$0bf80`, hard landing `$0cc54`; `$0b500` drift and decrement; `$10f08/$116a0` crash decrement; initialization/recovery/replay clear | Collision impulse, separation and initial 25/30 values once per event. Advance countdown phases by elapsed native time with carries; integrate saved drift ×T at its decay envelope. Emit expiry exactly once when crossing zero, not by testing equality after a large decrement. |
| Recovery G($9605), phase G($8cec), route G($9586/$98e4) | Abort `$07c78`, off-road `$105f4`, replay exit `$10e92`; `$108a2` phases 0..8 and resets; `$0cda4` skips while recovering | Nine-stage native recovery becomes a timed interpolation phase, advancing by T. Ground target and `(8-phase)*32` height are positions. Complete once; reset all motion/angle remainders and resample input. |
| Engine-start phase G($adde), enabled G($addc), race G($addf) | `$07d94/$07d9a`; `$0db40/$0db4c` in camera preparation; `$088xx/$108xx/$117xx` reset; controls, traffic, replay and engine read | Advance start phase by native elapsed time; preserve threshold events at 6/7. Separate phase advancement from geometry rebuild; do not charge elapsed time twice. Preserve the ordered native side effects on the T=1 compatibility path. |
| Traffic records at G($af06), 46 bytes each: phase +16 /200, speed +23, slew +21, target +22, direction +20, route pointers +0/+4 | `$0cdf8` init, `$0ce70` via `$0d40e` advance, `$0d450/$0d496` reverse/reset, `$0bc4c` collision reversal; objects +8..+18 written there and replay; collision/scene/replay consume | Speed slew ×T and route-phase advance ×T with carry. Process every crossed route boundary and branch in order; never skip topology when T>1. Geometry interpolation remains absolute. Reset phase carries on route resets/replay exit. |
| Course progress G($adcc/$add0), checkpoint latch G($af30), wrong-way G($e930), difficulty G($add5), lap/Phantom result flags | `$07b8c/$0880c` reset waypoint pointers; `$0dbbe/$0dbee` advance; `$0dee8/$0e272` set direction; `$092c0/$0936a` latch crossings and award time; `$07612/$08798` choose difficulty; scene, recovery, overlays and qualification consume | Discrete geometry-driven transitions: process crossings in order on each bounded substep, once per crossing. Do not scale pointer strides, difficulty or bonus amounts by T. Preserve BCD comparisons and report their clock dependence. |
| Score G($9788), BCD points | Init `$06ac6`; camera `$0db1e..$0db2c` adds MPH>>4 via BCD helper; other score events; `$10020` draws | Time-integrate the per-pass score rate with carry; keep one-shot bonuses discrete. The draw routine itself has no timer to scale. Do not charge an extra interval for collision camera rebuild; preserve native T=1 score-event multiplicity. |
| Instant replay: G($e91e), 90×158-byte ring G($b192)..G($e91d) | `$0898c` init, `$089d8` record/advance, `$089b4` rewind on collision; `$10b08` playback, copying player/traffic/camera/pitch | Keep native-duration history: timestamp records or sample at f0, with interpolation when a variable step spans sample times. Playback advances a time cursor, not one stored frame per displayed frame. Preserve collision rewind and skip semantics; restore companion state on mode changes. |
| Phantom recording/playback: G($e922/$e92c) phases /6, G($e924/$e928) record pointers, 12-byte poses | `$08a9c` records, `$08b0e/$08c84` interpolate/advance; `$118xx` reset; `$1100c` post-race playback saves/restores cursors | Advance phase in native time, crossing all six-step sample boundaries. Keep angle wrap and absolute pose interpolation. Post-race camera/player motion is a separate presentation timeline; never run live car physics there. |
| Post-race Doppler pitch G($9602), previous distance local at a5-22, volume G($958e) | `$1100c`: `$1119c..$111c8` computes current minus previous distance, pitch `800-6*delta`, distance attenuation; `$007d0` consumes; `$1126e` restores volume | This is a genuine finite difference: divide distance delta by elapsed native presentation time before the pitch conversion. Preserve the T=1 branch and reset previous distance at entry. Absolute distance attenuation is unscaled. |
| Replay shake/animation: `$10b08` locals, frame index d4, 3-pass animation divider, last-26-record effect | `$10dd8..$10e16`, `$10e5a`; draw and sound consume; `$00a36` RNG called twice per effect | Time-based replay phase. Trigger each historical event once even if multiple frames are crossed; RNG advancement tied to historical replay events, not display frequency. |
| RNG G($903c), 32-bit state | Initial zero; sole direct mutation `$00a54` inside `$00a36`; two callers `$10db8/$10dc6` | Discrete event sequence, no T multiplier. Zero bypasses recurrence and stays zero in all measured captures. No hardware-time read was found in this recurrence. |
| Overlay lifetime G($af32), message G($e92e) | Checkpoint/lap `$092c0/$0936a`, Phantom result `$08c84`, off-road `$1058e`, main/Phantom crash loops, race reset; `$10246` decrements | Replace 40/60-pass duration with native-time phase; draw from current phase. Preserve one-shot message selection and expiry. |
| Attract route G($94d4), phase /10, pointers G($94d8/$94dc), fork flags and cached deltas G($94bc..$94d7) | `$0d54c` through `$0d960` writes route pose/angles; init from route table; draw/camera consume | Separate attract elapsed-time phase; increment by T, process route wraps/forks, interpolate geometry. No player physics is called. Never let repeated scene preparation advance it twice. |
| Attract duration 1000 passes, overlay scroll G($fb54), alternate-page flag G($9584) | `$107d6/$1088c` init/advance, `$10672/$10706` decrement scroll; `$10898` toggle; overlay draw reads | Timed presentation, using its own active epoch. Phase ×T; crossed toggle/exit once. Gameplay time does not accumulate during attract. |
| GAME OVER 35 passes, split-text motion capped at 20 | `$10f66..$10ff0` local phase; text renderer consumes | Independent presentation elapsed time; phase ×T, clamp position, exit once at 35. No live physics catch-up on returning to menus. |
| Other menus/transitions | Submit callers `$0540a/$05efa/$06040/$0630e/$06a1a/$06bf6/$06d1a/$06fba/$077a2/$0850a/$11252/$1147c/$11510/$115e0/$1189e` | Input-driven waits remain event-driven. Animate 200-pass credits, +3 scrolling, bounded waits, seven-pass end-camera and post-race playback on separate presentation time. Keep fade/dissolve sequence indices discrete but schedule their intervals; exclude menus/loading from gameplay T. Intro optimization stays deferred. |
| Audio events `$008ae`, pitch G($9602), channel-start G($8fc6), sample pointers/periods | Control start, gear/skid/crash/checkpoint/off-road/replay callers; `$0baea` computes RPM-derived pitch, replay `$10c14` restores, crash clears pitch and recovery stops audio; `$007d0` programs Paula, `$00840/$00864` stop | Keep pitch conversion and DMA sample periods unchanged. Latch transition sounds once; sustained sounds may update pitch once after simulation. Do not restart collision/start samples per substep or per rendered replay frame. |
| `$10020` score, `$0f894` cracked windscreen, cockpit/background/polygon drawing | Draw state reads and framebuffer/blitter writes; `$1046e/$1058e/$10238` also have time/state side effects listed above | Draw once per outer pass. No generic T multiplication in rasterizers. Move or gate the listed side effects separately; these calls are not all pure rendering. |
| Audio service pointer G($9006), channel records G($900a)+12*channel, setup counters G($9020/$902c/$9038) | `$008ae` selects service; `$00864` clears it; `$00760` sets record +10 to 2 with sample/period/volume; VBL `$002f8..$003d4` calls `$042ae` or decrements channel counters | Already field-driven: leave durations and Paula programming unchanged. These are hardware setup phases, not simulation counters. |
| Native clocks, pause and mode flags | VBL `$02c4c/$02c8a`; reset `$06aca/$08870/$09462/$104e0/$11740`; BCD allowance helpers at `$09354/$09452`; deadline `$0b172`; many mode gates | Preserve native BCD semantics under the existing plan. New field epoch resets on entry/resume/exit; no pause/replay/loading debt. Report lap-clock phase dependence independently from car-state comparisons. |

Scene setup `$0d960` is particularly important: it copies current pose into the
render/previous domains, records replay, accrues score and advances engine-start
state. `$0baee` can call it again after collision through `$0cde2..$0cdee`.
Scaling only `$0cda4` and `$07c32` would leave multiple simulation systems tied to
rendering and would duplicate side effects on collision substeps.

The steering, force and contact routines do not contain an ordinary
finite-difference velocity estimate that should automatically be divided by T.
Position differences in `$0baee` describe collision segments; leave their geometry
intact. Rate conversion is required specifically when a new time-scaled contact
correction is stored back as an angular rate. The geometry-selected contact and
collision policies must be tested at T<1 and T>1; the table is a design, not an
already-validated variable-step solver.


## Local workflow and boundaries

Read development.md for commands and safe INSTANCE process isolation. Traces
are losslessly archived with uncompressed hashes. The local profiler-control copy
is verified against the old instrument; it changes capture controls only. Keep
all tools, game/ROM bytes, executables, screenshots and traces under ignored tmp/.
Commit only the explicit HardDrivin source/document files. The unrelated root
.DS_Store remains untouched. No GitHub operation or push was performed. Intro
optimization remains deferred.

## Direct state references

Individual code offsets for the core global fields. The inventory above also
covers indirect BCD helpers, input vectors, traffic/object writes, replay copies
and initial data/reset families. Numbers in the first column use G notation.

| Global | Direct writers | Reads/address consumers |
| --- | --- | --- |
| $8cec | $10ae0, $10aec | $108b8, $10aa8, $10ae4 |
| $903c | $a54 | $a3a, $a48, $a58 |
| $94d4 | $d8fe, $d90a | $d57c, $d902 |
| $9605 | $7c78, $8838, $105f4, $10af0, $10e92, $11728 | $8b6, $cda8, $e4c8, $108aa |
| $9606 | $8854, $bce0, $bdbe, $bfee, $cc54, $107f0, $108fc, $10e7c, $10f08, $116a0, $11704 | $8c2, $7d12, $b362, $b504, $b66a, $baf6, $e4c0, $10594, $10ef0, $10ef6, $10f34, $10f82, $11680, $11686, $116c8 |
| $9790 | $6aca, $8870, $9462, $104e0, $11740 | $6278, $6ec2, $6eee, $6fc2, $8874, $93c6, $93d0, $945c, $b172, $10060, $104ac, $105d8, $105e8, $1186c, $1196c |
| $9798 | $2cca, $887a, $104e4, $11872 | $934c, $944a, $10516 |
| $98ea | $909a, $d844, $dae4, $1106e | $d922, $d928, $dc72, $dca2, $dfe8, $e01e, $e360, $e3d8, $e4dc, $e564 |
| $98ec | $90bc, $d85a, $daf0, $11080 | $b154, $d934, $d93a, $dc82, $dcb2, $dffa, $e030, $e3e0, $e56c, $e70e, $1000c |
| $98ee | $90de, $d870, $dafc, $11092 | $d946, $d94c, $dc92, $dcc2, $e00c, $e042, $e36c, $e3ea, $e4e8, $e576 |
| $98f0 | $9096, $d922, $d9c6, $10a4e, $10b88, $11074 | $4ee4, $4f5a, $89e6, $8ac4, $9280, $be00, $be0a, $be1e, $be4c, $bf0a, $dadc |
| $98f2 | $90b8, $d934, $d9d2, $10a54, $10b8c, $11086 | $4ed2, $4edc, $4ef6, $4f48, $4f52, $4f6c, $89f4, $8ad2, $928a, $dae8 |
| $98f4 | $90da, $d946, $d9de, $10a5a, $10b92, $11098 | $4f0c, $4f82, $8a04, $8ae2, $9294, $be24, $be2e, $be42, $be58, $bef6, $daf4 |
| $98f6 | $9092, $b602, $bcb0, $bd8e, $bfd6, $cc16, $d928, $10996, $109f0, $10be0, $10cd2, $1107a, $11354, $1157e | $598c, $90e4, $be04, $be10, $be18, $be48, $c09a, $c0c4, $d9c6, $10a4e, $10aba, $10ce8, $110f0, $1115a, $1135a, $1159e |
| $98f8 | $90b4, $b60c, $bcba, $bd98, $bfe0, $cc20, $d93a, $109b4, $10a0e, $10ab4, $10bec, $10cda, $1108c, $11368, $11586 | $5996, $90ee, $c0a8, $c0d2, $c9e0, $c9ec, $c9f8, $ca04, $d9d2, $10a54, $10ac4, $10cf2, $110fe, $1136c, $115a8 |
| $98fa | $90d6, $b616, $bcc4, $bda2, $bfea, $cc2a, $d94c, $109d2, $10a2c, $10bfc, $10ce2, $1109e, $1137c, $1158e | $59a4, $90fc, $be28, $be34, $be3c, $be54, $c0b6, $c0e0, $d9de, $10a5a, $10ad2, $10d00, $1110a, $1116a, $11382, $115b6 |
| $98fc | $5992, $90ea, $b57e, $b5be, $bc8e, $bd6c, $bfb4, $cbdc, $10ac0, $10cee, $110fa, $11360, $115a4 | $b5fc, $bcaa, $bd88, $bfd0, $cc10 |
| $9900 | $599e, $90f6, $b588, $b5d6, $b5f8, $bc9a, $bd78, $bfc0, $cbf4, $10acc, $10cfa, $11106, $11374, $115b0 | $b606, $bcb4, $bd92, $bfda, $cc1a |
| $9904 | $59aa, $9102, $b592, $b5ee, $bca6, $bd84, $bfcc, $cc0c, $10ad8, $10d06, $11114, $11388, $115bc | $b610, $bcbe, $bd9c, $bfe4, $cc24 |
| $9908 | $bc68, $bd46, $bf8e, $cc6c, $108c4, $10aa4 | $b5b2, $bc86, $bd64, $bfac |
| $990a | $bc72, $bd50, $bf98, $cc72, $108c8, $10aa0 | $b5ca, $bc92, $bd70, $bfb8 |
| $990c | $bc7c, $bd5a, $bfa2, $cc78, $108cc, $10a9c | $b5e2, $bc9e, $bd7c, $bfc4 |
| $990e | $cc90, $ccc6, $cccc, $cd82, $108c0 | $b5f2, $cc42 |
| $9910 | $cabe, $caca, $cadc, $caee, $cb00 | $b394, $b6d8, $cb0a |
| $9911 | $59ca, $7db2, $7dc2, $7dd2, $bac6, $108e4, $11808 | $b40a, $b7e0, $b88e |
| $9912 | $59ce, $b59c, $bc80, $bd5e, $bfa6, $cc66, $108e8, $10e88, $1180c | $b596, $b5a0 |
| $9914 | $59b6, $bcd8, $bdb6, $bf84, $cb70, $cd14, $10a80, $117f0 | $b36e, $cd86 |
| $9916 | $59b2, $bcd4, $bdb2, $bf80, $cb6c, $cd4a, $cd7a, $10a84, $117ec | $b37c |
| $991a | $59ae, $b440, $b638, $108d0, $117f4 | $b386, $b62a, $b63c |
| $991c | $59e8, $7d36, $7d42, $7d50, $7d5a, $7df0, $b65a, $b796, $bce6, $bdc4, $bff4, $cc5a, $108dc, $10a8c, $11824 | $7d3a, $7d54, $b64e, $b69e, $b6e6, $b782, $b78a, $ed72 |
| $991d | $59d2, $b9e2, $b9ec, $10eae, $11810 | $b9ba, $b9c8, $b9ce, $b9da, $b9e6 |
| $991e | $b55e, $10a98 | $b578, $bc62, $bd40, $bf88, $cc6c |
| $9920 | $b532, $10a94 | $b582, $bc6c, $bd4a, $bf92, $cc72 |
| $9922 | $b51c, $b548, $b574, $10a90 | $b524, $b53a, $b550, $b566, $b58c, $bc76, $bd54, $bf9c, $cc78 |
| $9926 | $59c2, $bac2, $108d4, $11800 | $b734 |
| $9928 | $59c6, $b8a6, $bcc8, $bda6, $108d8, $10a88, $11804 | $b3b2, $b3c4, $b512, $b518, $b6c0, $b6c6, $b738, $b74e, $b764, $b774, $b7ca, $b7da, $b7e6, $b7fa, $b8b2, $bc24, $10ee2, $11672 |
| $992a | $59ba, $b726, $b8e8, $b8f2, $b8fe, $b954, $b9aa, $ba62, $ba68, $108e0, $117f8 | $b6fc, $b8ce, $b8ec, $b8f6, $b90c, $b92e, $b962, $b984, $ba2c, $ba3e, $ba54, $ba5c, $baa2, $bad8, $eb76, $eb90 |
| $992c | $59be, $baac, $117fc | $b3ba, $b402, $b642, $bab8, $bb06, $bb14, $bb22, $bccc, $bdaa, $ccb4, $db22, $ec56 |
| $9936 | $59e4, $b958, $b9ae, $ba72, $11820 | $5a04, $b678, $b68a, $b6d2, $b914, $b96a, $b9d4, $ba00, $ba8a, $11840 |
| $993e | $6faa, $87fa | $59d6, $59ec, $7ca8, $b904, $ea36, $10ea8, $11814, $11828 |
| $9940 | $5a00, $5a0c, $b95c, $b9b2, $ba86, $1183c, $11848 | $eafa |
| $9944 | $910c, $d890, $d9cc, $10a60, $11210 | $89ec, $8ac8, $929e, $9996, $d92e, $d96e, $d97c, $d9ea, $d9f8, $dd04, $e080, $e6aa, $11216, $11224 |
| $9946 | $9118, $d772, $d8fa, $d9d8, $10a6c, $110a4 | $89fc, $8ad8, $92ac, $99f0, $b376, $d940, $d98a, $d998, $da06, $da14, $db52, $dd26, $e0a2, $e7e2, $e806, $110b8, $110c6 |
| $9948 | $9124, $d778, $d8b0, $d9e4, $10a78, $110b0 | $8a0c, $8ae8, $92b6, $9a4e, $b36a, $d952, $d9a6, $d9b4, $da22, $da30, $db62, $dd48, $e0c4, $e78c, $110d4, $110e2 |
| $994a | $9106, $b258, $b456, $b466, $d92e, $10a64, $10d12, $1120a, $11394, $113aa, $113ba, $11596 | $b26e, $b44e, $b45e, $b4a8, $b4b6, $d9cc, $112a4, $113a2, $113b2 |
| $994c | $9112, $b1ca, $b25c, $b376, $b474, $b484, $d940, $10a72, $10d16, $110aa, $1139e, $11592 | $b1f8, $b206, $b28c, $b46c, $b47c, $b4c4, $b4d2, $cc96, $d9d8, $112b0 |
| $994e | $911e, $b260, $b372, $b492, $b4a2, $cb90, $cd0a, $cd9c, $d952, $10a7c, $10d1c, $110b4 | $b1a2, $b1ea, $b2aa, $b48a, $b49a, $b4e0, $b4ee, $cd8c, $d9e4 |
| $9950 | $4f22, $4f98, $deb6, $e234 | $c034, $c0f2, $db8e, $e2ec |
| $af31 | $8850, $b428, $b64a, $bcdc, $bdba, $10900, $10b00, $10e80 | $8a1a, $b3fc, $b50c, $b61a, $b72e, $b7ac |
| $af32 | $8864, $8e38, $935a, $93a4, $9470, $10246, $10604, $10efe, $11694, $11738 | $1023c |
| $e91e | $898c, $89b8, $89d0, $8a90 | $89c4, $89e0, $8a82, $10b44, $10b76, $10e4c |
| $e922 | $8aae, $8abc, $8c68, $8c74, $1185e | $8ab2, $8b2a, $8b40, $8c6c |
| $e92c | $8e52, $8e5e, $11868 | $8ca2, $8cb8, $8e56 |

## Overlay and recovery timing (development gate)

`VERIFY_TIME_PRESENTATION` requires TIME_SCALARS and CUSTOM1. Overlay starts of
40/60 native steps initialize an elapsed-field countdown, including same-value
restarts. Rendering publishes the ceiling of remaining fields/8 and saturates at
zero. Recovery initializes only once even when fractional updates leave its
native phase byte at zero. Height falls from 256 by four units per field, then
holds ground during fields 64..71; expiry occurs once at 72 fields. Recovery's
per-pass motion resets deliberately do not reset this separate timing state.

`HDPRES01` identifies two overlay words (remaining fields, last published count)
and two recovery words (age fields, active). Phantom crash expiry uses the same
overlay-start helper when the motion gate is compiled, avoiding overlapping
patches. Start helpers preserve X; the overlay update reproduces native SUBQ's
cleared X before loading the mode byte.

Evidence: `s4-presentation-long` and `s4-presentation-reference` match all 144
sampled player states through crash replay and recovery. Recovery flag/phase,
overlay count/mode and replay-request bytes also match at every sample; phases
0..8 are represented. This is the constant-input fixture, not the full driving
tape. `s4-presentation-math` executes the actual helpers on private state:
271 recovery transitions and 1125 overlay updates pass, covering T=0 through
T=1, initialization once, expiry once and the ground-height hold.
`s4-presentation-off` passes all disabled ranges. The normal build remains
byte-identical and the direct-branch audit passes 67 declared ranges.

These hooks still consume diagnostic constant intervals. The eventual dispatcher
must supply the correct elapsed interval to overlays drawn once per outer frame,
independently of bounded simulation substeps. Live fractional recovery/contact
transitions, replay duration, other presentation loops and real elapsed-time
integration remain unvalidated. Step 4 is still in progress.

Local fixture: check_presentation_math.py uses s4-presentation-math.slave with
VERIFY_TIME, TIME_SCALARS, TIME_PRESENTATION, PRESENTATION_MATH. Captures all
finished and owned emulators closed. Superseded by the dispatcher entry below.


Dispatcher progress: see GAME_TIME.md live elapsed-time section. New source
HardDrivinDispatch.s uses gated patches10f0c/8,10f28/8,7d0a/8,b3a0/8. Requires
MOTION,TRAFFIC,PRESENTATION. At outermeasure it selects <=8field steps; after
physics repeats10edc while pending, otherwise native8014+E706 draw. First input
is native; later held ramps only. HD DISP signature HDDISP01 follows two native
call pointers, 36byte state documented tracked. Scalar fields and TS_T updated
per substep. CUSTOM2 bypass only when DS_ENABLED30 set by successful install.
Presentation overlayrestart uses pending+currentfield interval, preserves X via
ADDA instead of ADD. Raceexit debt cancellation explicit but not tested yet.
check_dispatch.py captures150/250steps at10f28, memory-only conservation and
held-input checks; E706/7c32 calls filtered TS_ACTIVE excludes replay. Native
144states pass, live max6substeps/frame; no performance or equal-time claim.
First two dispatcher captures invalid installer stack restore; repaired, owned
jobs closed. Final source run s4-dispatch-ready adds installed-version delay gate.
Remaining immediate work: start-phase/score side effects, timed replay and
attract/menu loops; zero-time native discrete side effects; tests and acceptance.


Start/score progress: HardDrivinEvents.s is included and installed by DISPATCH.
HDEVENT1 -> score slot4,start slot4; each carry.w,charged.b,pad.b. _dispatch_take
clears charged flags. Tick consumesfield0..8 once per slot/substep; emitsone event
per8eligible fields. Forcednative bypasses gating and runs everyoriginalvisit.
Score native db1e..db32 entireBCDcall retained (ASR's X matters; invalidnibbles
possible); no new interpretation of scoreoperand. Startdb40/a, reset7d9a/6,
8860/8,108f4/8,1170c/8; score+lap clear886c/8,6ac6/8. Directbranch79pass.
VERIFY_EVENTS_MATH72privatecases takesallcarry0..7,n0..8,duplicate andnextstep.
check_events.py realmemorybeforeafterdb1e/db32 anddb40/db4a,350physicssteps,
T from TS_T; native144car+score+phase+enableexact; A500live121score/14phasevisits,
104score/12phaseevents,41fractional, no eligibleduplicate liveevent.
Remainingnext: timedreplay/Phantom, attract/menu, checkpointaudit, fullacceptance.


Replay playback progress: HardDrivinReplay.s under VERIFY_TIME_REPLAY_TIMING
requiresDISPATCH; optionalVERIFY_REPLAY_MATH ninefullrecords711words. Time VBL
addsRP_WALL unconditionally (CCRstillrestored), activeTS_FIELDSunchanged.
Hooks10bb0/6 begin preservesoriginalbranchto10e5c; 10bb6/8 selects scratch
thenreproducesMOVEA997A/MOVE.W6(a3),D0; 10e46/22 replacesringadvance+index with
age=(wall-start),D4=min(age/8,D6). HDRPLAY1 20state+158scratch. NvalidD6 fromnative
zero-recordscan, oldestA3capturedatbegin. Nativeforce age+=8; liveagefromVBL.
InterpolationunsignedXZ/signedY/shortest1440angles; packedengineFFFflagsold;
endpointcopyexact. Camera700behindandallnativeconsumersunchanged.
check_replay_playback.py anchors10bb0, retainsringandprivatefixture, captures
10bbe scratch/state until10e68exit; fullmodelwordcompare, elapsedtargetN*8,
optional--native and--slave; latesttoolalsoendbanksandrenderedreplay-end.png.
A500 s4-replay-playback87frames71fractional,N90,target720,exit725(lastdraw8).
Native144carcomparisonpassed; off82rangespassed. 020andfullnativejobsongoing
atthisentry; inspecttoolresultsbeforeassumingcomplete. Recordingcadence still
unconverted! Native89d8 captures158bytes percall; collision89b4 rewindsoneentry
beforeD960 rebuild. EligibilityphaseADDE>5 andADD7clear; 90-ringB192..E91D with
E91Ewriteptr. OldestplaybackA3 deriveswriteptr, zeros skipped decreasesD6.
Recordingconverterneedsresampled8fieldhistory androllbacktransaction or explicit
timestamps/capacityduration. RNG8038 at10db8/10dc6, effects10dd8 counters still
perdraw; overlayfallsback8 duringreplay, mustretime. No fullreplaycompletionclaim.


Replay follow-up: effect animation+RNG are now timed too. Extra ranges10db4/a,
10dc6/6,10dd8/2e(lastonlynonforcednative). Effectk=D4-max(D6-26,0),spriteindex
floor(k/3), reflectedafter5; pointerAEA0+16index setbeforePEA. RNGnative8038
calledtwiceperphase, cached RP_RNG1/2; skipsandnaturalexittaildrainthrough25.
PEAinsertedbelowhookreturnat10db4; nativeforcedretainsoldlocalcounterupdates.
RPstate32bytes: wall0,start4,age8,oldest12,count16,paused18,pad19,lastphase20,
target22,RNG1long24,RNG2long28; scratch158bytesstarts32. _time_pause/options
setpaused, _time_resume clears; VBLfreezesRPwallwhilepaused. ExistingTSactive
observerstillseparategameclock. VERIFY_REPLAY_PAUSE input-onlyhelperemitsSPACE
atRPage>=24, resumesafter40rawdrivefields; keyfixturedoesnotwritemodes/clocks.
VERIFY_STEPINPUT+VERIFY_TIME_REPLAY nowreleasesbuttonsoncrash/replayatcontrols
aswellasVBL(previousfixtureoverrodeitsownrelease). Doesnotaffectnormalflags.
Accepted: s4-replay-effects-020313frames273fractional,N90,exit720,100effectdraws,
52RNGcalls; s4-replay-effects-native77validrecords,77draws,age616,26effectdraws,
52calls; s4-replay-pause-constantA500N85,target680,exit681,61draws51fractional,
40pausedVBLswithfrozenclock,19effectdraws52calls. Private711wordcasespass.
Native+020replay-end.png inspected. Final-off85rangecheck,normalunchanged.
Invalid initial020stalledafter516frameswithuntimedeffectcounter; ownedjobsclosed.
A500fieldtapeanchorjobsdidnotreachreplayaftercodetimingchanges, stoppedownedPIDs;
constantinputcrashfixtureusedinstead. Allcurrentjobsfinished; noemulatorsleft.
Nextprioritytimedrecordingring+collisionrollback. Replayoverlaystillnative8fields
perdrawfallback (typicallycounter0aftercrashexpiry), needsmodalclockconversion.


Replay overlay follow-up completed: _replay_overlay_fields uses RP_WALL and a
separate previous timestamp, single clock read, unsigned wrap and65535 cap.
Reset at begin and overlay restart; presentation tick selects it for inactiveTS
with nativeADD7. Forcednative8 retained. Private HDRPOM01 holds9x16 outputs from
common interval+countdown helper, no native state writes. First fixture's ORI SR
likely faulted in usermode; three owned stalled jobs stopped and excluded. Repaired
fixture uses private clock only. s4-replay-overlay2-a500 passes9overlay/711pose
words,85entries61draws,exit680,40pausedfields,52RNG18effects. Native77draws/616age,
52RNG26effects passes. Ordinary final build byteidentical, branches85pass.
New capture_runtime_window.py captures500fields from10ed4 via VBL3f2, frontptr
changes, CDB0 physics returns,E706rendercalls, full allocatedglobals eachboundary.
s4-overlay2-window-off CUSTOM1off samebinary:38swaps3.793951FPS263.577ms,
38physics38draws, no replay/crash; inactivechecks pass. On:15swaps1.497612FPS
667.730ms,65physics15draws,no replay/crash. On-repeat all501snapshots and results
byteidentical. This is current diagnostic constantSTEPINPUT, not frozenA/B/equal
scene;60.5% FPSloss means acceptancegatefails. All ownedjobs terminal/closed.
Next priorities: profile gameplay regression, timed replay recording including
collision replacement, remaining presentation clocks and full acceptance.


Scene-cost follow-up: captured500field traces s4-dispatch-cost-on/off using
capture_runtime_profile.py (anchor10ed4,CUSTOM1on/off,sameoverlay2slave). Both
match independentwindow swap schedules exactly; coverage>99.99998%. Traces
losslesslycompressed.zst; report_runtime_profile.py uses exactretainedslave.lst
andlayoutpublished-_code_start to labelnewhooks. InclusiveB0D6=52.33%on31.71%off,
CDA4=7.48%on3.67%off; rendering10008=14.18%on40.21%off. Fullscene work repeated
perstep dominates, not solely math hooks.
New HardDrivinScene.s VERIFY_TIME_SCENE_CULL requiresDISPATCH,CUSTOM1. Hooks
B09E/6,B10C/6 skipvisible objects only when DSactive,pending>0,raceADD4nonzero,
object34zero. KeepallnearA194/contact andterrainB07A. Finalstep/fullpresentation
unchanged. HDSCENE1 countsaux/main32bit, preservesX viaADDA counters. Maingate
checks29 visibility beforecount. Raceexitguard avoids incompletefinaldraw when
pendingcancelled. NativeknownADD4writers beforephysics only; liveexitnotcovered.
VERIFY_SCENE_TWIN requiresCULL, B142/6 wraps recursiveB0D6 reference withstage1;
nestedtailbypassed toB18C, audio/offroadtailonce. Before/aftermarkerslocatedfrom
retainedlisting, HDSCTWN1 stage. check_scene_twin.py captures2Mbbanks100pairs.
IgnoreVBLlapclocks: firstfailedtestincludedthem, retainedsnapshotslaterpassafter
scopefix. s4-scene-twin2 passes10900objectmetadata,211nearobjects9209vertices,
contactflagsE94A/B/E960,player98F0..9955,score9788long,ADD4..DFlongs,E91Eptr.
25crashpairs,981mainobjectsfiltered,zeroauxiliaryskips(livecoveragegap).
Twinprecedesconservativeraceexitguard; itsnativepathsareunchanged otherwise.
s4-scene-native-final144states exactlyreference(s4-presentation-reference),
finaloffpass88ranges,branch88pass,normalfinalbyteidentical. Finalguardedwindow
s4-scene-window-guard23swaps2.296FPS435.476ms,73physics24render(lastunpublished),
16crashfields; prefilter15swaps1.498FPS667.73ms65physics,nocrash. Different
sceneprogression, noformal3%gateacceptance. Alljobs finished/ownedemulatorsclosed.
Remaining: fullscene/nearcontactacceptanceinclauxskip, raceexit, T extremes and
pixel/renderchecks; moreperformancework; timedreplayrecording/collisionrollback,
Phantom/attract/menu clocks andfullcrossmachine/humanacceptance.


Current priority changed by user: use one full elapsed-time physics update per
rendered gameplay frame on 68000; retain bounded substeps on 68020+. Plan step4
item2 now reflects this requirement. Current implementation still caps all CPUs
at8fields: do not merely remove cap without widening scalar/motion/contact math,
extending retention tables and multi-event/replay sampling, and validating largeT
collision sweeps/checkpoints. No silently discarded time. CurrentFPS diagnostic
73physics/23swaps per500fields motivates split. Previous question-onlyturn no
implementation progress; this turn adds independent live recording evidence.
Recording checker tools/check_recording.py and s4-record-live passed:
93transactions,36private interpolationrecords/2844words,69fractional samples,
78emitted over619eligiblefields,1nativecollisionrewind/duplicate/replacement.
All privatecurrent poses compared to nativeglobals+12traffic objects; whole ring
andwritepointer compared aftereverytransaction against independenttimemodel.
Initial s4-record-first invalid: verifier treatedAF06 pointer asinlinearray;
fixed dereference, freshcapture passed. Bothownedemulators closed. Newmodule
stilluncommitted; no020/native/offchecks yet. Recording assumesinterval<=8,
so needsmulti-sample emission fornew68000policy beforefinalacceptance.

Wide arithmetic prerequisite validated: HardDrivinTime.s scale_word/q16 accept
unsignedfields0..65535 onnewlongintervalpath; short0..8mathretained. Wordreturns
longquotient; Q16splitswhole/fractionbeforeconversion avoidsproductoverflow.
Q16inputrateboundstill16383. VERIFY_TIME_MATH HDWIDE01 300cases2400bytes;
check_time_math.py nowtakesoptionalrunname andcheckswide+legacycases.
s4-time-wide-fixed passes300wide,1215eighth,441Q16,11debt. Initials4-time-wide
failedprivatefixture upperhalfofcarryloopcounter afterwordincrement; fixedlong
increment, freshbootpasses. s4-wide-native144carstates exactpresentationreference.
Normalbyteidentical,patchbranches91pass. Alljobsclosed. NoCPUdispatchswitchyet:
next extendtables/products/events/replay andcallerwordnarrowing forT>1.
Userclarified020+physicsONEVERYFRAME, rendereruncapped, 50FPSmeansT1/8;
6.25Hzreferenceisnotupdatecap. PlanandGAME_TIMEreflectthis. Privatewidehelper
checksarenotlargeTgameplayacceptance. ReplayRecord.s stilluncommittedseparatework.

Decay/contact longerinterval prerequisite validated: new HardDrivinDecay.s
included bySCALARS, three unsignedfield lookuphelpers returnlonggain0..65536,
wordtables1929entries (706throttle,895spin,328contact). Each exactroundedQ16,
clampafterlastword avoids65536overflow. RuntimeVERIFY_DECAY_MATH72lookupcases
andalltablewords pass s4-decay-wide. Scalarretention andMotionspin callhelpers,
full-loss clearscarry; T1native untouched. Expandedexistingprivatefixtures to17
fieldvalues: s4-retention-wide595cases, s4-spin-wide595spin+allmotionregressions.
Contactresponse >8 helper handlesunsignedgainMULU andfull65536shift; rate uses
roundedgain*8/n, exactcoefficienterror<=.5+4/nLSB. s4-contact-wide216wide+existing
response/projection/liveprivatepitch/rollpass. Fullcontact_rate_scale stillhas
Q16overflowpotential atlargeT; notyetfixed. s4-decay-native144carstatesexactref,
s4-decay-off disabledrangespass, normalbyteidentical, branch91pass. Allownedjobs
closed. No CPUdispatcherchange/performanceclaim. Nextintegratorwideproducts,
eventmultiplicity/replaymultiemit, traffic, thenCPUpolicy andliveacceptance.

Ordinary/fractional position wide arithmetic validated. New shared
_time_product_s32_u16(D0signedlong,D1unsignedword)->D2high:D0low exactsigned64;
ordinaryposition >8fields uses numerator64*(v-u)+8*n*(v+u)+carry /128 withsigned
remainder. Projection >8 usesfloor((8*(v-u)+n*(v+u))/16)Q16 thenexistingcarrysplit.
Bothretainshortpath0..8. VERIFY_POSITION_WIDE_MATHrequiresMOTION, privateoutputs
HDPOSW01/HDRPWID1 8232bytes each,HDMULW01 432bytes;check_position_wide.py.
s4-position-wide-final1029ordinary+1029fractional+54productcasespass. Earlier
s4-position-wide/full also passed narrowerfixtures; finaladdsfullsignedlong
productextremes. s4-projection-wide-regression60component+1323Eulerpass;
s4-position-short-regressionallmotionfixturepasses(1323position405fall etc).
Allownedjobsclosed. NoCPUdispatcherchangeyet. Nextfall_displacementwide,
contact_scale_rateQ16overflow/writernarrowing, trafficroute multiwrap, events
andrecordingmultiemit. RECORDuncommittedstillonly<=8livevalidation; default
runtimecapstays8untilintegratorsready. NoFPSclaimfromprivatehelperchecks.

Falling-displacement extension validated: _motion_fall_displacement >8 uses
signed64 numerator -n*(16*v+2*frac)-a*n*(n-8)+carry, /128 truncatezero. Return
low32quotient fornativeADD.L coordinate, signedremainderfromwidehighsign (not
wrappedquotientsign). Nativeinvertedaccel atCCA6..CCC6 =5-speeddependentfunction,
notjust5; expandedfixturefullsignedwordaccel including+-2340. Newflag
VERIFY_FALL_WIDE_MATHrequiresMOTION; HDFPWID1 2205x8bytes. check_fall_wide.py
s4-fall-wide-fullpasses2205. Earlier s4-fall-wide945basiccasespasses. Existing
shortsuite s4-fall-short-regressionpassesall(405fallposition81fallvelocity etc).
Allownedjobsclosed. Sourcecapstill8,noCPUsplitactivation/noFPSclaim. Next
contact_scale_rate angularQ16overflow and anglewordnarrowing, throttle ADD.B
saturationbefore narrowing, fallvelocity/ordinaryvelocitywordwriters,traffic
multiwrap/events/replaymultiemit, thendispatcherCPUselectandliveacceptance.
Contact_scale_rateonlycalledroll_base andpitch_rate; possiblewideapproach
64product thenreducewholeangle modulo1440 (keepfraction) before Q16return,
likewiseordinaryangle_rate longincrements needcircularreductionbeforeADD.W.
Thisapproachnotimplementedyet; verifyanglewrapconsumersbeforechanging.

Controlramps longinterval fix validated: throttle_delta fields>8 addsfull long
increment tobytevalue thenclamps0..100 beforestore; existingoutwardfractionclear
andnativecallersaturation retained. Shortpath unchanged. rpm_delta signextends
rawtargetdistance D3 andcompares fullD0long scaled450limit, avoidingwordwrap;
reachedtargetreturnlong, lowword/nativecallersunchanged. VERIFY_RAMP_WIDE_MATH
requiresSCALARS; privatefake32bytes, HDRAMPT1 16x8 andHDRAMPR1 18x6results.
check_ramp_wide.py copiesinputs fromtmp/ramp-wide-inputs.json (generatedfrom
trackedfixtureinputs), modelsclamp/carry/target independently. s4-ramp-wide
16throttle18RPMpass; fieldsinclude1/8/9/511/600/32768/65535, invalidlast+gear.
s4-ramp-native144carstates exactreference, finalfield1711. Normalbyteidentical.
Allownedemulatorsclosed. NextcontactangularQ16wide +circularangle narrowing,
velocitywordwriters,trafficmultiplewrap,eventmultiplicity,replaymultipleemit,
CPUpolicy thenlivecrossmachineacceptance. Goalstillactive; noFPSclaimyet.

Angular integration wide path validated: nativeB44E..B4A2onlyone1440wrap.
_time_normalize_angle reducesfullsignedlong viaunsignedmagnitude2DIVUwords,
returns[-720,720], supportsLONG_MIN, preservesD1D2. motion_angle_rate fields>8
addsfullscaledinteger tocurrentangle thennormalizes andreturnsnorm-current for
originalADD.W; fractionalcarry unchanged. New contact_integrate_rate replaces
scale+add calls inroll_base/pitch_rate. <=8delegatesoldhelpers; >8 fullsigned64
Q16rate*n /8floor, addoldcarry, splittrunczero intointeger+signedfraction, then
normalizefullcurrent+integer. D0scratch, D1-D5/A0/A1preserved. Contactresponse
corrections themselvesremainexistingboundedhelper. VERIFY_ANGLE_WIDE_MATHcalls
private_angle_wide_test; HDANORM1=19long,HDACONT1=96x8,HDAMOTN1=92x8. Inputs
capturedJSONunderignoredtmp;check_angle_wide.py independentmodel. s4-angle-wide
allpass, includingT1/smallcases,multipleturns,invalidationand+-1440retention.
Fixturemacrorefactorbyteidentical. s4-angle-native144carstatesexactref; normal
byteidentical. Allownedemulatorsclosed. Nextvelocitywordwriters/saturation,
trafficroute multiwrap, events andrecordmultiemit, CPU policyactivation, full
crossmachine/performance/contact acceptance. NoFPSclaim,goalactive.

Traffic acceleration wide fix: _traffic_speed_step nowEXT.L currentfullspeed,
ADD.L accel*n,CMP.L terminal andMOVE.L cap before existingpublishDIVS8/nativebyte.
Validnativeaccel1..3,target9..20capgrid<=21 preserved; overspeedunchanged,
initializationforces8. VERIFY_TRAFFIC_SPEED_MATHrequiresTRAFFIC,HDTRSPD1 18x8;
check_traffic_speed_math.py / s4-traffic-speed-wide all18pass. Existingtoolnow
acceptsrunname;s4-traffic-speed-regression50reversal+init/zero-timepass. Jobsclosed.
Routephaseaudit: D380..D406onlyonephase200wrap; recordptr0/4current/next,
phase16,mode13,branchpreference15,cachevalid19,direction20,speed23. CF02..CFE4
normalizesnext: mainbounds98E0..AF26,branchjunctionsAF0A/AF0E; alternatebounds
9952..AF2A. For main mode, branchpreference+currentjunction+direction picks
alternate+20 oraltend-20 andmode13; alternateexit wrapsnexttoAF0E/AF0A andclears
mode13. Negativecrossings andjunctions needreferencevalidation. Geometry runs
BEFOREphaseincrement; avoidaccidentallyreplayingacceleration inroute loops.
Phasewide needs also capped-speed integration: oncecapreachedatfractionoftotal
interval, remainingtimecoasts. Endpointaveragealone undercounts; analytically
phase numerator/128 =2*n*vFull -deltaFull^2/accel +8*deltaFull (assumingcapreached),
versusn*(vFull+uFull)+8*deltaFull ifuncapped. Foraccel1..3 exactcarrymayneedden768
(LCM6) instead128; thisdesignnotimplementedyet. KeepnativeT1pathbitexact.
Player speed B8A6 iswordADD afterforce capped+40,-35exceptmodeflag; downstream
B8AA maps tospeed/RPM. Angular normalizationdone; player/fallvelocitynarrowing
andovershootstillrequireaudit. NoCPUmodeactivated, noFPSclaim. Consider an
explicitdiagnosticCPU-policybuild to measureone-updatecost beforefinishingall
traffic/timers; it must remain labeledincomplete andnotacceptance evidence.

CPU-policy experiment and wide events validated. VERIFY_DISPATCH_CPU queries
AttnFlags, pre020 takes full unsigned-word interval, 020+ keeps8field bound.
HDCPUP01 payload20=tag/attn/terminator longs,single.w,pad.w,oversized.l. >65535
fallback retains time via bounded steps, counts fallback; still experimental.
s4-cpu-policy-a500/off/020 all terminal with results:39/38/148 swaps and same
physics counts,3.894/3.794/14.776FPS. Not equal-scene/fullacceptance;02022crashfields.
These captures precede event extension. Events_tick now returns all floor((n+c)/8)
withlongadd, score loopsnativeBCD usingstackrepeatcount, startphase clamps7 and
nativeDB4A stillenables at>=6. ExpandedEVENTS_MATH128cadence+54phasecases.
s4-events-wide-count A500231scorevisits278nativeBCDcalls54multi,18startvisits,
2duplicates47fractional;020323score124calls31start,1duplicate354fractional.
Allcount/phase/carrychecks pass; independentBCDresultmodelnotclaimed.
s4-events-wide-native144car+score/start/throttle statesexactreference field1711;
s4-events-wide-offdisabledpass,normalbyteidentical,branch91pass. Allownedjobs
closed. check_events.py now --slave --wide; counts2c14calls betweenSI/SO.
Commit includesCPUdispatcher/Timeguard/Events/docs only. Record module+HD/Replay
include guards remain uncommitted from earlier; its live path onlyn<=8. Next
trafficphase coasting/multiple route crossings, replaymultiemit,velocitywriters,
remainingpresentation/audio, fullcrossmachine/performance/humanacceptance.

Fixed-field recording extended and validated, now ready to commit. TIME_RECORD
requiresREPLAY_TIMING; RECORD_MATHrequiresREPLAY_MATH. Record.s stateHDRECRD1
32bytes+previous/current158 unchanged. D960chargesprevious stepfields; unique
stampskeeporiginalwrite/before; repeatsreplacewholemultiemissiontransaction.
_record_emit extracted, loopsnum8-before throughinterval by8 (longloopcounter),
resetwriteorigin forrepeat; updatesphase modulo8 andper-sample emitted/replaced.
Signed interpolationbiasesword32768 thenunsignedweightedDIVU sofields65535safe.
Unsignedsum<=65535^2. Endpointsverbatim, angleshort1440,flagsheld. Newwidefixture
HDRRWM01 24records; existing36 shortrecords. HDRRWRA1 state36thenfake14224ring,
_record_wrap_test emits91samples atslot88 withbefore7/fields728; finalfullring
matchesPython independentmodel,write89,phase7. check_recording.py supports--wide
andauto-wrapfixture; everylivecapture verifiesfullring/pointer/nativeplayer+
12trafficobjectendpointposes. s4-record-wrap47A500transactions30multi(max3),
1collisionduplicate replaces2samples,76emitted606fields74fractionals; wrapsprivate91.
s4-record-wide-020189transactions79samples631fields,1collisionduplicate/replacement,
64fractionals (beforehelperextraction; final020playbackbelowusesnewhelper).
s4-record-wide-native144car/fullring/relocatedpointer/score/startthrottleexact
reference,field1712. Thiswasbeforenon-nativehelperextraction; forcednativepathsame.
s4-record-playbackA50076entries54draws49frac40pausefields52RNG19effects,
exit616target608oneframeovershoot. s4-record-playback-020final80entries224draws
200frac40pause52RNG72effects,exit642target640. Replaymath711+overlay9passboth.
s4-record-offdisabledpass,normalbyteidentical,branch91. Allownedjobsclosed.
s4-record-cost500fields37swaps37physics3.694FPS270.701ms19crashfields; original38
3.794FPS263.577msnocrash. Notmatchedscene/isolatedrecordcost; CPUoneupdateholds.
Source/runtime s4-record-final.slave23180bytes; math+wrap+pausebuild49466.
Remainingrecordacceptancegaps: eligibilitygap,abort,fullreset/recovery/tapecoverage.
Nexttrafficphase coasting/multiple route transitions, velocitywriters,
Phantom/attract/gameover/audio timelines andfullcrossmachine/performance/humanlaps.

Traffic long displacement and net-route walker implemented/validated. New
_traffic_phase_delta_wide D0v,D1u fullspeedeighths,D2unsignedfields,D3accel0..3,
D4signedcarry/768 =>D0longphase,D4rem; preservesD6D7/Aregs. Uses6*(n(v+u)+8delta),
longn>8cappedcaseadds6*n*delta-(6/a)*delta^2. TwoDIVU768limbs, signedtrunczero.
504exactFractioncases s4-traffic-phase-wide pass126capped,maxdelta1055728.
Live_phase_step enterswide ifn>8 ormicro!=0; carry6(a1)/128 +12(a1)/768 micro
(-5..5); bothclearunexpectedphasewrite,init/resetclearsall. Widefinalphase
normalized by_route_walk thennativeD380tailnoop; shortoldpathunchanged. _route_next
portsCF02..CFE4; _route_walk normalizesbeforeeachcross, updatespointers +/-dir*20,
clearscache19. Native geometry stillbeforephaseupdate. CodecommentTODOin-frame
turnaround path: netmovementcanhidebackwardjunctioncrossing beforeforwardtravel.
Need split at biased-displacement minimum, not merelyvelocityzero: forconstant
acceleration segment D(t)=(2*u*t+a*t*t+8*a*t)/128, minat t=-u/a-4 ifinsideframe;
minnumerator768=-(u+4a)^2*(6/a). Thenwalkminimumincrement,thenfinal-minus-minimum,
withinitialfractionincluded; retainonlyfinalcarry. Thisdesignnotimplementedyet.
Do NOT claimfulltrafficpath/step4acceptance. Integrationmodeltestsnetdisplacement.
RoutefixtureVERIFY_TRAFFIC_ROUTE_MATH copiesactualCF02..CFE4 andD380..D406bytes
intoexecutablestubs, addsRTS,flushescache. FakeA4globals providesJMPnative multiply
(notpointer). First s4-traffic-route-math stalledduewrongpointerstub; ownedPython
52227SIGINTclosedviaSession helper; excluded. Corrected s4-traffic-route-fixed
96casespassnativeinstructioncomparison,max9crossings,branch/main/altbothdirs.
LIVE s4-traffic-route-live1440 updates1428wide11coast136crossingspass;0201440
short1254fractional34crossingspass. DeliberateVERIFY_SLOW CUSTOM4=255 run
s4-traffic-route-slow144updates132wide12coast294crossings,114multi,max4pass.
s4-traffic-route-native1440before/afterrecords+poses byteidenticalreference,
92crossings,oldmodelpass. s4-traffic-route-offdisabledpass,normalbyteidentical,
branch91pass. NoFPSclaim. Allownedjobsclosed. check_traffic_wide.py --updates
--delay --profile capturesactualscalarfields plusfullrecords/companions/poses;
Fractionmodelverifiesnewcarry androutes. Phasefixturemacros504inputsbyteidentical,
routefixturemacrofullbinaryidentical. Runtime s4-traffic-route.slave23668bytes.
Next: trafficin-frame turnaround split, player/fallvelocitywriter audit,
Phantom/attract/gameover/audio timelines, fullcrossmachine andhumanacceptance.

Traffic in-frame turnaround now implemented. _traffic_turn_min takesD1oldfull,
D2fields,D3a,D4initialrem768 =>D5minimuminteger or0, preservesothers inclD6.
Onlyn>8,a>0,oldnegative,0<(-u/a-4)<n. Minimum numerator=-(u+4a)^2*(6/a)+carry;
minimumintegertrunczero, clipped<=0. Fullsigned-byte+fractionbounds quotient<8250,
soDIVU768safe. _phase_step savesminimum acrossdeltahelper, publishesfinalcarry,
then _traffic_route_motion walksinitialphase+minimum andremainingfinal-minus-min.
Originalfractioncountedonlyonce, finalremainderonly retained. Shortpathsame.
Privatephasefixtureexpandedto768inputs: nearzerou[-175,-32,-12,-9,-8,-5,-4]
andn8/9/15 plusu-175,n410. HDRPHW1(originalHDTRPHW1)finalq/rem8bytescase;
HDTRMIN1minimumlong/case. s4-traffic-turn-final-math passes768final+768minimum,
135capcoast46nonzero minima. Physicalzeronet u-175,a1,n410,v72 =>q0,min-228.
Nativeinstruction routefixture now126 cases withfinalDelta,minDelta,initialPhase
inputs. Candidate_route_motion; reference walksactualnativeCF02/D380 separately
fornegativelegandpositiveleg. s4-traffic-turn-final-route allpass,30turncases;
last6preparededgesphase100 final0 min-228 allchangependingroute/mode,3alsocurrent
segment. Earlier120-case s4-traffic-turn-routepassed beforepreparedcasesadded.
Live s4-traffic-turn-live1440updates1416wide10coast136crossings934fractionalpass;
NOactualturnarounds, soonlyprivatecorner-evidence, notlivecollisionacceptance.
Runtime s4-traffic-turn.slave23786bytes. Normalbyteidentical,branch91pass;
s4-traffic-turn-off disabledcapture terminalPASS,session64600closed.
Otherownedjobsclosed:70133(math),23274(route),83041(live)allterminalpass.
Nextvelocitywriter audit: scalar_time_velocity_add stillADD.W ofscaledlongD0
intoG9928, fall_delta updatesexpectedword andinverted/airborne ADD.W intoG990E.
Needauditfullwriters/consumers andchoosewideshadow vsbounds withoutinventedforce
caps. AlsoPhantom/attract/gameover/audio clocks, replaygap/abort/reset coverage,
fullT1drivingtape/worldstate, equalelapsedmatrix, performance/humanlaps remain.

Velocity storage/consumer audit completed as evidence, no gameplay clamp added.
NewinputonlyVERIFY_STEPINPUT_BRAKE=N requiresSTEPINPUT, conflictsRAMP. VBL and
controls helperoverridebutton4to5 at_drive_state.field>=N; onlyA0saved, Xunchanged.
Built s4-brake-audit.slave withN250, allcurrenttimegatesCPU+Record. New local
capture_velocity_audit.py --slave --fields --profile --custom1 --delay captures
V0B8A2 operands(old,rate,carry,last,n,drag/brake/gravity/drive,throttle,brake,gear,
heldbuttons),V1B8AA result; F0CCC2/CCD4(ifairborne) andF1CD86. Everywrite modeled
trunc(rate*n+carry)/8 thenwordwrap, companion checked; no guestGDBwrites.
s4-brake-original800fields66V range0..191nativeT1zerooverflows;A50061V-8..282
maxn16zerooverflow;020245V-5..281maxn4zerooverflow. BothnoFallcases.
A500brakefirstconsumedfield262 vs020250. At583 A500old27 rate-23 n12->-8;
componentsdrag1brake18gravity4drive0, settles-5. 020zero578thenrollsback-5under
samegravity4. Originalstopsfield689at0butgravity0 (differentrouteprogress). Thus
DO NOT clampnegativevelocitytozero; slopeforcephysicallyrollsback. Brakingdistance
notaccepted fromthisdifferent-scenecompare. SourceB7BE..B7DA nativecapsdragtoabsV
beforetime scaling; longintervalcanovershoot butneedsforce-awareanalysis, notblind
sumclamp. Fulltape s4-velocity-tape6000fields(noSTEPINPUT)588Vrange0..327maxn19,
20fall4..28maxn12; allwrite/carrychecksnooverflow. Allownedjobsclosed:51599,
12606,60202,94125 terminalpass. Localcaptures retainmemoryimages/logs/JSON.
Directforwardwriters59C6,B8A6,BCC8,BDA6,108D8,10A88,11804;fallCC90,CCC6,CCCC,
CD82,108C0. Existingfractionreset hooksaroundresets. Consumersstillwordincl1.5V
projectionB512andforceB832. Genericn65535counterexamplesrate40old0->327675 wraps-5;
fall5old0->40959wrapsnegative. No universalwide-state/solverpolicyimplemented.
Nohelper-onlyfixcanmakeallwordconsumerssafe; currentobservedprofilesinbounds.
Normal s4-brake-normal binaryidenticalbaseline; allcurrentflagsminusBRAKE
s4-brake-disabled-build identical s4-traffic-turn. NoFPSclaim/currentphysicschange.
Nextpresentationclocks: GAMEOVER10F66clr local-2, loop10F6A, animationphase
min(localcounter,20),10FE6increment,10FEAcmp35. Target280eligiblePALfields;
RP_WALL counterincrementsallVBLs exceptRP_PAUSED, so canreuseforpresentation
whenTIME_REPLAY_TIMING compiled. TS_ACTIVEfalseonraceexit, avoidusingTS_FIELDS
whichstops. Pause/optionshooksalreadyfreezeRP_WALL. Newtimelinegatecanrequire
REPLAY_TIMING. Retainforcednative35passes. Needdrawphasefloor(age/8),exitafter
280fieldsplusfinaldrawovershoot; overlayouts stilldefault8outsidegameplay/replay
so mustfeedgameoverintervaltoo. Phantom/attract/menu/audio/fullacceptanceremain.


GAME OVER timeline implemented and validated. New HardDrivinTimeline.s,
VERIFY_TIME_TIMELINES requires REPLAY_TIMING, installed behind CUSTOM1/SPS.
Hooks10F62/8 begin,10F6A/8 controls+phase+E49A tailcall,10FE6/10 elapsed end.
HDTMLIN1 payload16: start.l0,age.l4,overlay_last.l8,active.b12,pad3.
Uses RP_WALL pause-aware independentofTS_ACTIVE. Phase min(age>>3,35), native
renderer min20, exit firstcompletedframe>=280fields. Endclearsactive, supplies
CMP35flags and Xclear likeoriginalADDQ. SaveX ROXL/LSR, no privilegedSRread.
Overlayinterval branch/resetwired but0actualoverlaycalls inobservedGAMEOVER.
VERIFY_TIMELINE_PAUSE inputonlySPACEage>=24/resumeafter40drivefields, requires
DRIVE+TIMELINES. Newlocal check_gameover.py --profile --slave --native --pause,
freshnaturalracebootanchor10F62, phase/end/exit andpausedVBLread-onlycapture.
s4-gameover-pause-a50026frames283activefields(laststart272),40pausedwallfrozen;
s4-gameover-final-02098frames280fields(laststart278),40pausedwallfrozen;
s4-gameover-native-final35frames,nativephase0..34,280fields. Allpass/closed.
s4-gameover-final-a500earlierfinalsource also26/283 butnopausecountinstrument.
Initials4-gameover-a500checkfailedbecauseE49Aafterphasecanadvancewall; checker
nowrequiresage<=wall-start andphasefromage;finalevidenceabove. Initialruntime
alsohadSRread;finalusesROXL/LSRportableXsave. Normalfinalbyteidenticalbaseline,
s4-gameover-offallinactivepatchespass,branch94pass. Jobs70097/79993/23855/91431/
1495/18920allterminalclosed. No FPS orfullGAMEOVERworldequivalenceclaim.
NextPhantom/attract/menu/audio timelines, longstepvelocity/solverpolicy, replay
eligibility/abort/reset, fullT1tape+equalelapsedmatrix+performance+humanlaps.


Attract elapsed route/scroll/timeout committed as b0d199a.
VERIFY_TIME_ATTRACT requiresTIME_TIMELINES. NewHardDrivinAttract.s hooks10844epoch,
1084Econtrols/clock,1088Ctimeout,10898exit,D574route,D832math,D8FEadvance,
1067A/10714scroll. HDATTR01state16: start.l0,age.l4,route_age.l8,phase.w12,
active.b14. Native2setupcalls unchanged; runtimecopyD832..D8FE+RTS forinactive
math, final loadercacheflushcoverscopy. Route80fields/segment,timeout8000,
scroll200-floor(age/8),routecrossesallintermediates,clamps expiredtailto8000.
Finalexitnowconsumesoutstandingrouteinterval beforeclearactive/togglepage,
preventslostfraction atnextcycle. Earlyheadingmodelheldprevioussegmentphase9
wasWRONG: D772cachewriterresetsheadingtocurrentsegmentangle. Correctedhelper
holds currentanglephase0..32,thenblend(phase-32)/48, nativewrapcase. Gridcompare
caughtthisdespiteindependentmathmodelpassingoldassumption. Supersededcaptures
s4-attract-a500/020/pause containwrongheading, doNOTuseacceptance.
Correctcamera captures s4-attract-correct-a5001212draws8005fields40pause;
0204036draws8000fields40pause. 624sharedages fullnormalizedroute/geometry/pose/
scrollidentical; originalgrid152A500/565020poses match. finalforcednative
s4-attract-native-correct all1000frames match s4-attract-original (routepointers
normalizeactualmain/altallocations,NOTdatahunk; firstcomparatorwrongbasefixed
fromretainedmetadatawithoutnewcapture). Nativebuild still1000passes/6826fields.
Endpointfinalbuild s4-attract-endpoint.slave22472text (+headeronfile) withpause;
s4-attract-endpoint-second naturalcycle2,page255,1667draws8003fields100cross,
alt-routeexit,tailroute_age8000,phaseinitial,active0,pageflipconfirmed. Itsraw
40pausefieldsarefromcycle1, notcycle2. s4-attract-endpoint-020final4043draws8000,
40pause100cross3557frac,486nativegridmatches;epochcleanup/tailpass.
Final s4-attract-endpoint-off disabledpass. Branch104pass,normalbyteidentical.
Tools check_attract_time.py --profile --slave --native --original --pause
--delay --cycle; compare_attract_native.py names comparesretainedoriginalgrid.
VERIFY_ATTRACT_PAUSE requiresATTRACT+TIME_ATTRACT; keyboard1382 SPACEage24,
resume40rawVBLlater; rawVBLcounterinTIMEVBL independentofRP_PAUSED. HDATKEY1
raw.l0,resume.l4,phase.w8. No pose/clock/raceflag injections.
Slowstress s4-attract-slow CUSTOM4=255 timedout atstartupanchorafter300seconds;
ownedjobsclosedcleanup97070gdb/97058emulator. It didNOTreachcapture,notfailure
ofroutewalker. Retry s4-attract-slow80 session66908 TERMINALPASS/closed:93draws8032fields,
lastage7947,99drawcrossings(+tailcleanup),7frameswith2crossings,81fractional,
1altentry. Modelpass, finalrouteage8000+initialphase+active0+pageflip.
Allotherjobsclosed:55577,47225,60951,4729,60540,53389,39462,24176,29197,
45229(timeout),19012,94583,11576,27503,52127. Alljobsnowclosed; finaldocumentupdatedwithstressresult; committedb0d199a.

NextPhantom audit: live Phantom challenge has SEPARATE physics entry11664,
controls11668,sceneD960116A4,physics116B8,renderwait116BC,replay116E6. Current
elapseddispatcheronly10ED4 doesnotcoverthis, mustextendCPU/Tepoch forchallenge.
Postrace1100C isseparatepresentation/savesE924/E928andrewinds360bytes(30poses).
8A9Crecording gatedADDE,phaseE922incrementspercall,records6stepintervaltoE924,
12bytepose X0 Z2 Y4 negpitch6 negheading8 negroll10. Arena9644+3600bytes=300poses;
lastslotrewrittenoncefull(no wrap). 8B0Eplayback sameE922/6andE924+=12,
unsignedXZ,signedYwithseparatetermrounding,angle0shortwrap. Needfixed48field
recording/playback akinrecordmodule butseparateformat+eligibility+capacity.
8C84secondaryphantomE92C/E928stilltoaudit; challengeentry116EEinitializesflags.


Phantom dispatcher committed ade7164 afterfocusedvalidation. New
HardDrivinPhantom.s gateVERIFY_TIME_PHANTOMrequiresDISPATCH, CUSTOM1/SPS.
11894/6outerusesE931ratherthanADD4;copiessharedepochaccounting/reset/DSbegin.
11668/8controlsfirst/heldramps,TST979C;116BC/8pendingboundedsubstepsjump11668
insideexistingLINK,exitE931falsecancelsDS_PENDINGtoDISCARDED,otherwisefinaldraw.
116E6/8PL_P callsnewshared_time_replay_call thenUNLK/RTS;caller1189Esubmits.
_time_replay nowBSRsharedcall+nativeSubmit;nochangeinreplaysuspend/resetpolicy.
SceneCull stillrequiresADD4soPhantomdoesfullsceneeverysubstep (correctnessfirst).
Ghost/6phase andPhantompostrace/instructions NOTtimed yet; gateexperimental.

NewVERIFY_PHANTOM_ENTRY requiresDRIVE; syntheticdiagnosticbypassesqualification
at11958/8 tocallnative116EE thenreturn11994. Inputonly1151A/6suppliesSPACEto
instructions-pageemptykeypoll;1188C/8uses_verify_drive_raceinputepochreset.
Firstreference s4-phantom-reference timedoutinstructions becauseoldmenutape
missedclick; s4-phantom-off-reference obsoleteownedPython10277SIGINTcleaned
10466gdb/10457emulator. Bothterminalexcluded. Correctedfixturefixedreliability.
Tools capture_phantom.py (copyconstantinputcapture,anchor11664),
capture_phantom_window.py (500fieldpolicy,optional--delay/--expect-pause).
Finalreference s4-phantom-reference-fixed 144returnsfield1233; native-fixed144
field1251; carG98F6..9951(gearptrrelative)allmatch. PhasesE922/E92C,cursorsE924
relative9644/E928relative9640,ADDE,E931/E92D/E92Fall144match. Notfullworld/arena.
s4-phantom-ordinary-native144carstatesmatchpresentationreference field1693;
noactualreplayclaimed. s4-phantom-live-a500500fields52physics52draws52swaps,
intervals0then8..12,count1,attn512. s4-phantom-live-020196physics196draws195swaps,
interval0then2..4,count1,attn515. Theseoldinputfixturecapturesdidreachchallenge;
dispatcherunchanged, noqualifiedroute/performanceacceptanceclaim.
s4-phantom-paused-slowcorrectedfixture020CUSTOM4=12:53physics27draws,max2steps,
interval0..8,500clocktransitionspass. Pausewas96fields(VBLindices104..199),
not100: fixtureabsolute100/200thresholds, nextcontrolsconsumesfirstkeyat104.
Originalassert100failed; retainedtiming.bin independentlyrecheckedallTS/RP
increments+exactcontiguouspause, stepsconsumed/n<=8. results.jsonrecordsPASS;
checkerexpectedpauseargumentnowupperbound,clockrulesunchanged. DoNOTclaim100.
Normalbyteidentical; s4-phantom-offinactiveallpassdeclaredDRIVE/STEPINPUT/
PHANTOM_ENTRY, branch108pass. Allownedjobsclosed:68545timeout,49692done,
48955done,26625interrupted,46547done,40981done,72046done,16487checkerfailedthen
retainedanalysispass,96534done,26083done. Source+docscommittedade7164.
Nextghostfixed48fieldrecord/playback, actualPhantomexit/replay/pause/options,
postrace1100C and11278instruction/+3scroll/7passcamera, audio, remainingfull
step4acceptance. No arbitrarytimebudget nor goalcompletionclaim.


Ghost recording implemented and validated; committed as91b31cb.
VERIFY_TIME_GHOST_RECORD requires TIME_PHANTOM+TIME_RECORD. New module hooks
8A9C/6 and11858/10, fixed48 fields firstsample40, previous physics interval,
unsignedXZ/signedY/short-angle interpolation, exactright endpoint, native300slot
lastoverwrite semantics. HDGHREC1 payload24(stamp0,pointer4,age8,emitted12,
phase16.w,prevfields18.w,valid20.b), followedbyprevious/current12byteposes.
Native/inactive fallback returnsintoactual8AA2; resetclearscompanion.
WrapperXfixed: noemissionclearsX likeADDQphase; emissionX=(currentroll!=0)
likeoriginalNEG.W. No claimofallCCR/registerequivalence.
VERIFY_GHOST_RECORD_MATH privatefakeglobals with3guardedarenas; nativeactual
unpatched8A9C vs_elapsed wrapper1860calls n8, comparecursor/phase/Xeverycall,
310emissions, full3600byteequality; lastslot overwritten11times. Zero/nonzero
rollcasesincluded. Wide65535interval1365samples, fullbufferindependentmodel,
2223guardbytespass. Final evidence s4-ghost-record-math-flags(2800closed),
earliermath(30310closed)predatesXcheck. No privateposesinlivegameglobals.
Final runtime: s4-ghost-record-final-a500(33306closed)160visits,age1231,
25samples23fractional; final-020(96093closed)160/398/8/4. Entire3600buffer
before/after eachvisitmodelchecked. s4-ghost-record-long-final(20295closed)
VERIFY_SLOWCUSTOM4=64 naturalexitafter15visits,age967,20samples,7multi.
Earlier s4-ghost-record-slow(36744closed)wasMISSINGVERIFY_SLOW, NOT long-frame
evidence; nofunctionalclaimfromname. Initial02070842closedpass.
s4-ghost-record-off(28299closed)inactivepass (DRIVE,STEPINPUT,PHANTOM_ENTRY,SLOW
declared); specificallybothnewrangesPASS. Normal8392textbyteidenticalbaseline,
branch110pass. Finalruntimebuild24658text includesSLOW; privatefixture46316.
Tools check_ghost_record.py,check_ghost_record_math.py. Allownedjobsclosed.
Outstanding: duplicate/gap/reseed/resetwiderliveacceptance; ghostplayback8B0E/
8C84(opponentfinish crossing), postrace1100C rewind/cursors, menus/audio,
largeTphysicsvelocity/contact, fullnative/equalelapsed/performance/humanlaps.


Phantom opponent playback implemented/validated; committed as b93e0d6.
NewHardDrivinGhostPlayback.s, VERIFY_TIME_GHOST_PLAYBACK requiresTIME_PHANTOM;
installedbyphantom_installbeforeghostrecorder. Hooks8C84/8(nativeprologfallback
LINKA5-10,MOVEMD4/A2-A3 then8C8C) and11862/10(resetbestcursor+phase+GP).
OnlyDS_ACTIVE andADDE>=4 useselapsed; postrace/inactive/forcednativeoriginal.
HDGHPLY1state24: position0.l(nextpose),rendered4.l,laststamp8.l,expectedcursor12.l,
phase16.b,valid17.b,checks20.l. Renderprephysics atcurrentpos, checkcrossednative
8fieldpositions+current once; stopintermediatechecksif979Cset. Advancecurrent
scalarfieldsafterposefornextcall. Duplicate stampsskip, externalcursor/phase
changesreseed. PosehelperA0leftA1rightA2actorD6phase0..47; preservesA0-A3/D4-D7.
XZunsignedmean,Yseparatetermtrunc,pitchleftadjustbasedsignifabsdiff>720,
heading/rollstraighttrunc. Actualnative8DE0..8E52finishfragmentcopiedruntime
thenRTS; nativebox/messages/soundonce, cacheflushafterwrites. WrapperXclear.
Criticaltailaudit: initialgenerator5A80..5ACE writesonlyslots0..298, NOT299.
Winnercopy118E2..1193C duplicates298into299. HenceGP_END=298*48=14304andright
endpointclamps298. Capturedslot299all2020(uninitialized), initialghostnativegrid
finish10536, maxobservedangleabs1158. DoNOTholdslot299asoldinitialdraftdid.

PrivateVERIFY_GHOST_PLAYBACK_MATH: privateglobals with4nativearithjumpvectors,
6cases*48phase=288independentposes,36actualnativegridcompares. Syntheticfinish
boxbetweenposes0->48,nativecopiedfinishglobals+oneprivateaudiohit,5totalchecks.
Then65535intervalcap+heldfinalslot298withconflictingnextslotpitch; passes.
s4-ghost-play-math-final(58361closed)finalboundary; older math44064closed
andmath-events22719closedpredateonlytailfix. RuntimeA500s4-ghost-play-a500
17244closed:180visits177eligible1304fields155fractional141extrachecks.
s4-ghost-play-slow40587closed(CUSTOM4=64):15visits14eligible1047fields12frac120
extra, naturalchallengeexit, modelpass. These2capturespreboundaryfixbutpositions
belowbothbounds. Final020s4-ghost-play-final-02077908closed180/171/462/151/38;
old02081002closedhasidenticalcounts. Entireactorpose/cursor/flags modelchecked.
Native s4-ghost-play-native62944closed144stepsfield1251:carstatesmatch
s4-phantom-reference-fixed, bothrelativeghostcursors/phases andADDE/E931/E92D/
E92Fmatch144. Notwholeheap. s4-ghost-play-off51306closedpassed,newsitesbothPASS,
DRIVE/STEPINPUT/PHANTOM_ENTRY/SLOWdeclared. normal8392textbaselineidentical,
branch112pass. Runtimefinalbuild25418text; private53054text; native24846text.

FullinitialghostfinishwithexistinginputonlyBRAKE=0: finalsourcebrakebuild25306.
s4-ghost-play-finish-02063538closed4192visits4183eligible,positionafter10535,
actualfinishpose10532,3647fractional781extrachecks,exactonefinishflags event.
s4-ghost-play-finish-a50097490closed1119visits1116eligible,nextposition10542,
finishpose10533,984fractional1185extrachecks,oneevent. Everyposemodelmatched.
No realaudibility/audio-timingclaim; privatecounterprovesonecall, livecopied
nativecodeexecutesoriginalsoundpath. Allownedjobsclosed. Toolscheck_ghost_playback.py
(--until-finish),check_ghost_playback_math.py. Initialhistoryaudit.jsonunderA500.

Next: postrace1100C timing. 11032/38 savesE924/E928,rewinds360bytesclampedbase,
leavesphasesunchanged. 1111Csetsdistanceprevious1000. 11122..1114A exitsifE928>=
savedbest-12 OR E924>=savedplayer-12, then1114Aplayer8B0Eand1114Eopponent8C84.
111A0..111B4 distanceconsecutive delta*6 drivesG9602(soundpitch), needs /T.
11252submitbackto11122. 11262/68restorecursors, phasesNOTrestored. UseRP_WALL
postepoch(noTSactive); firstposeinitialphase, preservefullfractionalphasesfrom
GR_PHASE/GP_POSITION whereappropriate, nativeforcedpathunchanged. Needelapsed
postloopstopandbothposes BEFOREscene, restorecursorsemantics, derivativeaudio.
Otheropen: re-entry/pause/options; instruction/camera/+3scroll menus; audio;
largeTvelocity/solver; fullnative/equalelapsedmatrix/performance/humanlaps.

Post-race ghost elapsed presentation completed (step 4 remains open).
New HardDrivinGhostPost.s, TIME_GHOST_POST requires GHOST_RECORD+GHOST_PLAYBACK.
Hooks 1111c/6 epoch, 11122/30 both poses and end, 111a0/16 derivative pitch,
11262/0c cleanup. HDGHPOST payload44; RP_WALL epoch, full companion phase carry,
48 fields/record, duration min(saved-12-start)*4-phase, bounded at zero.
Native rewind and cursor restore preserved; terminal phases published without
reading beyond valid history. Pitch trunc(signed word delta*48/fields), first
frame native /8 and zero-field hold. Forced DISPATCH_NATIVE exercises new code.
Post controls at11232 call7c32; pause freezes RP_WALL. Overlay wiring exists but
observed post runs never invoke countdown, so no live expiry claim.
Evidence: s4-ghost-post-020 780 frames, target1367/elapsed1368; a500218,
target1352/elapsed1356; pause777 with40 paused fields at constant RP_WALL;
slow64 21frames, target1368/elapsed1375. All poses, pitch, cursors and phases pass.
Math72 derivative +384 cursor cases pass. Native-entry comparison170frames,
341 F/P/E snapshots identical across20 pose/cursor/phase/distance/pitch values.
ENTRY fixture deliberately calls1100c after48 naturally recorded samples;
not natural qualification/full-world equivalence. Natural elapsed runs reach
post-race normally. Earlier native comparison runs restarted challenge before
anchor, excluded; all owned jobs closed through Session cleanup.
Disabled retained capture passes all ranges including1189e fixture; normal build
byte-identical8392text; direct branch audit116timing ranges passes. Source and
GAME_TIME/PERFORMANCE_PLAN document scope; no full step4 acceptance claimed.
Next: instruction page11278 scrolling114b2..11522 and seven-pass camera11576..115ec;
audio audit; wide-T solver safety; full native/equal-time/performance matrix;
human A500/040 laps. Do not mark goal complete.

Instruction page timing implementation now in worktree, pending commit after
integrated runtime. New HardDrivinInstructions.s optional TIME_INSTRUCTIONS
requiresTIMELINES. Hooks114b2/6,114be/c,11572/8,1157a/22,115e4/a. HDINSTR1
payload20: start.l0,age.l4,first.b8,active.b9(1scroll/2camera),XYZwords10/12/14,
pitch16,heading18. Scroll18+floor(3*min(age,232)/8), cap105. Firstactualposeage0.
Camera n=min(age+8,56), initialXYZ-trunc(nativepredividedstep*n/8), pitch+n/8,
heading-2n. Finalduration56, skippedtailconsumed and wideXYZ refreshed onexit.
Forcednative usesnewcode ages0,8,..48; no fallback. No world/time injection.
HOLDfixture114ac/6 changesinputs only, releasebuttons,SPACEafter300inputfields.
PAUSEfixture keyhelperSPACEafter24scrollage andresume40inputfieldslater.
Runtime s4-instructions-020300scroll/19camera/56fields; a50085/5/58;
slow64 5/1/67 with finalpose+widepositionsverified; pause261/19/58 and40
pausedRP_WALLidentical. Allclosed. Native/referenceA50082scroll+7camera97
snapshots15values identical excludingwall. Allcamera modesADDE0ADD7=0attract0;
D960onlyrecordsifADDE>5 andADD7=0, no menureplayrecords. Independentclockcheck
agesRP_WALL-start with 0..1field samplinglag, retainedclock-check.json.
Disabledoldcapture s4-ghost-post-off all142rangespass; branchaudit121; normal
8392textbyteidentical. Integratedallgatesbuild27942text.
Initial s4-instructions-integrated session59054 terminalfailure beforecapture:
AF_UNIX path too long. OwnedSession cleanupclosed84781gdb/84771emu. Retry
uses shorterINSTANCE=s4-ins-full, freshoutput s4-instructions-integrated-final.

Integrated final session47098 closed PASS:300scroll/20camera/59fields, same
pose/endpoint and independentclockchecks. No active emulator jobs remain.
Instruction source+docs ready for commit. Next remaining audio/derivative audit,
large-T physics safety, full native/equal-time/performance acceptance and humanlaps.


Instruction timing committed202f858. Current audio follow-up worktree:
AUDIO_TIMING.md new verified21directnative8032 callers via audit_audio_calls.py.
VBLmusic andsample2fieldstartup unchanged; enginepitchabsoluteRPMconversion;
postdistance derivative alreadyconverted. Remaining repeatablelivecallers b166
(offroad8),b624(skid4),bc18(object9),bd02/bde2/cc84/cd52(contact7) needcadence/
eventidentityandacceptedchannel-start validation, notblanketdoneaudioaudit.
Replay.s nowpatch10c18/12 replacingperscratchframe skidflag request. Consume
rawhistoryindicesonce, includingcrossedrecordsandnaturalexittail. Clampcount-1,
ringwrap90, nativeforcedusesrealcode. HDRAUD01last.w0,pad.w2,requests.l4 reset
atbegin. PreserveincomingX/noevent, lastnativehandlerX/event; allregs saved.
Private ReplayAudioVerify module flagVERIFY_REPLAY_AUDIO_MATH requiresTIMING:
fakeeventvector/private90ring,startslot79,flagsphysicaleverythird, counts90/4/0/
90; duplicate/jumpvisits10 eachfirst3 andnative0..90. Test121visits61events,
allindex/argpairs andunusedsentinelbytespass; saves/restoresRP32+audio8.
Finalmath s4-replay-audio-math-final session25263closedpass. Earlier13256pass
predateshandlerXpreservationonly. Mathbuild50206text; no game bytescommitted.
Live s4-replay-audio-a500 session95464closed94frames/90records/exit721;
0206702closed314/90/720, bothallposesand52RNGpass. BothhistoriesNOskidflags,
zerorequests4, onecrash6atindex64; notliveaudibleskidcoverage.
Nativefieldtape10487 andglobalslow39870 terminalanchorTimeoutErrors; Session
cleanupclosedownedgdb92031/92121andemu92023/92112. Excludedevidence, no causeclaim.
Nativeconstant fixture retry22330closedpass77frames77recordsage616,52RNG,
oneevent6atindex51,zeroskidflagrecords. UsesSTEPINPUT320+TIME_REPLAYrelease.
NewVERIFY_REPLAY_SLOW requiresSLOW+REPLAY_TIMING; existingdelayonlywhenADD7
request/playbackactive, no change to defaultSLOW. Slow-only64 session48986
stillrunning at last observation, output s4-replay-audio-slow-only64,
INSTANCE=s4-ras2. Re-poll exacthandle; do not restart for observationtimeout.
Disabledoldcapture143rangespass, branch122, ordinary8392textbyteidentical.
No fullstep4complete. Nextliveaudio cadence, largeTphysics, fullmatrix/humanlaps.

Slow-only64 session48986 nowterminalPASS11frames/90records/age726,52RNG,
3effectdraws,oneevent6index66,zeroskidrecords. Allownedjobsclosed. Readyto
commitreplayaudio+audit; native/A500/020/slowruntimehistoryallnoskid, private
61knownskideventchecksarethenonzeroevidence. Do not claimliveaudibleskid.


Replayaudio committed2606472. Current liveaudio worktree ready for commit:
NewHardDrivinAudio.s flagVERIFY_TIME_AUDIO requiresREPLAY_TIMING, installedby
Time immediatelyafterreplay install. Hookb162/a wholeevent8call+argumentcleanup.
OnlyDS_ACTIVE elapsed path usesgate; inactive/forcednative exactnativecall.
HDLIVEAU payload20: wallboundary0.l,seenstep4.l,requests8.l,emitted12.l,valid16.b.
Firsteligibleimmediate; sameDSstepdedup; missingentirestep(gap>1) newepisode;
continuousdue8RP_WALLfields, preserve modulo8 remainder whenlate, coalescelong
backlogonecurrentrequest. PausesviaRPwall. Scopeoffroad8only; restaudioopen.
PrivateVERIFY_AUDIO_MATH19cases inclduplicate,gap,wrapbothclock/step,frozenwall,
largeinterval andresidual. Finalcapturetools checkmath+everygateinput/output,
allows0..2fieldreadlag. capture_audio_live.py records8ae event,760request,7b6
actualacceptedstart,832engineone-shot,physicscdb0,VBL3f2. No gamestateinjection.
Ungated1000fields: s4-audio-live-a500(74207closed)133physics,event8requests111,
starts111;020(89063closed)529physics,requests456,starts279. Otherstart event10.
Initialstrictminimumgate resetboundarytonowunder-requestedA500: old
s4-audio-cadence-a50019907closed and02098473closed superseded, NOTfinalpolicy.
FinalremainderA50084437closed:134physics,86offroadrequests/startsfields239..928;
02031757closed:525physics,90offroadrequests/starts213..925. Allmath/gatechecks
pass. actualsamplechannel2period700. Differenttrajectoriesnotfullhandlingproof.
Nativeoff40178/onnative73787closed:108steps,911fields,247observationsidentical
(eventargs/timestamps/stepindices/requests/starts/engine) exceptwrapperreturnPC.
Acceptedcomparison saved s4-audio-native-on/equivalence.json. Privatefixtureis
includedonlyinmathcaptures; finalregularnativebuildnoextras. branch123,
disabledoldcapture144ranges,normal8392byteidentical. Allownedjobsclosed.
Next sound targets b624(skid4),bc18(specialobject9),bd02/bde2/cc84/cd52(contact7)
needlivecoveragebeforechoosingcadence/eventidentity. ThenlargeTphysics/full
native/equal-time/performance/humanlaps. Step4goalremainactive.


Long-step dissipation correction validated, ready for commit. New
TIME_DISSIPATION requires SCALARS, included from Scalar after scale_word before
carry publication. n<=8 unchanged. Longstep separates effective resistance from
external drive/slope, limits oldvelocity+carry removal, uses wide signed external
product. Does not solve arbitrary external acceleration/native word consumers.
GAMEPLAY_SLOW requires SLOW+TIME, active gameplay only; menu fixture reliable.
Private326cases/130limited pass s4-dissipation-math (62744closed).
Long64 s4-dissipation-long64 (67220closed):23writes/1limited/0crossings,0..390,n79;
old long64 had6crossings,-192..390. Ordinary s4-dissipation-brake-a50017960closed:
62writes/2limited/1gradecrossing,-4..278,n16. slope3 preserved,31->-4 n12.
Moving25550733closed:9writes/4limited,0..1507,n269;1fall166 n266,0overflows.
Large speed1507 proves need broader external force/solver handling, noacceptance.
Native initial60376closed had replay-release fixture, differsoriginalstep82;
matching no-limiter control96183closed all108carstates+fieldtimestampsmatch.
Matched-input native51462closed all108originalcarstatesmatch, gearptrrelocated.
No fullworld/tape claim. Disabled56370closed144rangespass, branch123pass,
normal8392textbyteidentical. All ownedjobs now terminal/closed.
Tools capture_velocity_audit.py --dissipation, dissipation_model.py,
check_dissipation_math.py; build_replay_audio.sh includes TIME_REPLAY (input
release!) so omit this for native constant-input comparisons.
Next: full longstep force/integration safety (maxdelay huge acceleration), residual
live audio events, complete native/equalelapsed/performance matrix, human laps.


Dissipation correction committed d48ae05. Follow-up force audit/new skid work:
Expanded capture_velocity_audit.py records power(a5-14),roadE94A,turnF790,skidAF31.
audit_forward_force.py reconstructs native sqrt9564 including two-cycle rounding,
word3v and force caps. s4-force-moving25512881closed9matches; ordinary
s4-force-brake-a50081399closed62matches. Frozen-power native recurrence269fields
fromv0power44192 reaches617 vs live1345; v173power25500 gives345 vs1507. Not a
live solver or fullphysics reference. Longstep external integration stillopen.
Integrated build_step4_all.sh now accepts STEPINPUT explicitly (default fieldtape).
s4-all-current.slave built at d48ae05, includes all timing except SCENE_CULL,
no math/entry/inputrelease. 500field constantinput: off6335closed38swaps3.794,
a50049191closed37swaps3.69438physics38draws21crashfields;02011537closed148swaps
14.776149calls27crash;04068692closed240swaps23.962241calls22crash. Eachsingle
updateframe, max n22/4/3, oversized0. A500-2.63% but differentcrash exposure,
not A/B or equal-scene/full performanceacceptance. Crossmachine diagnosticJSON
under s4-all-current-a500. Docsupdated with exactscope.
Fieldtapeaudio6000fields final integrated: a50022975closed639physics322events,
02011901closed2352physics312events. No skid. Event7 CD52 4vs21, BD02 1vs3,
CC84 A5001; BCf6crash0201. No specialevent9. Needs contactidentity/cadence.

New VERIFY_STEPINPUT_STEER_AT=N requiresSTEPINPUT, holdscenteruntilfieldN then
STEPINPUT_X; bothVBL/controls, no gamestateinjection. N300 X639 elicits realskid.
Before patch s4-skid-input-a50043344closed39skidrequests/39starts over800fields;
02044553closed170/170. TIME_AUDIO nowalso hooksB620/A, independent HDSKIDAU20byte
cadence state, same_audio_due helper (19privatecases). Native/inactive exactcall,
Xpreservedonskip/handlerXoncall. Final s4-skid-cadence-a50071694closed38visits,
37requests37starts;0202435closed168visits55requests55starts; all actualgatedecisions
verifiedagainstwall+step with0..2fieldlag. capture_audio_live.py --gate-kind skid.
Raw samples channel3 period1100; no listeningclaim. Episode lengths/trajectories
differ so notequal-pathhandling. Contactevents remainseparate unpatched.
Disabled52439closed145rangespass, branch124pass, normalbyteidentical8392text.
NativeheldX639 original23933closed108steps893fields; patched80315closed108steps
925fields; compare_scalar_states all108carstatesmatch gearptrrelocated.
Unused builds s4-skid-native/original includefielddelayedinput, nevercaptured;
use heldinputs for native perstepcomparison. All ownedjobs terminal/closed.
Readycommit soundfeature+fixture+docs. Goal stillactive: fullphysicslargeT,
contactaudio/specialobject, fullnative/equalelapsed/performance matrix,humanlaps.


Live skid committed4359ede; force/timingdocs f9a8c85. Current partial-contact
sound correction ready forcommit. TIME_AUDIO alsohookCD4E/A with independent
HDCONTAU20byte state, same_audio_due helper. Onlymask3 pitch-relaxationcaller;
object/landingevent7 andevent9 untouched. Native/inactive exactcallandX.
Extended capture_audio_live.py --contact recordsCB0A everynewwheelmask and
BC14/BCFE/BDDE/CC80/CD4E caller with mask,fallv,speed,gaps4,objectpointer.
Before s4-contact-audit-02065841closed:23pitchcalls,episode524..5408calls
withmask3/fallv0. A50094703closed:4pitchcalls,firstepisode556/566.
NativeobjectBCFE repeats samepointer020at5985/5990fields velocity0; A500one.
Gated s4-contact-cadence-02020876closed andA50021076closed initially checker
failedunpairedAFTER becauseCD58 nativebranchalsoacceptsnon3masks. Retainedlogs
reanalysed bynew analyse_audio_capture.py: everybypassnon3 andAUstateunchanged,
allactualentry/returnpairsvalidated. No rerun/datafiltershortcut: explicitbranch
condition/stateasserts. 02024visits16emissions/starts14episodeentries; A5005/4/4,
3episodes. Allnewmask3episodesimmediate per contact-identity-check.json;
bypasses8/1. Both19privatecadencecasespass. Event7channel3period500.
Contactpost captures stillnativeobjectcounts0202/A5001. No listeningclaim.
Native10456closed all108carstatesmatch s4-skid-native-reference (gearrelocated).
Disabled45596closed s4-pitch-audio-off146rangespass; initial s4-contact-off
capture failedbeforeboot dueexistingdirectory, notoverwritten. Branch125pass,
normal8392textbaselinebyteidentical. Allownedjobs terminalclosed.
Next object/obstacle/landingeventidentity, specialevent9coverage; largeT nonlinear
force/solver handling; fullnative/equalelapsed/performance acceptance,humanlaps.


Partial contact audio committed a3a235d. New speed-triggered braking fixture
readyforcommit: VERIFY_STEPINPUT_BRAKE_SPEED=N requiresSTEPINPUT, excludesfield
BRAKE/RAMP, N1..32767. HDBRAKE1 latchword, VBL+controls reads nativeG9928 and
latchesbutton5 onthresholdcrossing. Clearsatfixture newrace epoch; no dynamics
injection. Build s4-speed-brake.slave28866text alltiming+STEPINPUT+BRAKE_SPEED180
+SLOW+GAMEPLAY_SLOW. Fixturesabsent normal and old nativeheld buildbyteidentical.
Tool capture_brake_distance.py new readsB662 entry/CDB0return, fields,XYZlongs,
velocity/fall,heading,throttle,buttons,brakeflag,mask,road,latch,n,consumedfields.
Stopsafter2zero-velocity physicsreturns. analyse_brake_distance.py retainsrows,
flatroadY0/Zsame/heading360/mask15/road255, zero-throttle common100 crossbounds.
Initial3analyses failedheading0 assumption; retainedstatesall360, corrected and
reanalyzed (no rerun). Initialcommon175 residualthrottle varied andexcluded;
allfinal100-to-stop sampleszerothrottle. Comparisondoesnot proveacceptance.
Allninecaptures terminal/closed:
43213 A500 firstanalysisfailthenpass;49913 020same;28686 040same;
32623 slowed4;32298 original;54779 A500fast (reanalyzedold175outputto100);
61043 030;87776 060;16063 04040. Sourcescalleds4-speed-brake-{a500,020,040,
slow4,original,fast,030,060,04040}. Originaldisabled146rangespass.
Common100distance estimates: original193.8929,A500183.975,fast184.075,
slow4188.1786,020196.5,030198.25,04025197.25,04040199.25,060199.25.
Boundsretained; A500broad27units/slow35units, notacceptancetolerance.
IMPORTANT nextrealbug: monotonicposition check foundone longunit BACKWARD near
stopwhilevelocityword1 on020field472..473 x221689->221688;030field466
221362->221361;060field472221530->221529. No negativevelocity; mask15 road255,
Y0 Z200224 heading360, throttle0. Exactrows in s4-speed-brake-a500/comparison.json.
Investigate projected fractions/Euler correction at T<1, not waive1/8worldreverse.
Need capture B500/full projected Q companions foraffectedstep or instrument
projectionhooks; do not assume a scalar velocitysign bug. Existing
HardDrivinMotion position helper uses v*T+(1-T)*(v-u)/2; inspect fullfractional
projectionpath beforedesigningfix. Theseclose-to-zero steps are reproducible.
Normal8392byteidentical, nativeheld27288byteidenticalwhennewfixtureabsent,
branch125pass. Allmeasurementdetails inGAME_TIME; PERFORMANCE_PLAN acceptance
stillopen. MainremaininglargeTsolver,collisionaudio,fullnative/equal-time/fps,
constant-throttlemetric,humandrivinglaps.


Near-stop correction final validation completed, ready to commit. Projection now
interpolates adjacent rounded native vectors at carry/8, guarded abs(v)<=21843;
outside preserves bounded old extension (extreme consumer safety still open).
Position merges integer and fractional remainders before publishing movement.
Dissipation limits short intervals too; n0 or n8 with oldcarry0 exact native.
Final math s4-projection-quant-math-final 77935 closed372pass;
s4-dissipation-all-intervals-final39466 closed326/148limitedpass.
Final integrated s4-brake-projection-final-a50045766 closed36 Xupdates;
-02030415 closed146; -slow4 6659 closed27; all independently reconstructed
combined displacements match, zero backward, zero stopped companion/projection,
held final position. Earlier merged030236/060235 supporting only preguard.
Native s4-projection-native-final32890 closed108 carstates exact against
s4-skid-native-reference, gearptrrelocated; notfullworld. Off47527 closed146
rangespass; normal8392textbyteidentical; branch125pass. All owned jobs closed.
Tracked docs updated. Still open: arbitrary longT force/storage/solver safety,
object/landing/specialobject audio, full native tape/equal-time handling and
constant-throttle/comparable performance acceptance, human A500/040 laps.


Nearstop committed d2ed019. Next constant-throttle measurement completed.
New VERIFY_STEPINPUT_HOLD_THROTTLE=N requiresSTEPINPUT,1..100,noBRAKE/BRAKESPEED/
RAMP. Latches neutralbuttons afternative throttle>=N, resetnewrace, VBL+controls;
no dynamics injected. New ignored capture_straight_motion.py and analyser.
Threshold22 all7 profiles hold22 except slow4 holds23 (overshoot, explicitlynot
equalinput). 500fields each, constantflat window280..420=2.804464s. Captures
s4-throttle22-{original,a500,fast,slow4,020,030,040,04040,060}; allterminalclosed.
A500repeat65169closed matches500VBL+37STEP observations exactly.
Worldunits/sec original173.555(stillaccelerating),A500267.597,fast268.758,
slow4268.221(throttle23),020264.578,030263.286,04025263.241,04040264.043,060263.286.
Boundsretained; notacceptancetolerance. ContactvalidateonlySTEP becauseVBLcan
see temporaryroad0duringphysics (A500396/409). Rawnotfiltered.
Forcecaptures s4-throttle-force-a50010035closed26matched;02057482closed103matched.
Same throttle22, A500223->231carry7/8 rate5 thengear2->3;020223->225carry4/8.
Aftershift drive8drag8power5940 net0 preservesdifference; beforeshiftpower8250.
Next concretephysics work: gear/force transitions withinlargeT, nofull000substeps.
Constantthrottle docs+fixture readycommit. Normal8392byteidentical; fixtureabsent
allgates29066byteidentical; disabled36275closed146pass; branches125pass;4invalid
configbuildsreject. All jobs closed incl56219(030/04040/060),76303(slow4/fast),
55507original,44215A500,52810 020,76106 040. No goalcompletionclaim.


Constantthrottle committedc56e99b. Newdrivetrainaudit complete, no livepatch.
capture_drivetrain.py forceB8A2,RPMB904,GEARBA8A,ENTRYB678 on500/020.
s4-drivetrain-a50014146closed107observations26engaged;02022757closed411obs102.
check_drivetrain.py every RPMslew/carry+gearconversionmatch,2upshiftseach.
drivetrain_model.py +audit_drivetrain_segments.py independently matchall128
wholeintervals includingpower/rate/velocity/RPM/gearcompanion,thenoffline1field
recurrence. A500 firstshift n15 v165+7/8 rpm5118+6/8->194;1field->183+6/8
shiftat2. secondn14 v223+1/8rpm5166->231+7/8;1field->225+3/8shiftat4.
020 firstn4v165+7/8rpm5006+2/8->168+3/8;1field170+6/8. secondn3v223+5/8
->225+4/8;1field225+2/8. Gearpairs G8cc4[(0,800),(7,800),(9,750),(10,600),
(10,450)]; power=floor(floor(throttle450/100)*den/num),halvedforRPMderived
wheel-speedmismatch>10 orskid. G9926=trunc(trunc(rpm*num/den)*500/140),
NOTpreviousvelocity. RPMtarget=trunc(trunc(v140/500)*den/num). Upshift>5200
after450T slew/down<2000;ratio doubledivision+nextcallcarryinvalidation.
No runtime1fieldloop chosen: costlargeT,positionintegral,manual/neutralandT1
compatibilityneeddesign. Modeldata retainedsegment-audit.json. Alljobsclosed.
TrackedGAME_TIME/PERFORMANCE_PLAN updatedreadycommit. Goalremainsactive.


Drivetrain model committed5a84035. Runtime reference nowimplemented, readycommit.
NewHardDrivinDrivetrain.s flagVERIFY_DRIVETRAIN_REFERENCE requiresMOTION/DISPATCH/
AUDIO. CUSTOM1installCDB6/8 pairengine+position, BACA/6 publishpitchonlylastinner.
EligibilityDSactive/fullmask15/auto1gear1..4/nofall/noskid/nocrash; n0/8nativepair.
Engine1fieldnativecalls, heldbrake restored, directnativeprojection helper+existing
_motion_position_add eachfield. FinalB500publisheswordpose+housekeepingonce with
fullscalarfieldsrestored; _motion_position_add skipsifDRIVEactive2. Active1inner.
HDDRIVE1 payload16: fields0.w remaining2.w brake4.w active6.w calls8.l frames12.l.
HDDTICK1 two signedrelativeoffsetsfrompayloadbase tobefore/afterbsrmotionadd,
usedbyextendedcapture_brake_distance.py. Initialabsoluteoffsetbuildrejected
relocation(noemulatorstarted,empty s4-drivetrain-fast-brake directoryleft);
finalrelativeoffsetbuildpasses. Native020PCtstunsupported fixedmovebytebefore
firstfunctionalbuild. Fullhelpertypegateexcludedfromnormalintegratedbuildscript.
Initialnaivepairperfield ref26timing36755closed32swaps3.194906FPS312.998ms vs
base26 37swaps3.694110FPS270.701ms. Finalstreamlined89867closedstill32swaps,
33physics33scene,491enginecalls,30pitchpubsoneperouter/nointermediate,active0
remaining0maxoutersteps1nmax18,nooversize/crash/replay.13.51%costdiagnostic;
notaccepted3%policy,nofullA/Bclaim. Earlierfasttiming32501closedsame32swaps.
Finaloperands74933closed341engagedmodels matchpower/rate/velocity/RPM/gear
check_drivetrain+audit_drivetrain_segments. Initial70539closed344matches.
Finalbrake42947closed484Xupdatesmatchmodels,no backward,stoppedcompanions0,
heldposition,start180common100dist196.875bounds178.125..209.375. Earliernaive
35793closed492pass(start185); notfinal. Finalnative8982closed108carstatesmatch
s4-skid-native-reference. Finaloff78599closed148rangespass; branchtoolupdated
includesnewfile127rangespass. Normal8392byteidentical. Earliernative19179closed
anddisabled38597closedalso pass butpredatestreamline. Allownedjobsclosed.
Remaining: cheaperforce/gearsegmentation (referencecosttoo high),othermodes and
largeintervals,fullhandlingcollisionacceptance,remainingaudio/fullFPSmatrix/human
laps. Goalactive; runtime referenceis diagnostic notfinalpolicy.


Drivetrain reference committed6950ca0. New VERIFY_DRIVETRAIN_SETTLED requires
REFERENCE, saves preengine scalar16+native wheel/velocity/RPM/MPH/gear/throttle
andgearrequest=28bytes. Exact postmatch allowsbulkpositionremaining-1 fields;
finalenginecallkeptforpitch. HDFIXPT1 skipfields0.l bulks4.l inputs8..35.
Statechanges never skipped; fullfieldsrestoreexisting. Allrunsclosed:
63890s4-drivetrain-settled26-timing34swaps3.394588FPS294.586574ms,34physics/scene,
331engine;21758 -counters repeatidenticalswapfields adds156skipped/14bulks,31pitch
oneperouter,remaining0. Previousunoptimized32swapscurrentbase37=>cost8.11%,
not3%acceptance.31365s4-drivetrain-settled-brake474positionupdatespass;98147
-brake-checked same, sixFIXEDsnapshots28bytesidentical54skippedfields and exact
repeatedfieldX/carry modelcheck(check_settled_capture.py). Finalstopvel/projcarry0.
50755native108carstatesmatchoriginalheld639;58416off148rangespass. Normal8392
byteidentical; referencewithoutSETTLED29642byteidentical topriorfinal26. Branch127.
Ignored capture_runtime_window nowrecordsHDFIXPT1 counters; capture_brake_distance
FIXED rows onlyatinnerHDDTICK entryn>1, nativeouterexcluded. Globalreplaceinitially
madehitskeytuple noticedandfixedbeforeexecution. No runtimeerrororadditionaljobs.
Docsupdatedreadycommit. Next optimizeCHANGINGengine state, likelysegmentswhere
integerforceinputs stayconstantwhilevelocitycarrychanges, preservingRPM/gear
events andpiecewiselinearprojection. Existing stableoptimization exactonly when
ALLengineinputsunchanged. No speculation across thresholds. Goalstillactive:full
largeT/manual/skid/contactphysics,remainingaudio,fullmatrixandhumanlapsopen.


Fractional batching validated and ready to commit. VERIFY_DRIVETRAIN_FRACTION
requiresSETTLED; allother26engineinputbytesfixed, absvelocity2..21843,
carrylinearsegmentbounds[-7,7]andnosigncrossing; preservesfinalpitchcall.
HDFRAC01 skippedfields/bulks longs +lastrate/activeinterval words.
Final26 capture34swaps35physics266engine147stablefields14bulks78fractionfields
34bulks32pitch, active0remaining0. Braking464generalXupdatesnoreverse/stop0;
fraction20bulks28fieldsrates-3,-2,-1,+3; acceleration27/47rates1,2,3;02049/60
rates1,2. Native108carstatespass/off148rangespass/branch127pass. Reviewbuild
s4-fraction-review byteidentical final26 source30142text. Normal and settled-only
outputs unchanged as previouslychecked. Allcapturejobsclosed. Analysis8160
authoritativehandle nowmissing; bothsolver-costs.json completed.
Ten-secondtraces s4-profile-current/fraction each500fields10.015944s37/34swaps.
Fractiontrace34swapfieldsmatchruntimeexactly. Fullphysics37/450.896ms vs
35/1115.935ms;engine37/57.612ms vs266/424.519ms; nativeposition37/56.444ms
vs35/17.653ms; innerposition313/305.287ms. InclusiveexcludesIRQ.
IMPORTANT fixed meanCPUcycles conversion in ignoredsolver_profile_costs.py:
headerbaseclock28375160 is4xA500CPUclock7093790; cyclesraw*unit/256, not/64.
Existingms/sharescorrect. Correctengineavg11046/11321cycles, inner6919.
Nexttargetrepeatedforceandprojectionwork, notfullscene/physicsdispatchrate.
Fullgeneralphysics/manual/skid/contact, collisionacceptance, remainingaudio,
fullmatrix/original3percentgate/humanlapsremainopen. Goalactive.


Fraction batching/cost evidence committed d5ed39b. Next gated positionoptimization
readycommit. VERIFY_DRIVETRAIN_POSITION requiresREFERENCE; onlyinnerposition
callroutesnew_drivetrain_position_add. n1 andallv/uaxeswithin+-16383 uses
combinedQ16=(9v-7u)*4096+floor((9q-7prevq)/16)+ic*512+fine thenonesplit;
othern/widevectorsfallbackgeneral. RegistersaveincludesA5integercarrypointer
(stride4), A0savedwordvectorstride2. Preservesliveprojectionupdate.
Build s4-position-combined26 text30316. Timing39258closed35swaps3.494429FPS
286.169814ms35physics/scene267engine32pitchunique/active0remaining0;control37
so5.41percentdeficitnot3acceptance. Previousfraction34.
Capture34544closed s4-position-combined26 314completeupdatesperaxis,nonzero
X304Y25Z0;33fraction66fieldsrates-2,-1,1,2,3;14stable153fieldsbothcheckpass.
Brake28083closed461axisupdatesX427Y0Z0, no backward/stoppedcarry0heldpos.
Steerinitial39799closed endedatfield500 withpendingPIN499; modelpassedall
completepairsbutchecker rejectedpartialend. Improvedcapture_brake_distance
tracksposition_pending andfinisheslastpairafterfieldlimit; nofiltering.
Initial020in39799failedbeforeboot profile020invalid(emptydirretained); correct
profilea1200-020. Nativein39799completed108carstatesallmatchheld639reference.
Final10107allclosed: steer-final356updatesperaxisX346Y0Z323;020-final473
X436Y53Z0; off148rangespass. Allthreeaxisoperandsmatchedindependentformula
check_position_axes.py; noFPSclaimsfromcaptureswhichfinishpendingpair.
Private68000microtool check_combined_micro.py uses sharedAMIGA_UNICORNlibvia
ctypes; actualhelper+time_splitextractedverbatimintoignoredmicro.s, vasmFbin.
_projection_update isstubbed, Qvaluesprovided; nofullprojectionclaim.2024signed
arithmeticcases+976fallbackcases pass, registers/stackpreserved, extremes
v/u16383guardandoutside, q114688,ic127,fine65535bothsigns. Savedmicrojson.
Normal8392byteidentical, flagabsent30142byteidenticalfractionfinal; missing
REFERENCEbuildrejects; branch127pass. Docsupdated. Allownedjobsclosed.
Nextreduceengine/force repetition/generalpolicy; fullmanual/skid/contactlargeT,
remainingaudio, fullhandling/matrix/originalFPSgate andhumanlapsstillopen.


Combinedposition committed11632c2. Next exactrootcache readycommit.
VERIFY_DRIVETRAIN_SQRT requiresREFERENCE; patchB856/6 originalJSR+ADDQsp.
Hookduplicateslonginputat12(sp)aftersavingD1/A0; native sqrt a4-7e42 resolves
tocode9564pureiterativeunsignedintegerfunction, no mutablegameinputs. Active1
onlycache; active0/fullnativebypass. Complete32bitkey+D0result; HDSQRT01
key0.lresult4.lvalid8.wpad10.whits12.lmisses16.l. Argumentcleanupmovesreturn
PCtooriginalargumentthenadds4sp/rts; capturedSPatB854beforepush==B85cafter.
Newcapture_sqrt.py initial57211failedatfirstprintf$a7unsupported; closed.
Samejobtimingcompleted35swaps3.494429FPS35physics267engine32pitchunique,
152stablefields15bulks64fractionfields31bulks, active0remaining0.
Correcteddebugger$sp61954closed: s4-sqrt26-checked266rootcalls90hits176misses;
020394calls205hits189misses. Allrootresultsexactindependentnative_sqrtmodel
andSPbalanced; hitcounts==consecutiveequalkeys. NoadditionalFPSgainclaim.
20190closed native108carstatesmatchheld639reference/off149rangespass.
Normal8392byteidentical; cacheabsent30316byteidenticalpreviousposition26;
missingREFERENCEbuildrejects; branch128pass. Final26slave30444text.
Allownedjobsclosed. Next repeatedpower/ratioevaluation ormoregeneralcheaper
engineintegration; currentdiagnosticstill5.41percentbehind37control.
Fullmanual/skid/contact/largeTphysics,remainingaudio/fullmatrix/originalFPS
andhumanlaps stillopen; cachepurefunctionreuse isnotfinishedstep4.


Rootcache committedbafe18c. New powercache validatedreadycommit.
VERIFY_DRIVETRAIN_POWER requiresREFERENCE, PL_PSS B696/42(skip36) replaces
engagedpowerconversionentireblock throughB6BC. Active1cachekeyratio(a2).l
and signedthrottlebyte; storesfullD0,intermediateD4word. Miss/native copies
bothnative stackmultiply/divide calls; slip/drag/brake/slope/RPM/gearunchanged.
HDPOWER1 ratio0.lthr4.wvalid6.wresult8.lfirst12.wpad14.whits16.lmisses20.l.
Builds power26text30648,constant30596,native29074. Alljobsclosed:
43949 power26 checked263calls252hits10miss1bypass;020396/366/29/1.
Power26timing35swaps35physics263engine32pitchunique,still3.494429FPS.
Important fixturelimitation: HOLD26actualA50029,02026; no equal-throttleclaim.
29480 samecompiledpower-constant off38swaps3.793951FPS263.577461ms38physics;
on34swaps3.394588FPS294.586574ms35physics/render394engine32pitchunique;
onefullpass/frame,nooversizedfallbacks,activeremaining0. Off0crash/replay;
on7crashfieldsatend0replay. 10.53percentFPSloss vsoriginal; 3percentrequires
>=3.680FPSor37swaps. NotisolatedarithmeticcostandnotfrozenA/Bacceptance.
Native108carstatespass; offinruntime150rangespass. 7029 fullthrottlepower
394calls361hits32miss1bypass, throttle0..100 andall4ratios;247complete
drivetrainupdates matchindependentforce/velocity/RPM/gearwith2shifts.
14289 onrepeatidenticalresults/swapfields/all501gamestates/physicsrecords.
Powercachecapturecapture_power.py readsB696/B6C0 pairedpow/first/SPchecks;
allcapturespass. Normal8392byteidentical, flagabsent30444sameasroot26;
invalidmissingREFERENCErejects; branch129pass. PERFORMANCE.md currenttable
updatedfromold15/38diagnosticto34/38 withcrash/trajectoryqualification.
Noactiveemulatorjobs. Remaininggoal unchanged: general longT/manual/skid/
contactsolvercorrectness,remainingaudio,fullnativeworldtape/equal-timehandling,
original3percentA/Bacceptance andhumanlaps. Nextpreferremaininggeneralphysics
coverage orlargercostreduction ratherthanmisreportingcontrol37asoriginal.


Powercache+freshperformance committed30c616d. Manual/neutralreference now
implementedvalidatedreadycommit. VERIFY_DRIVETRAIN_MANUAL requiresREFERENCE,
removesautomaticeligibilityguardandallowsgear0..4. Stillnocrash/skid/fall and
mask15; n0/8native. B9BA/6hook nativeREQbranchfirstinnerwhenorig==remaining,
laterinnerreturnBA8Awithoutclearing991D/95FF; active0native. Pureeventdeferral.
NewVERIFY_STEPINPUT_MANUAL requiresSTEPINPUT selectsmanualmenuX540clicks
insteadof100; emitsdecodedASCIIgear1,2,3,4,2,n,1,4,n,1oncontrolpasses
1,11,..91. HDMANIN1 passcount/indexwordsresetnewraceepoch, no gamegearwrites.
Actualmanualmode0confirmedallliveobservations; originalslavecgearhandler
alreadyclearsrequestequalcurrentgear, avoids nativeuninitializedlocalcase.
26801closed nativeoff/on108carstatesexact, field1344vs1377 (perpassfixture,
notelapsedcomparison). 24216closed manual-live850engine97neutral761later
deferred/10shifts;020359engine66neutral251deferred/10shifts.
check_manual.py independentlyRPMslew/carry+ratio+dampedmanualshift+neutralRPM
modelallpass, atmostoneshift/outer. A500controls41requestdelayedto47bycrash,
neutral51to55; notmissinginput. Allmodesremainmanualthroughoutcapture.
39079closed manual-position1400fields inner-only901updatesperaxis X847Y186
Z0nonzeropasscombinedmodel; off151rangespass. Added--inner-onlytocapture_brake
forreference-onlycoverage, nofilteringnativecrashPOUTmismatchasclaimedpass.
check_manual_micro.py actualhelperextractedFbin throughAMIGA_UNICORN:1500
branchcases380nonzeropendingrequestsdeferredunchanged; regs/stackpreserved.
Buildmanualtext30794,native29272. Normal8392byteidentical; absent30648equals
power26. Bothinvaliddependencybuildsreject; branch130pass. Alljobsclosed.
Stillopen skid/fall/partialcontact andgenerallargeT,remainingaudio,fullnative
worldtape/equal-timehandling andoriginalperformancegate/humanlaps. Current
performance34vs38constantwindowpredatesthisoptionalmanualgate. Goalactive.


Manualsupport committedd558181. Skidreference extensionreadycommit.
VERIFY_DRIVETRAIN_SKID requiresREFERENCE; removesAF31eligibilityexclusion,
but retainsmask15/fallv0/nocrash. Positiontick snapshotsoldnativevectors/Q,
thenAF31skipsintegerprojectionlikeB50C. projection_updatealreadyholdsQwhen
skid. FullB500onceatendstillspin/exit/audio; notcross-FPSexitproof.
12156closed A500800fields543axisupdates,253skidupdates308fields117scalar
velocitychangeswhile3vectors/Qheld. 85549closed020678updates359skid359fields
152scalarvelocitychanges; allpositionsmatchindependentmodel. Samejobforce
518nativeforce/scalarupdates232skid0overflow0zerocross allmodelmatch.
check_skid_projection.py MODEPIN/POUTvalidatefullmask15/fall0/heldvectors;
capture_brake nowlogsMODE forallsites. Fractionchecker usesheldqwhenskid:32
batches30skid82fieldsA500;02022batches21skid22fields; allinputsconstantand
repeatedpositionpass. Fixed4/43A500and8/16 020pass.
83352closed audio39visits39emissions uniqueserialouter, fullwallcadencepass.
Audioharnessprivate19casefixture nowoptionalwhenHDAUDMATabsent; livechecks
stillmandatory,no mathclaimforthisbuild. Runtime800fields72swaps73physics/
scene maxsteps1,529engine70pitchunique,active0remaining0, nmax18. Input
metadata via new--input-description reflectsX320untilfield300then639.
50614closed native108statesmatch s4-skid-native-reference/off151rangespass.
93754manual-skid723engine67neutral615deferred10shifts modelpass, butdidnot
logAF31. Addedskidcolumncapture_manual andreran47903closed same723+explicit
122skidupdates, all10shiftsonce; s4-manual-skid-checked authoritativecombo.
Normal8392byteidentical, flagabsent30794manualbuildbyteidentical; branch130
pass; missingREFERENCErejects. Skidref30688text, native29134, manualcombo30824.
Allownedjobsclosed. Remainingfall/partialcontact/generalcollision&largeT
handling, remainingaudio, fullnativeworld/equal-time/performance andhumanlaps.
Goalstillactive, currentoriginalconstantperformance34vs38predatesnewskidgate.


Airborne reference extension ready for commit. VERIFY_DRIVETRAIN_AIR requires
REFERENCE; removes only full-contact and zero-fall eligibility. Native CDA4 order:
steering, engine/position, surface/collision, CAB6 contact/gravity. Inner engine
and ordinary XYZ integrate first; native B500 final active2 restores full fields,
applies falling Y once, then outer CAB6 updates gravity. Crash and n0/8 unchanged.
check_fall_position_hooks.py generalized CLI name/--slave/--profile/--updates:
paired signed-wide Y model, detects mismatch resets, verifies full n and unique
outer serial; requires actual nonzero falling coverage. Baseline s4-fall-current-
variable200 passes13fall n0,4..18 (78wide), before DTserial instrumentation.
69595 closed s4-air-fall-a500200:9nonzero,7referencefall,4referencepartial,
136wide n0,6..18; s4-air-fall-020200:14referencefall n0,2..4, no partial.
13119 closed s4-air-position1600:1252axisupdates,71fall46air47partial,
63fraction/152fields and29fixed/139fields pass. Native108 car snapshots match
s4-skid-native-reference; CUSTOM1-off151 ranges pass. 54679 closed
s4-air-position-0201000:990axisupdates,127fall99air59partial,
22fraction/22fields8fixed/16fields pass. s4-air-force1124force/scalar+6gravity
writes match models; fall maxn12, no observed overflow/zero crossing.
Build air30670, native29116; absent30688 byteequals skid-reference; normal8392
byteequals s2-final-normal; branch130 passes; missingREFERENCE rejects. All
jobs terminal/owned emulators closed. Still no full collision/jump/loop/landing,
equal-time tolerance, remaining audio, full native-world tape, original FPS gate
or human-lap acceptance. Latest34vs38constant FPS diagnostic predates AIR.


Landing/penetration audio cadence ready for commit. TIME_AUDIO adds CC80/10
hook with separate HDLANDAU state. Fall velocity !=0 forces immediate event7,
otherwise _audio_due cadence; nonzero request anchors subsequent zero-fall
cadence. Hard-landing event6, gravity/position/impulses unchanged. Native bypass
original call. 71050 closed s4-air-contact-audit-a500/0202000: A50010CC80 all
fall0,020none. A500 current s4-landing-a5002000 has11visits11emissions with
onefall29, allwallclockmodelpass;161bypasses CC8A unchanged. 87029 initial
verifierfailedbecauseCC8A branchbypass; reanalysedretainedcapture afterexplicit
unchangedstatecheck passes. All11 event7 scheduler requests ch3/period500 rejected
because skid ch3/1100 started0or1fields earlier; noaudible-qualityclaim.
14334 closed s4-landing-020-slow4 hasnoactualgatevisits, coverageassertfails;
excluded, no implementationfailureclaimed. Actual68000 helper micro480cases,
400nonzerofallimmediate16suppressed,clock/stepwrap/regs/SP pass.
23237 closed nativeaudiooff/on208 observations identicalperphysicsserialand
parameters ignoringfield/caller; fields893vs925 so nottimestampidentity.
Nativecar108match s4-skid-native-reference; off152rangespass; branch131pass;
normal8392byteequal. Builds landing-reference30794,native29178text. Alljobs
terminal/ownedemulatorsclosed. Remaining object/obstacle/specialobjectaudio,
fastlive penetration suppression, listening, broadcollision/handling/equal-time,
fullworldnative-tape,originalFPSgate,humanlaps. Goal active.


Expanded native-world evidence ready to commit. No gameplay code change this turn.
87190 closed s4-landing-native-car-off captures108 off pair for existingon. Full
31952data/BSS differs at20 globalbyteaddresses only; classifiednativeclock/audio/
presentation (notmasked/strictgatefalse). 96414 closed s4-world-native-off/on,
latest s4-landing-native.slave compiledsame, CUSTOM1off/on, constantSTEPINPUT_X639.
capture_stepinputs.py --world now captures trafficcount*46,eachactor44bytes,
main/auxcount*56. Allbootpointers/counts checkedagain perphys snapshotby
compare_native_world.py,includingtrafficactor pointers. Addrsschemasmatchraw,
no normalization. External7184bytesall108equal:12trafficrecords12actors98main
11aux. Car92,zeroRNG4,replayring14220+writeptr4all108exact. All109controlsentry
inputfieldsbuttons/X/Y/keyrequests match. 893vs925fields; strictdataequal0/108.
20changedaddresses:8cda/db/e9,902d,9040/44/45,9091/92/95/99,94ba,9583,
95f0/f4,9792/93/9a/9b,addb. 94ba boolean agrees. Peraddressesnativeowners
inGAME_TIME; fullreport native-world-comparison.json retainsdifferences.
Old capture_stepinputs metadata falselyclaimedX320regardlessflags: tool now
usesgenericaccuratedescription; newworldcaptures metadataexplicitX639initial320,
buttonsentrymay0becausebeforeperpassreassertion. Retainedinputbytesunchanged.
Alljobsclosed. Nativeworld/tape requirement remainsnotcomplete: fixtureconstant,
no pointed-tovertexbuffer/pixelequality, clocksstilldiffer/latermodeeffectspossible.
Asyncquestionpending asks preservelegacyBCDdisplaysandcompareemulatedelapsed
lap/checkpointtime vsfixdisplayclockstoo; do notchangeclockswithoutanswer.
Independent contact/audio/physics/FPS acceptance remainsavailable. Goalactive.


Performance investigation after e011e58. Rejected two exact projection candidates;
no gameplay source changes retained. Patches tmp/vector-cache-rejected.patch
and cardinal-rejected.patch, built slaves retained. VECTOR two-entry cache reset
perouter matched3840actual68000cases/hits1350miss954flagslongregsstack; live
s4-vector-enabled422hits389miss but34swaps,2crashfields. Cardinal shortcut for
level pitch and four cardinal yaws matched4800actual68000cases/400fast4400fallback
including fullflags (use actual MOVE SR probe, API lazyflags falselyinitialfailed);
s4-cardinal-enabled34swaps7crashfields. Bothremoved after no measured FPSgain.
Latest uncachedallreference s4-vector-control34swaps35physics7crash. Original
s4-vector-original38swaps38physics0crash: initialharnessfailedinactiveDTserial0
uniqueness, complete501VBL retainedand reanalysed; inactivecode152rangepass,
allpitchDTstate0. capture_runtime_window nowonlyactiveCUSTOM1DTassertions.
32372exit1verifier,15072closed control/cache,32473closed cardinal. 95149closed
s4-single-constant-current (alltiming/noREFERENCE):37swaps3.694110FPS270.701176ms,
38physics/draw,21crash,maxsteps1;2.63%diagnosticloss notacceptance.
44813closed full5600field frozen tape same s4-single-tape-current.slave CUSTOM1
0/1, baseline_capture.py now--custom1 option. OffA108swap108physics0replay,
B349swap259physics90replay. OnA115swap116physics0replay, B258swap251physics7replay.
B loss26.07% literal3%gate needs339swaps. WorkloadBoff198crash675replayfields,
on195crash74replayfields; Atrajectoryend31719,200,24912 vs26542,0,25057.
Frontimages/statezst retainedboth windows; no matchedscene/costcausationclaim.
Astateendsnearstartingareaenabled; needauditnative recovery/events vsinputtape
ratherthanassumephysicsbug. Alljobsclosed. Clock-policyasyncquestionstillpending;
no clocks changed. Nextsolverwork accuracy/costtradeoff (one engine evaluation
vsfieldwise reference), full event/handling/tape/equal-time and finalFPS/humanlaps.


Traffic temporary-record safety fix ready for commit. FORCE candidate exposed
startupfault before cache/DT counters ran. 51819 terminal timeout,75876 interrupted
ownedgdb82929 then terminal,92100 ownedgdb1975 interrupted/capturedterminal;
35232 firstfault capture,18862/46535 instruction stepping closed. Native generator
5a14 makesstack46record andcallsCE70 at5a96; old _traffic_slot subtract/divu overflows
andwritesoutsidecompanions (longtrace A1 outside slowbank). Traffic slot nowchecks
below/end/native46stride, allocatedsize andnonnull; preservesX viaROXL/LSR, NULL
fallbacks speed/phase/collision reproduceoriginal, init/restartskipcompanionwrites.
Micro216boundcases3840nativepairs regsSPmemoryCCRpass (separatecodeaddressesavoid
Unicorn staleTB when switching native routines). check_patch_branches131pass.
16089candidateCUSTOM1off38swaps;38771predecessorenabled34 reproducepriorresult.
41545force+initialtrafficfix34swaps96hits302misses1crash; force experimentremoved,
patch tmp/force-cache-rejected.patch.23852finalnoFORCEtrafficfix34swaps34phys/
draw4crash,maxsteps1. Allforcecodeabsent tracked. 8462 closed nativeoff/on108world,
car/RNG/replay/12traffic/12actors/98main11aux exact, inputs109exact; globals20known
bytes differ,strictfalse;893vs929fields.3588byte generatedroute G9640 exact nonzero
atanchor startup-route-comparison.json. compare_scalar_states vsoldskidnative108pass.
trafficmodel1440updates92crossings0fractionspass.69322closed disabled152pass and
020500fields146swaps146phys/draw20crash,n0/2..5,maxsteps1,nooversized. Normal8392
byteequals s2-final-normal. Allownedjobsclosed. Final fullwindowA/B mustrerunafter
trafficfix; previous A/B predatesoutofboundsfix. Remaining generalintegration/
equal-time/contact/audio/performance/humanlaps unchanged, goalactive. Clockquestion
stillunanswered; noBCDclockchanges. Native8 andfocusedtestscope notfullacceptance.


Post-e7de60b corrected full-window measurements ready for commit. 90970closed
s4-traffic-fixed-tape-off/on (alltiming, noREFERENCE,noSTEPINPUT, nativefieldtape):
Aoff1084.313123FPS/on1154.592678FPS (+6.48%); Boff3767.219259FPS/on2584.953641FPS
(-31.38%,3%gate needs365swap/7.002681FPS). Bphysics376vs250,replayiterations0vs7;
off0crash/replayfields,on196crash[3165,3361),73replay[3361,3434). Aendoff31719,200,
24912 vs on26542,2,25057; Bdifferent stationary recoverylocations. New ignored
compare_gameplay_windows.py retainsmetrics/scope; analyse_recovery_windows.py
readsfullVBL snapshots andexplicitflags. Correctedonrecovery[905,970),[2378,2443),
[3434,3498),[4807,4871). 88140closed capture_recovery_triggers.py1250fieldsonly:
105f4offroadtimeout reachedfield904 road0velocity71 BCDclock1444deadline1434;
108b8firstat905,phase0..7 return10af8expiry969. Noabort7c78/replayexit10e92hits.
Recovery causes earlynear-startpose; not evidence of arithmeticteleport byitself.
70155closed full5600fieldoff/onrepeats; check_window_repeat.py verifiesidentical
slave/config/layout, windows/events/perfield, wholedata+BSS digestandfrontimages
bothmodesexact. Oldoff349 now376 differsacrosscompiledbuilds; exactcause not
isolated (layout/startuptiming are candidates). Newmatchedsamebuildmeasurements
supersedeoldcomparison; repeatabilityrulesoutnoise withinthispair.
Docsupdatedcurrentnumbersandcausaltrace. No gameplaycodechangedthisturn.
Alljobsclosed. Newasyncquestionpending whether addmatched-routebenchmarkalongside
originalstrictwindows orkeeporiginalonly; noresponseyet,noacceptancecriteria
changed. Priorclockpolicyquestionalsopending; noBCDchanges. Nextmeaningfulwork:
matched-workload cost attribution or integration/handling acrossCPUs; broader
contact/audio/largeT/finalFPS/humanlapsstillunproven. Goalactive.


Post-e6be32f cost attribution ready for commit. No game-code changes.33034closed
s4-b-cost-off/on 500fullPAL fields beginning4000, samebinarys4-traffic-fixed-profile
byteequals correctedtape, retainedVASMlisting. capture_solver_profile now accepts
--custom1/--first-field/--input-description and dumpsbeforebanks. Initialassumption
stationarywaswrong; fullretainedstates showmovingcars anddifferentviews; corrected
commentary/docs. Commonstationaryranges2499..3047 and4925..5600 exist butnotprofiled.
73346/57278 initialanalysesclosed. window_metrics fullslaverange nowincludesgated
helpers instead ofendingat_code_start. New complete_phase_costs.py initially used
IRQmarkerandSPreturn; auditfound prematureclosures infirmwareirqepilogue. Fixed
by mainstackcontext (contexts grouping, identifiedatphysicsentry), allphysics
closures verified10f28. window_metrics/solver_profile_costs physicscosts updated
samecontextfilter.1569/56264 reanalysisclosed; bothindependent-window-check pass:
fullpretrace data/BSS exactbaselinefield3999, all500perfieldswapsmatch81off57on,
coverage.999999831/.999999916. Meanframes123.653624 vs175.718307ms. Completeplayer
physics6.526258 vs8.844275ms;82vs56calls, nativeengine/position82vs56. Mean camera
.943/6.072,traffic6.325/11.789,sceneE49a12.810/14.844,B0D627.910/45.914,background
18.240/20.930,draw1000828.004/44.458 ms. Scene-drawpolygoncalls953/82=11.62195 vs
1394/56=24.89286. Nestedcostsnotdisjointpartition. Playerphysdelta2.318ms vsframe
52.0647ms; moregeometry/camera/trafficcost, notexcessplayerupdatefrequency. Old
IRQ-marker figures6.537/9.007 replaced bycontext-correctones. 46898closedverified
zstdtracearchives+sha+500fingerprintseach. Docsupdated; completephasechecksource
onlyignoredtools. Alljobsclosed. Nochange3%strictgateorcrossmachineacceptance.
Bothasyncquestions(benchmarkmatchedrouteaddition, BCDclockpolicy)stillpending;
noanswer/noassumptionapproval. Next work shouldaddress actualremainingelapsed
integration/contact/audio/crossmachinehandling, ormatched-workloadcosttests;
renderingrouteworkloadmakesexistingFPSlossnotapurephysicscostfigure. Goalactive.


Object collision operand audit: s4-object-impact-020/a500 terminal, sessions65699
and21819 exited0 with owned cleanup. Same corrected s4-traffic-fixed-tape build,
6200fields each,2405/607physics returns. capture_audio_live --impact records
BC62/BD40 before impulse andBCFE/BDDE/BCF2/BDD2 before sound;BC14 special too.
analyse_object_impacts.py verifies signed16 negative projection, signed16 doubling
added to longpose, clearedvelocity,45MPH eventthreshold, one paired event per site.
020threeimpulses (onehigh,twolow);A500two(onehigh,onelow); noobstacle/specialhits.
020zero-contact fields5982/5987 steps2335/2336 sameobject121388 sameposition
212336/0/200456, incomingvelocity+MPH+projection+drift allzero; bothaccepted
channel3period500. A500oneequivalentzeroevent field5994step590positionY1.
High020field3155step1290velocity186MPH51projection242/0/-139 andnativeposition
separation-484/0/278;A500field3164step316velocity196MPH54projection258/0/-140.
Bothhighrequestsacceptedchannel3period1700. This now proves repeatedzeromotion
objectoverlap instead of relyingonvelocityalreadyclearedatBCFE inolderlogs.
AUDIO_TIMING documents evidence. Nogamecodechanged. Next implement narrowly
objectevent7cadence: sameobject+zeroprojectionconsecutivevisit canuse8fieldclock;
nonzeroprojection/newobject/neweligibility immediate. Preserveothercontactstate,
forcednative/inactive behavior/X/registers;actual68000micro+livegate+native/off
checksneeded. Obstacleandspecialevent9remainuncovered, donotclaimvalidated.
Step4stillopenwithpreviousphysics/equaltime/performance/humanrequirements.


Object zero-motion audio cadence implemented in HardDrivinAudio.s BCFE/10:
HDOBJAU1 state24 bytes hasobjectpointer at20; projectedXYZ OR nonzero or changed
A3 immediately invalidatescadence; otherwiseexisting8wallfield _audio_due.
Preserveswrapperregs/SP/X, native/inactivecall; collisionimpulseunchanged.
Actual68000helper480cases440fresh10suppressed;actualwrapper32cases verifies
allpreservedregs/SP/Xnativehandlerreturn, inactiveunmodifiedstate,event7args,
nonzeroXYZindividually. Toolfixturesinitialextractemptydue/ORG/PCreldistance
errorsfixed, finalpassesobject-audio-micro.json/object-wrapper-micro.json.
Live6200fields s4-object-cadence-020:2409returns,2zerovisitsfield5983/5988,
firstemitsecondskip. A500607returnsonezeroemit. Bothonehighimpact6retained,
all3/2nativeimpulsepairsverified. GatecheckerfirstfailedAFTERBD08crashbypass;
fixedbyrequiringBCF2impact+unchangedcadencestate, retainedlogsrechecked.
Dispatchserial=completed-returncounter+1 so explicitobserved_step pairingadded.
Sessions79060/52690/60784terminal andownedcleanup. s4-object-native108carstates
matchs4-skid-native-reference;disabled153rangespass,branch132pass, normalbuild
byteequalbaseline. Final docsAUDIO_TIMING/PERFORMANCE_PLANupdated. NoFPSrerun
neededforrarecontacthook; nofullperformanceclaim. Nextuncoveredaudioobstacle/
specialevent9,livefreshlowimpact/reentry/listening; earlierfullphysics/equaltime/
largeT/originalperformance/humanlapsstillopen. Step4notcomplete.


Changing-input native-step diagnostic VERIFY_STEPINPUT_TAPE added (DRIVErequired,
STEPINPUTconflict). Existing97recordtable indexedvirtual1,9,17 percontrolsentry,
VBLholdslastinput;realfield/BCDclocksunchanged. Nootherstatewrites. Defaultnormal
andregularintegratedslavebyteequalpriorbuilds. ConditionalcounterPCrelativeafter
initialabsolute-relocationbuilderrorfixed; emptyfailedcapturedirremovedbeforeboot.
56132terminal off/on650physics+660controls, allworlddataretained. Inputsidentical,
all97records+19positionsverifiedfrompreviouspassmouseatcontrolsentry.
compare_native_world fails genuinely:car37badfirst97,RNGall650exact,trafficall650
exact,ring380bad/writepointer189bad, mainandseveralactorsfirst97,auxallmatch.
Off6256fields/on6510. First97recovery vsnative99: enabledclock1646 pastdeadline1644
atreturn96;offdeadline1603. 46268terminal directtrigger1100fields confirms105f4
nativeoffroadtimeoutofffield1003clock1605deadline1603velocity168;on1020clock1651
1644velocity175;108B8nextfield. Walltime later butphysicsserialearlieron.
This is actualremainingnativecompatibilitydependency,notpassedrequirement.
OriginalBCDpolicyunchanged; nocriteriarelaxed. Reportsretainraw/unclassifieddiffs.
Newcapture_disabled passes154ranges enabledDRIVE+STEPINPUT_TAPE;flagsrejection
checks pass. GAME_TIME/PERFORMANCE_PLAN documentfailedbroaderevidence. Allowned
jobsclosed,step4active. Next corephysics/equaltime/contactandclockdependency
stillopen, pluspreviousaudio/performance/humanlaps. Do notclaimcomplete.


Exact-throttle/crossmachine drivetrain work readyforcommit. Current hold22
buildstillA500231 vs020/040225. InitialreferenceA500overshootsactualthrottle24
(speed236..238),excludedfromequalinputcomparison. AddedVERIFY_STEPINPUT_EXACT_THROTTLE
requiresHOLD_THROTTLE;button4belowtarget,button1above,neutralonlyequalitylatched.
Onlyinputwrites, no dynamics. Normal+oldthresholdbinarybyteequalabsent;missing
prerequisitebuildfails. s4-throttle22-exact-{current,reference}-{profiles} each500
fields (all7profiles). OldanalysererroneouslypassedstationaryA500Fast;bothinitial
Fastbootsmanualneutral G9936=0/G993e=0. Strengthenedanalyse_straight_motion rejects
wrongstartmode/nonmoving asfailedreports. Twelvequalifiedoldmenucomparisons:
currentA500231 others225,referenceall6integer225 atthrottle22 fields280..420.
ReferenceA500distanceestimate725.808world bounds662..798.5, notfullaccuracyproof.
Directcapture_menu_choice s4-throttle-menu-fast confirmed6D46field999 samples
mouse320;at6F78field1000 mouse100/button1 butD0selection0;6FAAstoresmanual0.
Exactfixtureonlynowprepositionsatfield900before1000click (manual540 orauto100).
Fixedmenutrace s4-throttle-menu-fast-fixed:6D46X100field999;6F78D0word65456=-80;
6FAEauto1field1000. s4-throttle22-menu-current-fast moves/holds22speed231,
original280..420valid. reference-fast moves/speed225 butdoesnothold22until~334,
originalwindowFAIL[20,22,23]retained. Separateposthoc360..420windowvalidall14
comparisonsincludingfixedFastpair, currenttwo68000speed231/refallseven225.
Fractionalvelocityandpositionequal-timeNOTproved:referenceestimatedwallrate
252.882..267.230, sampling/publicationlatencystillunresolved. Fastpairnewmenu
buildothersoldmenu:NOTfinalsamebuildallprofilematrix. Noacceptancecriteriachanged.
Analysersavesoriginalconstant-throttle.json separatelyfromsuffix360-420files;
aggregateignoredthrottle-exact-comparison/throttle-common-late-window.json.
Sessions91643/97548/16129/92810terminal0,9076terminal1fromcoverageassertafter
ownedcleanup. Alljobsclosed. Sourcechangesonlydiagnostics+docs. Goalactive,
mainphysicsstillcurrentregular/referenceoptional, originalFPSgatefailunchanged.
Next: accurateconsumed-time/fractionalvelocitypositionmeasurement, finalbuild
matrixincludingdrawslow, referencecost/policy, nativeBCDrecoverydependency,
remainingcontact/audio/largeT/humanlaps. Do notclaimstep4complete.


Consumed-time steady-motion audit complete, docsready. 3749terminal0all14fresh
500fieldcaptures s4-clockmotion-{current,reference}-{all7profiles}, ownedcleanup.
Usesfinalcorrectedmenu s4-throttle22-menu-current/reference slaves (source9acd323).
Perpolicyall7slavebytesverifiedsame. capture_straight_motion --timing dumpsprivate
signaturestate, addsDSconsumed/serial,scalarinterval,velocitycarry/last,projectedX,
projectionQ16,positionQ16+position/128carry,gear/auto. No gamewrites.
analyse_consumed_motion fixed360..420 completedreturns checksfullflat/neutral/
actualthrottle22positiveauto, validvelocitycompanion,deltaDSconsumed==nextinterval,
serial+1,constantprojectedvector. ExactXq16=L*65536+motioncarry*512+projcarry;
assertdeltaXq16=Pq16*elapsed/8. All286pairszeroerror(143eachpolicy). Actualpalfield
142102/7093790 sec. Results consumed-motion.json andaggregateconsumed-motion-
comparison.json. CurrentvelocityeighthsA5001850,Fast1849,0201810,030+04025=1802,
04040+060=1805. Rates270.272216/270.077214/264.617170/263.252158/263.252158/
263.837163/263.837163. ReferenceA500+Fast1794(224.25),all020+1800(225exact).
Refrates262.277150vs262.862155,spread0.223048%;regular2.666667%. Notacceptance
threshold norFPS. Sameendpointobservedtime:currentA50055consumed/57observed
270.272216vs260.788980;ref04025 59/58=>262.862155vs267.394261. Timingdomain
explainsapparentconstant-vectorpositionloss,generaltrajectorynotproved.
RefA500gear2->3field200->215 interval15:216.375->225.625,throttle21->24;
thenfeedbackfield240v226thr23 ->253v224.375thr20 n13,field265v225.875thr23
->278v224.25thr20 n13;field290holds22. Ref020shift205->209n3v224.5->225
withthrottle22throughout. Residualplateaudifferenceconfoundedbyfeedbackhistory;
needmatchedpriorinput/controlledinitialconditionstofairlyisolate,notintegrator
errorassertion. Allmachinepositionsconstant-vectoraccountingexact. Nextgeneral
physics/equaltime,drawslow/finalperformance/nativeBCD/humanrequirementsstillopen.
No gamecodechanges thisturn, onlyignoredcapture/analyzers andtrackedGAME_TIME/
PERFORMANCE_PLAN docs. Alltoolcells1592/1593/1594/1595/1597/1599closed.


Controlled initial throttle validation now completes all seven standard profiles
plus delayed A500 drawing, using one identical reference slave. INITIAL_THROTTLE
requires EXACT_THROTTLE/HOLD/STEPINPUT and initializes throttle once at controls
entry only in race state2 with native acceleration eligible (GO, no crash, no
first-input reset, no termination). Neutral input thereafter. No pose, velocity,
gear or clock injection. Early fixture attempts before race/GO were rejected.
Debugger guest writes are ineffective; previous initialized-reference captures
are explicitly invalid. New capture verifies actual guest state read-only.
All762 moving returns match independent one-field drivetrain recurrence exactly
in velocity eighths, gear and fullQ16position, including both upshifts. Counts
A50021,Fast21,02089,030159,04025149,04040153,060154,slow16. Final225.375 all;
A500interval12..18,slow16..22,0203..5,others2..3. Retained slave/emulator hashes
agree across8captures. Aggregate initialized-motion-comparison.json; per-run
s4-guest-initial-reference-*/initialized-motion.json. The060 successfulrun uses
060-retry suffix after a transient shared-helper availability failure. All jobs
are terminal. Normal build and absentflag reference remain byteidentical; missing
EXACT_THROTTLE fails build. Earlier slowdraw current0/4 andref0 exactsteadyposition
passes also documented;ref4 cannotsettle22 and is excluded fromequalinput result.
Step4remainsopen: referenceoptional, regularsolver/generalhandling/braking/contact,
nativeBCD, originalFPSgate andhumanlaps unresolved. No acceptancecriteria changed.


Replay interpolation cost reduction validated. HardDrivinRecord.s shortcuts equal
unsigned/signed words and equal angles (still normalizes). Only8binarybytesadded;
no cadence/ring/physics policy changes. Actual68000 old/new fullrecord micro now
1280records/101120words includingseams,equaloutofrangeangles,packedflags,fullunsigned
weights agrees withindependent rationalmodel; regs/stack/guards checked.
Fresh500field A500 fullreference constantaccelerator traces s4-recordcost-before/
after produce34swaps each. Complete32recordtransactions252.624901->157.396540ms
(-37.695556%,95.228362ms less); interpolation54/55calls226.040523->130.728144ms.
Selfunsigned135.505280->62.099386ms. NoFPSgain;3.394588FPS294.586574ms/frame both.
Independent s4-record-equal-control-runtime/runtime allswapindices exact after
normalizing documentedindexorigins; exactslavehashchecked. Before34physics4crash,
after35physics10crash; notsameworkload nororiginal3percentacceptance.
Livecheck_recording with actualprofiledbuild supportsomittedprivatebuffers; full
A50046transactions/78emits/622fields/75fractionals/32multi(max3)/onecollisiontwo
replacements matcheveryringbyte,pose,writeptr. 020188transactions80emits633fields,
59fractionals,onecollisionreplacement passes. Largeembeddedmathfullreferencebuild
exceededBSRrange, notused; private arithmetic tested inisolatedassembledcode.
CUSTOM1off154ranges,132branchranges,normalbyteidentical. Tools/resultsignored;
GAME_TIME/PERFORMANCE_PLAN updated. All captures/analysis terminal. Remainingstep4
physics/clock/handling/braking/contact/FPS/humanlap acceptanceunchanged; goalactive.


Current-reference fractional braking matrix complete. STEPINPUT menu cursor now
prepositions for all step-input diagnostics, preserving original DRIVE fieldtape.
Old s4-brake-fine-a500-fast failed: initial gear0/auto0, stationary, no brake.
Capture now checks automaticfirstgear at anchor and fails before long capture.
Corrected samebuild s4-brake-fine-menu-reference across sevenprofiles plus slow4;
all initialmodes and retainedslave/emulatorhashes match. Captures names
s4-brake-fine-menu-{a500,a500-fast,a1200-020,a1200-030-50,a4000-040-25,a4000-040-40,
a4000-060-50,slow4}. Each176internal updates fromfractionalspeed100brackettozero:
1408 exactindependentmodel velocityword/carry,projectedvector,Q16position matches.
Model uses nativeforce(power0,road,brake),dissipation,adjacentprojectionandposition
extension; all contact/skid/Y/Z/fall/input qualifiers checked. Fixed stop holds
fullposition exactly with velocityword/carry/projectedvector zero.
Distances A500/Fast/030/04025/04040=198.949707;020199.270671;060199.053385;
slow4199.317057. Bracketpreceding eighths803/803/801/803/803/803/804/802. Derived
sixphase800..805 modelenvelope198.949707..199.731608 (width.781901), notarbitrary
acceptancetolerance. Canonical100+zero carry predicts199.474609. Rawonefieldbounds
retained. Aggregatefine-braking-comparison.json; perrunfine-braking.json.
Newlydistinguished fractionalbacktrack: sixupdates nearrest, maximum.01171875world
perupdate, total<=.03125; nativeintegerpositions neverreverse. Eulerextension
(9new-7old)/16 explainsit; earlierno-reversechecks onlyinteger. Nohandlingwaiver.
Normalbyteequalbaseline. Only sourcechange isdiagnosticmenugate; GAME_TIME andplan
updated. Allcaptures terminal. Goalstillopen: generalhandling/higher-speedbraking,
referencecost/regularsolver/nativeBCD/FPS/contact/audio/humanlaps unchanged.


Eight-field boundary diagnostic complete. VERIFY_DISPATCH_TEST_FIELDS1..65535
requires TIME_DISPATCH, conflicts DISPATCH_NATIVE; overrides d0 before dispatch
state publication without selecting native compatibility bypasses. Synthetic time,
not wall/FPS measurement. s4-boundary-7/8/9 full reference INITIAL_THROTTLE22 A500
160fields each, all owned captures terminal/closed. 7/9 each5 moving returns exact
fine independent model;8 six returns exact coarse model, all differ fine. First8
v40 vs39.625, dx60 vs59.328125;16fields v74 vs67.625. Previous eight-profile matrix
never covered n8. Normal byteequalbaseline; four invalid flag cases rejected.
GAME_TIME/PERFORMANCE_PLAN updated. Asked user handling-target preference: preserve
native-step behavior and redesign fractional integration, or accept consistent
fine handling with documented native differences. No reply yet, no criterion or
live branch changed. Core handling/performance/BCD/contact/humanlap gates remain.


Obstacle/special audio gates added while handling-target question remains pending.
TIME_AUDIO patches BDDE/10 event7, BC14/10 event9; separate24byte HDOBSAU1/HDSPEAU1.
Obstacle uses object helper preserving nonzero XYZ impulses; special uses identity
with D2=0 since native type95 no collision response. Forcednative/inactive original.
Private actual-wrapper matrix3072cases passes (initial cachedcode harness failure
corrected with fresh CPU pervariant). Native full BAEE routine relocated privately,
24 paired configurations/816calls exact carstate+crash/impulse; 1/2/8/16fields,
zero/nonzero projection,45/46MPH,obstacleflag rearmgap. Event9 repeats native17->3
at1field;zeroobstacle15->3;freshimpulses/highcrash retained. Reports
contact-wrappers-micro.json/collision-native-audio.json, tools check_contact_wrappers
and check_native_contact_audio. Syntheticprivatefixtures, notnaturalcollision or
soundstart/listening. s4-obstacle-native108carstates exactskidnative reference;
s4-obstacle-disabled156ranges passes;branch134passes;normal byteequalbaseline.
No owned captures remain live. Source+AUDIOTIMING+plan readyforcommit. No FPSclaim,
handling target/nativeBCD/FPS/generalcontact/humanlaps stillopen. Userhandling
question has no reply, no requirement changed.


Native endpoint model prerequisite audited against actual pristine B662 engine.
check_native_engine_model.py relocates native hunks/table/helpers private Unicorn;
flat fullcontact automatic no brake/skid, audioineligible.1600cases (576 structured,
1024seeded random) oldmodel184 mismatches due DIVS.W overflow in2950. Corrected
ignored drivetrain_model.convert leavesdividendlowword on signedquotientoverflow;
all1600native velocity/RPM/gear exact. native-engine-model.json retains corrected
andold mismatchexamples. Prior762controlled22 and10boundary7/9returns rechecked
exact. New samebuild s4-reference-throttle100-a500/a1200-020 240fieldcaptures:
12+57moving returns exactfine modelincluding Q16position,all3upshifts ages93/119/147,
119overflowmodeloperations each. initialized-motion analyser now uses actualinit
throttle insteadhardcoded22. throttle100-model-comparison.json retainshashmatch.
Allownedcaptures terminal. No gameplaycodechanged thisturn. Nativeendpointphase
shortcut notimplemented: algebraic n*(8-n)/128 p0=1,p1=0 Eulerextension reverses
phases5..8 toexactnativezeroendpoint (native-endpoint-extension.json). This alone
cannotfixbacktrack; target/input/gear/contact redesignrequired, no6.25Hzphysicscap
allowedperuser. Pendinghandlingquestion unanswered. Alloriginalacceptancegates
stillopen; GAME_TIME/plan documentthisevidence. Docsreadyforcommit.


Long-frame sweep implemented behind VERIFY_TIME_SWEEP (requires DISPATCH/MOTION).
Snapshot after recovery before scene; native loop-tail BD0E collects earliest
extra solid-object segment/AABB contact; BD14 rewinds and executes native response
once if no native contact won. Native8 and forcednative inactive; no full extra
scene/physics. First isolated integration failed because BB48 enters tail before
loading A3; fixed by skipping initial D4=count+1 visit. check_sweep_native32cases
pass including emptylist/nativepriority/order/ties;10000signed interpolation
cases pass. Tracked box primitive10002exact Fraction cases pass. Newmodule
HardDrivinSweep.s; snapshot/state signature HDSWEEP1. Fullbuild s4-sweep-fixed
30584text;branch136pass;normal8392byteequal s2-final-normal. Emulator
s4-sweep-native108carstates exact s4-skid-native-reference. Active
s4-sweep-live-a5001251fields116returns167tests0hits0overflow; no live crossing
evidence. Culling/turning/movingobjects/othercontacts/extremetravel remainopen,
normalnative separation retained. GAME_TIME/plan document limitedscope.
No change to outstanding integrator/BCD/performance/humanlap requirements.
CUSTOM1off s4-sweep-disabled158ranges pass. All owned captures terminal.


Post d8d0674: native-endpoint dense-output prototype under ignored harness
check_native_phase.py. Calls actual pristine engine fromphaseanchor everyframe
segment; linear velocity/RPM and endpoint displacement.32held-input partitions
and128native endpoints pass for22/100throttle and100/1fullbraking, no backward
position. BUT inputchange7fields throttle100 then1brake drops135to94 (41) when
native full8brake fromanchor100drops6. Rejected retroactiveinput; no runtimecode.
Userhandlingtarget asyncquestion re-presented, pending; default preserveoriginal.
check_sweep_rotation5000actualnative rotatedsigned cases pass. FullA500sweep
capture s4-sweep-live-full-a500 currently running; observe current process handle
rather than restart. GAME_TIME documents prototype and transform results.
Fullsweep capture now terminal:6000fields595returns251tests0hits0overflow,
intervals6..16/19 plusinitial0. No natural crossing evidence. No emulatorjobs
remain live. GAME_TIME/plan readyfor documentationcommit; coregates unchanged.


Extended sweep main-world coverage: scan active G9962/G9966 56byte mainrecords
after native scene priority, recompute relative XYZ fromworld8/10/12-camG98EA.
Conservative worldcube (sumextents+4) filters withlongendpoints beforewordrange
checks/rotation; no objectrecordwrites. SW_WORLD66 RAW68 SCANNED74 REJECTED78;
HDSWEEP1state82bytes. Auxiliary/moving/turning/extremeothercontacts stillopen.
check_sweep_world96nativecases pass (sceneabsent/stalecoords/camera/640field
6000unitcrossing/order/ties/nativepriority/inactive/types/wordedge),4addedhits;
old32+10000interpolationpass. Filter10000randomcases retains1395exactrotated
contacts. s4-sweep-world-live-a5001251fields113returns10094scans1407tests
1226rejects0hits0overflow. Forcednative108carstates exactskidreference;
disabled158ranges;branch136;normal8392byteequal. Build30836text.
500fieldprofile s4-sweep-world-profile:10.015943522s43swaps43physics;
sweep self200.153ms1.9983%, inclusiveworld137.004ms3.186ms/call,
fullphysics546.708ms;coverage99.9999916%. NotFPSdelta/gatepass.
Allownedcaptures/analysis terminal. Source/docs readyforcommit. Pendinghandling
question unanswered; no newintegrator nor waivedrequirements.


Incremental nativephase successor developed in ignored check_native_phase_incremental.py.
Native engine read-only hook atB904 samplespre-shiftRPM (Unicorn untilmiddle
instruction didnotstop; callbackworks). Updatescurrent+=(endpoint-anchor)*D/8;
forecastcurrent_before+(endpoint-anchor)*remaining/8, integrateprojectionfuture
only. Gearthreshold/conversionatphaseend usingcurrentRPM, notblendingpostgearRPM.
32heldinput combos128nativeendpoints pass;boundaryages7/8/9/16 V35/40/44.25/74,
pos52.5/60/73.875/171. Oldabruptbrake135->94fixed135->134.25.40segment570field
inputtape1440partitionchecks exact, shifts40/72/344. Transitionboundariesheldsame
allruns; notmissinginputwalltimeproof. Forceevalusesphaseanchor, generalhandling/
geareventpolicy/unscaledimpulses/reset/invalidation/manual/air/runtimecost open.
Private38byte phase-scalar.s kernel10000rationalQ16cases pass; phase-project.s
Q6forecastadjacentnativeprojection10000yawpitchcases pass, nonnegative0..21842.
Tools check_phase_scalar/project; reports phase-scalar-check/phase-project-check.
No newruntimegamecode, no releasestatechange, no waivedrequirements.
Handlingquestion stillpending, defaultoriginal. GAME_TIME/plan documentprototype.


Gated phase runtime implemented in HardDrivinPhase.s with prerequisite REFERENCE.
Phase hook B904 integrates V/RPM before automatic shift; partial phases skip gear
choice to BA8A, manual native branch retained. Frame path runs engine segments then
native B500 once. Existing motion-reset hooks invalidate phase on collisions and
recovery. Initialization now validates SS last velocity/RPM/gear before carrying
fractions. Eligibility flat grounded automatic, nonturning, velocity0..2000;
other modes retain reference fallback, whose Q3 companions lose finer phase bits.
New capture columns HDPHASE1 and analyse_phase_motion.py compare exact phase Q16
against pristine-engine Incremental oracle with flat/contact/heading qualifiers.
s4-phase-runtime-a50016 and02065 active returns pass (includes pre-throttle zero).
Same slave, but differing initial input phase: NOT crossmachine acceptance.
After stale guard fix, synthetic s4-phase-boundary-7/8/9 each10 active returns pass.
Analyser corrected initial inactive dispatcher handling; reports regenerated and
now assert failure status. Native s4-phase-native108carstates exact reference.
Normal byteequal s2-final-normal; branch137pass. CUSTOM1off159rangespass in
s4-phase-disabled/disabled-corrected.json declaring DRIVE+STEPINPUT; initial report
failed correctly because STEPINPUT enabled but not declared. All captures terminal.
Next: actual changing-input runtime, mode-transition precision and general modes,
reset coverage, sound and measured cost. Original handling/nativeBCD/FPS gates,
human laps remain open. No acceptance relaxation. Tracked GAME_TIME/plan updated.


Phase changing-input and steering work: capture_straight_motion --phase-inputs
now records INPUT atCDB6 and STEP atCDB0, native RPM/modes/trig and XYZcarry.
analyse_phase_inputs compares actual held input to pristine Incremental engine.
s4-phase-braking-a50048 and020194 complete updates exact,8/29input transitions,
no backward position, stopped by end. Qualifies flat/fullcontact; firstinterval0
setup excluded explicitly. Native published V/RPM also checked. 02014returns
have finer-than-Q3 state. Diagnostic s4-phase-transition-020(X639 STEER_AT100)
showed lost0.09375 velocity on turning-force fallback field104. X400probe ordinary
steering stays phaseactive; docs corrected former overly broad turning claim.
Removed only F790 fallback guard: native engine already evaluates its doubleddrag.
s4-phase-turn-a50010/02041 complete returns exact,4/15turnforce frames, pristine
engine + independent XYZ projected from capturedQ14trig. analyse_phase_steering
checks fullQ16XYZ, native V/RPM/gear,phase. Does not independently validate anglelaw.
Normal byteequal;branch137pass. Otherfallback transitions remainlossy/unaccepted.
Ten-second matched-source control s4-phase-cost-control34swaps/35physics1322.124ms,
401engine555.721ms; phase s4-phase-cost37swaps/37physics650.267ms,132engine193.878ms.
10.015943522seconds both;ms/swap294.586574->270.701176. Phase helpers54.560679ms;
end counters29phaseframes/74segments. Traces PRECEDE turningguard removal, notfinal
FPSgate; trajectories differ and regular/original3percentgate stillopen. Oldrecord
control binary mismatch caused fresh controlcapture ratherthan reuse. Fingerprints,
sha and verifiedzstd archives retained forboth; uncompressedtracesremoved. Alljobs
terminal. GAME_TIME/plan updated. Next generalizedsolver/manual/skid/offroad/air,
remainingtransitions/reset,fulltrajectory/BCD/originalperformance/humanlaps open.


Phase off-road support implemented: removed E94A road guard; native grass drag
now evaluated inside phase engine. _time_throttle_retention uses PH_DT only when
PH_ACTIVE, otherwise original scalar interval. First build used invalid68000
TST PC-relative, fixed to MOVE into already-savedD5; empty failedcapture removed
before retry, no emulator started for failedbuild. capture --phase-inputs now
includes throttlecarry/last. analyse_phase_offroad.py uses pristine engine with
actual road/turn flags, independent XYZ projection and mathematical r^T coefficient;
checks native V/RPM, phase Q16, throttle carry/last, exact engine/frame counts and
restored outerinterval. s4-phase-offroad-a50027returns13offroad13decays61segments
321fields intervals6..16;020114/55/37/139/327 intervals1..4;slow21/10/12/60/325
intervals10..19(delay4). All162returns exact, decaydt1..8 covered. Same normal
slave forA500/020, slow variant addsdrawgate. Native108exactreference;disabled159,
branch137pass;normalbyteequal. Alljobs terminal. NoFPSrerun, nohandlingacceptance.
Independent retention partition report phase-throttle-partition.json:100 over8
nativefields=(87,0),eightn1=(87,32636), difference0.49798583984375 throttleunits.
Existing native8truncation vsfractional retention remains explicit trajectory/
tolerance issue, not silently waived. GAME_TIME/plan updated. Next generalized
manual/skid/air/contact,remainingmodeprecision,fulltrajectories/nativeBCD/FPS/laps.


Grounded phase skid/slope extension ready: PH_SKID76 added,HDPHASE1state78bytes.
RemovedAF31andpitch/roll eligibility guards. _phase_movement_vector uses nativeheld
wordXYZ+projectionQ16 when entryPH_SKID, otherwiseforecastprojection. Published
projection remainsheld throughnative skidexit basedentryflag, notpost-exitflag.
NativeB500once withfullouterinterval handles spin/audio/exit. RemovedPH_LAST_POS
comparison/reinitialization forordinaryterraintranslations; explicit_motion_reset
andchangedV/RPM/gear stillinvalidate/reinitialize. PH_LAST_POS retaineddiagnostic.
Initial s4-phase-skid-020800fieldcapture hitflatguard atslopefield397 andcannot
validatewholecapture. Added INPUTCDB6/INTEGRATEDCDBE/STEP boundaries andHDMOTN01
spin carry/last,gradeflag,heldXYZ/Q to capture_straight_motion --phase-inputs.
analyse_phase_skid.py uses pristineengine grade/road/turn/skid flags,continuous
scalarphase, perframeactualterrain-correctedentryXYZtoCDBE independentmovement,
heldvectorchecks,fullintervalr^Tspin/native8,skidexitthresholdandthrottleloss.
Not independentterrain/contact/anglelaw orwholetrajectoryproof. Final s4-phase-
skid-slope-a50045returns21skid16slope1exit107segments548fields intervals8..16;
020187/92/70/1/235/571 intervals2..4;slow37/18/13/1/104/580 intervals12..19.
All269groundedprefixreturns exact. FIRSTairborne inputsfield561/574/595 stop
analysis explicitly; complete_capture_validated=false. Flightremainingunverified,
not skippedintoallpass. Same normalbuildA500/020; slowaddsdelay4. Native108exact,
disabled159pass,branch137pass,normalbyteequal. Alljobsclosed. Docsupdated. Nextair
andlanding support, manual,remainingfallbackprecision,terrain/contacttrajectory,
nativeBCD/fullperformance/humanlaps. Forair: native mask0 bypassesvelocitywrite,
so phase should retainfullcurrentV ratherthan quantizeanchor; gravityposition is
already outside ordinaryphaseadd and mustapplyonce withrestoredfullinterval.
