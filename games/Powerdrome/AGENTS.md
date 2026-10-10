# Powerdrome development

- **Never commit game, Kickstart or WHDLoad bytes**, or anything made from them: unpacked data,
  traces, memory dumps, screenshots, input recordings, built slaves. Keep them in `tmp/`, which
  is ignored. Copy `.gitignore` from the TD2 repo verbatim. It also ignores `*.lha *.adf *.rom
  *.slave *.bin *.png *.rec` at any depth.
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
- **No performance claim without a measurement**, and only from the right instrument (§7, §8).
- **No local paths in the repo**: no home directories, usernames, `~/Documents/...`, RetroPie or
  amiberry locations, and no paths into other projects. Name another project without its location
  ("AmigaXDev `docs/playbooks/new-game-playbook.md`"). Shared files come from `~/.local/share/amiga`
  (AmigaXDev) through the overridable variables of the shared `env.sh`, which `amiga/env.sh` sources (§1); scratch output goes to the repo's ignored
  `tmp/`, never `/tmp`. `~/.local` and `fsuae_common.sh` are the allowed convention.
- **History belongs in git.** Docs describe the current state (how to build, run and measure; how
  the game and the patches work; current numbers; open items). When a finding changes, update the
  reference in place instead of appending a dated section, and delete tools nothing uses.


## Read first

- `docs/open-work.md`: current status and next work.
- `docs/development.md`: setup, build, run and measurement.
- `docs/internals.md`: game, slave, timing and measured results.
