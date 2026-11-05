# Current scope

The user goal to finish measurement plan A is complete.

- A1: source rebuild validated; normal output matches the initial rebuild. The
  shipped difference is explained and all 119 pristine files remain unchanged.
- A2: VERIFY CUSTOM2 fixes the mission; all five CPUs and extra menu dwell agree.
  Seed 2 changes it. The controlled five-CPU take-off matrix is retained.
- A3: take-off, stationary airborne hover and authored ground attack with three
  visible ground targets plus an enemy helicopter are established. Nine required
  500-VBL windows pass; fps, tick rate and pacing timestamps are retained.
- A4: independent boots match across all 8 MiB fast RAM at ticks 100–102. Adjacent
  ticks differ. The comparison gate is ready for C; cross-CPU equality after the
  timing changes is still a C acceptance requirement.
- A5: bounded completed-swap log, overflow rejection and read-only retrieval work
  on all five CPUs. All 128 assembled-hook register/CCR/bounds cases pass.

Evidence and commands: `docs/measurement-a.md`; final acceptance:
`tmp/a-final/acceptance.json`. Source changes are committed as `8430132`.
User preference: commit each coherent whole as it is completed.

B is complete: default safe blitter waits (1d3250b), cache audit, and matched-tick
graphics/cache validation. Evidence: docs/measurement-b.md and tmp/b/acceptance.json.
C–G remain open in docs/PERFORMANCE_PLAN.md. C1 is resolved: exactly 3 ticks/s, so the native Elapsed Time display matches
real time (e8c65f6). C4 baseline pricing is committed (a7af2e9). The user then
selected the Wing Commander hybrid (679c275): the world stays at 3 Hz, while
controls are sampled per field and the player's own motion is integrated per
field; other objects get bounded renderer-only prediction. Extrapolation alone
was rejected because input stays at 3 Hz. No C runtime implementation exists
yet; C5c is (a): weapons launch at the next world tick, for now. See the tracked plan. T-74 graphics remains deferred. Original German
and real-hardware coverage remain release limitations; full-MMU asynchronous
blitter emulator rendering needs followup under F4. Preserve shared-harness
changes; session_a.py pins legacy protocol and session_b.py serves native MMU tests.
