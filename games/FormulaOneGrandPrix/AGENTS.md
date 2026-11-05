# F1GP — Formula One Grand Prix

## Scope

The launcher (`amiga/run.sh`, `tools/f1gp.py`) boots the game to gameplay, and the slave
loader and executable layout are documented. The work follows the steps
in `docs/plan.md`; take them when the user asks. The supplied install uses Codetapper's v1.0 slave;
no slave source is available.

Read `docs/open-work.md` first. Shared guidance starts at AmigaXDev
`docs/index.md`; the relevant workflow is `docs/playbooks/new-game-playbook.md`.
The current task takes precedence over that playbook's full setup workflow.

## Rules

- Never commit game, Kickstart, Workbench, WHDLoad or derived bytes, including
  unpacked data, built slaves, traces, dumps, screenshots and recordings.
  Keep them in ignored `tmp/`. Keep original inputs immutable.
- Pin inputs by SHA-256 in `manifest/` and verify them before extracting or using
  them. Never overwrite changed shared files. Shared setup moves differences to
  `.replaced/`; use AmigaXDev's `make pull-shared` for shared edits. WHDLoad
  developer packages retain only the latest verified installation, without backups.
- No machine-specific paths or paths into other projects in tracked files.
  Name other projects without their location. Use `amiga/env.sh` and overridable
  shared variables under `~/.local` and `~/.local/share/amiga`. Scratch goes in
  `tmp/`. Kickstart and Workbench sources are user-supplied (`TOSEC=`, `AMIGA_OS=`);
  never record mirror addresses for them.
- Never `pkill fs-uae` or `pkill gdb`. Use the shared `fsuae_common.sh` and stop
  only verified project-owned process IDs.
- Document addresses as game code-hunk or file offsets, not runtime addresses.
  No performance claims without appropriate measurements.
- Commits: author and committer Vesa Halttunen <vesuri@jormas.com>, unsigned,
  `core.hooksPath=/dev/null`, no trailers, one commit per coherent change.
  Set repository-local `commit.gpgsign=false` and `tag.gpgsign=false` when creating
  or cloning a personal repository and verify both effective values.
- Shell scripts must work with macOS `/bin/bash` 3.2.
- History belongs in git. Update current documentation in place.
- Agent instructions belong in `AGENTS.md`; `CLAUDE.md` only imports it.
- Before touching another project, check its git status. Leave dirty projects
  alone and report them. Follow its own instructions and commit conventions.
