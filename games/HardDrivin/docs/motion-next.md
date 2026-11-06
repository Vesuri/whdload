# Next motion work: fractional projection/contact (remaining design)

Current committed scalar and in-progress motion modules still use constant
VERIFY_SCALAR_FIELDS. Do not confuse these arithmetic experiments with a real
variable-T dispatcher. Keep the full step-4 objective and acceptance unchanged.

Ordinary projected position b500/b578 and its arithmetic are implemented; see
open-work.md's history (git, up to b9b59016) and GAME_TIME.md for evidence. Fractional longitudinal velocity is
still absent from native projection. Remaining nonlinear handling is unverified.

Position insertion points audited from native disassembly:
- b500 LINK #-2 + TST crash (8 bytes): PL_P entry wrapper can reproduce LINK,
  capture old projected velocities G991e/9920/9922, then trampoline to b508.
  Do not use PL_PS with a native LINK unless its extra return frame is handled.
- b578..b596 (30 bytes): ordinary XYZ integration. b596 is a separate branch
  target from crash entry and MUST remain a callable instruction boundary.
- b596..b5f2: crash-drift countdown/integration; b5f2 is a separate jump target.
- b5f2..b61a: fall displacement and recomputing word pose = long pose ASR3.
  Ordinary projected Y and falling motion both affect the same long Y.

Euler correction proposal (needs independent property and game tests):
For semi-implicit projected motion, with current integer projected rate v and
previous rate u, h=n/8, preserve native-step displacement with
    displacement = v*h + (1-h)*(v-u)/2
                 = (v*(8+n) - u*(8-n))/16.
At n=8 this is exactly v; at constant rate it is v*n/8. n=0 must explicitly
produce no integrated motion, rather than half a newly changed rate. This is an
exact algebraic simplification, not yet proof that correcting steering-induced
changes in the projected vector gives the desired handling. May need separating
engine acceleration from geometric rotation; decide with evidence.
Native old projected rates are still in G991e/20/22 at b500 entry, since engine
updates longitudinal velocity but projection is done later in b500.

A 1/128-position remainder can represent this expression and a nominal explicit-
Euler gravity correction exactly. Numerator for ordinary movement:
    8*(v*(8+n) - u*(8-n)) + carry128.
Products use signed word rates times small word factors; the 32-bit numerator
fits over the complete signed-word input range. A signed ASR7 plus correction
for negative remainder gives a LONG quotient and signed remainder, avoiding
DIVS overflow at the legitimate +32768 falling-position increment.

Falling position now implements the following provisional bias correction. Its
math and live T1 operands pass; small-T contact transitions remain unverified.
For native fall velocity updated AFTER position, the bias correction
is +a*h*(1-h)/2 in long Y (fall subtracts from Y). Numerator /128 would be
    -fall_velocity*n*16 - fall_fraction_eighths*n*2
    + prior_fall_acceleration*n*(8-n) + carry128.
Using prior acceleration reflects native delayed terrain classification, but
contact transitions need investigation: do not assert it is exact for nonlinear
contact. The bias can cause sub-world-unit upward motion early in an interval;
this follows preserving native explicit Euler, and must be assessed in handling
rather than silently choosing a different integrator.

Crash drift and countdown are now implemented and verified at native T. See
GAME_TIME.md and open-work.md's history (git, up to b9b59016) for the evidence. The drift envelope
keeps the native signed-truncated sample for eight fields, splitting at sample
boundaries. This preserves exact native total displacement for all subdivisions
and avoids the negative final drift in the earlier continuous correction design.
Full small-T collision/replay/Phantom interaction acceptance remains open.

Reset policy: new race, Phantom init, replay exit, recovery and collisions clear
companions. Pure integer terrain position projection should preserve fractions,
unlike a teleport; blindly invalidating on every changed position would erase
small-step precision. Track every writer from open-work.md's direct reference
index. Barrier/hard landing do not necessarily take the same reset path as
vehicle collisions. Angle constraints similarly need same-value reset handling.

Critical lesson from this turn: cd86 AND ccd0 are shared branch targets. Never
place a six/eight-byte patch at cd82 or cccc, which would overwrite them. Final
fall hooks dispatch at ccd4, cc8a and cca0 instead. Run check_patch_branches.py
on all new ranges, then inspect indirect/alias entry points separately.
