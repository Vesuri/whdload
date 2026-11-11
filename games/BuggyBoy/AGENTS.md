# Buggy Boy

Elite's Buggy Boy (1988) as Codetapper's WHDLoad slave
1.3, being improved as Buggy Boy Enhanced 2.0b (not released yet). The slave is by
Codetapper/Action (1.0 to 1.2, 2001; 1.3, 13.04.2022, added the frame rate control and the
trainer), credited in the ReadMe and the source header. Its source is kept in JOTD's
whdload_slaves (`B/BuggyBoy/usr` at eb73c315), so game.conf `AUTHOR` is JOTD and `UPSTREAM`
that path.
The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands and the ordered next items |
| `docs/development.md` | what differs from the shared workflow: inputs, the build against the shipped slave, traps |
| `docs/internals.md` | the versions the slave supports, how it loads, memory, every slave patch, frame rate control |

The slave source is `src/` (`BuggyBoyHD.s` with `ReadJoypad.s` and `Enhanced.s`, the
2.0b path for a 68020 or better; `BuggyBoy.islave.s` is the
RawDIC imager slave for the disk versions, not assembled here). `game.sh` generates the
`keyboard.s` the build uses ([development.md](docs/development.md)). `tools/` is the
harness: `buggyboy.py` (the gdb-stub server), `boot.sh`, `route.py`, `bench.py` (the race
benchmark), `chipprofile.py`, `states.py` and `verify.py`.
