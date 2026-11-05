# Phase 3 gameplay coverage — complete

Run: rebuilt 1.5b, TD_SETUP=a500, WARP=0, WINDOW=front, PAL, 512 KiB
chip + 1536 KiB slow RAM. Exact slave/configuration and RAM are retained in
`tmp/phase3/`. The disposable game drawer is used. No game/slave changes.

## Verified

- `td.py serve` attached at reset (PC $F800D2) and continued the windowed
  real-speed session. The server attaches as soon as its port is available,
  within the stub's 20-second window; see `serve-front.log`.
- Startup: Accolade logo, Test Drive title, credits and car introduction screens.
- No-input attract sequence: car introductions -> moving driving demo ->
  Accolade logo transition again. `attract-04.png` shows a Testarossa cockpit,
  road and working rear-view mirror. `demo-follow-00.png` is the next logo
  transition, not a display-defect finding.
- Startup/credits trace: three fields with 30930, 33443 and 33445 instruction
  PCs. Driving trace: 6497, 10224 and 7860 instruction PCs. See pc-check.json,
  driving-pcs.json and the retained trace files.
- No obvious persistent defect in the inspected logo, title, credits, Corvette
  specification screen or driving view. This limited visual sample does not
  clear gameplay/event screens. Arbitrary screenshots can catch partial draws.

## Gameplay coverage

All five cars were selected through the native menus and driven by keyboard.
Read-only state corroborates the screenshots; no game control state was written.

| Car | Motion evidence | Result |
|---|---|---|
| Porsche 911 Turbo | `porsche-driving.png` | Acceleration, upshifts and steering; wall crash |
| Ferrari Testarossa | `ferrari-driving-verified.png`, `ferrari-state/state.json` | Player mode 0, selection 1, gear 1, speed about 51 mph |
| Lotus | `lotus-driving.png`, `lotus-state/state.json` | Player mode 0, selection 2, gear 1, speed about 46 mph |
| Lamborghini Countach | `countach-driving-verified.png`, `countach-state/state.json` | Player mode 0, selection 3, gear 1, speed about 27 mph |
| Chevrolet Corvette | `corvette-driving.png`, `corvette-state/state.json` | Player mode 0, selection 4, gear 1, speed about 49 mph |

Porsche wall crash and Space acknowledgement are verified in `porsche-crash.png`
and `porsche-recovered.png`. The cracked windshield clears and the stopped car
returns to the road. Control-R opens the restart menu. No persistent visual defect
was observed in the inspected five cockpits, selected-car screens, crash or recovery.
Earlier `countach-attempt-*` files show an unsuccessful menu attempt (still Lotus),
and the first Ferrari attempt lacked clear motion evidence; neither is used as a pass.
The `lotus-state` RPM field was originally labelled as a tentative long and is not
used as RPM evidence; subsequent snapshots correctly read the RPM word.

Radar stop is verified: `route-05/end.png` shows the pursuing patrol car;
Down braking leads to `radar-stop-01.png`, with the SPEEDING TICKET overlay and
patrol car ahead. `radar-stop-state/state.json` proves zero speed and five chances.
After waiting, `radar-after-ticket.png` and `after-ticket/state.json`
show an intact cockpit, no traffic/pursuit state and the same five chances.
No persistent visual defect was observed in the ticket or resumed cockpit. Phase 5
confirmed that ticket release is automatic; the Space press in this route was incidental.

The gas station and transition to the next stage are verified below through player controls.
Event route work uses `tools/drive_route.py`: a bounded keyboard-driving helper
reads steering/traffic telemetry and supplies native key presses, with action logs
and per-step read-only state. Unsuccessful attempts (`route-01` through `route-04`)
remain labelled as such; the patrol collision/game-over image is not a radar-stop
pass. Successful route: `route-05` reaches pursuit onset, Down braking produces
the ticket, waiting clears pursuit, `route-07` drives to the stage
end, and `gas-approach` brakes into the station. `route-06` was interrupted because
a held downshift needed release; distinct shift pulses resolved that helper issue.
Telemetry fields are diagnostic observations, not a complete phase-5 state model.

## Debugger-native input

Host accessibility and host-window input are prohibited for this work. The local
`tools/native_input.py` sends `monitor key <Amiga raw hex> <0|1>` through GDB,
then advances bounded fields with `monitor fields`. Default taps last 10 fields;
`tap:40,30` gives a longer Space press for gameplay. Long holds can repeat
menu choices, so inspect the highlighted option before confirming it. Actions and responses are
retained in `tmp/phase3/input-actions.jsonl`. This uses the emulated keyboard
queue, not writes to game control state.

The diagnostic arm64 emulator is copied from 4D Sports Driving's private build
into `tmp/phase3/native-emulator/`; its binary, resources and source patch are
pinned in `manifest/runtime-inputs.sha256`, with source revision and capabilities
in `manifest/native-input.json`. It profiles the full 24-bit address space, so
`td.py` skips the x86-specific LLDB profiler adjustment only for that pinned hash.
The original x86 path remains supported and hash-checked. This diagnostic build
is used for gameplay coverage, not a cross-build performance comparison.

The native session attached at reset. Space press/release commands were dequeued
by the emulated keyboard and a read of the slave keyboard table confirmed a held
Space. `native-session/` retains the effective machine configuration, exact slave
and emulator metadata; `serve-native.log` retains attachment evidence. The native
build's three-field driving trace contains 8939, 9456 and 9154 instruction PCs,
recorded in `native-driving-pcs.json`. Use `td.py quit` to stop only this session.
AmigaXDev `docs/open-work.md` tracks consolidating and documenting native input
helpers in the shared environment (commit `7e81306`).

## Controls from the included Instructions

Space is the slave's fire mapping: skip title, select car, acknowledge mishap.
Up/down cycles cars; Up accelerates, Down brakes; Up+Space shifts up and
Down+Space shifts down; Left/Right steers. Control-R restarts, P pauses,
D toggles shifter display, O toggles shift pattern, M/S toggle music/effects.
Observe the selected gear and actual motion to confirm held inputs arrive.

## Repeatability limit

Leaving the game untouched reaches an attract-driving loop and is sufficient
for diagnostic trace capture (`profile_demo.sh`). It is not a fixed gameplay
benchmark by itself. The phase-4 fixed window, validated marker and VERIFY RNG
fixture now provide comparable baselines; see phase4.md. The full time model is documented in phase5.md. The player/event evidence above completes phase 3 only.

## Commands and retained run

From the game directory, launch with the pinned private input build:

```sh
FSUAE="$PWD/tmp/phase3/native-emulator/fs-uae" TD_SETUP=a500 WARP=0 WINDOW=front \
  SLAVE="$PWD/tmp/build/release/TestDrive.Slave" python3 tools/td.py serve
```

Use a second terminal for commands. `python3 tools/native_input.py tap:40` sends
Space. `down:4c tap:40,30 fields:150 up:4c` accelerates and shifts; use only in a
confirmed cockpit. `down:63 tap:13 up:63 fields:700` opens the restart menu.
Brief Down then Space chooses a new car; allow the selection animation to settle.
`drive_route.py NAME STEPS SPEED END_MARGIN` runs a bounded diagnostic route,
stopping at an event, pursuit onset or within END_MARGIN road units of the end
(default 100). Use a fresh NAME. It is a state-responsive coverage helper, not a
fixed replay or benchmark. It releases its held keys on exit. Screenshots and
JSON telemetry stay beneath `tmp/phase3/NAME/`.

For no-input captures, first stop the interactive server, then run
`SLAVE="$PWD/tmp/build/release/TestDrive.Slave" tools/profile_demo.sh` from the harness
root (default timeout 300 seconds). The wrapper owns a fresh boot and shutdown,
uses warp for automated capture, detects the driving view and retains RAM, exact
slave/configuration and a diagnostic trace. The separate windowed WARP=0 runs
above establish real-speed boot/play coverage. Timing and RNG prevent treating
an arbitrary demo window as an identical benchmark.

`native-session/` pins this run; `acceptance.json` and `evidence.sha256` inventory
its reviewed evidence. The completed session is shut down with `td.py quit`.
