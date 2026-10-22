# Mercenary 3

Investigation workspace for Mercenary III: The Dion Crisis (Novagen).
Read `docs/open-work.md` and `docs/plan.md` first. The investigation has started: the game boots under
WHDLoad and the slave is documented. Patches come after the playbook's setup is done.

## Rules

- Never commit game, Kickstart, Workbench or WHDLoad bytes, or anything made from
  them (unpacked data, traces, dumps, screenshots, recordings or built slaves).
  Keep downloads, extracted installer source and all generated material in ignored `tmp/`.
- Never `pkill fs-uae` or `pkill gdb`. Use the shared `fsuae_common.sh` helper;
  stop only processes whose ownership by this project has been verified.
- Commits: Vesa Halttunen <vesuri@jormas.com>, unsigned, hooks disabled with
  `core.hooksPath=/dev/null`, no trailers, one commit per coherent change.
  Keep repository-local `commit.gpgsign=false` and `tag.gpgsign=false`.
- Document code addresses as file or code-hunk offsets, never runtime addresses.
- No performance claims without measurements from the appropriate instrument.
- No local paths or usernames in tracked files. Name other projects without paths.
  Shared files use overridable variables from `~/.local/share/amiga/env.sh`;
  `~/.local` is the allowed installation convention. Scratch output belongs in `tmp/`.
  Kickstart and Workbench sources are user-supplied; never record mirror URLs.
- Pin inputs by SHA-256 in `manifest/` and verify before extraction or use.
- Preserve differing existing files; never silently overwrite local edits or inputs.
- History belongs in git; update current-state documentation in place.
- Shell scripts must work with macOS `/bin/bash` 3.2.
- Before changing another project, check its git status. Leave dirty projects alone.

## Guidance

- `docs/open-work.md`: current scope, findings and decisions.
- `docs/plan.md`: the step-by-step plan (step IDs, dependencies, done criteria).
- `docs/development.md`: inputs, verification and shared environment.
- `docs/internals.md`: the slave, the boot and the game's memory layout.
- AmigaXDev `docs/index.md`: shared topic routing; its standalone WHDLoad
  playbook provides guidance when investigation is authorized.
