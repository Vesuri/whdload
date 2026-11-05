# Arcade race timing (CUSTOM5, 2026-10-22)

`C5:L:Race timing:Amiga,Arcade,Arcade with Amiga qualifying time`. CUSTOM5=0 keeps the game's own
clocks, defects included. CUSTOM5=2 (2026-11-03, the user's request for easier testing) is
CUSTOM5=1 with the track's own qualifying time, 2:00 in Track.DAT, never overwritten.
CUSTOM5=1 installs `src/HardDrivinClock.s` (release flag `VERIFY_CLOCK`),
for the SPS 0126 edition and with any CUSTOM1. It is commit 16b1981 on the local branch `harddrivin-handling`, not pushed.

## The request and the decisions

The user asked for an option choosing between Amiga and arcade timing:
- in real time, not the arcade's 0.977;
- with the arcade's time limits;
- with MAME's defaults for the operator settings;
- with the arcade's other clock rules.

The arcade's own limits cannot be met on the Amiga course:
- **Distance:** in the track data, the start line is 52,791 world units from the speed route's
  checkpoint. That is about 18,500 ft at E1's 0.3504 ft per unit.
- **Flat out:** at the Amiga car's 125 MPH top speed, that alone takes 99–101 s. The arcade
  gives 96 s.
- **A bot driver:** the lap-main driver, at up to about 90 MPH, reached the checkpoint after
  181 s and finished the lap after 246 s.
- **The original:** its 1:45.99 lasts 212 real seconds, because the countdown runs at half
  speed.

So the user chose (2026-10-22):
- **Limits:** the arcade's limits doubled.
- **Revised 2026-10-23 (ARCADE_HANDLING_PLAN.md H3 round 9):** the Amiga course is the arcade's
  at 0.1791 ft per world unit, not E1's 0.3504, so start to checkpoint is about 9,500 ft, and
  arcade handling now drives it at the real scale. With CUSTOM1 = 2 the limits are the arcade's
  own; with CUSTOM1 = 0 or 1, whose car crosses the course at half its speedometer, they stay
  doubled. The installer doubles the table `_clock_limits` (the arcade's values) unless
  CUSTOM1 = 2, and for CUSTOM1 = 2 doubles the stop speed (24, 5 ft/s at the new scale).
- **Difficulty:** the options menu's difficulty picks the arcade's matching GAME DIFFICULTY
  preset.
- **Other operator settings:** MAME's defaults (CHAMP LAP QUALIFICATION EASY).
- **Per-incident limits:** off road, the grace after zero and the start countdown stay at the
  arcade's values, because they don't depend on the course length.

## Rules

| | Arcade (ARCADE_ROMS.md "Race clocks") | Amiga, CUSTOM5=0 (GAME_TIME.md) | CUSTOM5=1 |
| --- | --- | --- | --- |
| Rate | 244.14 ticks counted as 250/s: 0.977 | time left 0.500, lap 0.76–0.80 (X flag) | exactly 1.000: 2 + 2262/709379 hundredths a PAL field |
| Before the start | clock stopped, 10 s countdown | both clocks run from race set-up | time left held; the lap clock runs only for the 10 s countdown |
| Start | engine start or 10 s | button (clocks not reset) or countdown (reset) | both reset at either start |
| Starting time, cap | preset, 96 s (EASY) and capped there | 1:45.99, no cap | the preset (CUSTOM1 = 2: 1:36 / 1:30 / 1:24 for Easy/Medium/Hard; otherwise doubled, 3:12 / 3:00 / 2:48), capped there |
| Checkpoint | 32 s speed route, 29 s stunt route | 34 s less 3/5/7 s for difficulty | 32 s speed (G($9950) = 0), 29 s stunt; doubled unless CUSTOM1 = 2 |
| Finish | extended play 48/47/46 s (EASY) | 34 s less 3/5/7 s | the preset: 48/47/46, 44/44/45, 43/43/44 s; doubled unless CUSTOM1 = 2 |
| At zero | engine cut; ends below 5 ft/s or 10 s past zero; awards count against the time past zero | throttle cut, both clocks frozen, ends at speed 0; awards add to 0:00 | as the arcade: ends at |G($9928)| < 24 with CUSTOM1 = 2 (5 ft/s), < 12 otherwise (3.4 MPH on the native speedometer), or 10 s; lap clock keeps running |
| Crash to replay end | time left at 5/16, lap time excluded | clocks run through the crash countdown, stop in the replay | as the arcade |
| Off road | 2750 race ticks (11 s counted) | lap clock + 10.99, no seconds carry (shorter after SS 49) | lap clock + 11.00, carried; re-based when the finish zeroes the lap clock; the digits count the time left across the minute |
| Qualifying | lap − term ≤ champion (1:33.00), term +5 s, +0.5 s after each game without qualifying, up to +10 s, reset in the championship | lap < 2:00.00 (Track.DAT) | lap < champion + term: 1:33.00 + 5 s, +0.5 s after each game without qualifying, up to +10 s (doubled unless CUSTOM1 = 2), reset in the Phantom race; G($9794) and G($af00) are set at race set-up |
| Champion | the winner's lap from the green light | G($af00) = lap clock | the same, also kept as the new champion |
| Championship / Phantom race | no time limit | time left still runs, hidden (212 s) | no countdown |

Kept as on the Amiga:
- **Outside races** (G($add4) and G($e931) clear: attract, menus): the native clocks.
- **The Phantom race outcome:** decided by the ghost reaching the finish, not by the
  champion's time.
- **Lap 1** starts about 1,150 units past the finish line, so it is that much short. The
  arcade's lap 1 starts at its start-line marker.
- **HUD:** the Amiga's own. Time left shows M:SS and turns pen 8 below 0:20, like the
  arcade's colour change. There is no blinking lamp and no time gauge.
- **Not clock rules:** score, the crash immunity windows, the arcade's best-lap record.

## Patches (CUSTOM5=1)

| Site | Was | Now |
| --- | --- | --- |
| `$0005a` +$e | gate test, lap `$2c4c`, countdown `$2c8a` | `_clock_vbl` |
| `$07d94` +6 | button start, G($addf) = $ff | resets both clocks unless already started |
| `$083fe` +6 | track load, G($9794) = the track's 2:00 | the arcade's qualifying time, so the dash shows it before the first race set-up; CUSTOM5=2 keeps the track's |
| `$0887a` +6 | race set-up, time left = G($af12) | preset, qualifying time, champion's lap, handicap |
| `$08880`, `$0b178`, `$11878` +$e | deadline += $1099 via `$2c14` | += 11.00 s, carried |
| `$092fc` +$5e | checkpoint bonus | `_clock_award` 64/58 s |
| `$093fa` +$5e | finish bonus | `_clock_award` preset; off-road deadline re-based |
| `$104e4` +6 | countdown start, time left = G($af12) | preset |
| `$105dc` +8 | "OFF ROAD n": deadline − lap clock in plain BCD via `$2c30` | in hundredths, from 0: the carried deadline across a minute showed 1:02 − 0:59 as 43 |
| `$10edc` +$14 | time out: gate closed, end at speed 0 | end below 3.4 MPH or 10 s past zero |
| `$1196c` +6 | Phantom win, G($af00) = lap | also the new champion |

None of them overlaps another module's patch. CUSTOM5=0 installs nothing. Cost has not been
measured: `_clock_vbl` replaces two native routines of similar length once per field.

## Verification

- **`tools/check_clock.py SLAVE LISTING`** (Unicorn, the module against a Python model): all
  pass on `tmp/build/clock.slave`.
  - The BCD helpers on every clock up to 10 minutes, ±0..9 hundredths, and every conversion
    up to 99:59.99. This found two real bugs: a MOVE after ABCD/SBCD cleared C before the carry
    branch, and a pending total above 9 overflowed the digit subtract.
  - 200,000 VBL fields over random race states: before the start, running, crash, replay
    with the gate closed, pause, Phantom, time out, award in progress, outside races.
  - 50,000 hook calls.
- **`tools/check_installed_code.py`** against the previous release `i-handling.slave`, with
  CUSTOM5 unset: identical game code for CUSTOM1=0, 1 and 2.
- **FS-UAE A500 captures** (`tools/capture_clocks.py --custom5 1`, reported by
  `tools/arcade_report.py`; runs under `tmp/prof/clock-arcade/`):

| Run | Result |
| --- | --- |
| lap-slow (55 MPH), CUSTOM1=2 | time left fell 2 or 3 hundredths every field: 3:12.00 lasted 9,584 fields (exact: 9,584.7). Time out at 55 MPH; race over 10.0–10.6 s later (flush resolution 0.64 s), at 4 MPH |
| lap-main, CUSTOM1=2 | checkpoint at 0:24.50 left, +64 s; finish at 0:23.57, +96 s. Qualifying time 3:16.00. Crash at field 628 to recovery at 1569: time left at 0.628 hundredths a field (5/16: 0.626), lap clock stopped |
| lap-main, CUSTOM1=1 | three crashes, each at 0.627; the native car never reached the checkpoint. Time out at 46 MPH; over at below 3.4 MPH 1.3 s later |
| lap-offroad, CUSTOM1=2 | 11 off-road resets 11.10–11.26 s after leaving the road (11 s from arming). Time out at 54 MPH; over at 3 MPH, 3.5 s later |
| c1a-auto, CUSTOM1=0 | both clocks at real time with the original simulation |
| lap-main, CUSTOM1=2, CUSTOM5=0 | native clocks: time left 1.000 hundredth a field, lap 1.594; awards +30.99 s |

Not exercised in-game: the fixture presses a button at once, so the countdown start and the
hold before it rest on the Unicorn check. The same goes for an award reached after zero, the
cap, the Phantom race and the handicap's easing. The clocks assume a PAL machine's 313-line
fields, as the native ones do.

Build: `OUTPUT_SLAVE="$PWD/tmp/build/clock.slave" /bin/bash tools/build.sh -L
"$PWD/tmp/build/clock.lst"`; fixture slaves `build_feel.py lap-main lap-slow
lap-offroad c1a-auto`.
