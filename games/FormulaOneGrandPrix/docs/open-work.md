# Current scope

Goals: keep world simulation at real-time speed, present smooth motion up to 50 fps,
and improve performance, especially on 68020+ with fast RAM. The implementation plan
is [plan.md](plan.md); verified findings are in [internals.md](internals.md).

# Current status: B5/A7/A8: functional races pass; 040/060 timing blocked

| Work | Status |
| --- | --- |
| B1–B4; A1/A2/A3/A5/A6 | Complete, with gates recorded in internals. |
| B5 | Cache pilot implemented; gate not passed. 030/040 startup deadlock fixed in the emulator (AmigaXDev TOOL1); all 030/040/060 setups start with caches on and repeat exactly. |
| A7 | Matrix incomplete; full paired measurements remain open; the corrected zero-lead follow anchor passes a fresh repeat. |
| A8 | Developer gates and all-off checks pass; enabled ceiling measurements are in progress. |
| 68030 B5/A7/A8 cells | No longer deferred; open like the other CPUs. |
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

**B5, A7 and A8 are unfinished.** The current window-title emulator build is pinned;
a first 030 non-MMU cache-on whole race and clean quit pass (`tmp/b5-final/030-on-clock-b`).
A fresh 030 non-MMU cache-on pair (`-d`/`-e`) passes exact comparison with mouse
auto-switching disabled. All six 030/040/060 cache-on whole-race pairs also pass. The 020 cache-on pair also passes; matched gains remain next. The gated cache policy and VERIFY CACR logging are in
place. On the 68020, a whole Quick Race completed and quit cleanly with the instruction cache on.

**The 030/040 startup stalls are fixed.** They were an FS-UAE deadlock between
deterministic mode and the indirect UAE board
([details](internals.md#startup-failures-cause-and-fix-68030-68040)). AmigaXDev TOOL1
fixed it, and F1GP now pins the installed emulator. With `DETERMINISTIC=1`, all six
030/040/060 setups (MMU and non-MMU) reach the first race field with caches on, quit with
F10 OK, and repeat exactly from fresh boots. `tools/machine_matrix.py` can now run every
cell. AmigaXDev TOOL2 and TOOL3 are also done: the launcher refuses unknown CPU names, and
failed captures leave no image or trace. F1GP pins that launcher.

**Timing blocker:** the selected 040/060 cores produce field/DMA data but zero CPU
instruction records. Their exact repeats are functional evidence, not timing acceptance.
B5 gains and A8 ceilings on these CPUs require a shared-profiler decision. The corrected
020 ceiling comparison passes with a common intro-skipping route.

**Control correction:** cache-off matrix arms now explicitly use `NoCache`; the original
CPU policy can leave Fast RAM cacheable with an MMU. Old off runs lacking this override
are not accepted as uncached controls. New MMU off pairs pass.

Next steps, under the [current validation scope](plan.md#current-validation-scope):

1. **B5:** run whole Quick Races with caches on, using `machine_matrix.py ... on clock`,
   on 68020, 68030, 68040 and 68060 (MMU and non-MMU). Run the matching cache-off cells
   too, and record matched cache gains. Caches stay opt-in until this gate passes.
2. **A7:** capture both cache states on A500-equivalent, A1200, 020+Fast, 030, 040 and
   060, with actual layouts, per-window timings/chip slots and full race-clock evidence.
   The corrected zero-lead follow anchor passes; combined three-window captures are being collected.
3. **A8:** validate enabled no-wait/no-fill gates and matched instant-blitter controls, then
   measure each CPU's ceiling. All-off byte checks pass for all three build targets. The first 020 instant-blitter
   comparison failed the common-layout audit; intro-skipping recaptures fix it on 020
   and are being checked on 030.
4. **C1–C6:** implement real-time ticks using A3 ownership and A5 publication rules.

**A4** remains required before D.
