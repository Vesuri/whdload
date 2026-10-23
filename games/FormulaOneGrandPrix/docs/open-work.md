# Current scope

Goals: keep world simulation at real-time speed, present smooth motion up to 50 fps,
and improve performance, especially on 68020+ with Fast RAM. Follow [plan.md](plan.md);
results and acceptance evidence are in [internals.md](internals.md).

# Current status: C2 implementation in progress; B5/A8 gates remain open

| Work | Status |
|---|---|
| B1–B4; A1–A6 | Complete. Current A8 additions also pass the disabled-range gate. |
| B5 | Menus and whole races pass on every required CPU, with exact repeats, cache audits and clean quit. Matched work gains on 040/060 remain unavailable; gate not passed. |
| A7 | Complete under its “measured or failure explained” gate: 24 CPU-timing cells measured, 12 unavailable 040/060 cells explained. All 36 windows have repeated field/DMA captures; all whole-race pairs pass. |
| A8 | A500/A1200/020/030 four-arm ceiling audits pass. A developer-only preference-notification control fixes the 030 allocation mismatch. Only 040/060 CPU timings remain unavailable. |
| 68030 | B5/A7 measurements and A8 common-layout ceiling comparisons pass; no 030 item remains deferred. |
| A4 | Complete: car/track/camera/view map, static view paths and 250 checked A3 camera-return snapshots. |
| C1 | Complete: elapsed-VBL clock design, whole native updates, PAL/NTSC integer schedules and checked accounting model. The C2 prototype now installs runtime hooks behind a developer option. |
| C2 | Developer implementation and probes in progress; not accepted. Beam-based PAL/NTSC detection replaces the insufficient native rate word with user approval. |
| C3–G | Modal/input acceptance, presentation, optimisation and release work remain open under the plan. |

**Current F1GP step: finish C2, implementing the elapsed-VBL clock and loop separation.**
The user explicitly selected C2 while shared work remains deferred. The clock design
is in [Game time](internals.md#elapsed-vbl-world-clock-c1); it adds no CIA timer and
allows no fractional simulation updates. Its host accounting checks pass for PAL/NTSC.
B5/A8 are still incomplete; this work does not waive their measurement gates.

C2 remains open: finish conditional background-rebuild separation; validate
full replay, view changes and A5 CPU/blitter buffer ownership; rerun current-build
state comparisons after the remaining changes. The CPU HUD queue now preserves
selected gameplay/HUD state and completed replay/qualifying pictures against native
painting. Its bound was raised after a recorded overflow; developer storage is now
192 KiB; the A500 probe completes and quits without overflow but drops 41 fields
of debt. The fresh four-build disabled-feature suite passes, including all 234 hook-byte
negative checks. The replay R now paints once per publication;
a same-build replay tick-40 comparison passes selected authoritative state, and its
50-field trace passes CPU/blitter ownership and cadence checks. The native-painting
control correctly fails the R cadence check. Early PAL tick-160 probes matched all
26 car records, clocks, camera and selected A3 side effects across normal and
artificially delayed drawing. Those are selected-state checks, not C5 acceptance.
The qualifying probe also completed and quit cleanly, but dropped substantial debt;
that is overload, not evidence of real-time operation. Evidence is under `tmp/c2/`;
each capture carries its own build identity. Do not mix earlier prototypes with
current-build acceptance. Shared tooling remains untouched.

**Shared dependency: restore 040/060 CPU profiling when shared work is resumed.**
All currently measurable F1GP B5/A7/A8 cells and the 030 allocation fix are complete.
The 030 difference arose during the loader's notification-enabled `SetPrefs` call.
Developer-only `CUSTOM4=1` suppresses notification in every ceiling arm, preserving
common layout; gate-off retains the original argument and release bytes are unchanged.
Fresh disabled-byte gates, exact 030 repeats and all three MMU functional pairs pass.

**Shared tooling remains deferred by the user's decision.** The selected 040/060
non-MMU cycle-exact cores yield field/DMA data but no CPU instruction records. Their
repeated empty CPU profiles cannot establish drawing/tick time, work gains or ceilings.
When shared profiling is repaired and explicitly resumed, pin the new runtime and
recapture the affected B5/A7/A8 controls; do not relabel the current evidence. This
session changed no AmigaXDev files.

A4 is now complete; its state map is in [internals](internals.md#state-map-a4).
Continue with **C2–C6** (real-time ticks), then **D1–D10** (presentation), following
the plan and retaining the unresolved B5/A8 gates. Caches remain opt-in while B5
is open. The C2 prototype is developer-only and opt-in (`CUSTOM2` bit 1); no extrapolation
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
[A8 ceilings](internals.md#a8-developer-ceiling-gates--partial-result), and
[commands](development.md#cache-and-machine-matrix-pilot-b5a7).
All derived artifacts remain in ignored `tmp/`. No remote is configured; commits are local.

Important constraints for C:

- C1 schedules exactly eight native updates per 50/60 fields. The measured native
  race-clock increment implies a 1.03076 ratio at 8 Hz, outside C5(a)'s ±1% target.
  Resolve the clock calibration/acceptance interpretation before claiming C5(a);
  do not silently alter physics or the requested update cadence.

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
