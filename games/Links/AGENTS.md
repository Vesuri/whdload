# Links

Links - The Challenge of Golf (Access Software, 1992) under WHDLoad: a Kickstart 1.3
(kick13) slave that boots the game's DOS executables `title` (the intro) and `golf` from
the installed `data/` drawer, skips the game's own cache switch-off and fixes the course
list for course disks; version 2.0b makes it run with the caches on and its code from fast
memory. The original slave is by StingRay (V1.00 13.04.2013, V1.01
28.04.2013) (game.conf `AUTHOR`, `UPSTREAM`). Neither JOTD's nor StingRay's repository holds
it: `src/Links_WHD.s` is the source the whdload.de install package ships.
The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands and the ordered next items |
| `docs/development.md` | what differs from the shared workflow: inputs, the build, driving it |
| `docs/internals.md` | how it loads, memory, every slave patch, limitations |

The slave source is `src/`; `tools/` is the harness: `links.py` (the gdb-stub server with
mouse commands and the route to the first hole), `boot.sh` (boot, route, screenshot) and
`drawcheck.py` and `lzwcheck.py` (the slave's course drawing and unpacker against the
game's, in Unicorn)
([development.md](docs/development.md)).
