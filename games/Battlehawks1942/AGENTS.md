# Battlehawks 1942 (Amiga) — performance study

Profiling the ORIGINAL 1989/1990 Lucasfilm Games flight game (PAL v1.0), run under Galahad's
WHDLoad install (slave v1.0, 12/05/03, Retroplay pack `tmp/Battlehawks1942_v1.0_0053.lha`).
No game source and no slave source: Galahad's slave is reconstructed in
`whdload/original/Battlehawks1942.s` (rebuilds byte-identically, `make -C whdload original`).
The slave we build and patch is `whdload/Battlehawks1942.s` (WHDLoad 20 KickEmu, 512 KB chip
+ 512 KB fast memory). Work from cycle-exact FS-UAE traces and disassembly. Any change to the
game is meant to ship as WHDLoad slave patches. Goal: frame-rate-independent gameplay, 50 fps
on faster Amigas.

## Shared environment and knowledge

The shared environment comes from AmigaXDev, the repository next to this one: `make setup`
there installs `~/.local` and `~/.local/share/amiga`, and `amiga/env.sh` sources
`~/.local/share/amiga/env.sh`. The generic tools (trace reader, disassembly, ADF, patch lists,
the gdb server under `tools/bh.py`) are AmigaXDev's `amigaxdev` Python package; `tools/` holds
only this game's. The method and the lessons the projects share are in AmigaXDev:

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

- **Never commit game, Kickstart or WHDLoad bytes**, or anything made from them: disk images,
  extracted files, traces, memory dumps, screenshots, input recordings, built slaves. They live
  in `tmp/` (ignored).
- Addresses in docs are **`bh:` hunk-0 offsets of the game executable `BH`** (on `Disk.1`),
  `bh-data:` data-hunk offsets, `kick:` ROM addresses (`$FC0000`-based), or `slave:` offsets
  (the `Lxxx` labels) — never absolute addresses.
- Commits: author Vesa Halttunen <vesuri@jormas.com>, unsigned, no hooks, no Co-Authored-By lines.
  One commit per coherent feature.
- Never `pkill fs-uae` or `pkill gdb` (other projects run emulators): `fsuae_common.sh` kills only
  our own pid.
- No performance claim without a measurement from the right instrument (`docs/profiling.md`).
- Instruments (the input tape, experiments, anything that changes behaviour for measurement)
  go in the `VERIFY` build only. Game patches for players go behind an option.
- Only what DMA needs belongs in chip RAM; everything else in public memory (fast when there
  is any). BH already allocates that way; keep it so in any patch.
- Never edit a script while a capture is running it (bash reads scripts as it goes).

## Reference docs — read before working in the area

| Doc | Read it when |
|---|---|
| `docs/open-work.md` | **First.** What is known, what is not, ordered work items |
| `docs/profiling.md` | Running the game, driving it, tracing it, or quoting any performance number |
| `docs/c2p.md` | Touching the chunky-to-planar pass |
