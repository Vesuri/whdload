# Virus

David Braben's Virus (1988, Firebird) under WHDLoad: John Selck's V1.0 direct slave
(15.01.99), which loads the whole disk image into chip memory, hooks the keyboard interrupt
for the quit key and saves the highscores. The original slave is by John Selck (game.conf
`AUTHOR`, `UPSTREAM`); its install package ships no source, so `src/Virus.s` is a
reconstruction that rebuilds the shipped slave byte for byte
([development.md](docs/development.md)).
The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands and the ordered next items |
| `docs/development.md` | what differs from the shared workflow: inputs, the build, driving it |
| `docs/internals.md` | how it loads, memory, every slave patch, limitations |

The slave source is `src/`. There is no `tools/` yet: `make serve` drives it.
