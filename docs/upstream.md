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

## Following upstream

When upstream changes a slave we also changed, diff the recorded `UPSTREAM` commit against
the new one for that directory, apply the change to `src/`, and update `UPSTREAM`. When
upstream accepts our changes, the game's docs say so, and its release here can stop.
