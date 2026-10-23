# Current scope

Goals: keep world simulation at real-time speed, present smooth motion up to 50 fps,
and improve performance, especially on 68020+ with fast RAM. The implementation plan
is [plan.md](plan.md); verified findings are in [internals.md](internals.md).

# Current status: B5 startup cause found; decision on determinism

| Work | Status |
| --- | --- |
| B1–B4; A1/A2/A3/A5/A6 | Complete, with gates recorded in internals. |
| B5 | Cache pilot implemented; gate not passed. 030/040 startup stalls explained (emulator deadlock); all 030/040/060 setups start with caches on when deterministic mode is off. |
| A7 | Matrix incomplete; paired measurements and a reliable zero-lead follow anchor remain open. |
| A8 | Not started. Developer gates and ceiling measurements remain open. |
| 68030 B5/A7/A8 cells | Deferral lifted for root-cause work; not passed. |
| A4 | Open; required before D. |
| C–G | Implementation and acceptance work remain open under the plan. |

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
separate evidence, not a relabelled B3 baseline. No simulation patches are enabled.
The B5 cache policy is opt-in and disabled by default; its acceptance gate is still open.

**B5, A7 and A8 are unfinished.** The gated cache policy and VERIFY CACR logging are in
place. On the 68020, a whole Quick Race completed and quit cleanly with the instruction cache on.

**The 030 and 040 startup stalls share one cause: an emulator deadlock**
([details](internals.md#startup-failures-cause-found-68030-68040)) between FS-UAE's
deterministic mode and the indirect UAE board that every data-cache setup needs.
Neither F1GP, the slave nor the caches are involved. With deterministic mode off, the
030, 040 and 060 setups, both MMU and non-MMU, all reach the first race field with caches
on and quit with F10 OK. Those runs don't repeat exactly. Evidence is in `tmp/b5-cause/`.
The emulator fix is tracked as AmigaXDev TOOL1.

**Decision needed:** either fix the shared emulator so deterministic mode works with the
indirect board (TOOL1), or validate 030+ without deterministic mode. The second option
would mean accepting functional runs and treating timings as repeated measurements with
spread, not exact repeats.

Next steps, under the [current validation scope](plan.md#current-validation-scope):

1. **B5:** after that decision, run whole races on 68020, 68030, 68040 and 68060 (MMU and
   non-MMU) with caches on, and record matched cache gains. Caches stay opt-in until this
   gate passes.
2. **A7:** capture both cache states on A500-equivalent, A1200, 020+Fast, 030, 040 and
   060, with actual layouts, per-window timings/chip slots and full race-clock evidence.
   Repair the zero-lead follow anchor first: it can select the tow scene's own Viewing banner.
3. **A8:** implement the developer-only no-wait/no-fill gates and matched instant-blitter
   controls, extend the disabled-range checker, then measure each CPU's ceiling.
4. **C1–C6:** implement real-time ticks using A3 ownership and A5 publication rules.

**A4** remains required before D.
