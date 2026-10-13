# CD32 timing design: phase 8 decision

**Recommendation: D, the hybrid. User decision pending.** Retain the native world
at 10 updates/s, advance player orientation and camera from elapsed render time,
and interpolate other objects for display. This preserves most existing gameplay
clock policies while addressing control response. Phase 9 has not begun.

## Measured basis

One bounded Nav-1 held-fire capture in each of the eleven existing CPU/cache cells
uses the unchanged phase-7 world and original renderer. Updates 10–39 contain five
ships and 17–23 active objects including projectiles/effects. Asset loading and
initial acceleration are excluded. All 14 mapped gameplay state ranges match the
020 baseline at every selected update across all cells, including positions,
velocities, RNG, actions, targets, damage, energy and the world/draw counters.
Frames crossing a debugger stop are excluded, leaving 27–30 samples per cell.
This is representative short combat, not a worst-case mission or collision storm.

`S` brackets world entry `E:02a8` (file `02d4`) through its ordinary caller's
return `E:06bc` (file `06e8`); the stack must return by four bytes. It includes
all callees and preempting interrupts. `R` is the remainder of the interval
between ordinary loop entries `E:0698` (file `06c4`), including input, drawing,
HUD and waits. Neither value is a sum of selected routine self-cost samples.

The existing validated read-only observer measures emulated elapsed time using
`get_cycles()` and `512 × 3546895` units/s. “Elapsed clock counts” below divide
that interval by the live `cpucycleunit`; they include preemption/stalls and are
**not exclusive simulation instruction cycles**. Complete interrupt subtraction
remains the previously accepted practical-baseline gap. Consequently the stated
simulation reservation is a conservative elapsed-time allocation, not a claim of
exclusive simulation CPU utilisation. Accelerated results describe this emulator
model, not measured physical 030/040/060 hardware. Cache-equivalent results on
040/060 do not establish hardware cache equivalence.

## Prices

Each design column is **remaining render-budget Hz / world reservation %**.
These are arithmetic budgets with zero new-code overhead and a constant measured
non-world cost, **not predicted achieved FPS**. Existing display waits are included;
new phase-6 renderer selection, scheduling phase and changed presentation may alter
that cost. Fractional results do not predict field quantisation.

| Cell | n | world ms mean / p95 | elapsed clock counts | residual ms | B Hz / % | C20 Hz / % | C25 Hz / % | C50 Hz / % | D10 Hz / % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 020-default | 28 | 15.82 / 18.29 | 224450 | 97.18 | 8.8 / 14.0 | 7.0 / 31.6 | 6.2 / 39.6 | 2.2 / 79.1 | 8.7 / 15.8 |
| 020-nocache | 27 | 20.78 / 23.75 | 294783 | 106.88 | 7.8 / 16.3 | 5.5 / 41.6 | 4.5 / 51.9 | 0.0 / 103.9 | 7.4 / 20.8 |
| 030-mmu-default | 30 | 2.23 / 2.64 | 112673 | 37.84 | 25.0 / 5.6 | 25.2 / 4.5 | 25.0 / 5.6 | 23.5 / 11.2 | 25.8 / 2.2 |
| 030-mmu-nocache | 30 | 3.91 / 4.42 | 197120 | 36.17 | 25.0 / 9.8 | 25.5 / 7.8 | 24.9 / 9.8 | 22.2 / 19.5 | 26.6 / 3.9 |
| 030-nommu-default | 30 | 2.23 / 2.63 | 112381 | 37.84 | 25.0 / 5.6 | 25.2 / 4.5 | 25.0 / 5.6 | 23.5 / 11.1 | 25.8 / 2.2 |
| 030-nommu-nocache | 30 | 3.90 / 4.42 | 196837 | 36.17 | 25.0 / 9.7 | 25.5 / 7.8 | 24.9 / 9.8 | 22.3 / 19.5 | 26.6 / 3.9 |
| 040-dcache | 29 | 4.11 / 4.73 | 103654 | 39.75 | 22.8 / 9.4 | 23.1 / 8.2 | 22.6 / 10.3 | 20.0 / 20.5 | 24.1 / 4.1 |
| 040-default | 29 | 4.11 / 4.74 | 103649 | 39.74 | 22.8 / 9.4 | 23.1 / 8.2 | 22.6 / 10.3 | 20.0 / 20.5 | 24.1 / 4.1 |
| 060-dcache | 29 | 3.67 / 4.84 | 185004 | 39.13 | 23.4 / 8.6 | 23.7 / 7.3 | 23.2 / 9.2 | 20.9 / 18.3 | 24.6 / 3.7 |
| 060-default | 29 | 3.67 / 4.84 | 185004 | 39.13 | 23.4 / 8.6 | 23.7 / 7.3 | 23.2 / 9.2 | 20.9 / 18.3 | 24.6 / 3.7 |
| 060-nocache | 29 | 3.67 / 4.84 | 185004 | 39.13 | 23.4 / 8.6 | 23.7 / 7.3 | 23.2 / 9.2 | 20.9 / 18.3 | 24.6 / 3.7 |

For world rate `H`, reservation is `H*S/10` percent, and render budget is
`max(0, 1000-H*S)/R`, with costs in milliseconds. B costs one update per render:
`1000/(S+R)` Hz and `100*S/(S+R)` percent. C is shown at 20, 25 and 50 Hz rather
than silently assuming one finer rate. D uses 10 Hz.

The actual cost must include new work. If `A` is added work per world update and
`P` is added player/presentation work per render, fixed-rate budget becomes
`max(0,1000-H*(S+A))/(R+P)`; B becomes `1000/(S+R+A+P)`. These quantities remain
unmeasured until implementation. As an explicitly assumed sensitivity example,
adding 2 ms per render to D lowers the cached-020 budget from 8.7 to 8.5 Hz and
030 MMU/default from 25.8 to 24.5 Hz. This is not a measurement of interpolation.

At the observed p95 update cost, D reserves 18.3% cached / 23.8% uncached on 020;
C25 reserves 45.7% / 59.4%. C50 already exceeds the uncached 020's entire mean
budget before drawing. These short-window percentiles are not worst-case bounds.
B avoids multiple updates on a slow renderer, but each step then covers more than
the native 100 ms and requires the audited collision/threshold safeguards. D at
10 Hz can require more than one world update per rendered frame on 020; bounded
catch-up is necessary even though simulation alone fits comfortably here.

## Audit and implementation price

All 23 FR findings remain acceptance obligations; a smaller audit means fewer
changed clock policies, not skipped verification. See the per-item policy table
in [the framerate audit](framerate-audit.md).

| Design | Changed-clock and integration work | Preserved work / principal risk |
|---|---|---|
| B | 21 affected findings (FR-01–20,23): scaled movement/rotation, carried fractions, timers and signed counters, AI/action/mission sub-clocks, collision substeps, input/modal boundaries, draw emissions and RNG | FR-21/22 retain VBL clocks and per-event amounts. Broadest elapsed-step conversion; variable collision displacement and nonlinear steering need proof. |
| C | Same 21 affected findings: rescale continuous quantities for the chosen tick, preserve discrete AI/effects/mission opportunities on native sub-clocks, handle catch-up input and widened counters | FR-21/22 retained. Simpler fixed scheduler but multiplied world cost; merely changing constants changes handling and quantisation. |
| D | 11 substantial player/presentation/boundary findings: FR-01,02,11,12,13,15,16,18,19,20,23 | Ten world policies retained at native cadence: FR-03–10,14,17. FR-21/22 retained. Main risk is ownership and event hand-off between responsive controls and discrete world state. |

D still requires a real responsive player path. It must not degenerate into the
rejected design that only interpolates pictures while controls remain at 10 Hz.
Proposed ownership contract for the later implementation:

- Sample held controls each rendered frame and integrate player orientation with
  elapsed time, bounded steps and carried fractions. Keep a separate authoritative
  world snapshot; never write interpolated other-object positions into simulation.
- Consume accumulated player orientation/control input once at the world boundary;
  avoid applying native player steering a second time. Define thrust/afterburner
  duty over that interval so fuel and acceleration remain consistent.
- Latch fire/missile edges and held-fire intent. Launch, charge energy/ammunition
  and apply damage once on a world tick, using an explicitly selected authoritative
  player pose. Gun/missile launches retain up to one tick of scheduling latency;
  responsive view/control response does not promise immediate damage events.
- Use authoritative world positions for collision, range and missile-lock decisions.
  A render-rate aiming indicator may show the current view but must distinguish its
  pending selection from a world-confirmed target/lock. Test thresholds and tunnelling
  at the hand-off; do not assume interpolation improves collision detection.
- Separate draw-bound emissions (FR-15) and HUD/gameplay RNG (FR-16). Rebase both
  clocks at pause and modal transitions; loading creates no catch-up debt.

The exact input history, pose transfer and interpolation storage are phase-9/10
implementation choices to validate against this contract. Do not claim they are
already implemented or that the measured old-world costs prove their overhead.

## Evidence and gate

Retained captures: `tmp/phase8-combat/<cell>/`; reproducible analyser output and
input hashes: `tmp/phase8-combat/report.json`. The capture verifies loaded hunk
layout, fixture hash and every live CPU/cache audit field against the phase-4 cell.
The report rejects incomplete snapshots, incorrect root return stacks, duplicate
boundaries, non-monotonic times and non-unit world/draw counter progression.
A second fresh 020 boot reproduces the selected state and every reported cost
exactly (`tmp/phase8-combat-repeat/020-default/`).
Commands are in [development](development.md#phase-8-design-pricing).

Recommendation is ready for the user to choose B, C (with a tick rate), or D.
The gate in [open work](open-work.md#phase-8--choose-the-decoupling-design-user-decision)
explicitly reserves that choice to the user. No timing patch, phase 9 work or
release work is authorised by this recommendation alone.
