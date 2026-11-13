# Star Wars

Star Wars (Domark, 1988) under WHDLoad. The slave is StingRay's v2.00 (10.08.2016) as his
installer ships it, plus always-on fast-CPU fixes (`src/StarWarsFixes.s`) and CUSTOM2
"Enhanced framerate", 50 frames a second at the game's speed (`src/StarWarsSmooth.s`).
The original slave is by StingRay (game.conf `AUTHOR`, `UPSTREAM`): neither his WHDLoad
patches repository nor JOTD's holds it, so `src/StarWars_WHD.s` is the source from his
installer (`StarWars_Install/Source/StarWars_WHD.s`).
The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands and the ordered next items |
| `docs/development.md` | what differs from the shared workflow: inputs, the build against the shared WHDLoad tree, traps |
| `docs/internals.md` | how the game loads, Kickstart use, game time, every slave patch |

The slave source is `src/`; `tools/` is the development harness and never ships.
