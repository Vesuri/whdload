# Stunt Track Racer

Geoff Crammond's Stunt Car Racer in its North American release, Stunt Track Racer (1989,
MicroPlay), under WHDLoad: a direct slave that loads the game from the first 468480 bytes of
the disk (DIC image `Disk.1`), removes the Rob Northen encryption and copylock, and moves
the disk loader to files. The original slave is by Codetapper (game.conf `AUTHOR`,
`UPSTREAM`); Galahad wrote the turbo mode it carries. It shipped without source:
`src/StuntTrackRacer.s` is a byte-identical reconstruction.
The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands and the ordered next items |
| `docs/development.md` | what differs from the shared workflow: inputs, the build, traps |
| `docs/internals.md` | how it loads, memory, every slave patch, limitations |

The slave source is `src/`; `tools/` is the development harness and never ships.
