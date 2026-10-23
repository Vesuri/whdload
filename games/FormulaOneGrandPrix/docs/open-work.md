# Current scope

Goals: keep world simulation at real-time speed, present smooth motion up to 50 fps,
and improve performance, especially on 68020+ with Fast RAM. Follow [plan.md](plan.md);
results and acceptance evidence are in [internals.md](internals.md).

# Current status: A7 complete; B5 and A8 have unresolved gates

| Work | Status |
|---|---|
| B1–B4; A1/A2/A3/A5/A6 | Complete. Current A8 additions also pass the disabled-range gate. |
| B5 | Menus and whole races pass on every required CPU, with exact repeats, cache audits and clean quit. Matched work gains on 040/060 remain unavailable; gate not passed. |
| A7 | Complete under its “measured or failure explained” gate: 24 CPU-timing cells measured, 12 unavailable 040/060 cells explained. All 36 windows have repeated field/DMA captures; all whole-race pairs pass. |
| A8 | A500/A1200/020 four-arm ceiling audits pass. 030 control/no-wait/no-fill measurements pass, but its instant arm changes Fast-hunk placement by 24 bytes. 040/060 CPU timings are unavailable. Incomplete. |
| 68030 | Active, not deferred. Cache and baseline measurements pass; the A8 instant-blitter allocation difference is open. |
| A4 | Open; required before D. |
| C–G | Simulation, presentation, optimisation and release work remain open under the plan. |

**Next F1GP work: A8's 030 instant-blitter control.** Find a common-layout comparison
without accepting a different allocation or weakening the audit. Skipping the frontend
fixed the 020 comparison, but not the 030's 24-byte Fast-hunk difference. New
breakpoint captures show that the 24-byte Fast free-region difference already exists
before `LoadSeg`; removing boot fire presses shifts both arms equally and does not fix
it. Trace the startup allocation before game loading next.

**Shared tooling remains deferred by the user's decision.** The selected 040/060
non-MMU cycle-exact cores yield field/DMA data but no CPU instruction records. Their
repeated empty CPU profiles cannot establish drawing/tick time, work gains or ceilings.
When shared profiling is repaired and explicitly resumed, pin the new runtime and
recapture the affected B5/A7/A8 controls; do not relabel the current evidence. This
session changed no AmigaXDev files.

After those acceptance gaps are resolved, proceed to **C1–C6** (real-time ticks), then
**A4** and **D1–D10** (presentation), following the plan. Caches remain opt-in while B5
is open. No real-time simulation or extrapolation patches are enabled.

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
