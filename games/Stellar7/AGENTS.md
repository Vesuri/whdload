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
| `docs/open-work.md` | the plan, where it stands and the remaining step 11, the release (steps 6–10 are done) |
| `docs/development.md` | variants, builds and VERIFY fixtures, the fixed-window driver, rate matrices, packaging, traps |
| `docs/internals.md` | the program, game time, every slave patch, measurements, limitations |
| `README.md` | the summary and how to play the conversion |

The slave source is `src/` (`Stellar7.s` with the SIM60 modules and their VERIFY-only
`*_test.s` fixtures); `tools/` is the development harness and never ships. The three
variants in `game.conf` are builds of the same source, all run as the installed
`Stellar7NTSC.Slave`. `make play60` picks the variant from the machine's CPU.
