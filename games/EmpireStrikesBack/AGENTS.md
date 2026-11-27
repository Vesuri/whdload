# Empire Strikes Back

Empire Strikes Back (Vektor Grafix/Domark, 1989) under WHDLoad: a direct slave that loads the
game from the DIC image `Disk.1`, shows the title picture, saves the high scores and adds a
quit key. The original slave is by Codetapper (game.conf `AUTHOR`, `UPSTREAM`). It shipped
without source: `src/EmpireStrikesBack.s` is a byte-identical reconstruction.
The game is the Star Wars engine's successor; `games/StarWars` holds the fixes this work
brings over.
The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands and the ordered next items |
| `docs/development.md` | what differs from the shared workflow: inputs, the build, traps |
| `docs/internals.md` | how it loads, memory, every slave patch, limitations |

The slave source is `src/`; `tools/` is the development harness and never ships.
