# Releasing

```sh
make dist             # inside games/<Game>, or GAME=<Game> at the root; FORCE=1 overwrites
make dist             # at the root without GAME: every game
```

`make dist` builds the release slaves and repacks each original archive named in
`release/release.json` into `dist/` at the root, next to a `.sha256`. The archive is named
after the version in the slave's `$VER` string. `common/tools/package_release.py` documents
the format: members to replace (`build:<Variant>` or a file in the game), to add and to
remove, and optionally the archive's source drawer.

What the packager enforces, after AmigaXDev's WHDLoad playbook §13:

- The release has the previous release's members, with only the declared ones changed.
  Every other member is byte-identical to the original; replaced slaves and ReadMes differ.
- Source ships only where the original shipped source, and then exactly the `src/` files the
  release build was assembled from (`tmp/build/release/<Variant>.deps`).
- LHa for UNIX, level-1 headers, lh5 (`a1o5q2`); the result must pass `lha t` and extract
  to exactly the staged files.
- A replaced ReadMe mentions the version.

Before packaging:

- `release/ReadMe` is the original ReadMe with the new entry above the previous author's,
  its requirements line matching the slave header. The original author's credits and
  history stay.
- Test the release slave on the machines in `SETUPS`; the packager checks the archive, not
  gameplay.
- A game whose release needs more (icon tooltypes, a rewritten installer) defines
  `game_dist DIST` in `game.sh`; it must make the same checks.

## Publishing

A release is tagged `<Game>/v<version>` on the commit it was built from, and the archives
from `dist/` are attached to a GitHub release of that tag under the Vesuri account. The
release notes name the original slave's author and what changed.
