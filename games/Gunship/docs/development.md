# Gunship development setup

The slave source is `src/` (`GunshipHD.s` and its `timing-*.i`, `blitter.i` and VERIFY-only
`verify.i` modules); it came from JOTD's repository (game.conf `UPSTREAM`). Paths below are
relative to `games/Gunship`, and the tools expect it as the working directory.

- Inputs, pinned in `inputs.sha256`: `Gunship.lha` (the WHDLoad installer, `GunshipHD/`),
  `Gunship_v1.2_0658.lha` (the installed PAL release, `Gunship/`) and
  `Gunship_v1.2_NTSC_1489.lha` (the installed NTSC release, `GunshipNTSC/`).
  `make unpack ARCHIVES=<directory>` verifies them into `tmp/archives/` and unpacks them into
  `tmp/game/`.
- Builds (`docs/building.md` at the root): `make slave` builds `Gunship` (PAL 0658) and
  `GunshipNTSC` (`-DGUNSHIP_NTSC=1`, NTSC 1489) into `tmp/build/release/`; `make verify`
  the VERIFY builds into `tmp/build/verify/`. Two development builds: `make build BUILD=input`
  (VERIFY plus `TIMING_INPUT`) and `make build BUILD=native` (`GUNSHIP_NATIVE`: the original
  loop without the timing runtime). Probe builds made by tools (`build_*_c.py`,
  `build_visibility_probe_c.sh`, `check_*_build.py`) write to `tmp/build/` or `tmp/c/`.
- `make check`: the release bytes match `release/slaves.sha256`, then the unit tests that need
  only the builds and the installed drawers (`game.sh` `GAME_CHECKS`, logs in `tmp/check-*.log`).
  Most other `tools/test_*.py` read fixtures, listings or memory dumps an earlier capture left
  in `tmp/` (`tmp/c/`, `tmp/prof/`, ...) and are run by hand after those captures.
- `make dist`: `release/release.json` repacks `Gunship.lha` with both slaves, the new ReadMe
  and Install, and the source the release builds were assembled from.
- Native FS-UAE for scripted runs: `$AMIGA_SHARE/fs-uae-mouse`, built by AmigaXDev
  `scripts/build-fsuae.sh fs-uae-mouse "$PWD/tools/patches/fsuae-mouse.patch"`. The patch adds
  `monitor mouse DX DY` (port-0 mouse counts, ~1 screenshot pixel each) and
  `monitor button N 0|1` to the harness commands; the menus need the mouse. Works with
  `JOY0=none`. The shared `$FSUAE_ARM` (2026-10-06) predates even the harness patch.

## Running

- `make run SLAVE=original`: the shipped slave, windowed, real speed, sound. `make run` builds
  and boots the release slave; `SLAVE=path` boots any slave; `WHD_ARGS` adds WHDLoad arguments.
  Boots `WHDLoad Gunship.slave PRELOAD` from a disposable copy of `tmp/game/Gunship/` in
  `tmp/run/default/.run/dh1`. `make run VARIANT=GunshipNTSC` boots the NTSC drawer in NTSC.
- Default machine `SETUP=a500-fast` (game.conf; `game.sh` `game_prepare`): the shared
  cycle-exact `a500` (68000, 512 KB chip) with 8 MB Zorro II fast RAM and no slow RAM. Shared
  setup names also work (`SETUP=a1200-fast`); `AMIGA_SETUP` does the same.
- `tools/gunship.py`: `Session(out, env)` boots `common/run.sh` as its own instance
  (`INSTANCE=session-<out under tmp/>`, so `tmp/run/session-.../.run`, `Session.run`; own
  runtime and port) on the native build in warp, `DETERMINISTIC=1`, `JOY0=none`; `fields`,
  `key`, `shot`, `profile`. Without `SLAVE` it boots the shipped slave. `session_a.py` and
  `session_b.py` are the same on pinned older emulator protocols.
- `tools/route.py OUT STEP...`: scripted keys, mouse moves, clicks, shots, profiles.
- `tools/flight_profile.py OUT`: the in-game route (T-74, four Continues, 1 2 3) and a
  500-field trace with F1 ×10; raw chunks plus `profile.pkl.gz` (amigaxdev.callprofile).
- `tools/dump_start.py OUT [CHECK]`: memory at the window start; `tools/layout.py MEMDIR` finds the
  live gamemule hunks and the KickEmu Kickstart (layout.json).
- `tools/attrib.py RUN MEMDIR OUT.pkl` + `tools/report_attrib.py`: Barto chunks by context (task
  stack vs supervisor), rebuilt task call stacks, library calls by LVO, level-3 handlers.
- `tools/report.py PROFILE MEMDIR`: self cycles by function (callprofile reduction).
- `tools/aprof_run.py OUT` (MACHINE=a1200-030/040/060, gunship.MACHINES): exact per-PC profile of
  the window on any 020+ CPU with `$AMIGA_SHARE/fs-uae-aprof-mouse` (AmigaXDev aprof patch +
  tools/patches/fsuae-mouse.patch = tools/patches/fsuae-aprof-mouse.patch); records game clocks.
  `tools/aprof_report.py OUT/window.prof OUT`, `tools/aprof_matrix.py RUN...`. aprof does not
  run on the 68000 (protocol error): use the Barto trace there.
- `tools/var_scan.py`, `tools/fps.py`: per-field memory scans; fps.py's D+4BB0 sampling is NOT a
  frame counter in flight (frames span 3-7 fields); count executions of +04496 instead.
- `tools/dis.sh START END [MEMDIR] [HUNKBASE]`: gamemule hunk-offset disassembly.
- `tools/boot_shots.py OUT FIELDS STEP`: screenshots every STEP fields from reset.
- `tools/check_rebuild.py` is A1's record: it compares the then-native rebuild with the shipped
  slave and reads per-archive file manifests (`tmp/archives/<archive>.files.json`) that
  `make unpack` does not write; it does not pass on the current source.
- `monitor fields N` runs N+1 vsyncs (it finishes the partial field first): route field numbers
  drift by one per call; the game's VBL counter (hunk 2 +$1C) is the true field count.
- `--uae_uaeboard=full+indirect` hangs the aprof-mouse build at reset; data caches work without it.
- gdb caches registers across `monitor fields`: `maintenance flush register-cache` before reading.

Boot on a500-fast: black while the game LZW-unpacks its data (~1000 fields), Microprose logo
~1000, title ~1500–5000, then a self-playing demo flight from ~5500 fields after reset.

Keep downloads, extracted data, builds and analysis beneath the ignored `tmp/`.
The installer's source drawer (`tmp/game/GunshipHD/source/`) is a reference input; edit only `src/`.
Every run mounts a disposable copy, preserving the pristine drawers.

Read AmigaXDev `docs/playbooks/new-game-playbook-jotd.md` before further work.
Current scope and remaining work are in `docs/open-work.md`.
