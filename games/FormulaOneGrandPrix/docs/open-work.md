# Current scope

Goals: keep world simulation at real-time speed, present smooth motion up to 50 fps,
and improve performance, especially on 68020+ with fast RAM. The implementation plan
is [plan.md](plan.md); verified findings are in [internals.md](internals.md).

# A3 complete

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

Next scope:

1. **B5:** enable caches and validate menus/full races across the CPU/MMU matrix.
2. **A7**, alongside B5: complete the machine and race-clock measurements.
3. **A8:** use the existing developer/VERIFY gates to measure renderer ceilings.
4. **C1–C6:** implement the real-time clock and tick/presentation split using A3's
   ownership rules and A5's publication rule. The understanding prerequisites are complete.

**A4** is still needed before D's presentation snapshots. This session stops at A3;
B5 and implementation are new scope.
