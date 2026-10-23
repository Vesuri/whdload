# Current scope

Goals: keep world simulation at real-time speed, present smooth motion up to 50 fps,
and improve performance, especially on 68020+ with fast RAM. The implementation plan
is [plan.md](plan.md); verified findings are in [internals.md](internals.md).

# B5/A7/A8: continue with 68030 deferred

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

**B5, A7 and A8 are unfinished; 68030 validation is explicitly deferred.** A gated cache policy and VERIFY CACR
logging have been added. The 68020 completed a whole Quick Race and quit cleanly with
its instruction cache enabled; a fresh release-off capture passes the disabled-byte,
loader and quit checks. These are pilots, not acceptance of the full matrix.

The 68030 stalls before the language screen in the shared emulator's indirect
directory-drive path, with both the MMU-capable core and a verified non-MMU 030 configuration. Additional probes accidentally selected a 68020 through an
unsupported CPU spelling and are rejected as 030 evidence. The corrected runner checks
the effective CPU/MMU report before collecting evidence. Details and evidence are in
[internals](internals.md#b5-gated-cache-pilot--gate-not-passed); commands are in
[development](development.md#cache-and-machine-matrix-pilot-b5a7).

The user has deferred all 68030 cells for now. The shared findings are recorded in
AmigaXDev's backlog as **TOOL1** (indirect-drive startup wait), **TOOL2** (unsupported
CPU spelling/effective configuration), and **TOOL3** (stale capture reuse). Do not
investigate or fix those shared items in this session. No shared tooling or installed
runtime has changed. Deferred 68030 results are not passes.

**New non-deferred blocker:** the verified 68040/25 non-MMU cache-on check also failed
to advance past its first 25-field startup command. The live process was stopped after
2 minutes 23 seconds without reaching the language screen; evidence is retained in
`tmp/b5/040-on-clock`. See [the check and its limits](internals.md#non-deferred-b5-check-68040-startup-also-unsuccessful).
No shared-tool investigation or fix was made. 040 is still required, not deferred;
040 MMU and 060 cells remain untested. The next decision is how to handle this additional
startup blocker under the instruction to leave shared repairs out of this session.

Next steps, under the [current validation scope](plan.md#current-validation-scope-68030-deferred):

1. **B5:** validate whole races/menus on 68020 and both 68040/68060 MMU variants; record matched
   cache gains. Cache behavior stays opt-in until this gate passes.
2. **A7:** capture both cache states on A500-equivalent, A1200, 020+Fast, 040 and 060, with actual layouts,
   per-window timings/chip slots and full race-clock evidence. Repair the zero-lead
   follow anchor before accepting uncalibrated follow captures.
3. **A8:** implement the developer-only no-wait/no-fill gates and matched instant-blitter
   controls, extend the disabled-range checker, then measure the non-deferred CPUs' ceilings.
4. **C1–C6:** implement real-time ticks using A3 ownership and A5 publication rules.

**A4** remains required before D. Resume 68030 qualification in a later session after
its tooling blocker is resolved; no B5/A7/A8 step is marked complete by this deferral.
