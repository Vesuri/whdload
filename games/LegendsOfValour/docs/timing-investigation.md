# Simulation timing investigation (2026-10-06, ongoing)

Rendering patches W3–W6 keep the existing clock, movement and AI behaviour.
This investigation is separate; no simulation patch is enabled.

The earlier h12:14b78 movement-step reader is more specific than previously described:
it belongs to actor initialization, not a per-frame player movement update. The single
relocated caller of h12:14b64 is h12:14c56. It adds a random value in −3..1 to the current
frame-clock step, adjusts one actor type, clamps to at least one, then stores that speed
in actor fields at offsets 28 and 30. Consequently actor speed can depend on the frame
clock at creation as well as on update frequency. An elapsed-time design must distinguish
stored actor speeds from the rendering frame's compensation value.

A candidate persistent actor table is h12:0a2f0: 56 records of 128 bytes. The code uses
A0 = h12:0de5e and signed record offset −15214, increments the offset by 128, and iterates
56 times (h12:14110 and h12:14b42). These records are distinct from the visible-object
render records currently reported by lov_state.py. The townsman's record is not identified.

Observed record fields (names remain provisional):

| Offset | Observed use |
|---|---|
| 0 | actor flags; bit 0 excludes a record from active updating |
| 2 / 4 | two position words updated by adding fields 30 / 32 |
| 6 | packed cell location derived from the updated position words |
| 10 / 11 | region and actor-type filters |
| 28 / 30 | initialized from randomized frame-clock-dependent speed |
| 32 | second motion component, initialized to zero |
| 34 / 35 | replacement position fractions when the countdown expires |
| 36 / 37 | byte countdown and reload value |
| 76 | word countdown decremented during an actor state |

h12:140e6 checks an enable byte and calls h12:14108. That update adds the motion
components at h12:141ae–141ba, decrements the byte countdown at h12:141c6, writes
positions/cell at h12:141f0–141f8, and separately decrements a state countdown at
h12:141a0. These operations have no local elapsed-field scaling. The renderer calls h12:140e6
unconditionally at h12:027da, once per rendered frame (subject to the update enable byte).
There is also a caller at h12:14a94, so direct calls must be audited before changing update
ownership. At h12:027c4 the renderer decrements a counter and calls h12:15b1a every
sixteen rendered frames. That periodic work also needs classification and timing mapping.
The actor-to-render-record mapping still needs runtime confirmation.

Next: identify the townsman by correlating these persistent records with render records,
map all callers and pauses, then compare the same elapsed-field input at different render
rates. This must include actors created at different frame-clock steps. Preserve position
fractions and collision order when evaluating elapsed-field scaling or fixed simulation
ticks. The rendering cap and beam wait remain separate constraints.
