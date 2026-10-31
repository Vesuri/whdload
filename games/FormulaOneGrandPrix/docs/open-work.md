# Current scope

Goals: keep world simulation at real-time speed, present smooth motion up to 50 fps,
and improve performance, especially on 68020+ with Fast RAM. Follow [plan.md](plan.md);
results and acceptance evidence are in [internals.md](internals.md).

# Current status: C, D and E complete; B5/A8 pass for the current scope

| Work | Status |
|---|---|
| B1–B4; A1–A6 | Complete. Current A8 additions also pass the disabled-range gate. |
| B5 | Menus and whole races pass on every required CPU, with exact repeats, cache audits and clean quit. Gains recorded for 020/030. Passed for the current scope; 040/060 gains are deferred work. Caches are still opt-in. |
| A7 | Complete under its “measured or failure explained” gate: 24 CPU-timing cells measured, 12 unavailable 040/060 cells explained. All 36 windows have repeated field/DMA captures; all whole-race pairs pass. |
| A8 | A500/A1200/020/030 four-arm ceiling audits pass. A developer-only preference-notification control fixes the 030 allocation mismatch. Passed for the current scope; 040/060 CPU timings are deferred work. |
| 68030 | B5/A7 measurements and A8 common-layout ceiling comparisons pass; no 030 item remains deferred. |
| A4 | Complete: car/track/camera/view map, static view paths and 250 checked A3 camera-return snapshots. |
| C1 | Complete: elapsed-VBL clock design, whole native updates, PAL/NTSC integer schedules and checked accounting model. The C2 prototype now installs runtime hooks behind a developer option. |
| C2 | Complete as a developer-only loop implementation: bounded whole ticks, separated painting, safe publication and checked sound timing. PAL/NTSC beam detection is user-approved. |
| C3 | Complete: explicit modal suspension/rebase, replay and menu handoffs, native accelerated-time ownership, and checked PAL/NTSC/68000 routes. |
| C4 | Complete: one-shot presses are buffered until a native scan has seen them (user decision). All view keys, pause, double tap, replay tap, held view and joystick pass and repeat exactly. |
| C5 | Complete. (a) 7.987 ticks per emulated second (8 per 50 PAL fields, no drops) on the 030 and A1200; the A500-equivalent is overloaded (C6). (b) normal and slowed drawing give identical state at every tick of a race; the one-field difference is classified as an A1 timing input. (c) race, retirement, replay and the accepted pit coverage pass on the 030. |
| C6 | Complete: the A1200 runs at real time (7.7 fps, 6.7 in the tow window). On the A500-equivalent the clock gives 1.65 fps at 0.83×, because an undrawn tick costs 7.2 fields, so the 68000 keeps the native pacer by default (user decision); `CUSTOM2` bit 2 forces the clock for tests. |
| D1 | Complete: behind `CUSTOM2` bit 3, every completed tick records the A4 renderer inputs (view state, published camera, synthetic camera and 26 car records) with its field number in cur, keeping the previous tick in prev. A whole 030 race matches game memory at all 3162 ticks, leaves the race identical to the option off, repeats exactly and costs 0.24 ms per tick. |
| D2 | Complete: every picture gets α, the Q14 fraction of the next tick from the clock's credit plus the measured lead to its first displayed field, clamped to two ticks; α is 0 when pictures are longer than that horizon (one tick before D9). Over a whole 030 race the rule recomputes exactly, 95% of leads are exact, displayed world time never goes backwards (p95 error 1 field), and the race is unchanged. |
| D3 | Complete: around every picture's draw the slave stages a 1080-byte pose subset of the renderer inputs (camera publication, coefficients, horizon, viewport, track anchor and per-record pose) and restores the authoritative bytes right after the draw. VERIFY checks every restore against a D1 snapshot. A VERIFY probe staging the previous tick changes the inputs of 95% of pictures, yet the whole 030 race is identical to the option off at all 3226 ticks; 0.83 ms per picture. D4 predicts the camera and D5 the cars. |
| D4 | Complete: each staged picture with a usable history gets a camera extrapolated from the published camera (`cur + (cur − prev) × α`); the road anchor comes from the game's own segment search, and coefficients, horizon and viewport are recomputed with the native formulas. Snaps at view/source changes, TV cuts, rebases and jumps. Over a whole 030 race an independent model rebuilds all 5990 predictions exactly, the p95 camera position error against the ideal path falls from 490k to 30k world units (yaw 882 to 126), and the race is identical to the option off at all 3210 ticks; 0.034 ms per picture. |
| D5 | Complete: each predicted picture also extrapolates the 26 car records. Track-driven cars advance along their segments by fraction with the native stepping (lap wrap, pit branch and join), explicit cars in world X/Z with the game's segment search; a car is held at pit transitions, flag, status or jump changes and on the grid. Over a whole 030 race an independent model rebuilds every car exactly (144,157 predicted, 3263 held), the p95 car position error against the ideal path falls from 494k to 25k world units (yaw 871 to 239), and the race is identical to the option off at all 3082 ticks; 0.72 ms per picture. |
| D6 | Complete: every other moving item has a decision. Steering (wheel images), marshal flags, start lights, pit phases, shake, instruments and car flags stay at the tick; the tow truck, smoke and debris are drawn at offsets from the predicted car, and the rear view and pit-lane overlay from the staged camera. The covered-road (no-sky) flag is now derived from the predicted anchor. Holding steering beats extrapolating it (0.79% against 1.10% of car-pictures more than half a wheel image off at α = 1). The whole 030 race is rebuilt exactly and identical to the option off at all 3258 ticks. |
| D7 | Complete: every view draws from the staged records. In the chase and TV views the camera is placed and aimed natively from the predicted followed car, so the car no longer slides sideways in corners. Pit stops swap track ranges, now captured per picture. A whole 030 race through cockpit, TV, both chase views, onboard other cars and a replay is rebuilt exactly (3749 external cameras placed) and identical to the option off at all 3246 ticks; 0.022 ms per picture. |
| D8 | Complete: every tick's prediction at α = 1 (and 2) against the next actual tick, over the whole D7 race. Camera p95 position error 21,504 against 446,880 for holding the tick, cars 22,784 against 430,080. Braking barely raises it, steering reversals make yaw extrapolation worse than holding, and collisions are already held through the pose flag or status. The snap thresholds stay: the $100000 jump (twice the largest normal movement), the two-tick α clamp and three segments per tick. |
| D9 | Complete on the 68030/50 (040/060 deferred): every picture is placed at its displayed field and its camera and car steps are compared with the actual motion. Two causes of backward motion were fixed: a car whose predicted step reaches a pit change now stops at the end of its segment instead of being held at the tick, and α falls to 0 only for pictures longer than two ticks. Over a whole race the camera never steps back and stalls 6 times in 4579 moving pairs (2127 showing the tick); cars step back 51 times in 139,607, at most 14,734 world units, mostly off the grid. Steps are even (p5–p95 0.76–1.30 of the ideal, against 0–2.1). Per-field screenshots: with prediction 98–100% of pictures change the view, against once a tick without; frame times 3–4 fields in the cockpit and chase views, 5 in TV. Race unchanged, exact repeat, B4 gate PASS. |
| D10 | Complete (user decision): the first 040 play-test found the horizon drawn over the 3D (fixed) and steering jumps from extrapolation. Pictures now interpolate between the last two ticks, shown a tick plus the measured lead late (user decision). Over a whole 030 race the rebuild is exact, camera yaw steps back 25 times (118 extrapolated) and cars 23 (51), steps are even p5–p95 0.89–1.07 (0.76–1.30), and the race is unchanged; on the 040 the screen changes every field. The user found steering, every view, the replay cuts and the pit stop fine. Cars no longer jump at collisions: a car whose pose flag changes is interpolated along the track and drawn track-driven ([evidence](internals.md#d10-play-test--complete)); median evenness across such changes 1.01 (1.75 held), none beyond 2.5 (13.2), race unchanged. |
| E1 | Complete for the current scope: B5's gate, and with the C2 loop and interpolation a whole 030 race draws 13–14% more pictures with caches on (3.43 against 3.86 fields per picture, developer build). Caches stay opt-in in the slave; the release turns them on through its icon (G1). |
| E2 | Complete for the current scope (developer `CUSTOM2` bit 4): hunk 2's main code runs from a fast-RAM copy from the first live epoch, its data stays in chip. The race is identical with it off at every tick, every staged picture is rebuilt, and the 030 draws 31–32% more pictures (2.46 against 3.24 fields per picture, developer build). |
| E3 | Complete for the current scope (developer `CUSTOM2` bit 5): the race picture is drawn in a fast buffer, its fills and queued blits run on the CPU, and publication copies it into the free chip back buffer. A VERIFY twin matches all 14,062 fills and blits of a race against the blitter byte for byte, the race is identical with it off at every tick, every staged picture is rebuilt, and with E2 the 030 draws 2.05–2.07 times as many pictures (1.21 against 2.51 fields per picture, developer build). |
| E4 | Complete (user decision; developer `CUSTOM2` bits 6–8). The picture copy writes only the longs that differ from a fast shadow of each chip bitmap; a whole race compares every copy (5271, 0 faults), and in a rear-chase window publication falls from 18.5% to 11.4% of cycles (75 pictures against 68). Bit 7: the renderer's CPU-only chip data (edge pool, span masks, jump words and the scene's two variable blocks in hunk 2) moves to fast RAM; the same tick's picture and state are identical, and a picture's scene falls from 22.98 to 16.92 ms in rear chase and from 13.47 to 10.05 ms on the grid (same-build pairs). Bit 8: exact faster forms of the edge tracer's X-major steps and of the sky strip's reads; the same tick's picture and state are identical, and the scene falls a further 3.1% in rear chase (16.39 ms) and 4.7% on the grid (9.58 ms). E2–E4's fast areas come from WHDLoad 20's alternative memory configuration (`MEMCONFIG=1`), so chip-only machines keep the release's memory and boot. The remaining items (point projection, filler spans, the copy's compare loop, D3's walk) are spread thin, 1–3% each, and are left. |
| E5 | Measured, not kept ([evidence](internals.md#e5-aga-32-bit-fetch--measured-not-kept)): on AGA, 32-bit bitplane fetch with `DDFSTOP` 8 colour clocks earlier left the same tick's picture identical and cut a picture's scene by only 0.3% on the grid and 0.2% in rear chase (same-build pairs). The game's one data-fetch setting covers every screen, so the change would be global; 64-bit fetch can recover no more. |
| E6 | Complete (developer `CUSTOM2` bit 10, with E2; [evidence](internals.md#e6-hunk-2-code-and-data-the-cpu-reads-from-chip--complete)): the chip data areas left after E4 cost at most 0.4% each, so E6 moved the remaining chip cost, hunk 2 code E2 could not redirect: the scene's handlers loaded by absolute `LEA` and called through `JSR (A5)`, and h2+$242E0 behind a PC-relative table read that the slave now makes to the chip table. Hunk 2 code run from chip falls from 10.4% to 0.3% of rear-chase cycles; scene −11.8% and −9.8% in rear chase (two builds) and −4.8% on the grid; same tick's picture and state identical. Left: `c2_repeat_boxes` reads HUD boxes from the chip front (3.3–3.8% of cycles in a rear-chase window with boxes); E4's shadow of the front could serve them, unmeasured. |
| E7 | Complete ([evidence](internals.md#e7-the-68000--complete)): of E4's changes only the edge tracer's X-major form runs without fast RAM. Its hooks now apply on the 68000 too (developer `CUSTOM2` bit 8). On the A500-equivalent the tracer falls from 14.2% to 11.3% of cycles and the scene from 93.2 to 86.4 ms per call (clock forced), and the native pacer draws 64 frames in 500 fields against 62 (two runs each, exact). |
| E8 | Closed, not worked: the interrupt chain costs about 1.2% and no cheap change is known. |
| F | Make the slave run any F1GP-Ed-edited `f1gp` with the enhancements (user decision). F1 is complete ([write map](internals.md#f1-write-map--complete)): F1GP-Ed 3.44 and the f1gp.library developer archive are pinned; F1GP-Ed runs headless (`amiga/ed.sh`, `tools/f1_writemap.py`), and every save writes 281 bytes of code patches (a startup hook that opens f1gp.library, the grid-size routine, the file requester's 200 entries, the detail preset) plus each setting's data and code in hunks 0 and 2 and two relocation tables. The nine supplied datafiles write nothing outside the map. F2 is complete ([collisions](internals.md#f2-collisions--complete)): nothing is incompatible. The frame-rate settings need F3, the names restore needs a whole-block check (F5), and the filter-button and save-directory overrides need documenting (F5). E2 and E4 hold on every saved file, and the 2002-edited file runs to practice on the A500-equivalent and on the 030. Next: F3. |
| G, H | Release after F; finer simulation (H) only on the user's request. G4 started early for the user's A1200/040 test: `make dist` builds `dist/FormulaOneGrandPrix-2.0b.lha` (developer slave, enhancements on in the icons; [development](development.md#release-archive-g4)). |

**Next F1GP step: F3, frame rate and timing.** F2 found the 1995–2002 datafiles' frame rate (step 6750, cadence 6 fields) against C's fixed 1/8 s clock; the routes in `tools/f1gp.py` assume the stock start, which the 2002 settings skip (F4). F1 and F2 are complete: the write map and the collisions are in internals. E is complete. E7 put the edge tracer's
faster form on the 68000 too (+3.2% frames on the A500-equivalent); E8 was closed without
work. E6: hunk 2's indirectly entered code runs from fast RAM (scene −5 to −12%). E5 was measured and not kept. E4 is complete (user
decision): chip waits, the tracer's per-pixel loop and the sky strip's chip reads are
resolved, and the rest is
spread thin. The race depends on the build: measure each change as a same-build pair with
its bit off and on. Captures can fail with
gdb's "Invalid hex digit 79" when an emulator log line arrives during a memory read; a
retry is the remedy.

E3 is complete for the current scope
([evidence](internals.md#e3-drawing-in-fast-ram--complete-for-the-current-scope)): with
the picture in fast RAM, acquire no longer waits for the display or copies chip to chip,
so the 030 with E2 draws about twice as many pictures over the same race. Per-operation
twins prove the CPU fills and the software blitter exact; a twin of whole scenes cannot,
because the renderer keeps caches across draws. The copy into chip (22.5% of cycles in a
profile window) is now E3's main cost, ahead of E4's re-profile. E2 is complete for the
current scope
([evidence](internals.md#e2-hunk-2s-code-in-fast-ram--complete-for-the-current-scope)):
a static descent finds which of hunk 2's routines can run from a copy, and the 030 draws
31–32% more pictures.
E1 is complete for the current scope
([evidence](internals.md#e1-caches--complete-for-the-current-scope)): caches on draw 13–14%
more pictures over a whole 030 race. The cached and uncached arms are different races,
because uncached menus run slower and change the race's random seed, so the gain is over
the same route and race length rather than tick by tick. D10 is complete: the user
accepted the feel, including the extra lag of interpolation (user decision). Input still
takes effect at the next tick.

The first 040 play-test showed a glitch about every 25 fields while standing still: the
horizon trees were drawn over the 3D. It also happened with the option off and on the
max-speed 030, wherever pictures take one field each, and it is fixed
([cause](internals.md#c2-developer-implementation--complete)). With the option off,
standing still, the screen now changes 12 times in 13 tick advances on the max-speed 030
and 24 times in 24 on the 040, against 15 and 30 before. The play-test also showed
steering jumps from extrapolation: on the first steered frame, after releasing the
steering, and in right-hand corners. Pictures now interpolate between the last two ticks
([evidence](internals.md#d10-play-test--complete)). Interpolating at α alone held the
newest pose in 55% of the 030's pictures, so motion paused at the end of every tick; each
picture is now shown a tick plus the longer measured lead late, which keeps the steps even
(user decision). That is about half a tick more lag than the original game on the
normal-speed 030 and a sixth of a tick on the 040. In the second 040 play-test the user
found steering smooth, without jumps, the chase, TV and onboard views fine, and nothing
wrong at the replay cuts or the pit entry. The pit-stop sprites (BRAKE ON sign, visor
wipe) still stepped once a tick; their x positions are now interpolated too, which the
user found fine. Held cars still show their tick pose, ahead of the interpolated pictures;
20 small backward car steps over a race come from that.

D9 is complete ([evidence](internals.md#d9-smoothness--complete)) on the 68030/50; the
plan's 50 fps 68060 run is deferred with the other 040/060 work. The backward steps it
left were small: cars pulling away from the grid, and camera yaw at steering reversals,
which extrapolation overshoots (D8); D10's interpolation reduces both. In the TV retirement window, a light-blue patch on
the run-off right after a cut appears with the option off as well; whether the original
frame-locked game draws it is not established.

D8 is complete ([evidence](internals.md#d8-prediction-error--complete)). The prediction one
tick ahead is about 20 times closer than holding the tick, the error does not grow with
speed, and prediction is worse than holding only at 8 camera ticks and 61 of 72,199
moving car-ticks. The thresholds stay as they are.

D7 is complete ([evidence](internals.md#d7-every-view--complete)). Every view draws from
the staged records, and in the chase and TV views the camera follows the predicted car as
the game places it. Open from D7: blue polygons flashing on the
tarmac were seen in the TV view while Mansell's retired car drifted at the camera's
switching distance, where the game alternates view-code bit 6 every tick and every
picture shows the tick. The state is identical with the option off. D9's per-field
screenshots of that window show a light-blue patch beside the tarmac after the cut to
Patrese, identical with the option off; whether the original game draws it is not established.
Not exercised: a track-point TV camera and covered road.

D6 is complete ([evidence](internals.md#d6-everything-else-that-moves--complete)). Every
other moving item is either held at the tick (steering, flags, lights, pit phases, shake,
instruments, car flags) or drawn from the staged poses (tow truck, smoke, debris, rear
view, pit-lane overlay). The covered-road flag, which turns the sky off, now follows the
predicted anchor; Silverstone has no covered road, so a tunnel track is still unexercised.

D5 is complete ([evidence](internals.md#d5-car-prediction--complete)). Staged pictures
draw the camera and the cars at the picture's displayed time. Banners over the view (Viewing, Race won by)
are repeated after every scene drawn between ticks, as the game's per-frame HUD did.

D4 is complete ([evidence](internals.md#d4-camera-prediction--complete)). Staged pictures
draw an extrapolated camera: direction, pitch, height, yaw and world X/Z, with the
coordinates, road anchor, coefficients, horizon and viewport derived from them as the game
does. Lateral offset and lap segment stay at the tick.

D3 is complete ([evidence](internals.md#d3-stage-and-restore--complete)). Each picture is
drawn from a staged copy of its renderer inputs, and the authoritative bytes are back in
the game before any simulation code runs. Inside a tick the staged picture uses the
previous tick's snapshot (cur) as history, between ticks prev. Pictures with an unusable
history (another epoch, mode or view) snap. Inside a tick a picture is not staged when
drawing could start the debris deadline (A3), because that must follow native visibility.

D2 is complete ([evidence](internals.md#d2-presentation-phase-α--complete)). Each picture's
α counts from when the current tick fell due (the clock's credit) plus the lead the
previous picture of its kind took to reach the screen. The clamp is two ticks: pictures
drawn between ticks are displayed after the next tick is due (ideal α up to 1.5), so a
one-tick clamp lagged by up to 3 fields.

D1 is complete ([evidence](internals.md#d1-presentation-snapshots--complete)). At every
completed tick the slave keeps cur and prev copies of the renderer inputs, with field
numbers and the epoch, rebase and view state that D2/D4 need to decide when to snap.
They are verified against game memory at every tick of a whole 030 race, are read-only
for the game (identical per-tick state with the option off) and cost 0.24 ms per tick.

C6 is complete ([evidence](internals.md#c6-slow-machines--complete-the-68000-keeps-the-native-pacer)).
The A1200 holds real time with no drops (7.7 fps; tow 6.7). The A500-equivalent cannot:
an undrawn tick still runs the renderer's geometry for its side effects (about 145 ms
against 125), so the 68000 keeps the original frame-locked pacer unless `CUSTOM2` bit 2
forces the clock. Making undrawn ticks cheap would need the renderer's per-tick side
effects separated from its geometry; that remains possible later work.

C5 is complete ([evidence](internals.md#c5-real-time-acceptance)). (a) A whole Quick Race
completes 3200 ticks in 20000 fields with no dropped debt on `a1200-030` and `a1200`:
7.987 per emulated second (PAL fields are 49.92 Hz), race clock 2111/16384 s per tick
(1.029× real time). The A500-equivalent drops 17% of its fields (6.63 ticks per second).
(b) Normal and slowed (`CUSTOM4=3`) drawing give identical car and session state at every
one of 3208 common ticks, over 2406 undrawn catch-up ticks and dropped debt. The one-field
run (fastest non-cycle-exact CPU, user decision) enters the race with a different UI
random-stream state because its menus run faster: an A1 timing input, classified.
(c) Race, retirement/tow, replay and in-pit accelerated time pass with exact repeats; the
pit-box start plus accelerated time are the accepted pit coverage (user decision).
C6 now measures the A500-equivalent and A1200 against the projection, including the tow
window, and the user decides the 68000 default if the A500 cannot keep real time. The
030 also drops debt in the qualifying pit garage (115 fields in 400), a performance
target for later work.
See [C4 evidence](internals.md#c4-input-acceptance--gate-passed). The clock design
is in [Game time](internals.md#elapsed-vbl-world-clock-c1); it adds no CIA timer and
allows no fractional simulation updates. Its host accounting checks pass for PAL/NTSC.

C2 completion evidence covers the elapsed-VBL scheduler, bounded catch-up,
CPU HUD/background painting separation and external-view bitmap-base handling.
Its PAL/NTSC sound and publication audits pass; normal and forced-catch-up
rear-view pairs and replay match selected gameplay/HUD state and completed pictures.
TV/front-chase and A500 probes complete and quit cleanly. The 192 KiB developer HUD
queue does not overflow in these checks; the C2 A500 run drops 31 fields of
debt and qualifying drops 1263. These are overload diagnostics, not C5/C6 acceptance.
The C2 qualifying pair also matches. Its four-build disabled-feature
suite passes, including independent rejection of all 246 then-optional hook bytes.
Modal/replay transitions are now handled by C3;
C5 has since passed the real-time and equivalence gates. Evidence is under
`tmp/c2/`, with per-capture build identities. Shared tooling remains untouched.

C3 now excludes pause, menu/loading and replay-transition time without hiding it in
overload drops. Paused car/session state and clock remain unchanged; exact resume
checks show zero debt and a rebased sound interval. PAL, NTSC, forced-delay and 68000
pause routes pass, as do menu return (including paused return), native pit accelerated
time and natural replay completion. A whole race observes green, retirement/tow and
results, completing 3071 ticks with zero dropped fields. The fresh C3 disabled-feature
suite rejects mutations of all 288 optional hook bytes; release bytes remain unchanged.
C5 has since accepted the pit coverage and the real-time gates; C6 remains. See
[C3 evidence](internals.md#c3-modal-clock-boundaries) and the reproducible commands in
[development](development.md#c3-modal-boundary-validation).

**68030/50 is the primary target; 040/060 work is deferred to the end, if done at all**
(user decision). Keep the number of configurations as small as possible: new checks run
on `a1200-030` non-MMU with caches on, plus the A500-equivalent and A1200 only for
slow-machine steps (see [plan](plan.md#current-validation-scope)).
B5 and A8 pass for the current scope (68000, 68020, 68030). Their
040/060 timing items are the deferred work, not open gates. All F1GP B5/A7/A8 cells
for the current scope and the 030 allocation fix are complete.
The 030 difference arose during the loader's notification-enabled `SetPrefs` call.
Developer-only `CUSTOM4=1` suppresses notification in every ceiling arm, preserving
common layout; gate-off retains the original argument and release bytes are unchanged.
Fresh disabled-byte gates, exact 030 repeats and all three MMU functional pairs pass.

**Deferred 040/060 timing.** The F1GP collector uses the normal trace profiler, which
records no CPU instructions on the 040/060 cycle-exact cores. This is not a shared bug:
AmigaXDev's aprof emulator (`FSUAE_APROF`) profiles those cores without an MMU, and its
docs note that FS-UAE charges 040/060 time only for Chip/custom accesses and
multiply/divide, so emulated 040/060 frame rates and cache gains are not hardware timing.
If this work is resumed, count 040/060 work with aprof and confirm timing on a real
accelerator; do not relabel the current evidence.

A4 is now complete; its state map is in [internals](internals.md#state-map-a4).
Caches remain opt-in in the slave; the release turns them on through its icon (G1). The C2 implementation is developer-only and opt-in (`CUSTOM2` bit 1, D1 snapshots and D2 timing bit 3); no extrapolation
patch or release clock option is enabled.

Measurement controls now enforced:

- Cache-off arms use explicit WHDLoad `NoCache`; all CUSTOM bits zero alone can leave
  Fast RAM cacheable with an MMU. Old off captures without it are reference only.
- Exact repeats include configuration/build/runtime, routes, anchors, actual layout,
  every screenshot, semantic reductions and clean quit. Mouse auto-switching is disabled.
- Follow requires a different driver name, not another frame of the tow banner.
- Ceiling audits check actual patch bytes, common layout and effective blitter settings,
  including an unchanged blitter-wait policy. Fresh instant arms change only instant blits.
  Missing CPU timings are unavailable, never zero. Both failed allocation comparisons
  remain recorded alongside accepted results.

Current results: [A7 matrix](internals.md#a7-machine-matrix--gate-passed-with-explained-timing-failures),
[A8 ceilings](internals.md#a8-developer-ceiling-gates--passed-for-the-current-scope), and
[commands](development.md#cache-and-machine-matrix-pilot-b5a7).
All derived artifacts remain in ignored `tmp/`. No remote is configured; commits are local.

Important constraints for C:

- C1 schedules exactly eight native updates per 50/60 fields. C5(a) measured that tick
  rate (8.00 per second ± 1%) on the 030, A500-equivalent and A1200 (user decision).
  The displayed race clock keeps its native 2111/16384 s per tick (1.031× at 8 Hz);
  record it separately and don't change physics, cadence or the clock constant.

- Pit-animation counters, shared RNG/camera shake and visible-car debris expiry are
  drawing side effects that must retain native tick cadence and predicates.
- Camera preparation advances a damped camera state; HUD calls consume dirty flags and
  advance blink state. Separate these updates from painting.
- The car-update call includes HUD glyph compositing on some paths. Those bitmap reads
  are not physics input, but skipping the main renderer alone does not remove every
  display write from a catch-up tick.
- Keep per-tick native visibility for the debris latch; extrapolated presentation must
  not determine authoritative visibility effects.

B3's modern-KickEmu baseline remains accepted for its pinned build; original-slave
race equivalence is not claimed. B4, A3, current B5/A7 and A8 have distinct evidence and
build identities. A3's call-by-call ownership table remains the basis for C.
