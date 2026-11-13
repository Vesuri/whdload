# Bend response and invisible close traffic (2.0b)

The current release fixes two independently reproduced faults. Evidence is in
`tmp/handling-collision/`; `tools/check_handling_collision.py` checks the retained
captures against the current sources and release and writes `acceptance.json`.

## Bend response

The native h4:$7F5A load/CLR.W rounds travelled curvature down to whole units.
At the enhanced two-field period, gentle positive bends can round to zero on
every step while negative bends round away from zero. This under-applies one
turn direction and biases a route containing both directions. It is not an
input-assistance mode.

`sim_curve_step` converts travelled curvature to the native five-field scale,
applies the native whole-unit rounding, then scales back using a private carry
in the reset-owned simulation state. Five-field operation remains native with
its reset carry. Native road descriptors, steering input, grip thresholds and
collision boundaries are unchanged. This normalizes the rounding time scale;
it does not claim exact trajectories between different integration periods.

Native debugger input accelerates a Porsche to about 69 mph in third gear,
then releases all controls. With zero steering, the old enhanced build reaches
the right-wall collision at course position 448.958. Original C2-off reaches
826.279; the corrected enhanced candidate reaches 824.909. After the first
bend, in the flat section around position 285, lateral coordinates are -40.25
(old enhanced), -174.5 (original) and -177.80 (corrected). Samples are near the
same location, not an exact equal-time assertion. Retained captures:
`current-no-steering`, `original-no-steering`, `curve-candidate-no-steering`.
The candidate's bend helper and patch are the final production implementation.

## Invisible close vehicles

Native h4:$1AD4 multiplies the fixed close-car scale by road width, but omitted
SWAP before adding the integer screen centre. Thus it uses the fractional low
word as a pixel offset. For width 448 and forward scale $9160, the correct
integer product is 254; the old low word is 26624. A right-lane vehicle moves
far outside the image just as the collision range becomes active.

`traffic_near_edge` replays that multiply and screen-centre add with the missing
SWAP. The common overlay correctness patch list installs it for both C2 modes,
before the existing cache flush. Both front and rear fixed scales use this path.
No vehicle position, collision limit or collision decision changes.

`collision_capture.py` adds an isolated guest VERIFY fixture: once the player
passes position 100, it places a stationary truck 12 segments ahead using the
native traffic slot. Throttle/gears use native debugger keys; the debugger only
reads game state. The before capture shows an empty road at the actual forward
collision; the after capture shows the large truck directly ahead. Both retain
screenshots and collision registers. The traced near row moves from x=26556 to
x=186. Selected player and traffic physics state matches exactly in the retained
`near-car-before` and `near-car-after` start/collision snapshots. The separate
`near-car-before-trace` is additional projection evidence, not the exact-state
comparison arm. `near-car-after-off` confirms the corrected truck with C2 off.
`near-car-detail` retains a neighbouring-row diagnostic trace.

Grand Prix Circuit's issue was word arithmetic on full track addresses crossing
a 64 KB boundary. Test Drive uses numeric 16.16 segment positions and separate
track pointers. This reproduced fault is multiplication-word selection, not that
pointer carry bug. No exhaustive claim about all possible memory bugs is made.

## Validation and release

- 230 signed curvature/carry/period vectors and 192 traffic projection vectors
  execute the production helpers in a private guest data area. 1,726 added
  assertions pass, alongside 668 existing simulation and 1,421 renderer checks.
  Results are located through the installed overlay hook, since the larger
  scratch build leaves unused duplicate markers elsewhere in RAM.
- The direct-branch/instruction-boundary audit covers 87 declared ranges. Native
  incoming branches enter the new close-traffic hook at its start. Indirect
  destinations are not exhaustively proven.
- Final normal C2-on/off a1200-040 runs pass startup, 1,000 attract fields and
  native keypad-* quit to AmigaDOS. Captured patch bytes match the declarations.
- Packaged normal and VERIFY sources rebuild exactly; LHa integrity, membership
  and re-extraction pass. Normal/VERIFY text sizes: 12504 / 25754 bytes.

Normal slave SHA-256:
`b71fb4bd9df47de79f6ac70c2a31c98e92031283ac3c27843d9b01defb7bf4f1`.
Commits: `7786a9d` (bend response), `8103c64` (close traffic), local only.
Previous release is retained in `tmp/dist/2.0b-before-handling-collision-fix/`.
Version remains 2.0b (13.11.2026); ReadMe history is concise and player-facing.
The original hardware overlay A/B pair remains unchanged. Hardware testing stays
deferred; NTSC is unvalidated. Diagnostic sessions use separate runtime directories; the interactive release was
subsequently relaunched with the current slave.

## User-driven crash capture

The follow-up empty-road crash in the current normal release was captured with
read-only debugger breakpoints during user driving on a1200-040. It stopped at
h4:$43CE, the native engine over-rev damage event, with RPM 9761, damage threshold
9100 and damage counter 10. The event flag was still zero immediately before
that instruction. Neither a traffic nor a road-edge breakpoint triggered.
Evidence is in `tmp/handling-collision/user-crash-repro/`, including the user's
original screenshot, release hash, machine settings and debugger log. The subsequent
oncoming crash replaced the initial memory dump filenames; the initial engine
diagnosis and registers remain retained, but its full memory dump is no longer
available. The oncoming dumps are also preserved under `user-crash-repro/oncoming/`.
This diagnoses this reproduced crash only; it does not establish the cause of
every earlier report. No additional source change follows from this capture.

## Higher-speed handling follow-up

The next user-driven crash stopped at h4:$173A (oncoming traffic), at about
144.34 mph and course position 523.517, with player mode active and steering
snap disabled. It is distinct from the previous over-rev event.

`tools/handling_fast_capture.py` runs the Countach with native throttle/gears
and no steering, independently of the paused user emulator. The bounded throttle
window reaches approximately 127 mph, not the attempted 140 mph target. Current
C2-on and C2-off runs coast through the following bends to the first left-edge
collision at positions 1450.416 and 1453.485 respectively. Final speeds are
113.86 and 114.59 mph. Samples show substantial lateral drift in both arms.
The largest discrepancy at matching course positions is approximately 26 lane
units using linear interpolation of sparse samples, against total road width
896; it is not an exact state-equivalence test. Start positions differ by 3.0
segments and speeds by 0.57 mph because the same native input schedule is used.

Evidence: `tmp/handling-collision/fast-countach-on`, `fast-countach-off` and
`fast-countach-comparison.json`. C2-off retains original simulation arithmetic
plus the common correctness patches. These tests do not reproduce materially
stronger automatic road following in enhanced mode, but do not establish equal
handling for all speeds or steering inputs. The player's reported ease through
bends remains a subjective follow-up; no additional physics adjustment is made
without a demonstrated difference.
