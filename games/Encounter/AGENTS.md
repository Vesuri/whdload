# Encounter

Novagen's Encounter (1991, Paul Woakes) as JOTD's WHDLoad slave 1.2, brought in unchanged;
no improvement work has been done yet. The original slave is by JOTD (game.conf `AUTHOR`,
`UPSTREAM`): his `E/Encounter/usr` in whdload_slaves at 1635ba0e, which builds on Harry's
slave (1.0, 1.1), credited in the ReadMe.
The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands and the ordered next items |
| `docs/development.md` | what differs from the shared workflow: inputs, the build against the shipped slave, the server, traps |
| `docs/internals.md` | how the game loads, memory map, every slave patch as disk.1 file offsets, limitations |

The slave source is `src/` (`EncounterHD.s`, the install package's `source/EncounterHD.asm`);
`tools/` is the development harness (`tools/encounter.py`, the gdb-stub server;
`tools/bench.py`, the level-1 benchmark, with `boot.sh`, `route.py` and `chipprofile.py`)
and never ships.
