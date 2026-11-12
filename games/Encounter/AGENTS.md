# Encounter

Novagen's Encounter (1991, Paul Woakes): JOTD's WHDLoad slave 1.2 with an Enhanced
framerate option (2.0b, 12.11.2026). The original slave is by JOTD (game.conf `AUTHOR`,
`UPSTREAM`): his `E/Encounter/usr` in whdload_slaves at 1635ba0e, which builds on Harry's
slave (1.0, 1.1), credited in the ReadMe.
The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands and the ordered next items |
| `docs/development.md` | what differs from the shared workflow: inputs, the builds (release, VERIFY, the 1.2 reference), the server, the benchmark, equivalence checks, traps |
| `docs/internals.md` | how the game loads, memory map, every slave patch as disk.1 file offsets, the Enhanced path, limitations |

The slave source is `src/EncounterHD.s` with the generated `src/relocs.i`
(`tools/relocs.py`); `src/original/` is 1.2 as upstream has it (the install package's
`source/EncounterHD.asm`). `tools/` is the development harness and never ships:
`encounter.py` (the gdb-stub server), `bench.py` (the level-1 benchmark, with `boot.sh`,
`route.py`, `chipprofile.py` and `dataflow.py`), `codemap.py` (the static code map) and
`statehash.py` (per-step equivalence against 1.2).
