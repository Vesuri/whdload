# Open work — Legends of Valour

## State

- The slave is rebuilt from CFou!'s v1.0 disassembly on WHDLoad 20.0's kick13 example
  (`src/`), with a VERIFY-only input tape and instruments. Release 1.1b (beta) is built by
  `make dist` (`tools/release.py`, `docs/releasing.md`).
- W1–W6 rendering patches are always on in release builds and individually switchable in
  developer/VERIFY builds (`docs/performance-patches.md`). Spin route: 2.5 → 3.2 fps on the
  A500-equivalent, 12.4 → 16.1 fps on a 14 MHz 68020 (`docs/profiling.md` §9).
- Optional, off by default: frame-independent game timing, CUSTOM2 bit 6
  (`docs/simulation-timing.md`). One-degree direct mouse precision is automatic in
  release builds; UI turn buttons retain native behavior (`docs/one-degree-turning.md`).

## Open

- **Mouse precision:** accepted in play testing. The requested native-button behavior
  replaces one-degree button taps; further play feedback is welcome.
- **Game timing:** automated checks pass; subjective play feedback may still lead to changes.
  Re-run the affected comparisons in `docs/simulation-timing.md` after any change.
- **Conversation panel:** it polls through h2, so a tape `W` entry cannot wait for it and routes
  click EXIT blindly every 100 fields. A hook on its poll would make routes shorter and remove the
  risk of a window that starts inside a conversation.
