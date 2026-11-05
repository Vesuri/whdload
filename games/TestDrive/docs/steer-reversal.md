# Steering-reversal visual correction (2.0b)

Native keyboard captures reproduce the reported left/right pop on a1200-040,
first at 22 mph and then at about 69 mph in third gear. The native steering
handler adds an immediate lateral impulse independently of wheel position.
The old visual road bend included that impulse: alternating keys with the
wheel at zero flips the bend between approximately -0.09375 and +0.09375 degrees.

An isolated draw fixture holds lane 100 and camera fraction 32768 constant on
straight segment 30, alternating only those two visual poses. The projected
horizon moves 1.3494 pixels and affected road scanlines move up to two native
pixels (four in a doubled display). Signed sweeps at lanes 0 and 99 exclude a
large discontinuity in the sine calculation itself. The earlier camera-phase
lane-anchor fix is separate and retained.

`sim_visual_edge_capture`, installed at h4:$7F94, copies the direct-key impulse
before the wheel contribution is accumulated, then executes the displaced
wheel load and shift. `sim_bank_pose` at h4:$7FD6 removes that impulse's quarter
contribution from the visual pose before the existing coarse-rate conversion.
The wheel and road-curvature contributions remain. Native skid effects remain.
The private capture is overwritten every steering step. No vehicle motion,
grip, collisions, steering limits, speed, scoring or simulation clock is changed.
C2=0 keeps the original game path. VERIFY C5 bit 3 retains the old visual pose
for the original-arithmetic drawing oracle. No filtering or input delay is added.

## Validation

Evidence is retained under `tmp/steer-reversal/`; `tools/check_steer.py` checks
it against current sources and writes `acceptance.json`.

- `before-native`, `before-fast-native`, `candidate-fast-native`: native debugger
  throttle, gear and cursor input; no host accessibility or guest-memory writes.
  After correction the near-centred bank range falls from 0.1875 degrees to
  below 0.001 degree. These free-running keyboard captures have different input
  sampling phases; they are not bit-exact vehicle-state comparison evidence.
- `bank-sweep-before`, `bank-sweep-lane99`, `direct-pose-before`: guest draw-only
  fixtures; the last contains 66 frames with fixed camera and lane.
- `units` / `units-040`: 150 signed vectors across periods 2 and 5 exercise the
  actual production helpers against an independent integer model. 1,050 new
  assertions cover returned wheel scaling, private impulse capture, D1
  preservation, corrected pose and unchanged steering/motion/pose inputs.
  Together with existing tests, 1,718 simulation and 1,421 renderer assertions
  pass. Resolve renderer results through the installed overlay hook: this
  larger scratch slave leaves an extra unused marker copy in RAM.
- `normal-040-on` / `normal-040-off`: final normal slave startup, 1,000 attract
  fields and native keypad-* quit to AmigaDOS pass with C2 on and off. Captured
  patch bytes match all applicable declarations; optional hooks stay original
  with C2 off. The boundary/direct incoming-branch audit covers 85 ranges.
  It does not prove all indirect destinations.

Normal/VERIFY text sizes are 12,452 / 25,702 bytes. Packaged sources rebuild both
variants byte-identically; archives pass membership, extraction and LHa checks.
Current normal slave SHA-256:
`f014802ec2ba56561bbc2ffdb12c525f7c7fb7294039d284f3f4ab149c012941`.
Previous release is retained at `tmp/dist/2.0b-before-steering-fix/`. The isolated
1.4/1.5b overlay hardware pair is unchanged. Version remains 2.0b (13.10.2026).
Hardware testing is deferred, NTSC unvalidated, and nothing is pushed/published.
The user's existing emulator session is not restarted by these diagnostics.

This corrects the direct key-driven visual pop. Ordinary raster rounding,
wheel-driven movement and the real lateral response to keys remain. The native
two-line road raster branch at h4:$38DA bypasses the increment stores; it was
noticed during inspection but is unmodified and not established as the cause
of this reported steering reversal.
