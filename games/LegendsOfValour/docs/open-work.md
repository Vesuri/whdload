# Open work — Legends of Valour

Status 2026-10-07: playbook §1–§8 and W0–W6 complete. Fixed-window evidence
and commands are in `docs/profiling.md` §8. W2 uses MEMF_PUBLIC on every CPU;
W3–W5 select their replacements on 68000/10 and retain original code on 020+.
W6 improves the clear on both CPUs. W1–W6 are enabled in local preferences
(mask 63). Frame-rate-independent simulation timing remains required follow-up
work (`docs/performance-plan.md` §2.3.1); W7 remains deferred.

## Done

- Repo, rules, harness copied from Test Drive II (`lov.py`, `barto.py`, `lov_report.py`).
- Slave decoded without source (`tools/slave_info.py`) and rebuilt from the disassembly on WHDLoad
  20.0's kick13 example (`whdload/`), with a VERIFY-only input tape (`whdload/tape.s`).
- `AMIGA2` decrunched offline (`tools/unpack.py`); `lov_report.py` names all 17 hunks, the
  Kickstart and the live slave.
- Benchmark route `tools/tapes/spin.txt` (default character, large view, turning right), driven
  by game-state waits; reproducible fixed window `tools/fixed_window.sh` (two boots identical).
- Frame counter: `frames.py` counts the view's chunky-to-planar display step `h12:05ea6`.
- Baseline: **2.5 fps** on the A500-eq., **12.5 fps** on a 14 MHz 68020; render ~45–53%,
  chunky-to-planar ~26–30%, game logic 6–16% (`docs/profiling.md` §7).

- W0: shared hunk table, CPU/CUSTOM2 tags, disabled-hook checker and original/rebuilt
  first-button-poll comparison completed; startup pointer/timing limitations in §8.
- W1: CPU-selected Kalms C2P, all three sizes, 1,860 pixel twins passed. Spin fps
  2.5 → 3.0 / 12.4 → 14.8 (A500 / 020); matching-scene wall A/B confirms savings.
  Shipped build excludes VERIFY instruments.
- W2: PUBLIC chunky allocation on every CPU, matching owned free and original-pool fallback;
  2,096 pixel twins across all views plus lifecycle/failure checks passed. Ten fixed-window
  captures: 020 spin 14.9 → 16.0 fps, wall 14.2 → 15.1; stock 68000 FPS unchanged.
  W1+W2 enabled in ignored local preferences (mask 3); audit in `docs/w2-audit.md`.
- `swap_fields.py` agrees exactly with the full trace on the A500 fixed window.

## Simulation timing goal (active)

The equal-time drawing-delay experiment now confirms AI coupling on both CPUs:
52 of 56 decoded actor records diverge within each pair despite identical
starting world state. The welcoming townsman is now identified as actor 43;
his initial greeting freezes all actor state and the game clock for 100 fields
on both CPUs. See `docs/timing-investigation.md` for intervals and
limits. Fixed simulation ticks are proposed; 25 ticks/second versus 12.5 is
awaiting the user's choice. No timing patch is implemented or enabled yet.
Player/input, projectile, animation and pause handling must be covered together.

## Open questions

- **Game time (§9).** Heading is `h11:08c28`, player x/y `h11:08c1c`/`08c20`;
  `h12:14b78` reads movement step `h12:0cdd6` when initializing actor speed.
  `docs/timing-investigation.md` maps a persistent 56-record actor table and its
  renderer-driven position/countdown updates; the welcoming townsman is actor 43. The faster spin ends at a different heading
  with unchanged position; frame coupling remains. `tools/lov_state.py` maps visible-object
  render records and the new persistent-state observer identifies the townsman's world position. Deeper AI timing/state
  mapping remains open. W1/W2 retain existing timing; investigate a
  frame-rate-independent simulation step for movement, turning, animation and AI. Compare
  equal elapsed-field intervals across rendering rates, then evaluate elapsed-time scaling
  versus fixed ticks and A500 catch-up costs. See performance-plan §2.3.1 for the work plan.
- The conversation panel polls through h2, so `W` cannot wait for it; the route clicks EXIT
  blindly. A hook on its poll would make the route shorter.
- Entropy: the windows are identical across boots, so VPOSR reads do not leak into this
  route; re-check for any new route.

## Completed rendering patches

- W3: fixed-displacement wall pairs on 68000/10; fixed-wall column cost falls 6.6%.
- W4: eight counted sprite rows on 68000/10; scanned-row costs fall 7.5–9.0%.
- W5: tagged exact-quotient cache on 68000/10; quotient costs fall 1.7–21.3%.
  All eight original continuations have runtime D7/CCR liveness guards.
- W6: backwards MOVEM clear on both CPUs; clear costs fall 38–39% on the
  A500 equivalent and 18–19% on the 020.
- Both-CPU VERIFY runs cover every wall/sprite block, every clear width,
  all three view geometries, all seventeen legal flag reads, and 262,140
  exhaustive reciprocal cases per CPU. Each feature has a separate source commit
  and final fixed-window A/B on both CPUs and both routes.
- Source audit: `docs/w3-w6-audit.md`; full evidence and timing limits: profiling §8.

W7 (column-major layout and other later work) remains deferred by user decision.

Native capture blocking is resolved with the opt-in guest profiler handshake and
explicit PC-base normalization; see [native capture notes](native-capture.md).
Shared assets use ~/.local/share/amiga; projects are separate checkouts. ROM lookup
prefers shared files and retains verified fallbacks for ROMs not moved yet.


## Optional one-degree turning

CUSTOM2 bit 7 adds one-degree rendering and taps, with the existing held-turn
rate retained after 160 ms. Both-CPU table, full-angle ray, legacy-pixel, input
and allocation checks pass. See [the implementation plan](one-degree-turning-plan.md)
and profiling §8 for evidence, setup cost and interactive evaluation status.
The feature is isolated from the unfinished simulation prototype; W7 stays deferred.
