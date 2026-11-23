# Sentinel

Geoff Crammond's The Sentinel (Firebird, 1988) under WHDLoad: a direct slave that loads the
game's program from the RawDIC disk image, replaces its disk loader and keyboard delay, and
skips the protection track. The original slave is by Harry (V1.0, October 1998) and
StingRay (V1.01, 15.09.2017) (game.conf `AUTHOR`, `UPSTREAM`). Neither JOTD's nor StingRay's
repository holds it: `src/Sentinel.s` is the source the whdload.de install package ships.
The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands and the ordered next items |
| `docs/development.md` | what differs from the shared workflow: inputs, the build, driving it |
| `docs/internals.md` | how it loads, memory, every slave patch, limitations |

The slave source is `src/`; `tools/` is the harness: `sentinel.py` (the gdb-stub server and
the route), `render_check.sh`, `edgecheck.py` and `smc_census.py`
([development.md](docs/development.md)).
