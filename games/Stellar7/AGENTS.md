# Stellar 7

Read `docs/open-work.md` first, then `docs/development.md` and `docs/internals.md`.

## Shared environment and knowledge

The shared environment comes from AmigaXDev, the repository next to this one: `make setup`
there installs `~/.local` and `~/.local/share/amiga`, and `amiga/env.sh` sources
`~/.local/share/amiga/env.sh`. The method and the lessons the projects share are in AmigaXDev:

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

- **Never commit game, Kickstart or WHDLoad bytes**, or anything made from them: unpacked data,
  traces, memory dumps, screenshots, input recordings, built slaves. Keep them in `tmp/`, which
  is ignored. The `.gitignore` ignores `tmp/` and `*.lha *.adf *.rom *.slave *.bin *.png
  *.rec` at any depth.
- **Never `pkill fs-uae` or `pkill gdb`.** Other projects run emulators at the same time. Use
  `~/.local/share/amiga/fsuae_common.sh`, which kills only the pid this directory started and
  gives each directory its own gdb-stub port. Kill orphans of your own (a `serve`, a `gdb`, an
  FS-UAE that crashed and left its window up) by pid, after checking the pid is yours.
- Commits: use whatever author, signing, hooks and trailer conventions the user gives. In this
  repo that is `Vesa Halttunen <vesuri@jormas.com>`, unsigned, `core.hooksPath=/dev/null`, no
  Co-Authored-By lines, one commit per coherent feature. Ask if you're not told.
- Addresses in docs are **offsets into the game's code hunk or file**, using the same numbering
  as the slave's patch lists. Never quote absolute addresses, because they move with the memory
  configuration.
- **No performance claim without a measurement**, and only from the right instrument (AmigaXDev `docs/playbooks/new-game-playbook.md` §7, §8).
- **No local paths in the repo**: no user-specific absolute paths or paths into other projects. Name another project without its location
  ("AmigaXDev `docs/playbooks/new-game-playbook.md`"). Shared files come from `~/.local/share/amiga`
  (AmigaXDev) through the overridable variables of the shared `env.sh`, which `amiga/env.sh` sources (§1); scratch output goes to the repo's ignored
  `tmp/`, never `/tmp`. `~/.local` and `fsuae_common.sh` are the allowed convention.
- **History belongs in git.** Docs describe the current state (how to build, run and measure; how
  the game and the patches work; current numbers; open items). When a finding changes, update the
  reference in place instead of appending a dated section, and delete tools nothing uses.

