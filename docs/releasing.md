# Releasing

```sh
make dist             # inside games/<Game>, or GAME=<Game> at the root; FORCE=1 overwrites
make dist             # at the root without GAME: every game
```

`make dist` builds the release slaves and repacks the game's original installer archive,
named in `release/release.json`, into `dist/` at the root, next to a `.sha256`.
`common/tools/package_release.py` documents the format: members to replace (`build:<Variant>` or a file in the game), to add and to
remove, and optionally the archive's source drawer.

## Names

A release is the game's name with "Enhanced": "Stellar 7 Enhanced" in the release ReadMe's
title and `Short:` line, the GitHub release title and the games table of the root
`README.md`. The installed drawer and the slave keep their original names, so the new slave
replaces the old one in an existing installation.

Each game ships one archive, its installer package (never a pre-installed game), named
`<Game>Enhanced-<version>-<YYYYMMDD>.lha`: `<Game>` is the game's directory name, and the
version and date come from the first release slave's `$VER` string, which every release
slave carries as `$VER: <name> <version> (dd.mm.yyyy)`. In `release.json` that is
`"output": "<Game>Enhanced-{version}-{date}.lha"`; a game's own packager uses
`version_of` and `date_of` from `common/tools/package_release.py`.

The installed icon enables the enhancements by default (the tooltypes the slave needs, or
the installer writing them); the original behaviour stays one option away.

## Checks

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

A release is a lightweight tag, the archive's name without `.lha`
(`WingCommanderEnhanced-2.0b-20261019`), on the commit it was built from. The archive and
its `.sha256` from `dist/` are attached to a GitHub release of that tag under the Vesuri
account:

- title: the release ReadMe's title line, `<Title> Enhanced <version> (dd.mm.yyyy)`
  (`Wing Commander Enhanced 2.0b (19.10.2026)`);
- notes: the ReadMe's change points for that version only. The original author and the
  requirements are not version-specific; the game's ReadMe and docs carry them.
