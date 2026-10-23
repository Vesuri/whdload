# Current scope

Goals: keep world simulation at real-time speed, present smooth motion up to 50 fps,
and improve performance, especially on 68020+ with fast RAM. The implementation plan
is [plan.md](plan.md); verified findings are in [internals.md](internals.md).

# B5 startup gate blocked

B1–B4 and A1/A2/A3/A5/A6 are complete. A3's call-by-call table and drawing-side-effect
inventory are in [internals](internals.md#a3-simulation-versus-presentation); capture and
checking commands are in [development](development.md#call-boundary-state-and-drawing-ownership-a3).
Five 50-frame samples cover green, tow, follow, qualifying and replay. Every observed
drawing delta and every statically reachable renderer store is classified. The combined
gate and adversarial evidence checks pass. Builds, captures and rejected attempts stay
in ignored `tmp/`; no game/slave behavior changed.

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
race equivalence is not claimed. B4's changed builds and A3's ownership captures have
separate evidence, not a relabelled B3 baseline. No simulation or CPU-performance patches
are enabled.

Current session: **B5, A7 and A8 are unfinished.** A gated cache policy and VERIFY CACR
logging have been added. The 68020 completed a whole Quick Race and quit cleanly with
its instruction cache enabled; a fresh release-off capture passes the disabled-byte,
loader and quit checks. These are pilots, not acceptance of the full matrix.

The 68030 stalls before the language screen in the shared emulator's indirect
directory-drive path, with both the MMU-capable core and a verified non-MMU 030 configuration. Additional probes accidentally selected a 68020 through an
unsupported CPU spelling and are rejected as 030 evidence. The corrected runner checks
the effective CPU/MMU report before collecting evidence. Details and evidence are in
[internals](internals.md#b5-gated-cache-pilot--gate-not-passed); commands are in
[development](development.md#cache-and-machine-matrix-pilot-b5a7).

Next decision: expand work into repairing and validating shared AmigaXDev startup,
then repin the reviewed runtime if it changes. No shared tooling has been modified.
Do not accept the data-cache-disabled diagnostic as a substitute for B5.

After that blocker:

1. **B5:** validate whole races/menus on all required CPU/MMU cells and record matched
   cache gains. Cache behavior stays opt-in until this gate passes.
2. **A7:** capture both cache states across the six timing machines, with actual layouts,
   per-window timings/chip slots and full race-clock evidence. Repair the zero-lead
   follow anchor before accepting uncalibrated follow captures.
3. **A8:** implement the developer-only no-wait/no-fill gates and matched instant-blitter
   controls, extend the disabled-range checker, then measure the ceilings.
4. **C1–C6:** implement real-time ticks using A3 ownership and A5 publication rules.

**A4** remains required before D. This session stops at the failed B5 gate pending the
shared-tooling decision; neither A7 nor A8 is marked complete.
