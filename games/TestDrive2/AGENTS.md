# Test Drive II (Amiga) — WHDLoad slave patches

Improving the ORIGINAL 1989 Amiga game, run under JOTD's WHDLoad install (`duel` v1, 108 868
bytes). No game source: work from cycle-exact FS-UAE traces and disassembly. Every change to the
game ships as WHDLoad slave patches (`resload_PatchSeg` patch lists in `whdload/`).

## Shared environment and knowledge

The shared environment comes from AmigaXDev, the repository next to this one: `make setup`
there installs `~/.local` and `~/.local/share/amiga`, and `amiga/env.sh` sources
`~/.local/share/amiga/env.sh`. The generic tools (trace reader, disassembly, the gdb server
under `tools/td2.py`) are AmigaXDev's `amigaxdev` Python package; `tools/` holds only this
game's. The method and the lessons the projects share are in AmigaXDev:

| AmigaXDev doc | Holds |
|---|---|
| `docs/playbooks/new-game-playbook.md` | the method this repo follows |
| `docs/playbooks/new-game-playbook-hardware.md` | black screens and dumps on real Amigas, CPU caches |
| `docs/playbooks/whdload-mmu.md` | MMU compatibility and crash diagnosis |
| `docs/playbooks/fixed-time-simulation.md` | game time, fixed ticks, input per tick, raising the update rate |
| `docs/playbooks/simulation-and-presentation.md` | uncapped drawing, interpolation, smaller timesteps |
| `docs/environment.md` | the shared variables |
| `docs/reference/headless-fsuae.md` | the shared launcher, FS-UAE builds, the gdb stub |
| `docs/reference/measurement-method.md` | instruments, A/B discipline, pricing a change |
| `docs/reference/m68k-optimisation.md` | 68000/68020 cost model and code rules |
| `docs/reference/amiga-hardware.md` | Chip bus, FMODE, copper, blitter, caches |

Generic lessons go into those docs (edit them in AmigaXDev); this repository keeps what is
specific to this game.


## Rules

- **Never commit game, Kickstart or WHDLoad bytes**, traces, memory dumps or screenshots. They live
  in `tmp/` (ignored). No machine-specific paths either: shared files come from `~/.local/share/amiga`
  through the variables in `amiga/env.sh`. Addresses in docs are `duel` hunk-0 offsets (the slave's patch numbering).
- Commits: author Vesa Halttunen <vesuri@jormas.com>, unsigned, no hooks, no Co-Authored-By lines.
  One commit per coherent feature.
- Never `pkill fs-uae` (other projects run emulators): `fsuae_common.sh` kills only our own pid.

## Reference docs — read before working in the area

| Doc | Read it when |
|---|---|
| `docs/open-work.md` | **First.** The goal, working rules, open items and dropped decisions |
| `docs/game.md` | Reading or patching game code: addresses, tasks, time sources, state map, frame costs |
| `docs/simulation-design.md` | Changing the fixed-time simulation or its VERIFY fixtures |
| `docs/subunit-rendering.md` | Changing fractional road/car projection, sideways or hill smoothing |
| `docs/testing.md` | Running, tracing or testing the game, or quoting any performance number |

Docs describe the current state only; history belongs in git history.
