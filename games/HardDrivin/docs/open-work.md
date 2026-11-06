# Hard Drivin': open work

Where the work stands. This file is kept current; the log it replaced (every step since
2026-10-13, with its measurements) is in git history up to b9b59016. The arcade handling's
gap table and its remaining H3c candidates are in `ARCADE_HANDLING_PLAN.md` ("H3, refined").

## Release 4.0b (06.11.2026)

Being prepared for public release (the user's decisions, 2026-11-06):
- new icons set CUSTOM1=2 and CUSTOM5=1; reports go to the repository's issues, not the
  WHDLoad bug form; the ReadMe says a 1 MB Amiga is not enough (a 512 KB + 512 KB A500
  stops at "Can't allocate ExpMem", as the original slave's sizes always required); its
  history lists only the user-visible changes since JOTD's 3.0;
- CUSTOM2 is ignored under CUSTOM1 nonzero and listed as "Frame delay (Original
  simulation)";
- accepted: CUSTOM1=2's 12% A500 cost over CUSTOM1=1 (r34 on the flat C1c ground: 67.7
  against 60.2 ms a frame), the 90 MPH slide gap (C1f 90 hold: 7.7° arcade against 10.3
  A500 / 9.5 020), the native screech and off-road sounds; manual gears with arcade handling
  work (the user's own test);
- the slave's arrays and the engine power table are allocated (`_time_mem`, internals.md):
  63,720 to 55,004 bytes. A500 `lap-main` is equivalent (5,809 against 5,814 fields, the
  same route and checkpoints); the crash replay's 34 frames are identical to 01135eeb's.
  The allocation's failure path (CUSTOM1 acting as 0) has not been exercised;
- `tools/` keeps only the tools `development.md` and the arcade plan use.

Still to check: the ReadMe's claim that joystick and keyboard keep the game's own throttle
under arcade handling comes from the code and has not been tried in play.

## Postponed

### The landing's pitch

The user (recording 13.46.48, 0:32 against the replay at 0:46): on a landing the car's pitch
turns to the ground's in one frame, where the replay turns it over several. The native
contact pass (`$CAB6`) and the springs' first ground pass (`_suspension_touch`, CUSTOM1=2)
put the car on the ground's pitch at once; the replay interpolates its records. Two attempts
were reverted:
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

### A longer draw distance

The user asked for 1.5 times the distance on faster machines, the A500 as it is, and the
road extended only ahead. Native limits:
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

### Cars behind slopes and structures

The user's drives of the 04.11 build: on the stunt road past the barn (recording 09.28.11,
2:42-2:45) cars and a sign beyond the hill showed through its slope, and in replays
(recording 10.10.09, 1:17-1:30, 1:49-2:03) the player's car was often covered by blocks of
the scenery's colour or vanished. Both are `_occ_car`/`_occ_solid` (4440c9fe), the repaint
of a solid's faces after a car.

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
- **The stunt road's raised fork** (recording 09.09.10, 0:22; class 16, type 8, radius
  2172): its faces are drawn at its far key, cars after. A fix needs a plane test of each
  car against the structure's faces and a repaint, which costs A500 time.

## Known, not changed

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
in a race). A period is one word in each event's code (`$952`, `$9C0`). The user: keep them
native.

- Arcade handling (H3 round 3): brake taps at 85 MPH in a 1 g corner can spin the car (it
  stops within 3 s), and braking in a slide yaws more than the arcade (H3a's C1f rows). Not
  rechecked since the arcade brake (H3c 1).
- The H3c (2) scratch analyses are in ignored `tmp/hdgrab/`: `replay.py` replays a 020
  run's per-field `model.bin` inputs through `handling_fx`, `allarc.py` feeds the twin the
  arcade's loads and steering from the MAME traces (`tmp/arcade/mame/c/forces/`,
  `tmp/arcade/mame/c/coast/`), `coast.py` runs `feel.c1f` over the C1h runs, `mdump.py`
  dumps `model.bin` per pass.
