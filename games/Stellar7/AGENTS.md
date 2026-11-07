# Stellar 7

An experimental fixed-rate conversion of the supplied English NTSC Stellar 7: fixed
real-time simulation at 15 Hz on 68000 and 60 Hz on 68020+, rendering independent of
simulation, no interpolation. Psygore's 1.0 slave shipped without source; `src/Stellar7.s`
reconstructs its startup, so the slave is credited to Psygore (`game.conf` `AUTHOR`).

The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | the plan and where it stands (steps 1–11 are done; 2.0b is published) |
| `docs/development.md` | variants, builds and VERIFY fixtures, the fixed-window driver, rate matrices, packaging, traps |
| `docs/internals.md` | the program, game time, every slave patch, measurements, limitations |
| `README.md` | the summary and how to play the conversion |

The slave source is `src/` (`Stellar7.s` with the SIM60 modules and their VERIFY-only
`*_test.s` fixtures); `tools/` is the development harness and never ships. The three
variants in `game.conf` are builds of the same source, all run as the installed
`Stellar7NTSC.Slave`. `Stellar7` is the release slave: it carries both simulations,
each assembled alone from `src/payload.s` (`game.sh`), and installs the one for the
CPU. `Stellar7-Sim68000` and `Stellar7-Sim60` build one simulation into the slave;
the VERIFY tests use that form. `make play60` runs the release slave with `CUSTOM1=1`.
