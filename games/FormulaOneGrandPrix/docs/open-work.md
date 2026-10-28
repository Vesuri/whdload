# Current scope

Goals: keep world simulation at real-time speed, present smooth motion up to 50 fps,
and improve performance, especially on 68020+ with Fast RAM. Follow [plan.md](plan.md);
results and acceptance evidence are in [internals.md](internals.md).

# Current status: C3 complete; C4 buffering one-shot presses; B5/A8 pass for the current scope

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
| C4 | In progress. The user chose to buffer one-shot presses. Held view and per-tick joystick probes pass; the lost one-shot press repeats exactly and is the failing test to fix. |
| C5–G | Real-time acceptance, presentation, optimisation and release work remain open under the plan. |

**Next F1GP step: buffer C4 one-shot presses, then finish its input acceptance.**
A real key press/release during the forced batch delay is recorded by the keyboard IRQ
but lost before the next scan. Held view keys and per-tick joystick sampling pass.
**Decision (user):** buffer one-shot presses (view keys, pause) so the next native input
check sees each press exactly once; do not accept the native short-press limitation.
Keep native sampling points, held-key behavior and joystick sampling unchanged, keep
the buffer behind the developer C2 option, and keep disabled builds byte-identical.
The existing short-pulse probe must turn from FAIL to PASS on a rebuilt slave; then
finish pause, all view keys, replay/input and rapid-repeat acceptance and continue to
C5/C6. The two saved captures and their checker agree on acceptance FAIL
and exact-repeat PASS (`tmp/c4/acceptance.json`).
See [C4 evidence](internals.md#c4-input-acceptance--short-press-gate-failed). The clock design
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
C5 still requires the whole-machine real-time and equivalence gates. Evidence is under
`tmp/c2/`, with per-capture build identities. Shared tooling remains untouched.

C3 now excludes pause, menu/loading and replay-transition time without hiding it in
overload drops. Paused car/session state and clock remain unchanged; exact resume
checks show zero debt and a rebased sound interval. PAL, NTSC, forced-delay and 68000
pause routes pass, as do menu return (including paused return), native pit accelerated
time and natural replay completion. A whole race observes green, retirement/tow and
results, completing 3071 ticks with zero dropped fields. The fresh C3 disabled-feature
suite rejects mutations of all 288 optional hook bytes; release bytes remain unchanged.
Full pit-stop acceptance,
input acceptance and the whole-machine real-time gates remain C4–C6 work. See
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
Continue with **C4–C6** (input acceptance and real-time validation), then **D1–D10** (presentation), following
the plan. Caches remain opt-in until a release build turns them on; B5 no longer
blocks that. The C2 implementation is developer-only and opt-in (`CUSTOM2` bit 1); no extrapolation
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

- C1 schedules exactly eight native updates per 50/60 fields. C5(a) measures that tick
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
