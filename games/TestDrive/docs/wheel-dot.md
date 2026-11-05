# Steering-dot displacement report

Status: the reported intermittent post-crash displacement is not reproduced.
No slave source, release archive or ReadMe change is made for this report.

The latest saved screenshot, `tmp/run/default/.run/shots/FS-UAE_Full_261013-1251_00.png`,
shows the Countach. Its blue-dot bounds are (288,276)–(295,283) at 2x display
scale. An isolated guest steering tape reaches exactly those bounds before any
crash: event 0, all five lives, displayed angle -1101004/65536 degrees, sprite
vertical compensation 0. The dashboard matches at zero vertical displacement.
`tmp/wheel-dot/comparison.json` pins the screenshot and records the comparison.
`countach-before-crash/steered.png` is the pre-crash visual reference.
This establishes that the specific screenshot does not require a crash or shake;
it does not rule out a separate intermittent displacement during ordinary play.

## Native path

H4:$7EB2 caches twice the wheel angle at a4-26208 and calculates the indicator
from the car centre/radius parameters at a4-26318/-26316/-26314. H4:$2C82 feeds
sprite channel 7 through $275A; that helper subtracts a4-22462 from sprite Y.
H4:$248A invalidates the angle cache with $87654321 during display resets.
The Countach parameters are (130,196), radius 80. Its original trig arithmetic
at about -17 degrees gives the screenshot's position; the marker lies near the
inner edge of the rim. A constant vertical adjustment has not been justified.

## Retained checks

`tools/wheel_probe.py NAME a1200-040 verify 1` uses existing guest fixtures,
read-only debugger breakpoints and isolated runs. `ROAD_SHIFT_OPTIONS` selects
the recorded options. `before-recovery` (Porsche steering tape),
`straight-recovery` (Porsche straight tape), `ferrari-recovery` and
`countach-recovery` reach the native crash path, use the existing VERIFY timed
acknowledgement and sample recovery plus 200 fields. All restore the dot; both
ViewPort vertical offsets and the sprite compensation are zero in the retained
snapshots. These are not tests of manual acknowledgement. `before-crash` is a
failed early attempt at acknowledgement, not a passing recovery test.

`tools/wheel_arc_probe.py` with `arc-fixture/slave.slave` captures the pre-crash
Countach left turn. Its ignored source copy changes only the VERIFY input tape
to hold up+left, with a brief initial gear input. Do not treat its tape unit
vectors as normal VERIFY acceptance. Slaves, listings, effective machine
configurations, dumps and screenshots are under `tmp/wheel-dot/`. All diagnostic
processes were stopped by checked PID; the user's game was not altered.

Open: determine whether further steering restores the reported displacement,
and capture a live occurrence if it differs from the retained pre-crash image.
No real-hardware result is claimed.
