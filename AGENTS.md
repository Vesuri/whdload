# Personal repository commit rules

- This is a personal project. Keep work-related identities, accounts, metadata,
  configuration, and content out of commits and repository activity.
- Use Vesa Halttunen <vesuri@jormas.com> for both author and committer.
- Use the Vesuri GitHub account for all GitHub operations. Verify the active
  account before using the GitHub CLI; never use a work account here.
- Do not sign commits, tags, or pushes.
- Do not run Git hooks. Keep core.hooksPath set to /dev/null.
- Do not add Co-Authored-By trailers or other assistant attribution to commits.
- Before committing, verify the effective author and committer identities and
  signing/hooks settings, including any environment overrides.

# WHDLoad

Improved WHDLoad slaves for Amiga games, released here when the original maintainer
does not take the changes. Each game is a directory under `games/` with its own
`AGENTS.md` and `docs/`; shared build, run and release scripts are in `common/` and shared
docs are in `docs/`.

Working on a game: read its `AGENTS.md`, then its `docs/open-work.md`. For anything about
the repository (layout, running, building, releasing, bringing a game in) start at
`docs/index.md` and read only the rows that match the task. `make list` shows the games;
`make run` inside a game directory boots it (`docs/running.md`).

## The shared environment (AmigaXDev)

AmigaXDev's `make setup` installs every tool, reference and input under `~/.local`; it is
all already there, so do not search the disk or download anything. `common/env.sh` (sourced by
every `make` target) sources `~/.local/share/amiga/env.sh`, which exports the variables below
and puts the shared `python3`, the m68k cross tools, `vasmm68k_mot` and the native `fs-uae`
on `PATH`. In a bare shell, run `. common/env.sh` first. Paths in tracked files use the
variables, never the expanded paths. `$AMIGA_SHARE` is `~/.local/share/amiga`.

**Shared learnings.** Start at `$AMIGA_SHARE/docs/index.md`: a task and symptom table that
routes to the rest. The WHDLoad playbook `docs/playbooks/new-game-playbook.md` is the method,
with `-jotd`, `-stingray` and `-hardware` variants beside it. A game's current task takes
precedence over the playbook's full setup workflow. Most-used references under `docs/`:

| Doc | For |
|---|---|
| `reference/amiga-hardware.md` | Chip bus, copper, blitter, Paula, DMA, interrupts, OS handback |
| `reference/m68k-optimisation.md` | 68000 to 060 instruction costs and code rules |
| `reference/measurement-method.md` | profiling, instruments, A/B discipline (before any performance claim) |
| `reference/headless-fsuae.md` | FS-UAE builds, named machine setups, the gdb stub, screenshots |
| `reference/validation-harness.md` | equivalence proofs, fixtures, gameplay validation |
| `playbooks/fixed-time-simulation.md`, `simulation-and-presentation.md` | game time, higher update rates, interpolation |
| `playbooks/whdload-mmu.md`, `new-game-playbook-hardware.md` | MMU faults; crashes and black screens on real Amigas |
| `environment.md` | every variable and every shared tool, in full |

Generic lessons go into AmigaXDev's `docs/` (edit them in AmigaXDev, then `make share`
there), never into the installed copy. This repository keeps what is specific to these games.

**References.**

| What | Where |
|---|---|
| Hardware Reference Manual (OCS/ECS) | `$ADCD/ROM_Kernel_Manuals/Hardware_Manual` (AmigaGuide text); `$ADCD/HTML/Hardware_Manual_guide/node*.html` (grep these) |
| AGA registers | `$AGA_GUIDE` |
| ROM Kernel Manuals, Amiga Mail, 2.0/3.5 autodocs | `$ADCD/ROM_Kernel_Manuals/` (`Libraries_Manual`, `Devices_Manual`, `Autodocs`, `Includes`), `$ADCD/HTML/` |
| NDK 3.2 | `$AMIGA_SHARE/ndk/` (`Autodocs/`, `Include_I/`, `Include_H/`, `FD/`, `SFD/`); vasm uses `$NDK` |

**The WHDLoad developer package** (20.1) is at `$WHDLOAD`:

| What | Where |
|---|---|
| Slave API: `resload_*`, `PL_*` patch lists, slave header | `$WHDLOAD/Autodoc/whdload.doc`, `$WHDLOAD/Include/whdload.i`, `whdmacros.i` |
| User docs: options, tooltypes, cache, MMU, FAQ | `$WHDLOAD/Docs/en/*.html` |
| KickEmu (`kick13.s`, `kick31.s`, `kickfs.s`, ...), blitter fixes, `savegame.s`, `keyboard.s` | `$WHDLOAD/Src/sources/whdload/` |
| Example slaves (incl. `kick12`, `kick13`, `kick31`) and imagers | `$WHDLOAD/Src/slave-examples/`, `$WHDLOAD/Src/imager-examples/` |
| Install script template | `$WHDLOAD/Install Template/` (`Xxx Install`, `ReadMe`) |
| WHDLoad executable, RawDIC, Patcher, WHDInfo; QA slaves | `$WHDLOAD/C/`, `$WHDLOAD/Extra/`; `$WHDLOAD/Src/qa/` |
| Commodore Installer 43.3 | `$INSTALLER43` |

**Inputs.**
- Kickstarts: `$AMIGA_SHARE/Kickstarts/` (1.2, 1.3, 2.04, 3.1 A600, 3.1 A1200, each with its `.RTB`); `$KICKSTART`, `$KICKSTART_A1200` and `$KICK13`.
- Workbench 2.04: `$WORKBENCH_ADF`.
- SetPatch 40.16: `$SETPATCH`.

**Tools.**

| Need | Use |
|---|---|
| Assemble | `vasmm68k_mot` (`$VASM`); `common/build.sh` adds `-I$AMIGA_INCLUDE -I$WHDLOAD/Include -I$WHDLOAD/Src/sources -I$NDK` |
| Disassemble a dump or hunk | `python3 -m amigaxdev.disasm dis\|disd\|hotspots ...` (objdump underneath, `--cpu 68020` and up); `m68k-amiga-elf-objdump -D -b binary -m m68k:68000` |
| Hunk files | `hunktool` (amitools), `python3 -m amigaxdev.patchlist SLAVE OFFSET` decodes a slave's patch list |
| Disk images | `xdftool`, `xdfscan`, `rdbtool` (amitools, on `PATH` from the shared venv); `python3 -m amigaxdev.adf DISK` |
| Static analysis | Ghidra in `~/.local/share/ghidra/ghidra_<version>_PUBLIC/` (`support/analyzeHeadless`), with the shared scripts `$AMIGA_GHIDRA_SCRIPTS` (`ExportListing`, `DumpCallGraph`, ...) |
| Debug, trace, profile | `m68k-amiga-elf-gdb` against the FS-UAE gdb stub, through `common/tools/game_server.py` (`amigaxdev.gdbserve`: `stop`, `cont`, `shot`, `profile`, `wait`, `until`); traces through `amigaxdev.barto`, `callprofile` and `aprof` |
| Emulators | `fs-uae` (`$FSUAE_ARM`), the cycle profiler `$FSUAE_APROF`, the 040/060 MMU fix `$FSUAE_MMU`; the other `$AMIGA_SHARE/fs-uae-*` are diagnostic builds (`reference/headless-fsuae.md`, "Which FS-UAE"), and `fs-uae-src/` is the source |
| Release archives | `$LHA` (LHa for UNIX); `amigaxdev.release` |
| Python with Pillow, numpy, capstone, amitools and `amigaxdev` | the shared `python3` |
| CPU emulation in tools | Unicorn 2.1.4 with the arm64 fix: `$AMIGA_UNICORN/lib/libunicorn.2.dylib` (ctypes; no Python binding is installed) |
| Emulator processes | `$FSUAE_COMMON` (`fsuae_common.sh`): pid-scoped start and stop, a gdb port per run directory |

## Rules

- Never commit game, Kickstart, Workbench, WHDLoad or derived bytes, including
  unpacked data, built slaves, release archives, traces, dumps, screenshots and
  recordings. Keep them in ignored `tmp/` (each game's own) and `dist/`. Keep original
  inputs immutable.
- Pin inputs by SHA-256 and verify them before extracting or using them. Never
  overwrite changed shared files. Shared setup moves differences to `.replaced/`; use
  AmigaXDev's `make pull-shared` for shared edits. WHDLoad developer packages retain
  only the latest verified installation, without backups.
- No machine-specific paths or paths into other projects in tracked files.
  Name other projects without their location. Use the overridable shared variables
  under `~/.local` and `~/.local/share/amiga`. Scratch goes in `tmp/`, never `/tmp`.
  Kickstart and Workbench sources are user-supplied (`TOSEC=`, `AMIGA_OS=`); never
  record mirror addresses for them.
- Never `pkill fs-uae` or `pkill gdb`. Use the shared `fsuae_common.sh` and stop
  only verified project-owned process IDs.
- Document addresses as game code-hunk or file offsets, not runtime addresses.
  No performance claims without appropriate measurements.
- Credit the original slave author in every game's docs and release ReadMe, and record
  where its source came from.
- Commits: one commit per coherent change. Other sessions may be working on other games
  in this working tree at the same time: commit only your own paths with
  `git commit --only -- <paths>`, never `git add -A` or `git commit -a`, and leave other
  games' uncommitted changes alone. Changes to shared files (`common/`, `docs/`, the
  root) are separate commits and must not change any other game's release bytes.
- Shell scripts must work with macOS `/bin/bash` 3.2.
- History belongs in git. Update current documentation in place.
- Agent instructions belong in `AGENTS.md`; there is no `CLAUDE.md`.
