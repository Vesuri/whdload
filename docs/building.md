# Building

```sh
make slave            # release build
make verify           # VERIFY build: release plus instruments
make developer
make build BUILD=name # a build the game defines
make check            # the release build still gives release/slaves.sha256; game_check
make record           # write release/slaves.sha256 from the current release build
make clean
```

Every build goes to `tmp/build/<BUILD>/`: the slave (`<Variant>.Slave`; a run copies it
into the game drawer as `SLAVE_FILE`), its listing (`<Variant>.lst`, unless the defines name another with `-L`) and `<Variant>.deps`, the game files it was assembled from, which the
release packager uses for the shipped source. Without `VARIANT` every variant is built.

The default build assembles `SOURCE` with vasm against the shared WHDLoad 20.1 tree:

```
$VASM $VASM_FLAGS $DEFINES $DEFINES_<BUILD> -Isrc [-I<INCLUDES>] \
  -I$AMIGA_INCLUDE -I$WHDLOAD/Include -I$WHDLOAD/Src/sources -I$NDK
```

`VASM_FLAGS` defaults to `-m68000 -x -devpac -Fhunkexe -nosym`. The build defines are
none for `release`, `-DVERIFY=1` for `verify` and `-DDEVELOPER=1` for `developer`; a game
sets `DEFINES_<BUILD>` to change one or add a build. `VASM_EXTRA` adds flags from the command line
for one build (`make verify VASM_EXTRA='-DTRACE=1 -L tmp/trace.lst'`), on top of the game's. A game whose build is more than one
vasm call defines `game_build BUILD OUT` in `game.sh`, leaving `OUT/<Variant>.Slave`.

## Conventions

These follow AmigaXDev's WHDLoad playbook §10; the playbook has the reasons.

- The default (every option off) is the original game's experience, working correctly on
  every machine the slave supports. Bug fixes are therefore always on, with no option:
  broken drawing, sound or timing on faster CPUs (blitter waits, self-modifying code under
  caches, CPU-timed DMA waits), crashes, and the like. A fix keeps the original's behaviour
  where the original worked; say in `docs/internals.md` what it repairs.
- Gate every enhancement (a higher frame rate, changed game speed, trainers, anything a
  player would notice beyond the repair) behind a `CUSTOMn` option declared in
  `slv_config`. With it off, the bytes it would change are the fixed default's, and a
  check proves it.
- Instruments (fixtures, RNG pinning, unit tests) are in the VERIFY build only.
- Declare the lowest `slv_Version` the slave really needs.
- The release version is the slave's `DECL_VERSION`/`$VER` string (`2.0b`), not
  `ws_Version`. A `b` suffix marks a beta until play-testing is done.
- Compare a rebuilt slave with the shipped one by behaviour, and say what was compared.

## Byte identity across shared changes

`release/slaves.sha256` records each game's release slaves. A change to `common/` must
leave every game's `make check` passing; `make check` at the root runs them all. A change
to a game's own source updates its record with `make record` in the same commit.
