# Legends of Valour

A performance and timing rework of the 1992 US Gold / Synthetic Dimensions game under
WHDLoad: rendering patches always on, frame-independent game timing (CUSTOM2 bit 6, on in
the release's installed icon), one-degree mouse precision. CFou!'s v1.0 slave (06.02.2005, `LegendsOfValour_v1.0_0837.lha`) is
credited as the original (`game.conf` `AUTHOR`, `UPSTREAM`): `src/LegendsOfValourHD.s`
reconstructs it from the binary on WHDLoad 20.0's kick13 example. There is no game source:
work from cycle-exact FS-UAE traces and disassembly. The game is `data/AMIGA2`, a
PowerPacker-crunched 17-hunk executable that `tools/unpack.py` decrunches into
`tmp/unpacked/AMIGA2`; every change ships as slave patches.

The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | current state and what is still open |
| `docs/profiling.md` | running, driving and tracing the game, the machines, any performance number |
| `docs/performance-patches.md` | the rendering pipeline, game time, W1–W6 hooks and invariants, before changing rendering code |
| `docs/simulation-timing.md` | the optional game timing (CUSTOM2 bit 6) |
| `docs/one-degree-turning.md` | automatic mouse precision (developer CUSTOM2 bit 7) |
| `docs/releasing.md` | the release archive (`make dist`) |
| `README.md` | the summary, setup, how to play, the release options |

The slave source is `src/` (VERIFY-only fixtures included, Kalms C2P in `src/kalms/`, the
vendored `src/whdload/kick13.s`); `tools/` is the development harness and never ships.
Addresses in docs are `hN:OFFSET` offsets into hunk N of the decrunched AMIGA2,
`slave+OFFSET` slave code-hunk offsets, or `kick:` ROM addresses. Captures use `JOY0=none`
(the host mouse feeds port 0) and run one at a time as `INSTANCE=cap`, apart from
interactive `make run` sessions: never stop an interactive emulator.
