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

Shared Amiga guidance starts at AmigaXDev's `docs/index.md`, installed as
`~/.local/share/amiga/docs/index.md`. Its WHDLoad playbook is the method; a game's current
task takes precedence over the playbook's full setup workflow. Generic lessons go there
(edit them in AmigaXDev); this repository keeps what is specific to these games.

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
