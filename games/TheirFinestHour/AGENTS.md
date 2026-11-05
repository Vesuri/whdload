# Their Finest Hour

A performance study and enhanced slave for the original 1990 Lucasfilm game, run under
Psygore's WHDLoad install (slave v1.1, `data/bob` v1.1, 254 400 bytes, CRC16 `$274F`). There
is no game source: work from cycle-exact FS-UAE traces and disassembly. Psygore's 1.1 slave
shipped without source; `src/TheirFinestHour.s` rebuilds it from its disassembly, so the
slave is credited to Psygore (`game.conf` `AUTHOR`, `UPSTREAM`). Any change to the game ships
as patches in that slave.

The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

- Addresses in docs are `bob` hunk-0 offsets (the slave's `resload_PatchSeg` numbering,
  `bob:OFFSET`).
- Instruments (input tapes, RNG pinning, slow drawing) go in the `VERIFY` build only.
  Every game change is part of Enhanced framerate (off by default); `CUSTOM2=1` enables it.
  With CUSTOM2 unset/0, the enhancement patches leave the original bytes untouched.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands and what is next |
| `docs/development.md` | building, running, driving, tracing or checking the game, or quoting any performance number |
| `docs/internals.md` | the game's code and the slave's patches |
| `docs/framerate-audit.md`, `docs/ai-script-timing.md`, `docs/resource-timing-audit.md` | the frame-rate dependency audit (FR-01 to FR-28) and its regression checks |
| `README.md` | the release summary: what is improved, requirements, options |

The slave source is `src/` (`TheirFinestHour.s` with the game changes in `render.s`,
`transform.s`, `timing.s`, `sound.s`, `replay.s` and the VERIFY-only `verify.s`);
`release/readme-*.txt` are the ReadMe's features and history. `tools/` is the development
harness and never ships: `tools/tfh.py` drives the game through the gdb stub, and
`tools/package_release.py` (`make dist`) repacks Psygore's two archives.
