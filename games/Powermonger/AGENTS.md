# Powermonger

Bullfrog's Powermonger (1990, Electronic Arts) under WHDLoad: Wepl's direct DIC slave,
v1.4.1 (19.02.2025), with the v1.4 fast-memory drawing and frame-rate cap by Paraj and Wepl.
Version 2.0b adds Enhanced framerate (CUSTOM4: the world at the A500's pace, drawing as fast
as the machine allows, and with fast memory copying only changed screen parts to chip memory). The
original slave is by Wepl, updated by Paraj (game.conf `AUTHOR`, `UPSTREAM`).
The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands and the ordered next items |
| `docs/development.md` | what differs from the shared workflow: inputs, tools, captures, traps |
| `docs/internals.md` | the program, game time, every slave patch, measurements, limitations |

The slave source is `src/`; `tools/` is the development harness and never ships.
