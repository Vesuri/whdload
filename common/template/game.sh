# games/<Game>/game.sh: optional hooks for what game.conf cannot express. Sourced after
# game.conf and the shared environment by every common/ script. Delete what is unused,
# or the whole file.
#
# game_build BUILD OUT     replace the vasm build; leave OUT/$SLAVE_FILE and OUT/$VARIANT.deps
# game_prepare             before a run builds or boots (set SLAVE, FSUAE, AMIGA_SETUP, ...)
# game_drives DH0 DH1      add to or change the boot drives
# game_setup               edit FSUAE_SETUP_ARGS after the named machine is applied
# GAME_FSUAE_ARGS=(...)    extra FS-UAE arguments
# game_unpack              install the game into tmp/game/ from the verified tmp/archives/
# game_dist DIST           package the release into DIST instead of release/release.json
# game_check               the game's own checks (tools/ tests), run by make check
