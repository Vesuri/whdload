# Upstream slaves

Every game here improves a slave someone else made. That work stays credited and traceable.

## Credit

- `AUTHOR` in `game.conf` names the original slave's maintainer: the maintainer of its
  source repository when there is one (JOTD's or StingRay's repositories), otherwise the
  authors its ReadMe or slave names.
- `UPSTREAM` records where the source came from: a repository URL, path and commit, or
  `none` when the original shipped without source and `src/` is a reconstruction.
- The game's `AGENTS.md`, its release ReadMe and its GitHub release notes name the original
  author. The release ReadMe keeps the original credits and history; the new entry goes above.
- Source files taken from upstream keep their headers.

## Bringing a game in

A game comes in with its history from the first commit of this work, rewritten into
`games/<Game>/`, followed by one commit that moves it onto this layout.

- **A standalone project** (its own repository) comes in whole: every commit, every tool.
  The restructuring commit moves the slave source to `src/`, the harness to `tools/`,
  the docs to `docs/`, the release text to `release/`, writes `game.conf`, and replaces
  its run and build scripts with `common/` where they did nothing game-specific.
- **A fork branch** (JOTD's or StingRay's repository) comes in from the first commit of
  this work on the branch: the commits after the upstream merge base, limited to the game's
  directory, with that directory becoming `src/`. `UPSTREAM` records the repository, path
  and merge-base commit. Files the work kept outside git (a harness under an ignored
  `tmp/`) come in with the restructuring commit, after checking that none of them holds
  game or ROM bytes.

After the move the game must still build the same release bytes as before (`make record`
then records them), boot with `make run`, and pass `make check` with no game or ROM files
tracked.

### Procedure

1. **Check the source.** Its `git status` is clean (uncommitted work stays behind, so ask
   first). Scan the history that will come in for files that must never be published:
   `git log --all --format= --name-only` against the copyrighted and built extensions,
   and `git log -p` for home-directory paths and work identities.
2. **Rewrite the history** in a scratch clone under the ignored `tmp/import/`, never in
   the source.
   - A standalone project: `git filter-repo --to-subdirectory-filter games/<Game>`, then
     fetch the result and `git merge --allow-unrelated-histories --no-ff` it, message
     `Import <Title> with its history`.
   - A fork: `git filter-repo --path <game dir>/ --path-rename <game dir>/source/:games/<Game>/src/
     --path-rename <game dir>/:games/<Game>/release/` (the slave source to `src/`, the
     shipped ReadMe, Install script and icons to `release/`; adjust to the directory's
     layout). The commit map (`.git/filter-repo/commit-map`) gives the rewritten form of
     the merge base's state and of each of our commits after it. On a branch from `main`,
     commit that merge-base state as `Import <Title> slave source from <repository> at
     <commit> (by <maintainer>)`, then `git cherry-pick` our rewritten commits in order,
     which keeps their authors, dates and messages. Upstream commits before the merge base
     stay out.
3. **Record the baseline**: build every slave and the VERIFY builds with the project's own
   build, from a `git archive` of the imported tree under `tmp/baseline/` (a VERIFY build
   may overwrite the release file name; build them separately). Pass the shared
   `WHDLOAD=$WHDLOAD`: old makefiles may default to a retired versioned tree.
4. **Restructure** in one commit:
   - slave source (everything the assembler reads, VERIFY modules included) to `src/`;
     include bridges stay where `INCLUDES` finds them;
   - `game.conf` reproduces every slave the project built as a variant, with the same
     flags, include order and defines; `game.sh` only where needed (`game_build` for
     generated sources, `game_dist` for a custom packager, `game_check` for unit tests);
   - delete what `common/` replaces: `amiga/run.sh`, `amiga/env.sh`, the slave makefile,
     the project `.gitignore` and `CLAUDE.md`. Game-specific launchers move to `tools/` and
     call `common/run.sh`, with a target in the game's `Makefile`;
   - tools: `whdload/` becomes `src/`; built slaves come from `tmp/build/<BUILD>/<Variant>.Slave`
     via `make slave|verify VARIANT=...` (one variant when a listing path is given);
     `amiga/.run` becomes `tmp/run/<INSTANCE or default>/.run`; gdb servers use
     `common/tools/game_server.py`; sourcing `amiga/env.sh` becomes `../../common/env.sh`;
     vasm working directories and `-L` paths are relative to the game directory now; the
     original archives are in `tmp/archives/`; packagers write to `--dist` (the
     repository's `dist/`), keep their logs in the game's `tmp/`, and judge dirtiness by
     `git status -- .`; `NTSC_MODE` becomes `NTSC`;
   - docs: rewrite commands for the new targets (`make run SLAVE=original` boots the
     shipped slave, which the old `amiga/run.sh` did by default), keep the content; a new
     `AGENTS.md` in the template's form keeps the scope and the doc table, and the rules
     move to the root's.
5. **Verify**: `make unpack ARCHIVES=<the project's tmp>`, the release and VERIFY builds
   byte-identical to the baseline, `make record`, `make check` (with the unit tests),
   a boot through the game's server (`WARP=1 WINDOW=none`, `wait`, `shot`) reaching the
   game, every game-specific launcher, `make dist` into `dist/` (then delete the test
   output), `common/check.sh repo`, and both identity checks before committing.

## Following upstream

When upstream changes a slave we also changed, diff the recorded `UPSTREAM` commit against
the new one for that directory, apply the change to `src/`, and update `UPSTREAM`. When
upstream accepts our changes, the game's docs say so, and its release here can stop.
