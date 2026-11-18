# Archipelagos

Astral Software's Archipelagos (1989, published by Logotron) under WHDLoad: StingRay's
direct slave, which loads the game's Atari ST format program and its data as real files,
relocates it and patches out the disk loader and both protections. The original slave is by
StingRay (game.conf `AUTHOR`, `UPSTREAM`); John Selck wrote the v1.0 patch (1999) that
StingRay's v1.1 replaced. Neither JOTD's nor StingRay's repository holds it:
`src/ArchipelagosFiles_WHD.s` is the v1.1 source from the whdload.de install package, with
StingRay's v1.2 (31.08.2023) changes reconstructed from the slave the Retroplay archives
install ([development.md](docs/development.md)).
The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands and the ordered next items |
| `docs/development.md` | what differs from the shared workflow: inputs, the build, driving it, traps |
| `docs/internals.md` | how it loads, memory, every slave patch, limitations |

The slave source is `src/`; `tools/` boots, routes, counts frames and profiles
([development.md](docs/development.md#routes-and-profiling)).
