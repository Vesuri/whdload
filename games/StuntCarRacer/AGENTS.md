# Stunt Car Racer

Geoff Crammond's Stunt Car Racer (1989, MicroStyle) under WHDLoad: a direct slave that loads
the game from the first 468480 bytes of the disk (DIC image `Disk.1`), removes the Rob Northen
encryption and copylock, and moves the disk loader to files; with `SCR-TNT` in its drawer it
runs AmiGer/CARE's TNT (The New Tracks) version instead. The original slave is by Codetapper
(v1.0 to v1.3) and StingRay (v1.4) (game.conf `AUTHOR`, `UPSTREAM`); Galahad wrote the turbo
mode it carries and Harry the decryption keys.
The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands and the ordered next items |
| `docs/development.md` | what differs from the shared workflow: inputs, the build, traps |
| `docs/internals.md` | how it loads, memory, every slave patch, limitations |

The slave source is `src/`; `tools/` is the development harness and never ships.
