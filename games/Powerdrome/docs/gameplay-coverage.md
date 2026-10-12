# Gameplay coverage

Project status: Phases A–E are complete within the agreed scope, with steady A500 handling and natural-weather validation deferred by the user. Neither deferred gate is counted as passed. Phase F is untouched.
See the [current handoff](open-work.md) for completed checks, open gates and resume priorities.

The coverage campaign is complete for the existing guarded fast planar renderer. Across
seven selected twin captures, **30,623 completed staged scenes** passed with zero pixel,
register/CCR, scratch or guard mismatches. Copied fast raster code remained unchanged.
No production renderer change was necessary; the normal and ordinary VERIFY slaves remain
byte-identical. `CUSTOM1` stays optional and off by default, with the same native fallbacks.

## Completed steps

| Step | Evidence | Status |
| --- | --- | --- |
| C1 controls | Native input replay, execution probes, state snapshots and fallback counters | Complete |
| C2 race | 22 nominal minutes, four opponents with changed positions, qualifying/race transitions | Complete |
| C3 views | Cockpit/full view, map, T/P/L overlays, pause/resume and title inset | Complete |
| C4 incidents | Collision responses, accepted rescue, pit return, native repairs, departure and natural weather | Complete |
| C5 regression | Restart, exact repeat, 68000/020/060 checks, option-off and no-fast-memory hook audits, build isolation | Complete |

A requested input does not prove its resulting scenario occurred. Execution markers and
resulting native state accompany renderer diagnostics and inspected screenshots. Fixtures
feed the keyboard queue and sampled modifier/mouse-button inputs; they never force physics,
damage, weather or race state. The elapsed-time simulation runs once, with its native order.
Cache selection remains the user's standard WHDLoad CACHE/DCACHE choice.

## Results

Capture names below are directories under ignored `tmp/prof/`. Fields are PAL fields;
66,000 fields represent 22 nominal minutes. These instrumented runs establish correctness
and routing, **not performance**. Drawing twins and debugger probes change timing.

| Capture | CPU | Fields | Completed staged twins |
| --- | --- | ---: | ---: |
| `coverage-race-final3` | 68EC020 | 21,000 | 2,525 |
| `coverage-060-soak` | 68060-NOMMU, requested 50 MHz | 66,000 | 14,546 |
| `coverage-060-cruise` | 68060-NOMMU, requested 50 MHz | 34,000 | 7,592 |
| `coverage-020-repeat1` | 68EC020 | 3,000 | 395 |
| `coverage-020-repeat2` | 68EC020 | 3,000 | 395 |
| `coverage-weather-twin` | 68060-NOMMU, requested 50 MHz | 16,000 | 5,129 |
| `coverage-final-000-fast` | 68000 | 650 | 41 |
| **Total** | | | **30,623** |

The two 020 repeats have byte-identical `swaps-gdb.txt` logs, including presentation fields,
execution events and sampled state. The longer 060 soak passes `--require-long`: it records
15,997 opponent updates and four changed opponent positions, two full-view toggles, two map
toggles, each T/P/L overlay, and pause/resume. It records three track-collision responses and
5,791 wall-contact responses; repeated contact while resting is not a distinct impact.

Two accepted rescue requests precede the first pit return. Native repairs use `1,3,8,4,6`
then Space. The 34 departure-animation iterations span two departures, not 34 pit visits.
A session-end request is followed by a real race-menu selection, proving restart. The second
pit-return routine entry belongs to the next session and is not a second rescue. The soak
records 80 full-view native fallbacks. The cruise route samples 46 distinct track segments.

Natural weather is covered on track index 2, selected by ordinary menu keys. The weather
window begins at the first native effect draw (`$112f4`), validates 5,129 staged twins, and
records **139 native effect draws and 139 newly observed effect fallbacks**. It continues
through rendering after the effect ends. A separate `coverage-060-normal-alt` run with
`CUSTOM4=0` covers 34,000 fields, 20,505 staged scenes and 245 native weather draws/fallbacks;
those 20,505 scenes are not twin comparisons and are excluded from the total above.

`coverage-title` validates native title/inset routing: zero staged scenes and 222 native
inset entries in its 800-field window, with an inspected title screenshot.
`coverage-off` (020, 800 fields) and `coverage-final-000-native` (68000, 650 fields,
no fast RAM) preserve every audited native performance hook, with no decoded direct branch
into a hook interior and zero staged scenes. The final 68000 fast/no-fast full-view
screenshots were inspected. The fast case records 24 full-view native fallbacks.

The 020/060 setups use A1200, 2 MiB chip and 4 MiB fast RAM. The 68000 setup uses A500,
512 KiB chip, 1,536 KiB slow, and either 4 MiB or zero fast RAM. Runs use WHDLoad `NoCache`
for reproducibility. These are emulator results; physical boards are outside scope.

## Reproduce

Source `amiga/env.sh`, then run `make -C whdload coverage`. This produces the isolated
`tmp/build/Powerdrome-coverage.slave`. Only this build advertises the additional routes:

| CUSTOM5 | Route |
| --- | --- |
| 1 / 2 | Existing title / Practice launch fixtures |
| 3 / 4 | Practice / qualifying-race stress tape |
| 5 | Centering/acceleration cruise on the default course |
| 6 | Cruise on track index 2, selected with two native `0` menu keys |

`CUSTOM1` controls acceleration and `CUSTOM4=1` enables drawing twins. Ordinary `all`,
`verify` and `original-verify` targets omit the coverage replay and counters. Do not edit
capture scripts or rebuild a capture's slave while it is running.

```sh
AMIGA_MODEL=A1200 CPU=68060-NOMMU KICKSTART="$KICKSTART_A1200" \
CHIP_KB=2048 FAST_KB=4096 \
EXTRA_ARGS='--slow_memory=0 --uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency=50000000 --uae_cpu_cycle_exact=true' \
WHD_ARGS='CUSTOM1=1 CUSTOM4=1 CUSTOM5=4 NoCache' \
ANCHOR=0xbc7c FIELDS=66000 SWAP_ONLY=1 CAPTURE_SHOT=1 COVERAGE_STATE=1 \
COVERAGE_PROBES='0xc7f0 0xc736 0xc7d2 0x103a2 0xbf32 0xd3d6 0xc75c 0xc6b8 0xc6fe 0xbe12 0xbe40 0x13cde 0xfb84 0xfc9e 0x112f4 0x14764 0x120ca' \
tools/fixed_window.sh tmp/prof/coverage-race tmp/build/Powerdrome-coverage.slave
python3 tools/perf_status.py tmp/prof/coverage-race
python3 tools/coverage_status.py tmp/prof/coverage-race --require-long
```

The anchor is the first driving presentation after initial pit departure. The stress tape
requests session ends at fields 18,000 and 60,000 and finishes at 65,000. The fixture epoch
is the first simulation call, so measured event offsets differ slightly from tape positions.
For weather, use the same CPU/memory settings with `CUSTOM5=6`, `ANCHOR=0x112f4`,
`FIELDS=16000`, probes `0x112f4 0xe1a2 0xe1f8 0x120ca 0x103a2`, and a separate output
directory. Run both status tools, with `--require-effects` on `coverage_status.py`.
For the non-twin weather route use `CUSTOM4=0`, `ANCHOR=0xbc7c`, `FIELDS=34000`.

`swaps-gdb.txt` contains `PDEVENT` markers and `PDSTATE` samples. `configuration.json`
records options, probes and binary hashes; snapshots retain the native state and diagnostics.
Always run `perf_status.py` as well as `coverage_status.py`: it checks register/CCR details,
scratch, guards and copied-code immutability. Raw evidence remains under ignored `tmp/`.

## Build isolation and limits

Final SHA-256 identities:

- Normal (3,988 bytes): `2daa984b39bf2a367feb8d334359139a5f46084d7f31fd6d39a747f1e422dfa1`
- Ordinary VERIFY (5,216 bytes): `12af6b96dc10aefeb9026cf8a00a54cb89ae3ea350844859b139d61fa686ba71`
- Coverage fixture: `f514613eeb671c450824d5e84f9ae71a97832142023f80a687d2717cfecc75ba`

Normal and ordinary VERIFY match their pre-coverage outputs exactly. Captures retain their
individual fixture hashes; earlier routes used earlier instrumentation revisions with the
same production renderer. The final fixture is validated by the weather and 68000 cases.
Exact scene counts are observations of named captures, not contractual counts for future
fixture revisions. Scenario gates and zero renderer failures are the acceptance criteria.

Coverage is bounded to the selected routes on the default course and track index 2. Long
routes include stationary periods after impacts and do not prove completed player laps.
The native `$5c` state word is a session/difficulty counter, not a lap counter. Multiplayer,
every course/view/effect combination and every user-selected cache configuration are not
certified. Unsupported full/inset/effect/animation scenes retain native rendering; their
routing is observed, while pixel twins compare the supported staged scenes. This campaign
does not justify widening the fast path or changing the default. No selected coverage work
remains open.

## Instrumentation boundaries

The replay replaces complete six-byte instructions at `$5780` (VBL counter increment)
and `$ca3e` (simulation entry's state-pointer load). It replays the original instructions,
preserves their register/flag contract, and changes only the native input queue, sampled
buttons and shift-key word. The VBL hook continues through pause, so S can resume it.
Menu and pit fixtures submit keys through the existing native command handlers. Later
pit visits request both engine repairs, nose and wing repairs, then Space; repairs and
flight state changes remain native game operations.

The `PDCOV002` block counts simulation calls and native fallback scenes, with overlapping
full-view, inset, effect and animation categories. Fallback observation runs inside the
renderer's already-saved register/CCR frame. These are entry counts, whereas the existing
renderer diagnostic reports completed staged scenes. Do not subtract them as though they
were the same kind of counter.

Native event offsets include `$d3d6` (opponent update), `$c7d2` (accepted rescue), `$103a2`
(pit return), `$14764` (departure animation iteration), `$bf32` (session end), `$120ca`
(race selection), `$fb84` (wall-contact response), `$fc9e` (track-collision response), and
`$112f4` (effect rendering). Repeated departure iterations are not separate pit visits.
A B request alone is insufficient: the native rescue gate requires low fuel or both
engines failed with the ship stopped.
