# Gunship

Gunship 2.0b: optional enhanced framerate for the PAL (SPS 0658) and NTSC (SPS 1489)
releases of MicroProse's Gunship on 68020 and later. The world keeps its 3 Hz pace, while
controls and the helicopter's own motion run per field and other objects are predicted for
display (`CUSTOM1=1`, with a CPU renderer by default, `CUSTOM4`). The original slave is by
JOTD (game.conf `AUTHOR`, `UPSTREAM`): his `G/Gunship/usr` in whdload_slaves at ce5a2a25.

The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the measurement and timing work stands; the open items are in the plan |
| `docs/PERFORMANCE_PLAN.md` | the plan (A–G), each item's status, evidence and release limitations |
| `docs/TIMING_DESIGN.md` | the current timing design: ownership, source map, evidence, demo and release checks |
| `docs/PLAYER_STATE_INVENTORY.md` | the player-state field and writer inventory behind the timing work |
| `docs/CACHE_AUDIT.md`, `docs/cache-audit-b.md` | writable hunk-0 data, self-modifying code and cache policy |
| `docs/development.md` | inputs, builds, runs, the session library and the measurement tools, traps |
| `docs/measurement-a.md`, `docs/measurement-b.md` | plans A and B: reproducible commands and acceptance |
| `docs/analysis/` | the program: frame structure, interrupts, 3D renderer, time model, profiles |

The slave source is `src/` (`GunshipHD.s`, the `timing-*.i` runtime, `blitter.i` and the
VERIFY-only `verify.i`); `tools/` is the development harness and never ships, with the FS-UAE
patches its emulator builds need in `tools/patches/`. The two variants in `game.conf` are
builds of the same source, each run in its own installed drawer.
