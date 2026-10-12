# Wing Commander

Standalone WHDLoad improvement project for the OCS disk and CD32 versions.
Current scope: phase 4 baseline profiling of the CD32 intro machine matrix.
Runtime measurements, VERIFY-only cache audits and controlled rendering-ceiling
experiments are authorised. Derived material stays in ignored `tmp/`. Stop at
the phase 4 gate; do not start phase 5, release patches or OCS analysis.
Psygore authored the original v1.0 slaves; source code is unavailable.

## Rules

- Never commit game, Kickstart, Workbench or WHDLoad bytes, or anything made from
  them: unpacked data, disassemblies, traces, dumps, screenshots, input recordings
  and built slaves stay in ignored `tmp/`.
- Never `pkill fs-uae` or `pkill gdb`. Use the shared `fsuae_common.sh` and only
  stop this project's processes, checking ownership before killing a PID.
- Commits: author and committer `Vesa Halttunen <vesuri@jormas.com>`, unsigned,
  `core.hooksPath=/dev/null`, no Co-Authored-By or other trailers; one coherent
  change per commit.
- Addresses in documentation are code-hunk or file offsets, not runtime addresses.
- No performance claims without measurements from the appropriate instrument.
- No local paths in the repository: no home directories, usernames or paths into
  other projects. Name projects by name. Shared files use overridable variables
  from `amiga/env.sh`; `~/.local` and `~/.local/share/amiga` are the conventions.
  Scratch output belongs in `tmp/`, never in a system temporary directory.
- Pin downloaded inputs by SHA-256 in `manifest/`; verify before extracting or
  using them. Never overwrite changed local inputs or game trees.
- Setup never deletes: preserve differing files under `.replaced/` before any
  explicitly requested replacement. Never overwrite shared files edited in place.
- Kickstart and Workbench sources must be supplied by the user (`TOSEC=`,
  `AMIGA_OS=`); never record mirror addresses for them.
- Scripts must run under macOS `/bin/bash` 3.2. Quote paths containing spaces.
- History belongs in git; update current-state documentation in place.
- Keep the two game variants separate; do not assume their code or timing matches.
- Agent instructions belong in `AGENTS.md`; `CLAUDE.md` only imports it.

## Read first

| Document | Purpose |
|---|---|
| `docs/open-work.md` | Current scope and deferred work |
| `docs/development.md` | Inputs, setup and shared environment |
| `docs/internals.md` | Verified knowledge and unknowns |
| AmigaXDev `docs/playbooks/new-game-playbook.md` | WHDLoad workflow and validation |
| AmigaXDev `docs/environment.md` | Shared tools and variables |
| AmigaXDev `docs/reference/measurement-method.md` | Measurement discipline |
| AmigaXDev `docs/reference/validation-harness.md` | Correctness checks |
