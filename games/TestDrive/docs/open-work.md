# Test Drive open work

Phases 1–11 are complete within the authorized local scope. Current 2.0b (13.10.2026) is a
PAL emulator beta with fixed-time simulation, blitter interrupt suppression and
fractional rendering and the road-jump correction (`road-shift.md`) and analogue needle limit
(`rpm-needle.md`), steering-reversal visual correction (`steer-reversal.md`),
restored bend response and visible close traffic (`handling-collision.md`), and
continuous cornering scenery (`corner-jump.md`, including its measured cost exception),
and the opening-music sample repeat fix (`audio-repeat.md`). `phase11.md` records full release regression and verified
local regression evidence; `release-2.0b.md` describes the release archive (`make dist`).

Upstream merged this work (PR #28, Vesuri:testdrive at e3c38acc) into jotd666/whdload_slaves
master as 3e2d99b5 (13.10.2026). Upstream's `T/TestDrive` there is what this game
imported (without the game executable `TD` and the typed-in `Instructions`, which ship
from the original archive), but JOTD has not released it, so the release is made here.

1. Phase 12: transfer reusable engine/overlay findings to AmigaXDev docs and
   update its project index.
2. Deferred hardware follow-up: play-test the 2.0b release candidate on the real
   A1200/68040. Also preserve and test the isolated overlay-cache A/B pair:
   fixed 1.5b versus rebuilt repository 1.4 in `tmp/dist/overlay-cache-ab/` and its
   zip. Include a player race and native quit; record CPU/cache/MMU and WHDLoad
   settings. Public archives contain 1.3, not a shipped 1.4 baseline.
3. Release: `make dist` gives the installer archive, `TestDriveEnhanced-2.0b-20261013.lha`
   ("Test Drive Enhanced 2.0b (13.10.2026)"); publishing it is a separate step
   (the repository's `docs/releasing.md`).
4. NTSC timing is unvalidated; do not extend PAL acceptance claims to it.
5. Investigate the intermittent post-crash steering-dot displacement report.
   The supplied Countach screenshot is reproduced exactly before a crash; four
   isolated recovery tests restore the dot. No fix is established. See
   `wheel-dot.md` and `tmp/wheel-dot/comparison.json`.

Full release regression includes all five cars, same-period state comparisons,
renderer oracles/costs, three CPU presets, both available WHDLoad runtimes and
native quit. Native debugger input and read-only telemetry handle game controls;
no host accessibility is used. Original event blocking paths remain intact.

The user has confirmed the sample-repeat fix by listening to the 2.0b release
on the a1200-040 emulator with caches and enhancements enabled. Real-hardware
audio validation remains part of the deferred hardware follow-up.
